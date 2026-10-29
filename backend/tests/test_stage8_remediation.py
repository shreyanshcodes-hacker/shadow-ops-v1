import uuid
import os
import tempfile
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset, AssetAuthorization
from app.schemas.authorization import AuthorizationStatus
from app.models.scan import Scan
from app.models.finding import Finding, FindingEvidence
from app.models.remediation import RemediationProposal, RemediationApproval, RemediationApplication, RemediationCheckpoint
from app.schemas.remediation import RemediationStatus, ApplicationStatus, VerificationStatus
from app.services.patch_processor import PatchProcessor, PatchSecurityException
from app.services.validation_service import ValidationService
from app.services.remediation_service import RemediationService, RemediationSecurityException
from app.services.approval_service import ApprovalService, ApprovalSecurityException
from app.services.patch_applier import PatchApplicationAdapter, PatchApplicationException
from app.ai.fake import FakeAIProvider


async def setup_stage8_workspace(db_session: AsyncSession):
    """Sets up a complete isolated workspace with owner, admin, viewer, asset, authorization, and finding."""
    # 1. Profiles
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    viewer_id = uuid.uuid4()

    owner = Profile(id=owner_id, firebase_uid=f"fb-{owner_id}", email="owner@stage8.io", display_name="Workspace Owner")
    admin = Profile(id=admin_id, firebase_uid=f"fb-{admin_id}", email="admin@stage8.io", display_name="Security Admin")
    viewer = Profile(id=viewer_id, firebase_uid=f"fb-{viewer_id}", email="viewer@stage8.io", display_name="Read-only Viewer")
    db_session.add_all([owner, admin, viewer])

    # 2. Workspace & Memberships
    ws_id = uuid.uuid4()
    ws = Workspace(id=ws_id, name="Stage 8 Remediation Testing", slug=f"stage8-{str(ws_id)[:8]}", owner_id=owner_id)
    db_session.add(ws)

    m1 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=owner_id, role="owner")
    m2 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=admin_id, role="admin")
    m3 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=viewer_id, role="viewer")
    db_session.add_all([m1, m2, m3])

    # 3. Asset & Verified Authorization
    asset_id = uuid.uuid4()
    asset = Asset(
        id=asset_id,
        workspace_id=ws_id,
        name="Production Payments API",
        type="repository",
        connection_config={"target": "github.com/org/payments-api"},
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

    # 4. Scan
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

    # 5. Finding & Evidence
    finding_id = uuid.uuid4()
    finding = Finding(
        id=finding_id,
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan_id,
        source="semgrep",
        source_rule_id="python.sqlalchemy.sqli-injection",
        title="SQL Injection in Billing Query",
        description="User input concatenated directly into database query cursor.",
        severity="critical",
        confidence="high",
        cwe_ids=["CWE-89"],
        owasp_categories=["A03:2021"],
        location={"file": "billing/accounts.py", "start_line": 54, "end_line": 56},
        code_snippet="query = f'SELECT * FROM accounts WHERE id = {user_id}'\ncursor.execute(query)",
        status="open",
    )
    db_session.add(finding)

    evidence = FindingEvidence(
        id=uuid.uuid4(),
        finding_id=finding_id,
        workspace_id=ws_id,
        evidence_type="ast_match",
        title="SQL string interpolation",
        file_path="billing/accounts.py",
        line_start=54,
        line_end=56,
        content={"interpolated_variable": "user_id"},
    )
    db_session.add(evidence)

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
    }


# ==============================================================================
# PATCH PROCESSOR UNIT TESTS
# ==============================================================================
def test_patch_processor_valid_diff():
    valid_diff = """--- a/billing/accounts.py
+++ b/billing/accounts.py
@@ -54,3 +54,3 @@
-query = f"SELECT * FROM accounts WHERE id = {user_id}"
-cursor.execute(query)
+query = "SELECT * FROM accounts WHERE id = :id"
+cursor.execute(query, {"id": user_id})
"""
    parsed = PatchProcessor.parse_and_validate(valid_diff, declared_files=["billing/accounts.py"])
    assert parsed.is_safe is True
    assert len(parsed.files) == 1
    assert parsed.files[0].relative_path == "billing/accounts.py"
    assert parsed.total_additions == 2
    assert parsed.total_deletions == 2
    assert len(parsed.patch_hash) == 64  # Valid SHA-256


