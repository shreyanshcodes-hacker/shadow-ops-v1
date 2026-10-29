import io
import json
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset, AssetAuthorization
from app.models.scan import Scan
from app.models.finding import Finding, FindingEvidence
from app.models.attack_path import AttackPath, RiskSnapshot
from app.models.remediation import RemediationProposal, RemediationApproval, RemediationApplication
from app.models.verification import VerificationJob, VerificationReview
from app.models.report import Report
from app.schemas.report import ReportType, ReportFormat, ReportCreateRequest
from app.services.dashboard_service import DashboardService
from app.services.report_generator_service import ReportGeneratorService, redact_sensitive_data
from app.services.report_export_service import ReportExportService


async def setup_stage10_test_context(db_session: AsyncSession):
    """Sets up rich workspace context with assets, scans, findings, risk snapshot, and verification data."""
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    viewer_id = uuid.uuid4()

    owner = Profile(id=owner_id, firebase_uid=f"fb-owner-{owner_id.hex[:6]}", email="owner@stage10.io", display_name="Stage10 Owner")
    admin = Profile(id=admin_id, firebase_uid=f"fb-admin-{admin_id.hex[:6]}", email="admin@stage10.io", display_name="Stage10 Admin")
    viewer = Profile(id=viewer_id, firebase_uid=f"fb-viewer-{viewer_id.hex[:6]}", email="viewer@stage10.io", display_name="Stage10 Viewer")
    db_session.add_all([owner, admin, viewer])

    ws_id = uuid.uuid4()
    ws = Workspace(id=ws_id, name="Stage 10 Security Ops", slug=f"stage10-{ws_id.hex[:6]}", owner_id=owner_id)
    db_session.add(ws)

    m1 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=owner_id, role="owner")
    m2 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=admin_id, role="admin")
    m3 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=viewer_id, role="viewer")
    db_session.add_all([m1, m2, m3])

    # Asset
    asset_id = uuid.uuid4()
    asset = Asset(
        id=asset_id,
        workspace_id=ws_id,
        name="Core Payments Gateway",
        type="repository",
        connection_config={"target": "github.com/startup/payments", "environment": "production"},
        criticality="critical",
        status="active",
        created_by=owner_id,
    )
    db_session.add(asset)

    auth = AssetAuthorization(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        authorization_type="ownership",
        status="verified",
        authorized_by="admin@stage10.io",
        authorized_at=datetime.now(timezone.utc),
    )
    db_session.add(auth)

    # Scan
    scan_id = uuid.uuid4()
    scan = Scan(
        id=scan_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_type="code",
        status="completed",
        triggered_by=admin_id,
        completed_at=datetime.now(timezone.utc),
        scan_config={"target": "main", "scanner": "semgrep"},
        summary={"total_findings": 2},
    )
    db_session.add(scan)

    # Finding 1: Critical JWT secret flaw
    f1_id = uuid.uuid4()
    f1 = Finding(
        id=f1_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan_id,
        source="semgrep",
        source_rule_id="python.jwt.hardcoded-jwt-secret",
        title="Hardcoded JWT Secret Token in Authentication Module",
        description="A static JWT signing secret was discovered in auth/jwt_service.py.",
        severity="critical",
        confidence="high",
        status="open",
        location={"file_path": "backend/auth/jwt_service.py", "line_start": 45, "line_end": 47},
        cwe_ids=["CWE-798"],
        owasp_categories=["A07:2021"],
    )
    db_session.add(f1)

    ev1 = FindingEvidence(
        id=uuid.uuid4(),
        finding_id=f1_id,
        workspace_id=ws_id,
        evidence_type="code_snippet",
        title="Static Token Assignment",
        file_path="backend/auth/jwt_service.py",
        line_start=45,
        line_end=47,
        content={"snippet": "JWT_SECRET = 'super-secret-api-key-12345678'\napiKey = 'my-fake-secret-9999'"},
    )
    db_session.add(ev1)

    # Finding 2: High SQL Injection flaw
    f2_id = uuid.uuid4()
    f2 = Finding(
        id=f2_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan_id,
        source="semgrep",
        source_rule_id="python.sqlalchemy.raw-sql-injection",
        title="Unsanitized SQL Query Parameter in User Lookup",
        description="String formatting is used to construct a SQL query.",
        severity="high",
        confidence="high",
        status="open",
        location={"file_path": "backend/services/user_repo.py", "line_start": 88, "line_end": 90},
        cwe_ids=["CWE-89"],
        owasp_categories=["A03:2021"],
    )
    db_session.add(f2)

    # Risk Snapshot
    risk_snap = RiskSnapshot(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        score=78.5,
        risk_band="CRITICAL",
        model_version="risk-v1",
        factors={"findings_count": 2, "critical_attack_paths": 1},
        calculated_at=datetime.now(timezone.utc),
    )
    db_session.add(risk_snap)

    # Attack Path
    ap = AttackPath(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        name="Public to Payments DB",
        title="Public Internet to Payments DB via Hardcoded JWT",
        risk_band="CRITICAL",
        is_critical=True,
        target_asset="payments_db",
        entry_point="internet",
        node_count=3,
        status="active",
    )
    db_session.add(ap)

    # Remediation Proposal
    rem_id = uuid.uuid4()
    rem = RemediationProposal(
        id=rem_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        finding_id=f1_id,
        source_scan_id=scan_id,
        status="applied",
        title="Load JWT Secret from Environment Variable",
        proposal_title="Load JWT Secret from Environment Variable",
        problem_summary="Hardcoded secret replaced with os.getenv('JWT_SECRET').",
        proposed_solution="Read secret securely from environment settings.",
        rationale="Eliminates credential leakage risk.",
        affected_files=["backend/auth/jwt_service.py"],
        patch_reference="diff --git a/backend/auth/jwt_service.py...",
        validation_results={"syntax_valid": True},
        created_by=admin_id,
        approved_by=admin_id,
        approved_at=datetime.now(timezone.utc),
        applied_by=admin_id,
        applied_at=datetime.now(timezone.utc),
    )
    db_session.add(rem)

    # Verification Job (Stage 9)
    v_job = VerificationJob(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        finding_id=f1_id,
        proposal_id=rem_id,
        status="PASSED_PENDING_REVIEW",
        vulnerability_status="NO_LONGER_DETECTED",
        regression_status="PASS",
        scanner_status="COMPLETED",
        test_status="PASS",
        policy_verdict="VERIFIED_CANDIDATE",
        policy_reasons=["Flaw absent in independent rescan with all regression checks clean."],
    )
    db_session.add(v_job)

    rev = VerificationReview(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        job_id=v_job.id,
        finding_id=f1_id,
        reviewer_id=admin_id,
        decision="accepted",
        rationale="Confirmed fix with clean verification scan.",
        finding_status_after="fixed",
        reviewed_at=datetime.now(timezone.utc),
    )
    db_session.add(rev)

    await db_session.commit()

    return {
        "workspace": ws,
        "owner": owner,
        "admin": admin,
        "viewer": viewer,
        "asset": asset,
        "scan": scan,
        "finding1": f1,
        "finding2": f2,
        "risk_snapshot": risk_snap,
        "remediation": rem,
        "verification_job": v_job,
    }


