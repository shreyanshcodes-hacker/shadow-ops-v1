from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.profile import Profile
from app.models.remediation import RemediationProposal, RemediationApplication
from app.models.finding import Finding
from app.schemas.verification import (
    VerificationTriggerRequest,
    VerificationReviewRequest,
    VerificationJobResponse,
    VerificationComparisonResponse,
    VerificationRegressionCheckResponse,
    VerificationReviewResponse,
    VerificationListResponse,
)
from app.security.dependencies import get_current_user
from app.services.workspace_service import WorkspaceService
from app.services.verification_service import VerificationService, VerificationServiceException

router = APIRouter(tags=["Fix Verification & Regression Analysis"])


@router.post(
    "/remediations/{id}/verify",
    response_model=VerificationJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_remediation_verification(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID for multi-tenant isolation"),
    payload: Optional[VerificationTriggerRequest] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers independent fix verification and regression analysis for an applied remediation proposal.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    # Fetch proposal
    p_stmt = select(RemediationProposal).where(
        RemediationProposal.id == id,
        RemediationProposal.workspace_id == workspace_id,
    )
    p_res = await db.execute(p_stmt)
    proposal = p_res.scalar_one_or_none()
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Remediation proposal not found in this workspace.",
        )

    # Find latest application if available
    app_stmt = (
        select(RemediationApplication)
        .where(
            RemediationApplication.proposal_id == proposal.id,
            RemediationApplication.workspace_id == workspace_id,
        )
        .order_by(RemediationApplication.applied_at.desc())
    )
    app_res = await db.execute(app_stmt)
    application = app_res.scalars().first()

    service = VerificationService(db)
    try:
        job = await service.trigger_verification(
            workspace_id=workspace_id,
            finding_id=proposal.finding_id,
            user_id=current_user.id,
            proposal_id=proposal.id,
            application_id=application.id if application else None,
        )
        return job
    except VerificationServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/findings/{id}/verify",
    response_model=VerificationJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_finding_verification(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID for multi-tenant isolation"),
    payload: Optional[VerificationTriggerRequest] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers independent fix verification directly for a finding.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = VerificationService(db)
    try:
        job = await service.trigger_verification(
            workspace_id=workspace_id,
            finding_id=id,
            user_id=current_user.id,
            proposal_id=payload.proposal_id if payload else None,
            application_id=payload.application_id if payload else None,
        )
        return job
    except VerificationServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/verifications",
    response_model=VerificationListResponse,
)
async def list_verifications(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    finding_id: Optional[UUID] = Query(None, description="Optional finding filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists verification runs within a workspace."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = VerificationService(db)
    jobs = await service.list_jobs(
        workspace_id=workspace_id, finding_id=finding_id, limit=limit, offset=offset
    )
    return VerificationListResponse(items=jobs, total=len(jobs))


@router.get(
    "/verifications/{id}",
    response_model=VerificationJobResponse,
)
async def get_verification(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full verification execution details, checks, and comparisons."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = VerificationService(db)
    job = await service.get_job(id, workspace_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification job not found in this workspace.",
        )
    return job


@router.get(
    "/verifications/{id}/comparisons",
    response_model=List[VerificationComparisonResponse],
)
async def get_verification_comparisons(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves baseline vs rescan comparison records for a verification job."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = VerificationService(db)
    job = await service.get_job(id, workspace_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification job not found.",
        )
    return job.comparisons


@router.get(
    "/verifications/{id}/checks",
    response_model=List[VerificationRegressionCheckResponse],
)
async def get_verification_checks(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves regression and syntax checks for a verification job."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = VerificationService(db)
    job = await service.get_job(id, workspace_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification job not found.",
        )
    return job.regression_checks


@router.post(
    "/verifications/{id}/review",
    response_model=VerificationReviewResponse,
)
async def review_verification(
    id: UUID,
    payload: VerificationReviewRequest,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits human sign-off decision (accepted/rejected) on a verification job.
    Accepting closes the finding as 'resolved'.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = VerificationService(db)
    try:
        review = await service.review_verification(
            workspace_id=workspace_id,
            job_id=id,
            reviewer_id=current_user.id,
            decision=payload.decision.value,
            rationale=payload.rationale,
        )
        return review
    except VerificationServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/verifications/{id}/rerun",
    response_model=VerificationJobResponse,
)
async def rerun_verification(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reruns verification checks and rescan for an existing verification job."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = VerificationService(db)
    job = await service.get_job(id, workspace_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification job not found.")

    try:
        new_job = await service.trigger_verification(
            workspace_id=workspace_id,
            finding_id=job.finding_id,
            user_id=current_user.id,
            proposal_id=job.proposal_id,
            application_id=job.application_id,
        )
        return new_job
    except VerificationServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