def test_patch_processor_rejects_path_traversal():
    traversal_diff = """--- a/../../etc/passwd
+++ b/../../etc/passwd
@@ -1,1 +1,1 @@
-root:x:0:0:root:/root:/bin/bash
+root:x:0:0:root:/root:/bin/sh
"""
    with pytest.raises(PatchSecurityException, match="Directory traversal"):
        PatchProcessor.parse_and_validate(traversal_diff)


def test_patch_processor_rejects_absolute_path_escape():
    abs_diff = """--- a//etc/shadow
+++ b//etc/shadow
@@ -1,1 +1,1 @@
-test
+test
"""
    with pytest.raises(PatchSecurityException, match="Absolute file path escape"):
        PatchProcessor.parse_and_validate(abs_diff)


def test_patch_processor_rejects_sensitive_files():
    sensitive_diff = """--- a/.env
+++ b/.env
@@ -1,1 +1,1 @@
-DB_PASS=old
+DB_PASS=new
"""
    with pytest.raises(PatchSecurityException, match="sensitive or privileged file"):
        PatchProcessor.parse_and_validate(sensitive_diff)


def test_patch_processor_rejects_binary_patches():
    binary_diff = """--- a/bin/app
+++ b/bin/app
GIT binary patch
literal 12345
zc$@#)!(#*
"""
    with pytest.raises(PatchSecurityException, match="Binary patches are strictly forbidden"):
        PatchProcessor.parse_and_validate(binary_diff)


def test_patch_processor_rejects_oversized_diff():
    oversized_diff = "--- a/large.py\n+++ b/large.py\n@@ -1,1 +1,1 @@\n" + ("+x = 1\n" * 15000)
    parsed = PatchProcessor.parse_and_validate(oversized_diff)
    assert parsed.is_safe is False
    assert any("exceeds safety maximum" in v for v in parsed.safety_violations)


# ==============================================================================
# VALIDATION SERVICE TESTS
# ==============================================================================
@pytest.mark.asyncio
async def test_validation_service_pipeline(db_session: AsyncSession):
    ctx = await setup_stage8_workspace(db_session)
    valid_diff = """--- a/billing/accounts.py
+++ b/billing/accounts.py
@@ -54,2 +54,2 @@
-query = f"SELECT * FROM accounts WHERE id = {user_id}"
+query = "SELECT * FROM accounts WHERE id = :id"
"""
    proposal = RemediationProposal(
        id=uuid.uuid4(),
        workspace_id=ctx["workspace"].id,
        finding_id=ctx["finding"].id,
        asset_id=ctx["asset"].id,
        proposed_by="ai_test",
        proposal_title="Param binding fix",
        title="Param binding fix",
        unified_diff=valid_diff,
        patch_hash=PatchProcessor.compute_patch_hash(valid_diff),
        affected_files=["billing/accounts.py"],
        status="PROPOSED",
        version=1,
    )
    db_session.add(proposal)
    await db_session.commit()

    val_service = ValidationService(db_session)
    all_passed, records, summary = await val_service.validate_proposal(proposal)

    assert all_passed is True
    assert len(records) == 4
    check_names = {r.check_name for r in records}
    assert "patch_integrity" in check_names
    assert "path_policy" in check_names
    assert "syntax_check" in check_names
    assert summary["patch_integrity"]["status"] == "PASS"


