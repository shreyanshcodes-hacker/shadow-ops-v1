from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.session import get_db
from app.models.profile import Profile
from app.models.notification import Notification, NotificationPreference, NotificationRule, WorkflowRun
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationUnreadCountResponse,
    NotificationPreferenceUpdate,
    NotificationPreferenceResponse,
    NotificationRuleCreate,
    NotificationRuleResponse,
    WorkflowRunResponse,
    WorkflowRunListResponse,
)
from app.security.dependencies import get_current_user
from app.services.workspace_service import WorkspaceService
from app.services.notification_service import NotificationService
from app.services.event_outbox_service import EventOutboxService
from app.services.workflow_engine import WorkflowEngine, ControlledWorkflowActionException

router = APIRouter(tags=["Notifications & Controlled Workflow Automation"])


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    category: Optional[str] = Query(None, description="Filter by event category"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists notifications for current user within isolated workspace."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = NotificationService(db)
    items, total, unread_count = await service.list_notifications(
        workspace_id=workspace_id,
        user_id=current_user.id,
        unread_only=unread_only,
        category=category,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(items=items, total=total, unread_count=unread_count)


@router.get("/notifications/unread-count", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves fast unread notification count for shell badge display."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = NotificationService(db)
    _, _, unread_count = await service.list_notifications(
        workspace_id=workspace_id, user_id=current_user.id, limit=1
    )
    return NotificationUnreadCountResponse(unread_count=unread_count)


@router.post("/notifications/{id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marks a single notification as read."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = NotificationService(db)
    notif = await service.mark_as_read(workspace_id, current_user.id, id)
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return notif


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marks all notifications in workspace as read for current user."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = NotificationService(db)
    count = await service.mark_all_as_read(workspace_id, current_user.id)
    return {"status": "success", "updated_count": count}


@router.get("/notifications/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gets user's delivery and category preferences for this workspace."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = NotificationService(db)
    return await service.get_or_create_preferences(workspace_id, current_user.id)


@router.put("/notifications/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates user notification preferences."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = NotificationService(db)
    return await service.update_preferences(workspace_id, current_user.id, payload)


@router.get("/notifications/rules", response_model=List[NotificationRuleResponse])
async def list_notification_rules(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists workspace notification routing rules."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = NotificationService(db)
    return await service.list_rules(workspace_id)


@router.post("/notifications/rules", response_model=NotificationRuleResponse)
async def create_notification_rule(
    payload: NotificationRuleCreate,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a workspace routing rule (Admin/Owner only)."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    service = NotificationService(db)
    return await service.create_rule(workspace_id, payload)


@router.get("/workflows/runs", response_model=WorkflowRunListResponse)
async def list_workflow_runs(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    limit: int = Query(50, ge=1, le=100),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists controlled workflow execution history for workspace."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    stmt = (
        select(WorkflowRun)
        .where(WorkflowRun.workspace_id == workspace_id)
        .order_by(WorkflowRun.created_at.desc())
        .limit(limit)
    )
    items = (await db.execute(stmt)).scalars().all()
    return WorkflowRunListResponse(items=items, total=len(items))


@router.post("/workflows/runs/{id}/retry", response_model=WorkflowRunResponse)
async def retry_workflow_run(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Safely retries a failed workflow execution."""
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    engine = WorkflowEngine(db)
    try:
        return await engine.retry_run(id, workspace_id)
    except ControlledWorkflowActionException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/events/outbox/process")
async def process_event_outbox(
    batch_size: int = Query(25, ge=1, le=100),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Triggers batch processing of pending outbox events."""
    outbox_service = EventOutboxService(db)
    processed = await outbox_service.process_batch(batch_size=batch_size)
    return {"status": "success", "processed_events": processed}
