import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset, AssetAuthorization
from app.schemas.authorization import AuthorizationStatus
from app.models.scan import Scan
from app.models.finding import Finding, FindingEvidence
from app.models.remediation import RemediationProposal, RemediationApplication
from app.models.verification import VerificationJob, VerificationComparison, VerificationRegressionCheck
from app.schemas.verification import (
    VerificationJobStatus,
    VulnerabilityVerificationStatus,
    RegressionCheckStatus,
    ScannerVerificationStatus,
    VerificationPolicyVerdict,
    VerificationReviewDecision,
)
from app.services.evidence_comparison_engine import EvidenceComparisonEngine
from app.services.regression_runner import RegressionRunner
from app.services.verification_policy import VerificationPolicyEngine
from app.services.verification_service import VerificationService, VerificationServiceException


async def setup_stage9_test_context(db_session: AsyncSession):
    """Sets up workspace, members, asset, authorization, finding, and remediation proposal/app."""
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    viewer_id = uuid.uuid4()

    owner = Profile(id=owner_id, firebase_uid=f"fb-owner-{owner_id.hex[:6]}", email="owner@stage9.io", display_name="Owner")
    admin = Profile(id=admin_id, firebase_uid=f"fb-admin-{admin_id.hex[:6]}", email="admin@stage9.io", display_name="Admin")
    viewer = Profile(id=viewer_id, firebase_uid=f"fb-viewer-{viewer_id.hex[:6]}", email="viewer@stage9.io", display_name="Viewer")
    db_session.add_all([owner, admin, viewer])

    ws_id = uuid.uuid4()
    ws = Workspace(id=ws_id, name="Stage 9 Verification Workspace", slug=f"stage9-{ws_id.hex[:6]}", owner_id=owner_id)
    db_session.add(ws)

    m1 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=owner_id, role="owner")
    m2 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=admin_id, role="admin")
    m3 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=viewer_id, role="viewer")
    db_session.add_all([m1, m2, m3])

    asset_id = uuid.uuid4()
    asset = Asset(
        id=asset_id,
        workspace_id=ws_id,
        name="Production Auth Service",
        type="repository",
        connection_config={"target": "github.com/org/auth-service"},
        criticality="critical",
        created_by=owner_id,
    )
    db_session.add(asset)

    auth = AssetAuthorization(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        authorization_type="ownership",
        status=AuthorizationStatus.AUTHORIZED.value,
    )
    db_session.add(auth)

    scan_id = uuid.uuid4()
    scan = Scan(
        id=scan_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_type="code",
        status="completed",
        triggered_by=owner_id,
    )
    db_session.add(scan)

    finding_id = uuid.uuid4()
    finding = Finding(
        id=finding_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan_id,
        source="semgrep",
        source_rule_id="python.jwt.hardcoded-jwt-secret",
        title="Hardcoded JWT Secret Key",
        description="JWT secret string is committed directly in source code.",
        severity="critical",
        confidence="high",
        cwe_ids=["CWE-798"],
        owasp_categories=["A07:2021"],
        location={"file_path": "auth/tokens.py", "line_start": 42, "line_end": 44},
        code_snippet="JWT_SECRET = 'hardcoded-insecure-secret-key-123'",
        status="open",
    )
    db_session.add(finding)

    evidence = FindingEvidence(
        id=uuid.uuid4(),
        finding_id=finding_id,
        workspace_id=ws_id,
        evidence_type="ast_match",
        title="Hardcoded Secret Match",
        file_path="auth/tokens.py",
        line_start=42,
        line_end=44,
        content={"secret_entropy": 4.5},
    )
    db_session.add(evidence)

    # Remediation proposal
    proposal_id = uuid.uuid4()
    proposal = RemediationProposal(
        id=proposal_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        finding_id=finding_id,
        proposal_title="Load JWT Secret from Environment",
        problem_summary="Hardcoded secret allows token forgery.",
        proposed_solution="Read secret from os.environ with fallback guard.",
        rationale="Follows 12-factor application secrets management.",
        title="Load JWT Secret from Environment",
        description="Read secret from os.environ with fallback guard.",
        affected_files=["auth/tokens.py"],
        patch_hash="abc123hash",
        status="APPLIED",
        version=1,
    )
    db_session.add(proposal)

    # Remediation application
    app_id = uuid.uuid4()
    application = RemediationApplication(
        id=app_id,
        proposal_id=proposal_id,
        workspace_id=ws_id,
        applied_by=admin_id,
        status="APPLIED",
        patch_hash="abc123hash",
        applied_diff="--- a/auth/tokens.py\n+++ b/auth/tokens.py\n@@ -42,1 +42,1 @@\n-JWT_SECRET = 'hardcoded-insecure-secret-key-123'\n+JWT_SECRET = os.environ['JWT_SECRET']",
        changed_files=["auth/tokens.py"],
        verification_status="VERIFICATION_PENDING",
    )
    db_session.add(application)

    await db_session.commit()

    return {
        "owner": owner,
        "admin": admin,
        "viewer": viewer,
        "workspace": ws,
        "asset": asset,
        "auth": auth,
        "finding": finding,
        "evidence": evidence,
        "proposal": proposal,
        "application": application,
    }