# ==============================================================================
# 1. Dashboard Metrics: Missing Data vs. Zero Invariant
# ==============================================================================
@pytest.mark.asyncio
async def test_dashboard_missing_data_vs_zero_invariant(db_session: AsyncSession):
    """
    Verifies that a workspace with zero scans explicitly flags has_completed_scans=False
    and alerts the user that 0 findings does NOT imply zero vulnerabilities.
    """
    owner_id = uuid.uuid4()
    owner = Profile(id=owner_id, firebase_uid=f"fb-empty-{owner_id.hex[:6]}", email="empty@test.io", display_name="Empty")
    ws_id = uuid.uuid4()
    ws = Workspace(id=ws_id, name="Empty Perimeter Startup", slug=f"empty-{ws_id.hex[:6]}", owner_id=owner_id)
    mem = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=owner_id, role="owner")
    db_session.add_all([owner, ws, mem])
    await db_session.commit()

    dash_service = DashboardService(db_session)
    metrics = await dash_service.get_workspace_metrics(ws_id)

    assert metrics.has_completed_scans is False
    assert "not completed any vulnerability scans" in metrics.data_disclaimer
    assert "Zero detected vulnerabilities does not mean the perimeter is secure" in metrics.data_disclaimer
    assert metrics.scans.completed == 0
    assert metrics.risk.is_calculated is False
    assert metrics.risk.current_score is None
    assert metrics.risk.risk_band is None


