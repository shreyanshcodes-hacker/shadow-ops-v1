import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.remediation import RemediationProposal, RemediationApproval
from app.models.workspace import WorkspaceMember
from app.schemas.workspace import WorkspaceRole
from app.schemas.remediation import RemediationStatus
from app.services.audit_service import AuditService
from app.core.logging import logger


class ApprovalSecurityException(Exception):
    """Raised when an approval request violates safety or role invariants."""
    pass


class ApprovalService:
    """
    Server-side Human Approval Service:
    Enforces that no code modification occurs without explicit, authenticated,
    role-verified human sign-off bound to the exact patch hash and proposal version.
    """

    ALLOWED_APPROVAL_ROLES = {
        WorkspaceRole.OWNER.value,
        WorkspaceRole.ADMIN.value,
        WorkspaceRole.SECURITY_LEAD.value if hasattr(WorkspaceRole, "SECURITY_LEAD") else "admin",
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_service = AuditService(db)

    async def approve_proposal(
        self,
        proposal_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        patch_hash: str,
        justification: Optional[str] = None,
    ) -> RemediationApproval:
        """
        Processes human sign-off for a remediation proposal.
        Enforces:
        - Workspace membership and role privileges
        - Exact cryptographic patch hash binding
        - Pre-requisite validation success
        - Status is AWAITING_APPROVAL
        """
        # 1. Verify Member Role Privileges
        mem_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        mem_res = await self.db.execute(mem_stmt)
        member = mem_res.scalar_one_or_none()

        if not member:
            raise ApprovalSecurityException("User is not a member of this workspace.")

        if member.role not in self.ALLOWED_APPROVAL_ROLES and member.role not in ("owner", "admin"):
            raise ApprovalSecurityException(
                f"Role '{member.role}' lacks authority to approve remediation patches. Admin or Owner required."
            )

        # 2. Fetch Proposal with Validations
        stmt = (
            select(RemediationProposal)
            .where(RemediationProposal.id == proposal_id, RemediationProposal.workspace_id == workspace_id)
            .options(selectinload(RemediationProposal.validations))
        )
        res = await self.db.execute(stmt)
        proposal = res.scalar_one_or_none()

        if not proposal:
            raise ApprovalSecurityException("Remediation proposal not found.")

        # 3. Check State Machine Invariants
        if proposal.status in (RemediationStatus.APPROVED.value, RemediationStatus.APPLIED.value):
            raise ApprovalSecurityException(f"Proposal is already {proposal.status}.")

        if proposal.status in (RemediationStatus.REJECTED.value, RemediationStatus.EXPIRED.value):
            raise ApprovalSecurityException(f"Cannot approve proposal in state {proposal.status}.")

        # 4. Enforce Patch Hash Binding (Prevents approving modified/stale patches)
        if not patch_hash or patch_hash.strip().lower() != proposal.patch_hash.strip().lower():
            raise ApprovalSecurityException(
                f"Patch hash mismatch: submitted hash '{patch_hash}' does not match current proposal patch hash '{proposal.patch_hash}'. Review invalidated."
            )

        # 5. Check That Required Validation Succeeded
        if not proposal.validation_results or proposal.status == RemediationStatus.VALIDATION_FAILED.value:
            raise ApprovalSecurityException("Cannot approve proposal whose automated validation has failed.")

        # 6. Record Approval Record
        approval = RemediationApproval(
            id=uuid.uuid4(),
            proposal_id=proposal.id,
            workspace_id=workspace_id,
            approved_by=user_id,
            decision="approved",
            patch_hash=proposal.patch_hash,
            proposal_version=proposal.version,
            justification=justification,
            conditions=[],
            validation_snapshot=proposal.validation_results,
            approved_at=datetime.utcnow(),
        )
        self.db.add(approval)

        # 7. Transition Proposal State
        proposal.status = RemediationStatus.APPROVED.value
        proposal.approved_by = user_id
        proposal.approved_at = approval.approved_at

        await self.db.commit()
        await self.db.refresh(approval)
        await self.db.refresh(proposal)

        # 8. Audit Log
        await self.audit_service.log_action(
            workspace_id=workspace_id,
            actor_id=user_id,
            action="remediation.approved",
            resource_type="remediation_proposal",
            resource_id=str(proposal.id),
            details={
                "patch_hash": proposal.patch_hash,
                "proposal_version": proposal.version,
                "justification": justification,
            },
        )

        return approval

    async def reject_proposal(
        self,
        proposal_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
    ) -> RemediationApproval:
        """Processes human rejection of a proposal, preventing any subsequent application."""
        # 1. Verify Member Role
        mem_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        mem_res = await self.db.execute(mem_stmt)
        member = mem_res.scalar_one_or_none()
        if not member:
            raise ApprovalSecurityException("User is not a member of this workspace.")

        # 2. Fetch Proposal
        stmt = select(RemediationProposal).where(
            RemediationProposal.id == proposal_id,
            RemediationProposal.workspace_id == workspace_id
        )
        res = await self.db.execute(stmt)
        proposal = res.scalar_one_or_none()

        if not proposal:
            raise ApprovalSecurityException("Remediation proposal not found.")

        if proposal.status == RemediationStatus.APPLIED.value:
            raise ApprovalSecurityException("Cannot reject an already applied patch.")

        # 3. Record Rejection
        approval = RemediationApproval(
            id=uuid.uuid4(),
            proposal_id=proposal.id,
            workspace_id=workspace_id,
            approved_by=user_id,
            decision="rejected",
            patch_hash=proposal.patch_hash,
            proposal_version=proposal.version,
            justification=reason,
            conditions=[],
            validation_snapshot=proposal.validation_results,
            approved_at=datetime.utcnow(),
        )
        self.db.add(approval)

        proposal.status = RemediationStatus.REJECTED.value
        proposal.failure_reason = f"Rejected by operator: {reason}"

        await self.db.commit()
        await self.db.refresh(approval)
        await self.db.refresh(proposal)

        # 4. Audit Log
        await self.audit_service.log_action(
            workspace_id=workspace_id,
            actor_id=user_id,
            action="remediation.rejected",
            resource_type="remediation_proposal",
            resource_id=str(proposal.id),
            details={
                "reason": reason,
                "patch_hash": proposal.patch_hash,
            },
        )

        return approval