# ==============================================================================
# 1. Evidence Comparison Engine Tests
# ==============================================================================
def test_evidence_comparison_engine_categories():
    baseline = EvidenceComparisonEngine.extract_baseline_snapshot(
        finding_id="f-123",
        rule_id="python.jwt.hardcoded-jwt-secret",
        file_path="auth/tokens.py",
        line_start=42,
        line_end=44,
        code_snippet="JWT_SECRET = 'hardcoded-secret'",
    )

    # A. Clean Fix: No matching findings in rescan
    cat, ev, shift, sim, expl = EvidenceComparisonEngine.compare(
        baseline=baseline,
        rescan_findings=[],
        affected_files=["auth/tokens.py"],
    )
    assert cat == VulnerabilityVerificationStatus.NO_LONGER_DETECTED.value
    assert "NO LONGER DETECTED" in expl

    # B. Still Present: Same rule, same file, same line & snippet
    still_present_findings = [
        {
            "rule_id": "python.jwt.hardcoded-jwt-secret",
            "file_path": "auth/tokens.py",
            "location": {"file_path": "auth/tokens.py", "line_start": 42},
            "code_snippet": "JWT_SECRET = 'hardcoded-secret'",
        }
    ]
    cat, ev, shift, sim, expl = EvidenceComparisonEngine.compare(
        baseline=baseline,
        rescan_findings=still_present_findings,
        affected_files=["auth/tokens.py"],
    )
    assert cat == VulnerabilityVerificationStatus.STILL_PRESENT.value
    assert "STILL PRESENT" in expl

    # C. Modified / Moved: Same rule, shifted by 50 lines
    moved_findings = [
        {
            "rule_id": "python.jwt.hardcoded-jwt-secret",
            "file_path": "auth/tokens.py",
            "location": {"file_path": "auth/tokens.py", "line_start": 120},
            "code_snippet": "ALT_SECRET = 'hardcoded-secret-moved'",
        }
    ]
    cat, ev, shift, sim, expl = EvidenceComparisonEngine.compare(
        baseline=baseline,
        rescan_findings=moved_findings,
        affected_files=["auth/tokens.py"],
    )
    assert cat == VulnerabilityVerificationStatus.MODIFIED_OR_MOVED.value
    assert "shifted" in expl or "modified" in expl

    # D. Possible Regression: New flaw introduced in affected file
    regression_findings = [
        {
            "rule_id": "python.lang.security.insecure-eval",
            "file_path": "auth/tokens.py",
            "location": {"file_path": "auth/tokens.py", "line_start": 50},
            "code_snippet": "eval(token_payload)",
        }
    ]
    cat, ev, shift, sim, expl = EvidenceComparisonEngine.compare(
        baseline=baseline,
        rescan_findings=regression_findings,
        affected_files=["auth/tokens.py"],
    )
    assert cat == VulnerabilityVerificationStatus.POSSIBLE_REGRESSION.value

    # E. Incomplete baseline -> UNCOMPARABLE
    cat, ev, shift, sim, expl = EvidenceComparisonEngine.compare(
        baseline={},
        rescan_findings=[],
    )
    assert cat == VulnerabilityVerificationStatus.UNCOMPARABLE.value


# ==============================================================================
# 2. Regression Runner Tests
# ==============================================================================
def test_regression_runner_checks():
    # Valid Python
    valid_py = "import os\ndef get_secret():\n    return os.environ.get('SECRET')\n"
    res = RegressionRunner.check_syntax("auth/tokens.py", valid_py)
    assert res["status"] == RegressionCheckStatus.PASS.value

    # Invalid Python syntax
    invalid_py = "def broken(:\n    return"
    res_inv = RegressionRunner.check_syntax("auth/tokens.py", invalid_py)
    assert res_inv["status"] == RegressionCheckStatus.FAIL.value

    # Dangerous patterns
    dangerous_py = "import os\nos.system('rm -rf /')"
    res_dang = RegressionRunner.check_security_invariants("cleanup.py", dangerous_py)
    assert res_dang["status"] == RegressionCheckStatus.FAIL.value

    # Boundary integrity
    res_bound_pass = RegressionRunner.check_boundary_integrity(
        changed_files=["auth/tokens.py"],
        approved_files=["auth/tokens.py"],
    )
    assert res_bound_pass["status"] == RegressionCheckStatus.PASS.value

    res_bound_fail = RegressionRunner.check_boundary_integrity(
        changed_files=["auth/tokens.py", "config/database.py"],
        approved_files=["auth/tokens.py"],
    )
    assert res_bound_fail["status"] == RegressionCheckStatus.BLOCKED.value