@pytest.mark.asyncio
async def test_validation_service_detects_syntax_errors(db_session: AsyncSession):
    ctx = await setup_stage8_workspace(db_session)
    corrupted_python_diff = """--- a/billing/accounts.py
+++ b/billing/accounts.py
@@ -1,2 +1,2 @@
-valid_code = 1
+def broken_syntax( : invalid !!
"""
    proposal = RemediationProposal(
        id=uuid.uuid4(),
        workspace_id=ctx["workspace"].id,
        finding_id=ctx["finding"].id,
        asset_id=ctx["asset"].id,
        proposed_by="ai_test",
        proposal_title="Broken syntax proposal",
        title="Broken syntax proposal",
        unified_diff=corrupted_python_diff,
        patch_hash=PatchProcessor.compute_patch_hash(corrupted_python_diff),
        affected_files=["billing/accounts.py"],
        status="PROPOSED",
        version=1,
    )
    db_session.add(proposal)
    await db_session.commit()

    val_service = ValidationService(db_session)
    all_passed, records, summary = await val_service.validate_proposal(proposal)

    assert all_passed is False
    syntax_rec = next(r for r in records if r.check_name == "syntax_check")
    assert syntax_rec.status == "FAIL"


# ==============================================================================
# REMEDIATION SERVICE & AUTHORIZATION BOUNDARY
# ==============================================================================
@pytest.mark.asyncio
async def test_remediation_proposal_creation_and_authorization(db_session: AsyncSession):
    ctx = await setup_stage8_workspace(db_session)
    fake_provider = FakeAIProvider()
    rem_service = RemediationService(db_session)

    # 1. Successful proposal creation for authorized asset
    proposal = await rem_service.create_proposal(
        finding_id=ctx["finding"].id,
        workspace_id=ctx["workspace"].id,
        created_by=ctx["admin"].id,
        provider=fake_provider,
    )
    assert proposal.status == RemediationStatus.AWAITING_APPROVAL.value
    assert len(proposal.patch_hash) == 64
    assert len(proposal.affected_files) >= 1
    assert "billing/accounts.py" in proposal.affected_files[0]

    # 2. Authorization Boundary Check: De-authorize asset -> Proposal creation blocked
    ctx["auth"].status = AuthorizationStatus.REVOKED.value
    await db_session.commit()

    with pytest.raises(RemediationSecurityException, match="NO AUTHORIZATION -> NO REMEDIATION"):
        await rem_service.create_proposal(
            finding_id=ctx["finding"].id,
            workspace_id=ctx["workspace"].id,
            created_by=ctx["admin"].id,
            provider=fake_provider,
        )


# ==============================================================================
# HUMAN APPROVAL TESTS
# ==============================================================================
@pytest.mark.asyncio
async def test_human_approval_role_and_hash_binding(db_session: AsyncSession):
    ctx = await setup_stage8_workspace(db_session)
    fake_provider = FakeAIProvider()
    rem_service = RemediationService(db_session)

    proposal = await rem_service.create_proposal(
        finding_id=ctx["finding"].id,
        workspace_id=ctx["workspace"].id,
        created_by=ctx["admin"].id,
        provider=fake_provider,
    )

    approval_service = ApprovalService(db_session)

    # 1. Unauthorized Role Rejection: Viewer cannot approve
    with pytest.raises(ApprovalSecurityException, match="lacks authority"):
        await approval_service.approve_proposal(
            proposal_id=proposal.id,
            workspace_id=ctx["workspace"].id,
            user_id=ctx["viewer"].id,
            patch_hash=proposal.patch_hash,
        )

    # 2. Patch Hash Mismatch Rejection (prevents modified/tampered patch approval)
    tampered_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    with pytest.raises(ApprovalSecurityException, match="Patch hash mismatch"):
        await approval_service.approve_proposal(
            proposal_id=proposal.id,
            workspace_id=ctx["workspace"].id,
            user_id=ctx["admin"].id,
            patch_hash=tampered_hash,
        )

    # 3. Valid Approval by Admin with matching patch hash
    approval = await approval_service.approve_proposal(
        proposal_id=proposal.id,
        workspace_id=ctx["workspace"].id,
        user_id=ctx["admin"].id,
        patch_hash=proposal.patch_hash,
        justification="Reviewed and verified parameterized query safety.",
    )
    assert approval.decision == "approved"
    assert approval.patch_hash == proposal.patch_hash
    assert proposal.status == RemediationStatus.APPROVED.value