# ==============================================================================
# 2. Dashboard Metrics and Trends with Active Data
# ==============================================================================
@pytest.mark.asyncio
async def test_dashboard_metrics_and_trends_active_workspace(db_session: AsyncSession):
    ctx = await setup_stage10_test_context(db_session)
    dash_service = DashboardService(db_session)

    metrics = await dash_service.get_workspace_metrics(ctx["workspace"].id)
    assert metrics.has_completed_scans is True
    assert metrics.assets.total == 1
    assert metrics.assets.authorized == 1
    assert metrics.scans.completed == 1
    assert metrics.findings.open == 2
    assert metrics.findings.by_severity.get("critical") == 1
    assert metrics.findings.by_severity.get("high") == 1
    assert metrics.risk.current_score == 78.5
    assert metrics.risk.risk_band == "CRITICAL"
    assert metrics.remediations.applied == 1
    assert metrics.verifications.verified_candidates == 1

    trends = await dash_service.get_workspace_trends(ctx["workspace"].id, days=30)
    assert trends.data_available is True
    assert len(trends.findings_trend) == 30
    assert len(trends.risk_score_trend) >= 1
    assert len(trends.remediation_trend) == 30


# ==============================================================================
# 3. Sensitive Data Redaction
# ==============================================================================
def test_sensitive_data_redaction():
    raw_code = (
        "const apiKey = 'sk-proj-1234567890abcdef1234567890';\n"
        "const bearer = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.abc';\n"
        "const dbUri = 'postgres://dbuser:supersecretpass@db.internal:5432/main';\n"
        "const key = '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----';"
    )
    sanitized = redact_sensitive_data(raw_code)
    assert "sk-proj-" not in sanitized
    assert "supersecretpass" not in sanitized
    assert "-----BEGIN RSA PRIVATE KEY-----" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized


# ==============================================================================
# 4. Report Generation: All 5 Report Types
# ==============================================================================
@pytest.mark.asyncio
async def test_report_generation_all_five_types(db_session: AsyncSession):
    ctx = await setup_stage10_test_context(db_session)
    gen = ReportGeneratorService(db_session)

    # 1. Executive Summary
    req_exec = ReportCreateRequest(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        title="Executive Security Assessment Q4",
        format=ReportFormat.JSON,
        include_ai_summary=True,
    )
    r_exec = await gen.generate_report(ctx["workspace"].id, req_exec, generated_by="admin@stage10.io", user_id=ctx["admin"].id)
    assert r_exec.status == "completed"
    assert r_exec.completeness_status == "COMPLETE"
    assert "metrics" in r_exec.snapshot_data
    assert "executive_narrative" in r_exec.snapshot_data
    assert len(r_exec.snapshot_data["top_critical_findings"]) > 0

    # 2. Technical Vulnerability Report
    req_tech = ReportCreateRequest(
        report_type=ReportType.TECHNICAL_VULNERABILITY,
        title="Technical Vulnerability Audit",
        format=ReportFormat.JSON,
    )
    r_tech = await gen.generate_report(ctx["workspace"].id, req_tech, generated_by="admin@stage10.io")
    assert r_tech.status == "completed"
    assert len(r_tech.snapshot_data["findings"]) == 2
    # Verify redaction applied to evidence
    first_f = r_tech.snapshot_data["findings"][0]
    if first_f["evidence_items"]:
        snippet = first_f["evidence_items"][0]["snippet_redacted"]
        assert "super-secret-api-key" not in snippet
        assert "[REDACTED_SECRET]" in snippet

    # 3. Remediation Progress Report
    req_rem = ReportCreateRequest(
        report_type=ReportType.REMEDIATION_PROGRESS,
        title="Remediation Velocity & Progress",
        format=ReportFormat.JSON,
    )
    r_rem = await gen.generate_report(ctx["workspace"].id, req_rem, generated_by="admin@stage10.io")
    assert r_rem.status == "completed"
    assert r_rem.snapshot_data["total_proposals"] == 1
    assert len(r_rem.snapshot_data["proposals"]) == 1

    # 4. Verification & Regression Report (Stage 9 focus)
    req_ver = ReportCreateRequest(
        report_type=ReportType.VERIFICATION_REGRESSION,
        title="Independent Fix Verification Ledger",
        format=ReportFormat.JSON,
    )
    r_ver = await gen.generate_report(ctx["workspace"].id, req_ver, generated_by="admin@stage10.io")
    assert r_ver.status == "completed"
    assert r_ver.snapshot_data["total_verification_jobs"] == 1
    assert r_ver.snapshot_data["human_signoffs_count"] == 1
    assert r_ver.snapshot_data["jobs"][0]["vulnerability_status"] == "NO_LONGER_DETECTED"

    # 5. Asset Security Posture Report
    req_ast = ReportCreateRequest(
        report_type=ReportType.ASSET_SECURITY_POSTURE,
        title="Monitored Asset Inventory",
        format=ReportFormat.JSON,
    )
    r_ast = await gen.generate_report(ctx["workspace"].id, req_ast, generated_by="admin@stage10.io")
    assert r_ast.status == "completed"
    assert r_ast.snapshot_data["total_assets"] == 1
    assert r_ast.snapshot_data["assets"][0]["authorization"]["status"] in ("authorized", "verified")


