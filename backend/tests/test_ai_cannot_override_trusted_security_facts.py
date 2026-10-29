import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember, Role
from app.models.asset import Asset, AssetAuthorization
from app.models.scan import Scan
from app.models.finding import Finding, FindingEvidence, FindingAIAnalysis
from app.ai.manager import AISecurityManager
from app.ai.provider import AIProvider, AIStructuredResponse, AIResponseMetadata
from app.ai.schemas import FindingAnalysisOutput, SupportingEvidenceItem


class AdversarialMockProvider(AIProvider):
    """
    Simulates an AI model that attempts to claim a critical finding is 'low' risk
    and tries to hallucinate invalid evidence IDs.
    """
    provider_name = "gemini"

    async def generate_text(self, prompt, system_instruction=None, config=None):
        raise NotImplementedError()

    async def generate_structured(self, prompt, response_schema, system_instruction=None, config=None):
        fake_data = FindingAnalysisOutput(
            summary="Attacker claims this is negligible and not a threat.",
            technical_explanation="Attempted adversarial downgrade of scanner truth.",
            impact="None, minimal impact claimed.",
            confidence=0.15,
            classification="Informational Notice",
            uncertainty="High uncertainty",
            supporting_evidence=[
                SupportingEvidenceItem(evidence_id="non-existent-fabricated-id-123", relevance="Fake evidence")
            ],
        )
        metadata = AIResponseMetadata(
            provider=self.provider_name,
            model="gemini-1.5-pro",
            prompt_tokens=100,
            completion_tokens=80,
            total_tokens=180,
            estimated_cost_usd=0.0001,
            latency_ms=30,
        )
        return AIStructuredResponse(
            parsed=fake_data,
            raw_json=fake_data.model_dump(),
            metadata=metadata,
        )


@pytest.mark.asyncio
async def test_ai_cannot_override_trusted_security_facts(db_session: AsyncSession):
    """
    MANDATORY SECURITY INVARIANT TEST:
    Verifies that under NO circumstances can AI Security Manager analysis:
    1. Overwrite or modify scanner severity (Level 1/2 trusted scanner facts).
    2. Mutate rule IDs, source types, or code locations.
    3. Retain hallucinated evidence IDs.
    """
    # 1. Setup workspace and authorized scan
    user_id = uuid.uuid4()
    profile = Profile(
        id=user_id,
        firebase_uid=f"firebase-{user_id}",
        email="lead_sec@shadowops.io",
        display_name="Lead Sec",
    )
    db_session.add(profile)

    ws_id = uuid.uuid4()
    workspace = Workspace(
        id=ws_id,
        name="Security Invariant WS",
        slug=f"sec-inv-{ws_id.hex[:6]}",
        owner_id=user_id,
        plan="enterprise",
    )
    db_session.add(workspace)

    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        user_id=user_id,
        role="owner",
    )
    db_session.add(member)

    asset_id = uuid.uuid4()
    asset = Asset(
        id=asset_id,
        workspace_id=ws_id,
        name="Core App",
        type="repository",
        criticality="high",
        status="active",
        created_by=user_id,
        connection_config={"identifier": "github.com/org/core-app"},
    )
    db_session.add(asset)

    authz = AssetAuthorization(
        id=uuid.uuid4(),
        asset_id=asset_id,
        workspace_id=ws_id,
        authorization_type="ownership",
        status="verified",
        verified_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db_session.add(authz)

    scan_id = uuid.uuid4()
    scan = Scan(id=scan_id, workspace_id=ws_id, asset_id=asset_id, scan_type="code", status="completed", triggered_by=user_id)
    db_session.add(scan)

    # 2. Trusted Scanner Finding (Level 1/2 Ground Truth)
    finding_id = uuid.uuid4()
    trusted_severity = "critical"
    trusted_rule_id = "semgrep.rules.rce_command_injection"
    trusted_snippet = "os.system(user_command)"
    trusted_location = {"file": "api/exec.py", "start_line": 88, "end_line": 90}

    finding = Finding(
        id=finding_id,
        workspace_id=ws_id,
        scan_id=scan_id,
        asset_id=asset_id,
        source="semgrep",
        source_rule_id=trusted_rule_id,
        title="Remote Command Injection via os.system",
        description="Untrusted user argument passed to shell.",
        severity=trusted_severity,
        confidence="high",
        cwe_ids=["CWE-78"],
        code_snippet=trusted_snippet,
        location=trusted_location,
        status="open",
    )
    db_session.add(finding)

    evidence_id = uuid.uuid4()
    evidence = FindingEvidence(
        id=evidence_id,
        finding_id=finding_id,
        workspace_id=ws_id,
        evidence_type="ast_match",
        title="Command Execution AST Node",
        file_path="api/exec.py",
        line_start=88,
        line_end=90,
        content={"matched_code": trusted_snippet},
    )
    db_session.add(evidence)
    await db_session.commit()

    # 3. Execute AI Security Manager with an adversarial downgrade provider
    adversarial_provider = AdversarialMockProvider()
    manager = AISecurityManager(session=db_session, provider=adversarial_provider)

    result = await manager.analyze_scan_findings(scan=scan, force=True)
    assert result["status"] == "completed"

    # 4. Reload finding directly from DB to verify immutable facts
    refetched_finding = await db_session.get(Finding, finding_id)
    assert refetched_finding is not None

    # INVARIANT CHECKS:
    # 1. Scanner severity MUST remain unchanged
    assert refetched_finding.severity == trusted_severity, (
        f"VIOLATION: Scanner severity was modified from '{trusted_severity}' to '{refetched_finding.severity}'"
    )

    # 2. Scanner source & rule MUST remain unchanged
    assert refetched_finding.source == "semgrep"
    assert refetched_finding.source_rule_id == trusted_rule_id

    # 3. Code snippet and location MUST remain unchanged
    assert refetched_finding.code_snippet == trusted_snippet
    assert refetched_finding.location == trusted_location

    # 4. Finding status MUST remain unchanged
    assert refetched_finding.status == "open"

    # 5. Check that AI analysis is recorded as advisory Level 3 data
    stmt = select(FindingAIAnalysis).where(FindingAIAnalysis.finding_id == finding_id)
    analysis_res = await db_session.execute(stmt)
    analysis = analysis_res.scalar_one_or_none()

    assert analysis is not None
    assert analysis.classification == "Informational Notice"
    assert analysis.confidence == 0.15

    # 6. Verify hallucinated evidence ID was filtered out
    supporting_eids = [e["evidence_id"] for e in analysis.supporting_evidence]
    assert "non-existent-fabricated-id-123" not in supporting_eids
