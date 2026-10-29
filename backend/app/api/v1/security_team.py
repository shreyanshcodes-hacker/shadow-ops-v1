from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.profile import Profile
from app.models.security_team import SecurityTeamRun
from app.models.scan import AgentRun
from app.schemas.security_team import (
    CreateTeamRunRequest,
    HumanReviewRequest,
    SecurityTeamRunRead,
    SecurityTeamRunDetailRead,
    AgentRunRead,
    TeamAssessment,
)
from app.security.dependencies import get_current_user
from app.services.workspace_service import WorkspaceService
from app.services.security_team_orchestrator import SecurityTeamOrchestrator

router = APIRouter(prefix="/security-team", tags=["AI Security Team & Orchestration"])


@router.post("/runs", response_model=SecurityTeamRunRead, status_code=status.HTTP_201_CREATED)
async def trigger_security_team_run(
    request: CreateTeamRunRequest,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers an analytical Security Team evaluation over an authorized asset perimeter.
    Enforces multi-tenant workspace isolation and strict scope parameters.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(request.workspace_id, current_user.id)

    orchestrator = SecurityTeamOrchestrator(session=db)
    try:
        team_run = await orchestrator.create_team_run(
            workspace_id=request.workspace_id,
            asset_id=request.asset_id,
            requested_by=current_user.id,
            scan_id=request.scan_id,
            orchestration_version=request.orchestration_version,
        )

        # If run is queued, execute the multi-agent pipeline
        if team_run.status == "QUEUED":
            team_run = await orchestrator.execute_team_run(team_run.id)

        return team_run
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/runs", response_model=List[SecurityTeamRunRead])
async def list_security_team_runs(
    workspace_id: UUID = Query(...),
    asset_id: Optional[UUID] = Query(None),
    scan_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists historical Security Team evaluations within the caller's workspace.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    conds = [SecurityTeamRun.workspace_id == workspace_id]
    if asset_id:
        conds.append(SecurityTeamRun.asset_id == asset_id)
    if scan_id:
        conds.append(SecurityTeamRun.scan_id == scan_id)
    if status_filter:
        conds.append(SecurityTeamRun.status == status_filter)

    stmt = select(SecurityTeamRun).where(and_(*conds)).order_by(desc(SecurityTeamRun.created_at))
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/runs/{run_id}", response_model=SecurityTeamRunDetailRead)
async def get_security_team_run(
    run_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full detail of a Security Team run including timeline and individual agent executions.
    """
    stmt = (
        select(SecurityTeamRun)
        .options(selectinload(SecurityTeamRun.agent_runs))
        .where(SecurityTeamRun.id == run_id)
    )
    res = await db.execute(stmt)
    team_run = res.scalar_one_or_none()
    if not team_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security team run not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(team_run.workspace_id, current_user.id)

    # Parse assessment if present
    assessment = None
    if team_run.team_summary and "executive_summary" in team_run.team_summary:
        try:
            assessment = TeamAssessment.model_validate(team_run.team_summary)
        except Exception:
            pass

    return SecurityTeamRunDetailRead(
        id=team_run.id,
        workspace_id=team_run.workspace_id,
        asset_id=team_run.asset_id,
        scan_id=team_run.scan_id,
        status=team_run.status,
        requested_by=team_run.requested_by,
        orchestration_version=team_run.orchestration_version,
        team_summary=team_run.team_summary,
        confidence=float(team_run.confidence),
        started_at=team_run.started_at,
        completed_at=team_run.completed_at,
        reviewed_by=team_run.reviewed_by,
        reviewed_at=team_run.reviewed_at,
        review_notes=team_run.review_notes,
        created_at=team_run.created_at,
        updated_at=team_run.updated_at,
        agent_runs=team_run.agent_runs,
        assessment=assessment,
    )


@router.get("/runs/{run_id}/agents", response_model=List[AgentRunRead])
async def get_team_run_agent_executions(
    run_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists individual agent runs and structured outputs for a specific team run.
    """
    stmt = select(SecurityTeamRun).where(SecurityTeamRun.id == run_id)
    res = await db.execute(stmt)
    team_run = res.scalar_one_or_none()
    if not team_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security team run not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(team_run.workspace_id, current_user.id)

    agent_stmt = (
        select(AgentRun)
        .where(AgentRun.team_run_id == run_id)
        .order_by(AgentRun.created_at)
    )
    agent_res = await db.execute(agent_stmt)
    return list(agent_res.scalars().all())


@router.get("/runs/{run_id}/assessment", response_model=TeamAssessment)
async def get_team_run_assessment(
    run_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the final structured Team Assessment synthesized by the Security Reviewer Agent.
    """
    stmt = select(SecurityTeamRun).where(SecurityTeamRun.id == run_id)
    res = await db.execute(stmt)
    team_run = res.scalar_one_or_none()
    if not team_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security team run not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(team_run.workspace_id, current_user.id)

    if not team_run.team_summary or "executive_summary" not in team_run.team_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not ready or synthesis incomplete",
        )

    return TeamAssessment.model_validate(team_run.team_summary)


@router.post("/runs/{run_id}/review", response_model=SecurityTeamRunRead)
async def mark_security_team_reviewed(
    run_id: UUID,
    request: Optional[HumanReviewRequest] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Human-in-the-loop review boundary:
    A verified human security engineer endorses that the AI Security Team assessment was inspected.
    """
    stmt = select(SecurityTeamRun).where(SecurityTeamRun.id == run_id)
    res = await db.execute(stmt)
    team_run = res.scalar_one_or_none()
    if not team_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security team run not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(team_run.workspace_id, current_user.id)

    orchestrator = SecurityTeamOrchestrator(session=db)
    updated = await orchestrator.mark_human_reviewed(
        team_run_id=run_id,
        user_id=current_user.id,
        notes=request.notes if request else None,
    )
    return updated


@router.post("/runs/{run_id}/cancel", response_model=SecurityTeamRunRead)
async def cancel_security_team_run(
    run_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Safely aborts an in-progress security team evaluation.
    """
    stmt = select(SecurityTeamRun).where(SecurityTeamRun.id == run_id)
    res = await db.execute(stmt)
    team_run = res.scalar_one_or_none()
    if not team_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security team run not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(team_run.workspace_id, current_user.id)

    orchestrator = SecurityTeamOrchestrator(session=db)
    updated = await orchestrator.cancel_team_run(team_run_id=run_id, user_id=current_user.id)
    return updated