# ==============================================================================
# 3. Deterministic Policy Engine Tests (verification-policy-v1)
# ==============================================================================
def test_verification_policy_engine_rules():
    clean_checks = [
        {"check_name": "syntax", "status": "PASS", "output_summary": "clean"},
        {"check_name": "boundary", "status": "PASS", "output_summary": "clean"},
    ]

    # Rule: Clean fix -> VERIFIED_CANDIDATE
    verdict, reasons, reg_status = VerificationPolicyEngine.evaluate(
        vulnerability_status=VulnerabilityVerificationStatus.NO_LONGER_DETECTED.value,
        scanner_status=ScannerVerificationStatus.COMPLETED.value,
        regression_checks=clean_checks,
        test_status="PASS",
    )
    assert verdict == VerificationPolicyVerdict.VERIFIED_CANDIDATE.value
    assert reg_status == "PASS"

    # Rule: Vulnerability still present -> FAILED
    verdict, reasons, _ = VerificationPolicyEngine.evaluate(
        vulnerability_status=VulnerabilityVerificationStatus.STILL_PRESENT.value,
        scanner_status=ScannerVerificationStatus.COMPLETED.value,
        regression_checks=clean_checks,
    )
    assert verdict == VerificationPolicyVerdict.FAILED.value

    # Rule: Regression check failed -> FAILED
    failing_checks = [
        {"check_name": "syntax", "status": "FAIL", "output_summary": "SyntaxError"},
    ]
    verdict, reasons, _ = VerificationPolicyEngine.evaluate(
        vulnerability_status=VulnerabilityVerificationStatus.NO_LONGER_DETECTED.value,
        scanner_status=ScannerVerificationStatus.COMPLETED.value,
        regression_checks=failing_checks,
    )
    assert verdict == VerificationPolicyVerdict.FAILED.value

    # Rule: Scanner incomplete -> FAILED or BLOCKED
    verdict, reasons, _ = VerificationPolicyEngine.evaluate(
        vulnerability_status=VulnerabilityVerificationStatus.NO_LONGER_DETECTED.value,
        scanner_status=ScannerVerificationStatus.FAILED.value,
        regression_checks=clean_checks,
    )
    assert verdict == VerificationPolicyVerdict.FAILED.value


# ==============================================================================
# 4. End-to-End Verification Service & Mandatory Human Sign-Off
# ==============================================================================
@pytest.mark.asyncio
async def test_verification_service_workflow_and_finding_closure(db_session: AsyncSession):
    ctx = await setup_stage9_test_context(db_session)
    service = VerificationService(db_session)

    # 1. Trigger verification for finding with applied remediation
    job = await service.trigger_verification(
        workspace_id=ctx["workspace"].id,
        finding_id=ctx["finding"].id,
        user_id=ctx["admin"].id,
        proposal_id=ctx["proposal"].id,
        application_id=ctx["application"].id,
        simulated_rescan_findings=[],  # Vulnerability resolved
    )

    assert job.status == VerificationJobStatus.PASSED_PENDING_REVIEW.value
    assert job.policy_verdict == VerificationPolicyVerdict.VERIFIED_CANDIDATE.value
    assert job.vulnerability_status == VulnerabilityVerificationStatus.NO_LONGER_DETECTED.value

    # CRITICAL INVARIANT: The finding MUST NOT be closed automatically!
    stmt = select(Finding).where(Finding.id == ctx["finding"].id)
    res = await db_session.execute(stmt)
    f_check = res.scalar_one()
    assert f_check.status == "open"
    assert f_check.fixed_at is None

    # 2. Reject verification sign-off
    review_rej = await service.review_verification(
        workspace_id=ctx["workspace"].id,
        job_id=job.id,
        reviewer_id=ctx["admin"].id,
        decision=VerificationReviewDecision.REJECTED.value,
        rationale="False positive fix; need further security analysis.",
    )
    assert review_rej.decision == "rejected"

    res = await db_session.execute(stmt)
    f_check2 = res.scalar_one()
    assert f_check2.status == "open"

    # 3. Accept verification sign-off (human operator closes the flaw)
    review_acc = await service.review_verification(
        workspace_id=ctx["workspace"].id,
        job_id=job.id,
        reviewer_id=ctx["admin"].id,
        decision=VerificationReviewDecision.ACCEPTED.value,
        rationale="Verified in independent rescan and unit tests; fix confirmed valid.",
    )
    assert review_acc.decision == "accepted"

    res = await db_session.execute(stmt)
    f_resolved = res.scalar_one()
    assert f_resolved.status == "fixed"
    assert f_resolved.fixed_at is not None