# ==============================================================================
# 5. Report Exports: JSON and PDF Documents
# ==============================================================================
@pytest.mark.asyncio
async def test_report_export_json_and_pdf(db_session: AsyncSession):
    ctx = await setup_stage10_test_context(db_session)
    gen = ReportGeneratorService(db_session)

    req = ReportCreateRequest(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        title="Export Test Report",
        format=ReportFormat.PDF,
    )
    report = await gen.generate_report(ctx["workspace"].id, req, generated_by="admin@stage10.io")

    # JSON Export
    json_str, j_file, j_type = ReportExportService.export_json(report)
    assert j_file.endswith(".json")
    assert j_type == "application/json"
    parsed_json = json.loads(json_str)
    assert parsed_json["report_id"] == str(report.id)
    assert "snapshot_data" in parsed_json

    # PDF Export via ReportLab
    pdf_bytes, p_file, p_type = ReportExportService.export_pdf(report)
    assert p_file.endswith(".pdf")
    assert p_type == "application/pdf"
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF-")


# ==============================================================================
# 6. REST API Endpoints & Multi-Tenant Workspace Isolation
# ==============================================================================
@pytest.mark.asyncio
async def test_report_api_endpoints_and_isolation(client: AsyncClient, db_session: AsyncSession):
    ctx_a = await setup_stage10_test_context(db_session)

    # Tenant B setup
    user_b = Profile(id=uuid.uuid4(), firebase_uid="fb-tenant-b-stage10", email="b@stage10.io", display_name="Tenant B")
    ws_b = Workspace(id=uuid.uuid4(), name="Tenant B Workspace", slug=f"tb10-{uuid.uuid4().hex[:6]}", owner_id=user_b.id)
    db_session.add_all([user_b, ws_b])
    mem_b = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="owner")
    db_session.add(mem_b)
    await db_session.commit()

    headers_admin_a = {"Authorization": f"Bearer test-token-{ctx_a['admin'].firebase_uid}"}
    headers_tenant_b = {"Authorization": f"Bearer test-token-{user_b.firebase_uid}"}

    # 1. Fetch dashboard metrics via API
    res_dash = await client.get(
        f"/api/v1/reports/dashboard?workspace_id={ctx_a['workspace'].id}",
        headers=headers_admin_a,
    )
    assert res_dash.status_code == 200
    dash_json = res_dash.json()
    assert dash_json["has_completed_scans"] is True
    assert dash_json["findings"]["open"] == 2

    # 2. Fetch trends via API
    res_trends = await client.get(
        f"/api/v1/reports/dashboard/trends?workspace_id={ctx_a['workspace'].id}&days=30",
        headers=headers_admin_a,
    )
    assert res_trends.status_code == 200
    assert len(res_trends.json()["findings_trend"]) == 30

    # 3. Create Report via API
    create_payload = {
        "report_type": "executive_summary",
        "title": "API Generated Executive Report",
        "format": "pdf",
        "include_ai_summary": False,
    }
    res_create = await client.post(
        f"/api/v1/reports?workspace_id={ctx_a['workspace'].id}",
        json=create_payload,
        headers=headers_admin_a,
    )
    assert res_create.status_code == 201
    rep_data = res_create.json()
    report_id = rep_data["id"]
    assert rep_data["status"] == "completed"

    # 4. Tenant B cannot access Tenant A's report (Multi-tenant isolation)
    res_cross = await client.get(
        f"/api/v1/reports/{report_id}?workspace_id={ws_b.id}",
        headers=headers_tenant_b,
    )
    assert res_cross.status_code == 404

    # 5. Download report as PDF via API
    res_pdf_dl = await client.get(
        f"/api/v1/reports/{report_id}/download?workspace_id={ctx_a['workspace'].id}&format=pdf",
        headers=headers_admin_a,
    )
    assert res_pdf_dl.status_code == 200
    assert res_pdf_dl.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res_pdf_dl.headers["content-disposition"]
    assert res_pdf_dl.content.startswith(b"%PDF-")

    # 6. Download report as JSON via API
    res_json_dl = await client.get(
        f"/api/v1/reports/{report_id}/download?workspace_id={ctx_a['workspace'].id}&format=json",
        headers=headers_admin_a,
    )
    assert res_json_dl.status_code == 200
    assert "application/json" in res_json_dl.headers["content-type"]
    parsed_dl = res_json_dl.json()
    assert parsed_dl["report_id"] == report_id