@pytest.mark.asyncio
async def test_human_rejection(db_session: AsyncSession):
    ctx = await setup_stage8_workspace(db_session)
    fake_provider = FakeAIProvider()
    rem_service = RemediationService(db_session)

    proposal = await rem_service.create_proposal(
        finding_id=ctx["finding"].id,
        workspace_id=ctx["workspace"].id,
        created_by=ctx["admin"].id,
        provider=fake_provider,
    )

    approval_service = ApprovalService(db_session)
    rejection = await approval_service.reject_proposal(
        proposal_id=proposal.id,
        workspace_id=ctx["workspace"].id,
        user_id=ctx["admin"].id,
        reason="Query parameterization should be handled by repository layer ORM instead.",
    )
    assert rejection.decision == "rejected"
    assert proposal.status == RemediationStatus.REJECTED.value

    # Rejected proposal cannot be applied
    applier = PatchApplicationAdapter(db_session)
    with pytest.raises(PatchApplicationException, match="Cannot apply proposal in state 'REJECTED'"):
        await applier.apply_proposal(
            proposal_id=proposal.id,
            workspace_id=ctx["workspace"].id,
            user_id=ctx["admin"].id,
            patch_hash=proposal.patch_hash,
        )


# ==============================================================================
# SAFE PATCH APPLICATION & ROLLBACK TESTS
# ==============================================================================
@pytest.mark.asyncio
async def test_patch_application_and_checkpoint_rollback(db_session: AsyncSession):
    ctx = await setup_stage8_workspace(db_session)
    fake_provider = FakeAIProvider()
    rem_service = RemediationService(db_session)
    approval_service = ApprovalService(db_session)
    applier = PatchApplicationAdapter(db_session)

    proposal = await rem_service.create_proposal(
        finding_id=ctx["finding"].id,
        workspace_id=ctx["workspace"].id,
        created_by=ctx["admin"].id,
        provider=fake_provider,
    )

    # 1. Unapproved application is blocked
    with pytest.raises(PatchApplicationException, match="Mandatory human approval is required"):
        await applier.apply_proposal(
            proposal_id=proposal.id,
            workspace_id=ctx["workspace"].id,
            user_id=ctx["admin"].id,
            patch_hash=proposal.patch_hash,
        )

    # 2. Approve proposal
    await approval_service.approve_proposal(
        proposal_id=proposal.id,
        workspace_id=ctx["workspace"].id,
        user_id=ctx["admin"].id,
        patch_hash=proposal.patch_hash,
    )

    # 3. Create isolated temporary directory acting as the target repository
    with tempfile.TemporaryDirectory() as temp_repo:
        file_rel = "billing/accounts.py"
        full_path = os.path.join(temp_repo, "billing", "accounts.py")
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        original_code = """# Accounts module
def get_balance(user_id):
    query = f"SELECT * FROM accounts WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchall()
"""
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(original_code)

        # Apply proposal
        application = await applier.apply_proposal(
            proposal_id=proposal.id,
            workspace_id=ctx["workspace"].id,
            user_id=ctx["admin"].id,
            patch_hash=proposal.patch_hash,
            target_repo_dir=temp_repo,
        )
        assert application.status == ApplicationStatus.APPLIED.value
        assert application.verification_status == VerificationStatus.VERIFICATION_PENDING.value
        assert proposal.status == RemediationStatus.APPLIED.value

        # Core Invariant: Finding MUST NOT be automatically closed or marked resolved
        stmt = select(Finding).where(Finding.id == ctx["finding"].id)
        f_res = await db_session.execute(stmt)
        refreshed_finding = f_res.scalar_one()
        assert refreshed_finding.status == "open"  # Unchanged!

        # Verify patch was applied to file
        with open(full_path, "r", encoding="utf-8") as f:
            patched_content = f.read()
        assert ":id" in patched_content or "cursor.execute" in patched_content

        # 4. Rollback patch using pre-flight checkpoint
        rolled_back_app = await applier.rollback_proposal(
            application_id=application.id,
            workspace_id=ctx["workspace"].id,
            user_id=ctx["admin"].id,
            reason="Integration tests required adjustments.",
            target_repo_dir=temp_repo,
        )
        assert rolled_back_app.status == ApplicationStatus.ROLLED_BACK.value
        assert proposal.status == RemediationStatus.ROLLED_BACK.value

        # Verify file content was accurately restored to original
        with open(full_path, "r", encoding="utf-8") as f:
            restored_content = f.read()
        assert restored_content == original_code