# ==============================================================================
# 5. RBAC Enforcement on Human Sign-Off
# ==============================================================================
@pytest.mark.asyncio
async def test_human_signoff_rbac_restriction(db_session: AsyncSession):
    ctx = await setup_stage9_test_context(db_session)
    service = VerificationService(db_session)

    job = await service.trigger_verification(
        workspace_id=ctx["workspace"].id,
        finding_id=ctx["finding"].id,
        user_id=ctx["admin"].id,
        proposal_id=ctx["proposal"].id,
        application_id=ctx["application"].id,
        simulated_rescan_findings=[],
    )

    # Viewer role CANNOT sign off on verification
    with pytest.raises(VerificationServiceException, match="Only workspace Admins and Security Engineers"):
        await service.review_verification(
            workspace_id=ctx["workspace"].id,
            job_id=job.id,
            reviewer_id=ctx["viewer"].id,
            decision=VerificationReviewDecision.ACCEPTED.value,
            rationale="Attempting sign-off without permission.",
        )


# ==============================================================================
# 6. API Endpoints & Multi-Tenant Workspace Isolation
# ==============================================================================
@pytest.mark.asyncio
async def test_verification_api_endpoints_and_isolation(client: AsyncClient, db_session: AsyncSession):
    ctx_a = await setup_stage9_test_context(db_session)

    # Tenant B setup
    user_b = Profile(id=uuid.uuid4(), firebase_uid="fb-tenant-b", email="b@stage9.io", display_name="Tenant B")
    ws_b = Workspace(id=uuid.uuid4(), name="Tenant B", slug=f"tb-{uuid.uuid4().hex[:6]}", owner_id=user_b.id)
    db_session.add_all([user_b, ws_b])
    mem_b = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="owner")
    db_session.add(mem_b)
    await db_session.commit()

    headers_admin_a = {"Authorization": f"Bearer test-token-{ctx_a['admin'].firebase_uid}"}
    headers_tenant_b = {"Authorization": f"Bearer test-token-{user_b.firebase_uid}"}

    # 1. Trigger verification via API for remediation
    res_trigger = await client.post(
        f"/api/v1/remediations/{ctx_a['proposal'].id}/verify?workspace_id={ctx_a['workspace'].id}",
        headers=headers_admin_a,
    )
    assert res_trigger.status_code == 201
    job_data = res_trigger.json()
    job_id = job_data["id"]
    assert job_data["status"] == "PASSED_PENDING_REVIEW"
    assert job_data["policy_verdict"] == "VERIFIED_CANDIDATE"

    # 2. Cross-workspace isolation: Tenant B cannot access Tenant A's verification job
    res_cross = await client.get(
        f"/api/v1/verifications/{job_id}?workspace_id={ws_b.id}",
        headers=headers_tenant_b,
    )
    assert res_cross.status_code == 404

    # 3. List verifications for Workspace A
    res_list = await client.get(
        f"/api/v1/verifications?workspace_id={ctx_a['workspace'].id}",
        headers=headers_admin_a,
    )
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # 4. Retrieve comparisons
    res_comp = await client.get(
        f"/api/v1/verifications/{job_id}/comparisons?workspace_id={ctx_a['workspace'].id}",
        headers=headers_admin_a,
    )
    assert res_comp.status_code == 200
    assert len(res_comp.json()) >= 1

    # 5. Retrieve regression checks
    res_checks = await client.get(
        f"/api/v1/verifications/{job_id}/checks?workspace_id={ctx_a['workspace'].id}",
        headers=headers_admin_a,
    )
    assert res_checks.status_code == 200
    assert len(res_checks.json()) >= 1

    # 6. Human Review Sign-Off via API
    res_review = await client.post(
        f"/api/v1/verifications/{job_id}/review?workspace_id={ctx_a['workspace'].id}",
        json={
            "decision": "accepted",
            "rationale": "Codebase rescan confirmed resolution and AST invariants are satisfied.",
        },
        headers=headers_admin_a,
    )
    assert res_review.status_code == 200
    assert res_review.json()["decision"] == "accepted"
    assert res_review.json()["finding_status_after"] == "fixed"

    # 7. Rerun verification via API
    res_rerun = await client.post(
        f"/api/v1/verifications/{job_id}/rerun?workspace_id={ctx_a['workspace'].id}",
        headers=headers_admin_a,
    )
    assert res_rerun.status_code == 200
    assert res_rerun.json()["id"] != job_id
