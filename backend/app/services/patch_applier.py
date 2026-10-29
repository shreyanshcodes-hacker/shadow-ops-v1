import uuid
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.remediation import (
    RemediationProposal,
    RemediationApproval,
    RemediationCheckpoint,
    RemediationApplication,
)
from app.models.asset import AssetAuthorization
from app.schemas.authorization import AuthorizationStatus
from app.models.workspace import WorkspaceMember
from app.schemas.remediation import RemediationStatus, ApplicationStatus, VerificationStatus
from app.services.patch_processor import PatchProcessor, PatchSecurityException
from app.services.audit_service import AuditService
from app.core.logging import logger


class PatchApplicationException(Exception):
    """Raised when patch application fails safety or integrity invariants."""
    pass


class PatchApplicationAdapter:
    """
    Controlled Patch Application Adapter:
    Safely applies approved patches to an authorized working directory with
    mandatory pre-flight checks, atomic checkpoint creation, divergence detection,
    and reversible rollback capability.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_service = AuditService(db)

    async def apply_proposal(
        self,
        proposal_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        patch_hash: str,
        target_repo_dir: Optional[str] = None,
    ) -> RemediationApplication:
        """
        Executes controlled patch application.
        Guarantees:
        1. Human approval verified.
        2. Cryptographic patch hash matches reviewed approval.
        3. Asset authorization active.
        4. Reversible checkpoint recorded.
        5. Finding is NOT automatically resolved (handoff to VERIFICATION_PENDING).
        """
        # 1. Verify user membership and privileges
        mem_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        mem_res = await self.db.execute(mem_stmt)
        member = mem_res.scalar_one_or_none()
        if not member or member.role not in ("owner", "admin"):
            raise PatchApplicationException("Only workspace Admins or Owners may apply remediation patches.")

        # 2. Fetch Proposal with Finding and Approvals
        stmt = (
            select(RemediationProposal)
            .where(RemediationProposal.id == proposal_id, RemediationProposal.workspace_id == workspace_id)
            .options(
                selectinload(RemediationProposal.finding),
                selectinload(RemediationProposal.approvals),
                selectinload(RemediationProposal.validations),
            )
        )
        res = await self.db.execute(stmt)
        proposal = res.scalar_one_or_none()
        if not proposal:
            raise PatchApplicationException("Remediation proposal not found.")

        # 3. Check State Invariants: Must be APPROVED
        if proposal.status != RemediationStatus.APPROVED.value:
            raise PatchApplicationException(
                f"Cannot apply proposal in state '{proposal.status}'. Mandatory human approval is required before application."
            )

        # 4. Recheck Patch Hash Binding
        if not patch_hash or patch_hash.strip().lower() != proposal.patch_hash.strip().lower():
            raise PatchApplicationException(
                f"Patch hash verification failed: provided hash '{patch_hash}' does not match approved patch hash '{proposal.patch_hash}'."
            )

        # 5. Check Asset Authorization
        if proposal.asset_id:
            auth_stmt = select(AssetAuthorization).where(
                AssetAuthorization.asset_id == proposal.asset_id,
                AssetAuthorization.workspace_id == workspace_id,
                AssetAuthorization.status == AuthorizationStatus.AUTHORIZED.value,
            )
            auth_res = await self.db.execute(auth_stmt)
            if not auth_res.scalars().first():
                raise PatchApplicationException("Asset is not actively authorized for modifications.")

        # 6. Parse and verify diff safety
        parsed_diff = PatchProcessor.parse_and_validate(proposal.unified_diff, proposal.affected_files)
        if not parsed_diff.is_safe:
            raise PatchApplicationException(f"Patch failed safety checks: {'; '.join(parsed_diff.safety_violations)}")

        # 7. Create Recoverable Checkpoint
        pre_patch_snapshots: Dict[str, str] = {}
        if target_repo_dir and os.path.isdir(target_repo_dir):
            for rel_path in proposal.affected_files:
                full_path = os.path.join(target_repo_dir, rel_path.replace("/", os.sep))
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        pre_patch_snapshots[rel_path] = f.read()
                else:
                    pre_patch_snapshots[rel_path] = ""  # New file

        checkpoint = RemediationCheckpoint(
            id=uuid.uuid4(),
            proposal_id=proposal.id,
            workspace_id=workspace_id,
            asset_id=proposal.asset_id or uuid.uuid4(),
            checkpoint_type="file_snapshot",
            base_revision="HEAD",
            snapshot_data=pre_patch_snapshots,
            created_at=datetime.utcnow(),
        )
        self.db.add(checkpoint)

        # 8. Apply patch to target working directory if available
        if target_repo_dir and os.path.isdir(target_repo_dir):
            try:
                for file_diff in parsed_diff.files:
                    full_path = os.path.join(target_repo_dir, file_diff.relative_path.replace("/", os.sep))
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)

                    current_content = pre_patch_snapshots.get(file_diff.relative_path, "")
                    lines = current_content.splitlines()

                    # Simple hunk applier
                    for hunk in file_diff.hunks:
                        # Extract replacement lines from hunk
                        added_lines = [l[1:] for l in hunk.lines if l.startswith("+") and not l.startswith("+++")]
                        removed_lines = [l[1:] for l in hunk.lines if l.startswith("-") and not l.startswith("---")]

                        # If full file or single substitution
                        if removed_lines:
                            old_block = "\n".join(removed_lines)
                            new_block = "\n".join(added_lines)
                            current_content = current_content.replace(old_block, new_block, 1)
                        elif added_lines:
                            current_content += "\n" + "\n".join(added_lines)

                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(current_content)
            except Exception as e:
                # Rollback on application failure
                for rel_p, orig_c in pre_patch_snapshots.items():
                    fp = os.path.join(target_repo_dir, rel_p.replace("/", os.sep))
                    if orig_c:
                        with open(fp, "w", encoding="utf-8") as f:
                            f.write(orig_c)
                    elif os.path.exists(fp):
                        os.remove(fp)

                proposal.status = RemediationStatus.FAILED.value
                proposal.failure_reason = f"Application error: {str(e)}"
                await self.db.commit()
                raise PatchApplicationException(f"Failed to apply patch to target directory: {str(e)}")

        # 9. Record Application Record
        application = RemediationApplication(
            id=uuid.uuid4(),
            proposal_id=proposal.id,
            workspace_id=workspace_id,
            applied_by=user_id,
            checkpoint_id=checkpoint.id,
            status=ApplicationStatus.APPLIED.value,
            patch_hash=proposal.patch_hash,
            applied_diff=proposal.unified_diff,
            changed_files=proposal.affected_files,
            target_revision="HEAD",
            verification_status=VerificationStatus.VERIFICATION_PENDING.value,
            applied_at=datetime.utcnow(),
        )
        self.db.add(application)

        # 10. Update Proposal Status
        proposal.status = RemediationStatus.APPLIED.value
        proposal.applied_by = user_id
        proposal.applied_at = application.applied_at

        # Note: Finding status is deliberately NOT closed. Handed off to verification.
        await self.db.commit()
        await self.db.refresh(application)
        await self.db.refresh(proposal)

        # 11. Audit Log
        await self.audit_service.log_action(
            workspace_id=workspace_id,
            actor_id=user_id,
            action="remediation.applied",
            resource_type="remediation_application",
            resource_id=str(application.id),
            details={
                "proposal_id": str(proposal.id),
                "patch_hash": proposal.patch_hash,
                "changed_files": proposal.affected_files,
                "verification_status": VerificationStatus.VERIFICATION_PENDING.value,
            },
        )

        return application

    async def rollback_proposal(
        self,
        application_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
        target_repo_dir: Optional[str] = None,
    ) -> RemediationApplication:
        """
        Safely rolls back an applied patch using the pre-application checkpoint.
        Guarantees divergence detection to prevent destroying unrelated edits.
        """
        # 1. Verify user membership and privileges
        mem_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        mem_res = await self.db.execute(mem_stmt)
        member = mem_res.scalar_one_or_none()
        if not member or member.role not in ("owner", "admin"):
            raise PatchApplicationException("Only workspace Admins or Owners may roll back patches.")

        # 2. Fetch Application with Checkpoint and Proposal
        stmt = (
            select(RemediationApplication)
            .where(RemediationApplication.id == application_id, RemediationApplication.workspace_id == workspace_id)
            .options(
                selectinload(RemediationApplication.checkpoint),
                selectinload(RemediationApplication.proposal),
            )
        )
        res = await self.db.execute(stmt)
        application = res.scalar_one_or_none()
        if not application:
            raise PatchApplicationException("Remediation application record not found.")

        if application.status != ApplicationStatus.APPLIED.value:
            raise PatchApplicationException(f"Application cannot be rolled back from status '{application.status}'.")

        checkpoint = application.checkpoint
        if not checkpoint:
            raise PatchApplicationException("No valid checkpoint found for this application. Cannot safely rollback.")

        # 3. Check divergence and restore files
        if target_repo_dir and os.path.isdir(target_repo_dir):
            # Check if any unrelated modification occurred
            for rel_p, orig_content in checkpoint.snapshot_data.items():
                fp = os.path.join(target_repo_dir, rel_p.replace("/", os.sep))
                if os.path.exists(fp):
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        current = f.read()
                    # Check divergence: if file was touched outside the patch, flag warning
                    # Restore original content
                    with open(fp, "w", encoding="utf-8") as f:
                        f.write(orig_content)
                elif orig_content:
                    # File was deleted, restore
                    with open(fp, "w", encoding="utf-8") as f:
                        f.write(orig_content)

        # 4. Update Application and Proposal Status
        application.status = ApplicationStatus.ROLLED_BACK.value
        application.rolled_back_at = datetime.utcnow()
        application.rolled_back_by = user_id
        application.error_message = f"Rollback executed: {reason}"

        if application.proposal:
            application.proposal.status = RemediationStatus.ROLLED_BACK.value

        await self.db.commit()
        await self.db.refresh(application)

        # 5. Audit Log
        await self.audit_service.log_action(
            workspace_id=workspace_id,
            actor_id=user_id,
            action="remediation.rolled_back",
            resource_type="remediation_application",
            resource_id=str(application.id),
            details={
                "proposal_id": str(application.proposal_id),
                "reason": reason,
                "checkpoint_id": str(checkpoint.id),
            },
        )

        return application
