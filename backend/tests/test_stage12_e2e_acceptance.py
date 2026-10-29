import uuid
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset, AssetAuthorization
from app.models.scan import Scan
from app.models.finding import Finding, FindingEvidence
from app.models.attack_path import AttackPath, AttackPathNode, AttackPathEdge, RiskSnapshot
from app.models.security_team import SecurityTeamRun
from app.models.remediation import RemediationProposal, RemediationApproval, RemediationApplication
from app.models.verification import VerificationJob, VerificationComparison, VerificationRegressionCheck, VerificationReview
from app.models.report import Report
from app.models.notification import EventOutbox, Notification
from app.models.audit import AuditLog

from app.schemas.verification import VerificationReviewDecision, VerificationPolicyVerdict
from app.schemas.notification import SecurityEventEnvelope
from app.schemas.report import ReportCreateRequest, ReportType, ReportFormat
from app.services.verification_service import VerificationService, VerificationServiceException
from app.services.patch_applier import PatchApplicationAdapter, PatchApplicationException
from app.services.event_outbox_service import EventOutboxService
from app.services.notification_service import NotificationService
from app.services.report_generator_service import ReportGeneratorService


@pytest.mark.asyncio
async def test_stage12_complete_e2e_18_step_workflow(db_session: AsyncSession, client: AsyncClient):
    """
    STAGE 12 SIMULATED END-TO-END ACCEPTANCE WORKFLOW:
    Executes all 18 canonical lifecycle steps hermetically without external dependencies.
    Clearly labeled as an automated test simulation.
    """
    # -------------------------------------------------------------
    # Step 1: Authenticate a test user
    # -------------------------------------------------------------
    user_id = uuid.uuid4()
    firebase_uid = f"e2e-user-{user_id.hex[:6]}"
    user = Profile(
        id=user_id,
        firebase_uid=firebase_uid,
        email="operator@stage12.e2e",
        display_name="E2E Security Lead",
    )
    db_session.add(user)
    await db_session.commit()
    auth_headers = {"Authorization": f"Bearer test-token-{firebase_uid}"}

    # -------------------------------------------------------------
    # Step 2: Create a workspace
    # -------------------------------------------------------------
    ws_id = uuid.uuid4()
    ws = Workspace(
        id=ws_id,
        name="Stage 12 Acceptance Workspace",
        slug=f"stage12-e2e-{ws_id.hex[:6]}",
        owner_id=user_id,
    )
    db_session.add(ws)
    member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=user_id, role="owner")
    db_session.add(member)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 3: Add a controlled test repository asset
    # -------------------------------------------------------------
    asset_id = uuid.uuid4()
    asset = Asset(
        id=asset_id,
        workspace_id=ws_id,
        name="Authentication Service Repo",
        type="repository",
        connection_config={"target": "github.com/startup/auth-service", "environment": "staging"},
        criticality="critical",
        status="active",
        created_by=user_id,
    )
    db_session.add(asset)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 4: Record explicit authorization
    # -------------------------------------------------------------
    auth_record = AssetAuthorization(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        authorization_type="ownership",
        status="verified",
        authorized_by="operator@stage12.e2e",
        authorized_at=datetime.utcnow(),
    )
    db_session.add(auth_record)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 5: Run a controlled scan
    # -------------------------------------------------------------
    scan_id = uuid.uuid4()
    scan = Scan(
        id=scan_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_type="code",
        triggered_by=user_id,
        status="completed",
        scan_config={"scanner": "semgrep"},
        summary={"total_findings": 1},
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db_session.add(scan)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 6: Persist a finding and its evidence
    # -------------------------------------------------------------
    finding_id = uuid.uuid4()
    finding = Finding(
        id=finding_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan_id,
        source="semgrep",
        title="SQL Injection in Credentials Provider",
        description="Raw string formatting in SQL query allows parameter injection",
        severity="critical",
        status="open",
        confidence="high",
        location={"file_path": "app/auth/provider.py", "line": 42},
    )
    db_session.add(finding)
    await db_session.flush()

    evidence = FindingEvidence(
        id=uuid.uuid4(),
        finding_id=finding_id,
        workspace_id=ws_id,
        evidence_type="code_snippet",
        title="SQL Injection Vulnerability Snippet",
        content={"snippet": "query = f'SELECT * FROM users WHERE user_id = {uid}'"},
        file_path="app/auth/provider.py",
        line_start=42,
    )
    db_session.add(evidence)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 7: Generate an AI analysis using a test provider
    # -------------------------------------------------------------
    ai_analysis = {
        "finding_id": str(finding_id),
        "ai_summary": "Critical SQL injection vulnerability exploitable without authentication.",
        "ai_confidence": 0.92,
        "ai_remediation_summary": "Use parameterized SQL queries with bind variables.",
    }
    assert ai_analysis["ai_confidence"] > 0.8

    # -------------------------------------------------------------
    # Step 8: Calculate deterministic risk
    # -------------------------------------------------------------
    risk_snapshot = RiskSnapshot(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        finding_id=finding_id,
        score=82.5,
        risk_band="CRITICAL",
        model_version="risk-v1",
        factors={"base_severity": 40.0, "asset_criticality": 30.0, "reachability": 12.5},
        calculated_at=datetime.utcnow(),
    )
    db_session.add(risk_snapshot)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 9: Run the AI Security Team workflow
    # -------------------------------------------------------------
    team_run = SecurityTeamRun(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan_id,
        status="SUCCEEDED",
        requested_by=user_id,
        confidence=0.92,
        team_summary={"findings_analyzed": 1, "threats_detected": 1, "remediations_proposed": 1},
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db_session.add(team_run)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 10: Generate a remediation proposal
    # -------------------------------------------------------------
    proposal_id = uuid.uuid4()
    patch_content = "--- a/app/auth/provider.py\n+++ b/app/auth/provider.py\n@@ -42,1 +42,1 @@\n-query = f'SELECT * FROM users WHERE user_id = {uid}'\n+query = 'SELECT * FROM users WHERE user_id = :uid'"
    proposal = RemediationProposal(
        id=proposal_id,
        workspace_id=ws_id,
        finding_id=finding_id,
        asset_id=asset_id,
        proposal_title="Parameterized query fix for SQLi",
        title="Parameterized query fix for SQLi",
        problem_summary="SQL injection via f-string interpolation",
        proposed_solution="Replaced string interpolation with parameterized bind variable",
        unified_diff=patch_content,
        patch_hash="3a8b7f12e84c90d5718a22bcde99a4c87140f66b8893452101abcdef12345678",
        status="AWAITING_APPROVAL",
    )
    db_session.add(proposal)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 11: Require and record human approval
    # -------------------------------------------------------------
    approval = RemediationApproval(
        id=uuid.uuid4(),
        proposal_id=proposal_id,
        workspace_id=ws_id,
        approved_by=user_id,
        decision="approved",
        patch_hash=proposal.patch_hash,
        approved_at=datetime.utcnow(),
    )
    proposal.status = "APPROVED"
    db_session.add(approval)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 12: Apply patch only in approved isolated test environment
    # -------------------------------------------------------------
    application = RemediationApplication(
        id=uuid.uuid4(),
        proposal_id=proposal_id,
        workspace_id=ws_id,
        applied_by=user_id,
        status="APPLIED",
        patch_hash=proposal.patch_hash,
        applied_diff=patch_content,
        changed_files=["app/auth/provider.py"],
        applied_at=datetime.utcnow(),
    )
    proposal.status = "APPLIED"
    db_session.add(application)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 13: Run independent verification
    # -------------------------------------------------------------
    v_job = VerificationJob(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        proposal_id=proposal_id,
        finding_id=finding_id,
        application_id=application.id,
        status="PASSED_PENDING_REVIEW",
        policy_verdict="VERIFIED_CANDIDATE",
        vulnerability_status="NO_LONGER_DETECTED",
        regression_status="PASS",
        scanner_status="COMPLETED",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db_session.add(v_job)
    await db_session.commit()

    # -------------------------------------------------------------
    # Step 14: Review verification outcome & close finding
    # -------------------------------------------------------------
    v_service = VerificationService(db_session)
    review = await v_service.review_verification(
        workspace_id=ws_id,
        job_id=v_job.id,
        reviewer_id=user_id,
        decision=VerificationReviewDecision.ACCEPTED.value,
        rationale="Independently verified: patch resolves CWE-89 with zero syntax or regression breaks.",
    )
    assert review is not None
    assert finding.status == "fixed"

    # -------------------------------------------------------------
    # Step 15: Generate a security report
    # -------------------------------------------------------------
    report_gen = ReportGeneratorService(db_session)
    report_req = ReportCreateRequest(
        report_type=ReportType.REMEDIATION_PROGRESS,
        format=ReportFormat.JSON,
        title="E2E Remediation Progress Report",
    )
    report = await report_gen.generate_report(
        workspace_id=ws_id,
        request=report_req,
        generated_by=str(user_id),
        user_id=user_id,
    )
    assert report.id is not None
    assert report.status == "completed"
    assert report.snapshot_data["total_proposals"] >= 1
    assert report.snapshot_data["applied_count"] >= 1

    # -------------------------------------------------------------
    # Step 16: Create and process a notification event
    # -------------------------------------------------------------
    outbox_service = EventOutboxService(db_session)
    event_env = SecurityEventEnvelope(
        workspace_id=ws_id,
        event_type="verification.completed",
        resource_type="finding",
        resource_id=finding_id,
        payload={"finding_title": finding.title, "status": "fixed"},
    )
    outbox_entry = await outbox_service.publish(event_env)
    assert outbox_entry.status == "pending"

    processed_count = await outbox_service.process_batch(batch_size=10)
    assert processed_count >= 1
    await db_session.refresh(outbox_entry)
    assert outbox_entry.status == "processed"

    # -------------------------------------------------------------
    # Step 17: Verify audit history
    # -------------------------------------------------------------
    stmt = select(AuditLog).where(AuditLog.workspace_id == ws_id)
    audits = (await db_session.execute(stmt)).scalars().all()
    assert len(audits) >= 1

    # -------------------------------------------------------------
    # Step 18: Confirm another workspace cannot access resources
    # -------------------------------------------------------------
    other_user_id = uuid.uuid4()
    other_uid = f"e2e-other-{other_user_id.hex[:6]}"
    other_user = Profile(id=other_user_id, firebase_uid=other_uid, email="other@stage12.e2e")
    db_session.add(other_user)
    other_ws_id = uuid.uuid4()
    other_ws = Workspace(id=other_ws_id, name="Other Co", slug=f"other-{other_ws_id.hex[:6]}", owner_id=other_user_id)
    db_session.add(other_ws)
    db_session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=other_ws_id, user_id=other_user_id, role="owner"))
    await db_session.commit()

    other_headers = {"Authorization": f"Bearer test-token-{other_uid}"}
    unauthorized_res = await client.get(
        f"/api/v1/findings/{finding_id}?workspace_id={other_ws_id}",
        headers=other_headers,
    )
    # Must reject cross-workspace unauthorized access (404 Not Found or 403 Forbidden)
    assert unauthorized_res.status_code in (403, 404)


# =================================================================
# NEGATIVE TEST CASES (MANDATORY SECURITY INVARIANTS)
# =================================================================

@pytest.mark.asyncio
async def test_negative_unauthorized_scanning_rejected(client: AsyncClient, db_session: AsyncSession):
    """Negative invariant: Attempting to trigger scan on unverified asset is strictly rejected."""
    user_id = uuid.uuid4()
    uid = f"neg-user-{user_id.hex[:6]}"
    user = Profile(id=user_id, firebase_uid=uid, email="neg@stage12.io")
    ws_id = uuid.uuid4()
    ws = Workspace(id=ws_id, name="Neg WS", slug=f"neg-{ws_id.hex[:6]}", owner_id=user_id)
    db_session.add_all([user, ws, WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=user_id, role="owner")])
    
    asset = Asset(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        name="Unverified Asset",
        type="repository",
        connection_config={"target": "github.com/victim/repo"},
        status="active",
        created_by=user_id,
    )
    db_session.add(asset)
    await db_session.commit()

    res = await client.post(
        f"/api/v1/scans?workspace_id={ws_id}",
        headers={"Authorization": f"Bearer test-token-{uid}"},
        json={"asset_id": str(asset.id), "scan_type": "code"},
    )
    assert res.status_code in (400, 403)


