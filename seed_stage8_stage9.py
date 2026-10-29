import asyncio
import os
import sys
import uuid
import hashlib
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.profile import Profile
from app.models.workspace import Workspace
from app.models.finding import Finding
from app.models.remediation import (
    RemediationProposal,
    RemediationValidation,
    RemediationApproval,
    RemediationCheckpoint,
    RemediationApplication,
)
from app.models.verification import (
    VerificationJob,
    VerificationComparison,
    VerificationRegressionCheck,
)

async def seed_stage8_9():
    async with async_session_maker() as session:
        # Check profile
        stmt = select(Profile).where(Profile.email == "operator@shadowops.io")
        res = await session.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            print("Operator profile not found. Please run seed_local.py first.")
            return

        # Check workspace
        ws_stmt = select(Workspace).where(Workspace.slug == "shadowops-core")
        ws_res = await session.execute(ws_stmt)
        workspace = ws_res.scalar_one_or_none()
        if not workspace:
            print("Workspace not found.")
            return

        # Check finding
        f_stmt = select(Finding).where(Finding.workspace_id == workspace.id)
        f_res = await session.execute(f_stmt)
        findings = list(f_res.scalars().all())
        if not findings:
            print("No findings found.")
            return

        sqli_finding = findings[0]

        # Check if proposal already seeded
        prop_stmt = select(RemediationProposal).where(RemediationProposal.workspace_id == workspace.id)
        prop_res = await session.execute(prop_stmt)
        if prop_res.scalars().first():
            print("Stage 8 and 9 demo records already seeded.")
            return

        print("Seeding Stage 8 remediation proposal and applied patch...")
        diff = """--- a/billing/accounts.py
+++ b/billing/accounts.py
@@ -54,3 +54,4 @@
-query = f'SELECT balance, status FROM accounts WHERE customer_id = {customer_id}'
-cursor.execute(query)
+query = "SELECT balance, status FROM accounts WHERE customer_id = :customer_id"
+cursor.execute(query, {"customer_id": customer_id})
"""
        patch_hash = hashlib.sha256(diff.encode("utf-8")).hexdigest()

        prop_id = uuid.uuid4()
        proposal = RemediationProposal(
            id=prop_id,
            workspace_id=workspace.id,
            asset_id=sqli_finding.asset_id,
            finding_id=sqli_finding.id,
            proposal_title="Parameterize SQL Query in billing/accounts.py",
            problem_summary="Untrusted user input interpolated directly into SQL query string.",
            proposed_solution="Use parameter binding dictionary to prevent SQL injection.",
            rationale="Eliminates CWE-89 injection sink by separating code from data.",
            title="Parameterize SQL Query in billing/accounts.py",
            description="Use parameter binding dictionary to prevent SQL injection.",
            affected_files=["billing/accounts.py"],
            unified_diff=diff,
            patch_hash=patch_hash,
            status="APPLIED",
            version=1,
            approved_by=profile.id,
            approved_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            applied_by=profile.id,
            applied_at=datetime.now(timezone.utc) - timedelta(minutes=4),
        )
        session.add(proposal)

        val1 = RemediationValidation(
            id=uuid.uuid4(),
            proposal_id=prop_id,
            workspace_id=workspace.id,
            check_name="syntax_integrity:billing/accounts.py",
            status="PASS",
            duration_ms=45,
            output_summary="Python AST successfully parsed modified file without syntax errors.",
        )
        val2 = RemediationValidation(
            id=uuid.uuid4(),
            proposal_id=prop_id,
            workspace_id=workspace.id,
            check_name="security_invariants:billing/accounts.py",
            status="PASS",
            duration_ms=28,
            output_summary="Zero forbidden sinks (eval, os.system, raw format) detected.",
        )
        session.add_all([val1, val2])

        approval = RemediationApproval(
            id=uuid.uuid4(),
            proposal_id=prop_id,
            workspace_id=workspace.id,
            approved_by=profile.id,
            decision="approved",
            patch_hash=patch_hash,
            proposal_version=1,
            justification="Verified syntax and parameter binding fix.",
            approved_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        session.add(approval)

        checkpoint = RemediationCheckpoint(
            id=uuid.uuid4(),
            proposal_id=prop_id,
            workspace_id=workspace.id,
            asset_id=sqli_finding.asset_id,
            checkpoint_type="file_snapshot",
            base_revision="HEAD~1",
            snapshot_data={"files": ["billing/accounts.py"]},
            created_at=datetime.now(timezone.utc) - timedelta(minutes=4),
        )
        session.add(checkpoint)

        application = RemediationApplication(
            id=uuid.uuid4(),
            proposal_id=prop_id,
            workspace_id=workspace.id,
            applied_by=profile.id,
            checkpoint_id=checkpoint.id,
            status="APPLIED",
            patch_hash=patch_hash,
            applied_diff=diff,
            changed_files=["billing/accounts.py"],
            verification_status="VERIFICATION_PENDING",
            applied_at=datetime.now(timezone.utc) - timedelta(minutes=4),
        )
        session.add(application)

        print("Seeding Stage 9 fix verification job...")
        job_id = uuid.uuid4()
        verif_job = VerificationJob(
            id=job_id,
            workspace_id=workspace.id,
            asset_id=sqli_finding.asset_id,
            finding_id=sqli_finding.id,
            proposal_id=prop_id,
            application_id=application.id,
            status="PASSED_PENDING_REVIEW",
            vulnerability_status="NO_LONGER_DETECTED",
            regression_status="PASS",
            scanner_status="COMPLETED",
            test_status="PASS",
            policy_verdict="VERIFIED_CANDIDATE",
            policy_version="verification-policy-v1",
            policy_reasons=[
                "Independent rescan confirmed target vulnerability is no longer detected, with no syntax or regression errors."
            ],
            baseline_snapshot={
                "rule_id": sqli_finding.source_rule_id,
                "file_path": "billing/accounts.py",
                "line_start": 54,
                "line_end": 57,
                "code_snippet": sqli_finding.code_snippet,
            },
            started_at=datetime.now(timezone.utc) - timedelta(minutes=3),
            completed_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        )
        session.add(verif_job)

        comparison = VerificationComparison(
            id=uuid.uuid4(),
            job_id=job_id,
            workspace_id=workspace.id,
            finding_id=sqli_finding.id,
            comparison_category="NO_LONGER_DETECTED",
            rule_id=sqli_finding.source_rule_id,
            file_path="billing/accounts.py",
            baseline_evidence={
                "code_snippet": sqli_finding.code_snippet,
                "rule_id": sqli_finding.source_rule_id,
            },
            rescan_evidence={},
            line_shift=0,
            similarity_score=0.0,
            explanation=f"Vulnerability '{sqli_finding.source_rule_id}' is NO LONGER DETECTED in 'billing/accounts.py'. Parameterized query confirmed clean.",
        )
        session.add(comparison)

        reg1 = VerificationRegressionCheck(
            id=uuid.uuid4(),
            job_id=job_id,
            workspace_id=workspace.id,
            check_name="syntax_integrity:billing/accounts.py",
            status="PASS",
            duration_ms=32,
            output_summary="Syntax verified clean for billing/accounts.py",
        )
        reg2 = VerificationRegressionCheck(
            id=uuid.uuid4(),
            job_id=job_id,
            workspace_id=workspace.id,
            check_name="ast_security_invariants:billing/accounts.py",
            status="PASS",
            duration_ms=19,
            output_summary="Security invariants verified: no dangerous sinks found.",
        )
        reg3 = VerificationRegressionCheck(
            id=uuid.uuid4(),
            job_id=job_id,
            workspace_id=workspace.id,
            check_name="unit_test_suite",
            status="PASS",
            duration_ms=115,
            output_summary="Target regression tests passed without errors.",
        )
        session.add_all([reg1, reg2, reg3])

        await session.commit()
        print("Stage 8 and 9 demo records seeded successfully!")
        print(f"  Remediation Proposal ID: {prop_id}")
        print(f"  Verification Job ID: {job_id}")

if __name__ == "__main__":
    asyncio.run(seed_stage8_9())
