from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.profile import Profile
from app.models.remediation import RemediationProposal, RemediationApplication
from app.schemas.remediation import (
    RemediationProposalCreateRequest,
    RemediationProposalResponse,
    RemediationListResponse,
    RemediationApprovalRequest,
    RemediationApprovalResponse,
    RemediationRejectRequest,
    RemediationApplyRequest,
    RemediationApplicationResponse,
    RemediationRollbackRequest,
    RemediationValidationResponse,
)
from app.security.dependencies import get_current_user
from app.services.workspace_service import WorkspaceService
from app.services.remediation_service import RemediationService, RemediationSecurityException
from app.services.approval_service import ApprovalService, ApprovalSecurityException
from app.services.patch_applier import PatchApplicationAdapter, PatchApplicationException
from app.services.validation_service import ValidationService

router = APIRouter(tags=["Remediation & Patch Management"])


# ==============================================================================
# 1. Propose Remediation for Finding
# ==============================================================================
@router.post(
    "/findings/{finding_id}/remediations",
    response_model=RemediationProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_remediation_proposal(
    finding_id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID for multi-tenant isolation"),
    payload: Optional[RemediationProposalCreateRequest] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an AI Remediation Proposal for a specific finding.
    Strictly verifies asset authorization before generation.
    Enforces unified diff format, minimal code modification, and sandbox boundary checks.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = RemediationService(db)
    try:
        proposal = await service.create_proposal(
            finding_id=finding_id,
            workspace_id=workspace_id,
            created_by=current_user.id,
            custom_guidance=payload.custom_guidance if payload else None,
            model_preference=payload.model_preference if payload else None,
        )
        return await service.get_proposal(proposal.id, workspace_id)
    except RemediationSecurityException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==============================================================================
# 2. List Remediation Proposals
# ==============================================================================
@router.get("/remediations", response_model=RemediationListResponse)
async def list_remediations(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    status: Optional[str] = Query(None, description="Filter by proposal status"),
    finding_id: Optional[UUID] = Query(None, description="Filter by finding ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all remediation proposals for the authenticated workspace."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = RemediationService(db)
    items = await service.list_proposals(workspace_id, status=status, finding_id=finding_id)
    return RemediationListResponse(items=items, total=len(items))


# ==============================================================================
# 3. Get Proposal Detail
# ==============================================================================
@router.get("/remediations/{id}", response_model=RemediationProposalResponse)
async def get_remediation_proposal(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single remediation proposal with all validations, approvals, and applications."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = RemediationService(db)
    proposal = await service.get_proposal(id, workspace_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation proposal not found")
    return proposal


# ==============================================================================
# 4. Re-run Validation on Proposal
# ==============================================================================
@router.post("/remediations/{id}/validate", response_model=RemediationProposalResponse)
async def validate_remediation_proposal(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Triggers bounded validation pipeline checks on an existing proposal."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = RemediationService(db)
    proposal = await service.get_proposal(id, workspace_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation proposal not found")

    val_service = ValidationService(db)
    all_passed, validations, summary = await val_service.validate_proposal(proposal)

    proposal.validation_results = summary
    if all_passed:
        proposal.status = "AWAITING_APPROVAL"
        proposal.failure_reason = None
    else:
        proposal.status = "VALIDATION_FAILED"
        proposal.failure_reason = "Automated validation checks failed."

    await db.commit()
    await db.refresh(proposal)
    return await service.get_proposal(id, workspace_id)


# ==============================================================================
# 5. Human Approval
# ==============================================================================
@router.post("/remediations/{id}/approve", response_model=RemediationApprovalResponse)
async def approve_remediation_proposal(
    id: UUID,
    payload: RemediationApprovalRequest,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mandatory human sign-off before patch execution.
    Requires Admin or Owner role and exact patch hash confirmation.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    approval_service = ApprovalService(db)
    try:
        approval = await approval_service.approve_proposal(
            proposal_id=id,
            workspace_id=workspace_id,
            user_id=current_user.id,
            patch_hash=payload.patch_hash,
            justification=payload.justification,
        )
        return approval
    except ApprovalSecurityException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==============================================================================
# 6. Human Rejection
# ==============================================================================
@router.post("/remediations/{id}/reject", response_model=RemediationApprovalResponse)
async def reject_remediation_proposal(
    id: UUID,
    payload: RemediationRejectRequest,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rejects proposal and permanently prevents its application."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    approval_service = ApprovalService(db)
    try:
        approval = await approval_service.reject_proposal(
            proposal_id=id,
            workspace_id=workspace_id,
            user_id=current_user.id,
            reason=payload.reason,
        )
        return approval
    except ApprovalSecurityException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==============================================================================
# 7. Safe Patch Application
# ==============================================================================
@router.post("/remediations/{id}/apply", response_model=RemediationApplicationResponse)
async def apply_remediation_proposal(
    id: UUID,
    payload: RemediationApplyRequest,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Applies an approved patch in a controlled manner.
    Requires prior human approval and matching patch hash.
    Sets verification status to VERIFICATION_PENDING. Does NOT automatically close finding.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    applier = PatchApplicationAdapter(db)
    try:
        application = await applier.apply_proposal(
            proposal_id=id,
            workspace_id=workspace_id,
            user_id=current_user.id,
            patch_hash=payload.patch_hash,
        )
        return application
    except PatchApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==============================================================================
# 8. Rollback Applied Patch
# ==============================================================================
@router.post("/remediations/{id}/rollback", response_model=RemediationApplicationResponse)
async def rollback_remediation_proposal(
    id: UUID,
    payload: RemediationRollbackRequest,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Rolls back an applied patch to its pre-application checkpoint.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    # Find active application for this proposal
    stmt = (
        select(RemediationApplication)
        .where(
            RemediationApplication.proposal_id == id,
            RemediationApplication.workspace_id == workspace_id,
            RemediationApplication.status == "APPLIED",
        )
        .order_by(RemediationApplication.applied_at.desc())
    )
    res = await db.execute(stmt)
    application = res.scalars().first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active APPLIED application found for this proposal to rollback."
        )

    applier = PatchApplicationAdapter(db)
    try:
        updated_app = await applier.rollback_proposal(
            application_id=application.id,
            workspace_id=workspace_id,
            user_id=current_user.id,
            reason=payload.reason,
        )
        return updated_app
    except PatchApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==============================================================================
# 9. Remediation History
# ==============================================================================
@router.get("/remediations/{id}/history")
async def get_remediation_history(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the immutable audit history of validations, approvals, and applications."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = RemediationService(db)
    proposal = await service.get_proposal(id, workspace_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation proposal not found")

    return {
        "proposal_id": proposal.id,
        "status": proposal.status,
        "version": proposal.version,
        "patch_hash": proposal.patch_hash,
        "validations": proposal.validations,
        "approvals": proposal.approvals,
        "applications": proposal.applications,
    }