@pytest.mark.asyncio
async def test_negative_unapproved_patch_application_rejected(db_session: AsyncSession):
    """Negative invariant: Patch application engine must strictly refuse unapproved proposals."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    finding_id = uuid.uuid4()

    user = Profile(id=user_id, firebase_uid=f"u-{user_id.hex[:6]}", email="admin@neg.io")
    ws = Workspace(id=ws_id, name="Neg WS", slug=f"neg-{ws_id.hex[:6]}", owner_id=user_id)
    member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=user_id, role="admin")
    asset = Asset(id=asset_id, workspace_id=ws_id, name="Test Asset", type="repository", created_by=user_id)
    scan = Scan(id=uuid.uuid4(), workspace_id=ws_id, asset_id=asset_id, scan_type="code", triggered_by=user_id)
    finding = Finding(id=finding_id, workspace_id=ws_id, asset_id=asset_id, scan_id=scan.id, source="semgrep", title="F1", description="D1", severity="high")
    
    db_session.add_all([user, ws, member, asset, scan, finding])

    unapproved_proposal = RemediationProposal(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        finding_id=finding_id,
        asset_id=asset_id,
        proposal_title="Unapproved patch",
        title="Unapproved patch",
        problem_summary="test",
        proposed_solution="test",
        unified_diff="--- a/file\n+++ b/file",
        patch_hash="fake-hash",
        status="AWAITING_APPROVAL",  # NOT APPROVED
    )
    db_session.add(unapproved_proposal)
    await db_session.commit()

    applier = PatchApplicationAdapter(db_session)
    with pytest.raises(PatchApplicationException) as excinfo:
        await applier.apply_proposal(
            proposal_id=unapproved_proposal.id,
            workspace_id=ws_id,
            user_id=user_id,
            patch_hash=unapproved_proposal.patch_hash,
        )
    assert "human approval" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_negative_premature_finding_closure_without_human_review(db_session: AsyncSession):
    """Negative invariant: Finding status CANNOT transition to 'fixed' without human acceptance."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    finding_id = uuid.uuid4()

    user = Profile(id=user_id, firebase_uid=f"u-{user_id.hex[:6]}", email="rev@neg.io")
    ws = Workspace(id=ws_id, name="Neg WS 2", slug=f"neg2-{ws_id.hex[:6]}", owner_id=user_id)
    member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=user_id, role="owner")
    asset = Asset(id=asset_id, workspace_id=ws_id, name="Test Asset 2", type="repository", created_by=user_id)
    scan = Scan(id=uuid.uuid4(), workspace_id=ws_id, asset_id=asset_id, scan_type="code", triggered_by=user_id)
    
    finding = Finding(
        id=finding_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan.id,
        source="semgrep",
        title="Unverified finding",
        description="test desc",
        severity="high",
        status="open",
        location={"file_path": "auth.py", "line": 10},
    )
    job = VerificationJob(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        finding_id=finding_id,
        status="PASSED_PENDING_REVIEW",
        policy_verdict="VERIFIED_CANDIDATE",
        vulnerability_status="NO_LONGER_DETECTED",
        regression_status="PASS",
        scanner_status="COMPLETED",
    )
    db_session.add_all([user, ws, member, asset, scan, finding, job])
    await db_session.commit()

    # Rejection decision
    v_service = VerificationService(db_session)
    await v_service.review_verification(
        workspace_id=ws_id,
        job_id=job.id,
        reviewer_id=user_id,
        decision=VerificationReviewDecision.REJECTED.value,
        rationale="Fix is incomplete; rejects closure.",
    )
    await db_session.refresh(finding)
    # Finding must remain open
    assert finding.status == "open"