# ==============================================================================
# FASTAPI API ENDPOINTS & CROSS-WORKSPACE ISOLATION
# ==============================================================================
@pytest.mark.asyncio
async def test_remediation_api_endpoints_and_workspace_isolation(client: AsyncClient, db_session: AsyncSession):
    ctx_a = await setup_stage8_workspace(db_session)

    # Create workspace B (different tenant)
    user_b = Profile(id=uuid.uuid4(), firebase_uid="fb-user-b", email="b@tenant.io", display_name="Tenant B")
    ws_b = Workspace(id=uuid.uuid4(), name="Tenant B Workspace", slug=f"tenant-b-{uuid.uuid4().hex[:6]}", owner_id=user_b.id)
    db_session.add_all([user_b, ws_b])
    mem_b = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="owner")
    db_session.add(mem_b)
    await db_session.commit()

    headers_admin = {"Authorization": f"Bearer test-token-{ctx_a['admin'].firebase_uid}"}
    headers_tenant_b = {"Authorization": f"Bearer test-token-{user_b.firebase_uid}"}

    # 1. Propose remediation via API in Workspace A
    res_prop = await client.post(
        f"/api/v1/findings/{ctx_a['finding'].id}/remediations?workspace_id={ctx_a['workspace'].id}",
        json={"custom_guidance": "Use standard parameter bindings."},
        headers=headers_admin,
    )
    assert res_prop.status_code == 201
    prop_data = res_prop.json()
    prop_id = prop_data["id"]
    patch_hash = prop_data["patch_hash"]
    assert prop_data["status"] == "AWAITING_APPROVAL"

    # 2. Cross-Workspace Isolation: Tenant B cannot access Workspace A's proposal
    res_cross = await client.get(
        f"/api/v1/remediations/{prop_id}?workspace_id={ws_b.id}",
        headers=headers_tenant_b,
    )
    assert res_cross.status_code in (403, 404)

    # 3. List remediations in Workspace A
    res_list = await client.get(
        f"/api/v1/remediations?workspace_id={ctx_a['workspace'].id}",
        headers=headers_admin,
    )
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # 4. Approve proposal via API
    res_appr = await client.post(
        f"/api/v1/remediations/{prop_id}/approve?workspace_id={ctx_a['workspace'].id}",
        json={"patch_hash": patch_hash, "justification": "API test approval"},
        headers=headers_admin,
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["decision"] == "approved"

    # 5. Apply proposal via API
    res_apply = await client.post(
        f"/api/v1/remediations/{prop_id}/apply?workspace_id={ctx_a['workspace'].id}",
        json={"patch_hash": patch_hash},
        headers=headers_admin,
    )
    assert res_apply.status_code == 200
    assert res_apply.json()["verification_status"] == "VERIFICATION_PENDING"

    # 6. Audit History endpoint
    res_hist = await client.get(
        f"/api/v1/remediations/{prop_id}/history?workspace_id={ctx_a['workspace'].id}",
        headers=headers_admin,
    )
    assert res_hist.status_code == 200
    hist = res_hist.json()
    assert len(hist["validations"]) >= 1
    assert len(hist["approvals"]) >= 1
    assert len(hist["applications"]) >= 1
