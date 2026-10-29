import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset, AssetAuthorization
from app.models.scan import Scan, AgentRun
from app.models.finding import Finding, FindingEvidence
from app.models.attack_path import AttackPath
from app.models.security_team import SecurityTeamRun
from app.schemas.security_team import (
    AgentRequest,
    AgentResponse,
    AgentStatus,
    ReconOutput,
    VulnerabilityAnalystOutput,
    AttackPathAnalystOutput,
    RiskAnalystOutput,
    TeamAssessment,
    CreateTeamRunRequest,
    HumanReviewRequest,
)
from app.services.security_agents import (
    AgentRegistry,
    ReconAgent,
    VulnerabilityAnalystAgent,
    AttackPathAgent,
    RiskAnalystAgent,
    SecurityReviewerAgent,
)
from app.services.security_team_orchestrator import SecurityTeamOrchestrator, MAX_AGENT_RETRIES
from app.services.security_team_context import (
    ReconContextBuilder,
    VulnerabilityContextBuilder,
    AttackPathContextBuilder,
    RiskContextBuilder,
    ReviewerContextBuilder,
)
from app.ai.fake import FakeAIProvider


async def create_stage7_fixture(db_session: AsyncSession):
    """Sets up a complete Stage 7 workspace, asset, scan, findings, and attack paths."""
    user_id = uuid.uuid4()
    profile = Profile(
        id=user_id,
        firebase_uid=f"firebase-{user_id}",
        email="lead_analyst@shadowops.io",
        display_name="Lead Analyst",
    )
    db_session.add(profile)

    ws_id = uuid.uuid4()
    workspace = Workspace(
        id=ws_id,
        name="Stage 7 Cloud Workspace",
        slug=f"stage7-ws-{ws_id.hex[:6]}",
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
        name="Payments Service",
        type="repository",
        criticality="critical",
        status="active",
        created_by=user_id,
        connection_config={"identifier": "github.com/shadowops/payments-api"},
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
    scan = Scan(
        id=scan_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_type="code",
        status="completed",
        triggered_by=user_id,
    )
    db_session.add(scan)

    # Add 2 findings
    f1_id = uuid.uuid4()
    f1 = Finding(
        id=f1_id,
        workspace_id=ws_id,
        scan_id=scan_id,
        asset_id=asset_id,
        source="semgrep",
        source_rule_id="semgrep.rules.sql_injection",
        title="SQL Injection in Payments DB",
        description="User parameters concatenated into raw SQL string.",
        severity="critical",
        confidence="high",
        cwe_ids=["CWE-89"],
        code_snippet="cursor.execute(f'SELECT * FROM accounts WHERE id = {acc_id}')",
        location={"file": "db/accounts.py", "start_line": 42, "end_line": 45},
        status="open",
    )
    db_session.add(f1)

    ev1 = FindingEvidence(
        id=uuid.uuid4(),
        finding_id=f1_id,
        workspace_id=ws_id,
        evidence_type="ast_match",
        title="Raw SQL Execution Pattern",
        file_path="db/accounts.py",
        line_start=42,
        line_end=45,
        content={"snippet": "cursor.execute(f'SELECT * FROM accounts WHERE id = {acc_id}')"},
    )
    db_session.add(ev1)

    f2_id = uuid.uuid4()
    f2 = Finding(
        id=f2_id,
        workspace_id=ws_id,
        scan_id=scan_id,
        asset_id=asset_id,
        source="semgrep",
        source_rule_id="semgrep.rules.hardcoded_jwt_secret",
        title="Hardcoded JWT Secret in Auth Module",
        description="Static secret used to sign authorization tokens.",
        severity="high",
        confidence="high",
        cwe_ids=["CWE-798"],
        code_snippet="JWT_SECRET = 'super-secret-key-12345'",
        location={"file": "auth/tokens.py", "start_line": 12, "end_line": 12},
        status="open",
    )
    db_session.add(f2)

    # Add an Attack Path
    path_id = uuid.uuid4()
    path = AttackPath(
        id=path_id,
        workspace_id=ws_id,
        scan_id=scan_id,
        name="Auth Token Bypass to Database Exfiltration",
        title="Auth Token Bypass to Database Exfiltration",
        description="Attacker leverages hardcoded JWT secret to forge tokens and reach SQL injection sink.",
        entry_point="auth/tokens.py",
        target_asset=asset.name,
        node_count=2,
        edge_count=1,
        risk_score=85.0,
        risk_band="CRITICAL",
        confidence=0.9,
        is_critical=True,
        status="active",
        factors={"findings_critical": 1},
        model_version="risk-v1",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(path)

    await db_session.commit()

    return {
        "user_id": user_id,
        "profile": profile,
        "workspace": workspace,
        "asset": asset,
        "scan": scan,
        "findings": [f1, f2],
        "attack_path": path,
    }


def test_agent_request_response_contract():
    """Verifies that AgentRequest and AgentResponse enforce required contract fields."""
    req = AgentRequest(
        agent_name="RECON_AGENT",
        workspace_id=uuid.uuid4(),
        context={"target": "github.com/shadowops/payments-api"},
    )
    assert req.agent_name == "RECON_AGENT"
    assert req.task == "Execute specialized analytical assessment."

    resp = AgentResponse(
        agent_name="RECON_AGENT",
        status=AgentStatus.SUCCEEDED,
        summary="Analysis complete",
        structured_output={"relevant_components": ["db/accounts.py"]},
        confidence=0.88,
        prompt_version="recon-v1",
    )
    assert resp.status == AgentStatus.SUCCEEDED
    assert resp.confidence == 0.88

    # Confidence range validation
    resp_valid = AgentResponse(
        agent_name="RECON_AGENT",
        status=AgentStatus.SUCCEEDED,
        summary="Validation test",
        confidence=1.0,
    )
    assert resp_valid.confidence == 1.0


def test_prompt_fencing_and_secret_redaction():
    """Verifies prompt fencing and that sensitive secrets are sanitized before agent ingestion."""
    raw_secrets = {
        "api_key": "AKIAIOSFODNN7EXAMPLE",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...",
    }
    asset_data = {
        "name": "API Gateway",
        "type": "repository",
        "criticality": "critical",
        "connection_config": raw_secrets,
        "description": "Payment microservice with secret key: AKIAIOSFODNN7EXAMPLE",
    }
    system_instruction, user_prompt = ReconContextBuilder.build(
        asset_data=asset_data,
        scan_data={"id": "scan-123", "scan_type": "code"},
        findings_summary=[],
    )
    assert "<system_instructions>" in system_instruction
    assert "<untrusted_security_data>" in user_prompt
    assert "<task>" in user_prompt
    # Confirm secrets redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in user_prompt
    assert "[REDACTED_AWS_KEY]" in user_prompt or "[REDACTED" in user_prompt


@pytest.mark.asyncio
async def test_specialized_agents_execution_with_fake_provider(db_session: AsyncSession):
    """Executes each of the 5 specialized agents independently and validates their structured outputs."""
    fixture = await create_stage7_fixture(db_session)
    provider = FakeAIProvider()

    # 1. Recon Agent
    recon_agent = ReconAgent()
    recon_ctx = {
        "asset": {
            "name": fixture["asset"].name,
            "type": fixture["asset"].type,
            "criticality": fixture["asset"].criticality,
            "connection_config": fixture["asset"].connection_config,
        },
        "scan": {"id": fixture["scan"].id, "scan_type": fixture["scan"].scan_type},
        "findings": [{"title": f.title, "severity": f.severity, "location": f.location} for f in fixture["findings"]],
    }
    recon_resp = await recon_agent.execute(
        AgentRequest(
            agent_name="recon",
            workspace_id=fixture["workspace"].id,
            context=recon_ctx,
        ),
        provider=provider,
    )
    assert recon_resp.status == AgentStatus.SUCCEEDED
    assert "relevant_components" in recon_resp.structured_output
    assert 0.0 <= recon_resp.confidence <= 1.0

    # 2. Vulnerability Analyst Agent
    vuln_agent = VulnerabilityAnalystAgent()
    vuln_ctx = {
        "findings": [
            {"id": str(f.id), "title": f.title, "severity": f.severity, "confidence": f.confidence, "cwe_ids": f.cwe_ids, "description": f.description}
            for f in fixture["findings"]
        ],
        "evidence": {
            str(fixture["findings"][0].id): [
                {"id": str(uuid.uuid4()), "file_path": "db/accounts.py", "line_start": 42, "line_end": 45, "title": "SQL Injection"}
            ]
        },
    }
    vuln_resp = await vuln_agent.execute(
        AgentRequest(
            agent_name="vulnerability_analyst",
            workspace_id=fixture["workspace"].id,
            context=vuln_ctx,
        ),
        provider=provider,
    )
    assert vuln_resp.status == AgentStatus.SUCCEEDED
    assert "interpretations" in vuln_resp.structured_output

    # 3. Attack Path Agent
    path_agent = AttackPathAgent()
    path_ctx = {
        "findings": [{"id": str(f.id), "title": f.title} for f in fixture["findings"]],
        "relationships": [],
        "attack_paths": [
            {
                "id": str(fixture["attack_path"].id),
                "title": fixture["attack_path"].title,
                "risk_score": 85.0,
                "risk_band": "CRITICAL",
                "entry_point": fixture["attack_path"].entry_point,
                "node_count": 2,
                "edge_count": 1,
                "description": fixture["attack_path"].description,
            }
        ],
    }
    path_resp = await path_agent.execute(
        AgentRequest(
            agent_name="attack_path",
            workspace_id=fixture["workspace"].id,
            context=path_ctx,
        ),
        provider=provider,
    )
    assert path_resp.status == AgentStatus.SUCCEEDED
    assert "candidate_relationships" in path_resp.structured_output

    # 4. Risk Analyst Agent
    risk_agent = RiskAnalystAgent()
    risk_ctx = {
        "attack_paths": [{"id": str(fixture["attack_path"].id), "risk_score": 85.0, "risk_band": "CRITICAL"}],
        "risk_factors": {"critical_findings": 1, "high_findings": 1},
        "peak_score": 85.0,
        "risk_band": "CRITICAL",
    }
    risk_resp = await risk_agent.execute(
        AgentRequest(
            agent_name="risk_analyst",
            workspace_id=fixture["workspace"].id,
            context=risk_ctx,
        ),
        provider=provider,
    )
    assert risk_resp.status == AgentStatus.SUCCEEDED
    assert "important_contributing_factors" in risk_resp.structured_output

    # 5. Security Reviewer Agent
    reviewer_agent = SecurityReviewerAgent()
    rev_ctx = {
        "recon_output": recon_resp.structured_output,
        "vulnerability_output": vuln_resp.structured_output,
        "attack_path_output": path_resp.structured_output,
        "risk_output": risk_resp.structured_output,
        "deterministic_score": 85.0,
        "deterministic_band": "CRITICAL",
        "findings_count": len(fixture["findings"]),
        "paths_count": 1,
    }
    rev_resp = await reviewer_agent.execute(
        AgentRequest(
            agent_name="security_reviewer",
            workspace_id=fixture["workspace"].id,
            context=rev_ctx,
        ),
        provider=provider,
    )
    assert rev_resp.status == AgentStatus.SUCCEEDED
    assert "executive_summary" in rev_resp.structured_output
    assert rev_resp.structured_output.get("review_status") == "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED"


@pytest.mark.asyncio
async def test_orchestrator_full_pipeline(db_session: AsyncSession):
    """
    Tests end-to-end execution of the multi-agent pipeline via SecurityTeamOrchestrator:
    - Runs all 5 agents sequentially
    - Produces a unified TeamAssessment
    - Records 5 AgentRun entries linked to the team_run
    - Enforces that scanner facts and deterministic risk remain unaltered
    """
    fixture = await create_stage7_fixture(db_session)
    provider = FakeAIProvider()
    orchestrator = SecurityTeamOrchestrator(session=db_session, provider=provider)

    created_run = await orchestrator.create_team_run(
        workspace_id=fixture["workspace"].id,
        asset_id=fixture["asset"].id,
        requested_by=fixture["user_id"],
        scan_id=fixture["scan"].id,
    )
    assert created_run.status == "QUEUED"

    team_run = await orchestrator.execute_team_run(created_run.id)

    assert team_run.status == "SUCCEEDED"
    assert team_run.completed_at is not None
    assert team_run.team_summary is not None
    assert team_run.team_summary.get("review_status") == "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED"
    assert "highest_priority_findings" in team_run.team_summary
    assert team_run.confidence > 0.0

    # Verify AgentRun records
    stmt = select(AgentRun).where(AgentRun.team_run_id == team_run.id)
    res = await db_session.execute(stmt)
    agent_runs = res.scalars().all()

    assert len(agent_runs) == 5
    agent_names = {r.agent_name for r in agent_runs}
    assert agent_names == {
        "recon",
        "vulnerability_analyst",
        "attack_path",
        "risk_analyst",
        "security_reviewer",
    }
    for ar in agent_runs:
        assert ar.status == "SUCCEEDED"
        assert ar.output != {}
        assert ar.tokens_input is not None

    # INVARIANT CHECK: Ground truth scanner severity in Finding was NOT mutated
    f1_check = await db_session.get(Finding, fixture["findings"][0].id)
    assert f1_check.severity == "critical"
    assert f1_check.status == "open"


@pytest.mark.asyncio
async def test_orchestrator_idempotency(db_session: AsyncSession):
    """Verifies that duplicate team run triggers return the existing active run without re-running."""
    fixture = await create_stage7_fixture(db_session)
    provider = FakeAIProvider()

    # Pre-insert an active RUNNING team run
    active_run = SecurityTeamRun(
        id=uuid.uuid4(),
        workspace_id=fixture["workspace"].id,
        asset_id=fixture["asset"].id,
        scan_id=fixture["scan"].id,
        status="RUNNING",
        requested_by=fixture["user_id"],
        orchestration_version="security-team-v1",
    )
    db_session.add(active_run)
    await db_session.commit()

    orchestrator = SecurityTeamOrchestrator(session=db_session, provider=provider)
    returned_run = await orchestrator.create_team_run(
        workspace_id=fixture["workspace"].id,
        asset_id=fixture["asset"].id,
        requested_by=fixture["user_id"],
        scan_id=fixture["scan"].id,
    )

    # Must return the existing active run
    assert returned_run.id == active_run.id
    assert returned_run.status == "RUNNING"


@pytest.mark.asyncio
async def test_cancellation_and_human_review(db_session: AsyncSession):
    """Tests run cancellation and the mandatory human review boundary."""
    fixture = await create_stage7_fixture(db_session)
    provider = FakeAIProvider()
    orchestrator = SecurityTeamOrchestrator(session=db_session, provider=provider)

    # 1. Test Cancellation
    queued_run = SecurityTeamRun(
        id=uuid.uuid4(),
        workspace_id=fixture["workspace"].id,
        asset_id=fixture["asset"].id,
        scan_id=fixture["scan"].id,
        status="QUEUED",
        requested_by=fixture["user_id"],
        orchestration_version="security-team-v1",
    )
    db_session.add(queued_run)
    await db_session.commit()

    canceled_run = await orchestrator.cancel_team_run(
        team_run_id=queued_run.id,
        user_id=fixture["user_id"],
    )
    assert canceled_run.status == "CANCELED"

    # 2. Test Human Review
    succeeded_run = SecurityTeamRun(
        id=uuid.uuid4(),
        workspace_id=fixture["workspace"].id,
        asset_id=fixture["asset"].id,
        scan_id=fixture["scan"].id,
        status="SUCCEEDED",
        requested_by=fixture["user_id"],
        orchestration_version="security-team-v1",
        team_summary={"review_status": "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED"},
    )
    db_session.add(succeeded_run)
    await db_session.commit()

    reviewed_run = await orchestrator.mark_human_reviewed(
        team_run_id=succeeded_run.id,
        user_id=fixture["user_id"],
        notes="Approved assessment. High priority patch assigned to engineering team.",
    )
    assert reviewed_run.reviewed_by == fixture["user_id"]
    assert reviewed_run.reviewed_at is not None
    assert "Approved assessment" in reviewed_run.review_notes


@pytest.mark.asyncio
async def test_security_team_api_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers,
):
    """
    Tests REST API endpoints for Security Team:
    - POST /api/v1/security-team/runs (Trigger run)
    - GET /api/v1/security-team/runs (List runs)
    - GET /api/v1/security-team/runs/{id} (Get run detail)
    - GET /api/v1/security-team/runs/{id}/agents (Get individual agent runs)
    - GET /api/v1/security-team/runs/{id}/assessment (Get structured assessment)
    - POST /api/v1/security-team/runs/{id}/review (Submit human review)
    - Cross-workspace isolation (Forbidden / Not Found for other workspace)
    """
    fixture = await create_stage7_fixture(db_session)
    headers = auth_headers(
        uid=fixture["profile"].firebase_uid,
        email=fixture["profile"].email,
    )

    # 1. Trigger Run
    resp = await client.post(
        "/api/v1/security-team/runs",
        headers=headers,
        json={
            "workspace_id": str(fixture["workspace"].id),
            "asset_id": str(fixture["asset"].id),
            "scan_id": str(fixture["scan"].id),
        },
    )
    assert resp.status_code == 201
    run_data = resp.json()
    assert run_data["status"] == "SUCCEEDED"
    run_id = run_data["id"]

    # 2. List Runs
    list_resp = await client.get(
        f"/api/v1/security-team/runs?workspace_id={fixture['workspace'].id}",
        headers=headers,
    )
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert any(r["id"] == run_id for r in runs)

    # 3. Get Run Detail
    detail_resp = await client.get(
        f"/api/v1/security-team/runs/{run_id}?workspace_id={fixture['workspace'].id}",
        headers=headers,
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["agent_runs"]) == 5

    # 4. Get Agent Runs
    agents_resp = await client.get(
        f"/api/v1/security-team/runs/{run_id}/agents?workspace_id={fixture['workspace'].id}",
        headers=headers,
    )
    assert agents_resp.status_code == 200
    agents = agents_resp.json()
    assert len(agents) == 5

    # 5. Get Assessment
    assessment_resp = await client.get(
        f"/api/v1/security-team/runs/{run_id}/assessment?workspace_id={fixture['workspace'].id}",
        headers=headers,
    )
    assert assessment_resp.status_code == 200
    assessment = assessment_resp.json()
    assert assessment["review_status"] == "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED"

    # 6. Submit Human Review
    review_resp = await client.post(
        f"/api/v1/security-team/runs/{run_id}/review?workspace_id={fixture['workspace'].id}",
        headers=headers,
        json={"notes": "Security architect signed off on SQL injection remediation plan."},
    )
    assert review_resp.status_code == 200
    reviewed_data = review_resp.json()
    assert reviewed_data["reviewed_by"] == str(fixture["user_id"])
    assert "signed off" in reviewed_data["review_notes"]

    # 7. Multi-Tenant Isolation: Another user/workspace CANNOT access this run
    other_uid = str(uuid.uuid4())
    other_headers = auth_headers(uid=other_uid, email="intruder@external.org")

    other_resp = await client.get(
        f"/api/v1/security-team/runs/{run_id}?workspace_id={fixture['workspace'].id}",
        headers=other_headers,
    )
    assert other_resp.status_code in (403, 404)
