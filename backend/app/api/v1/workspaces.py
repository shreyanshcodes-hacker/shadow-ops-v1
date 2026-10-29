from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.profile import Profile
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceMemberResponse,
    MemberInvite,
)
from app.security.dependencies import get_current_user, RequireWorkspaceMember
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("", response_model=List[WorkspaceResponse])
async def list_my_workspaces(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all workspaces the authenticated user belongs to."""
    service = WorkspaceService(db)
    return await service.list_workspaces(current_user.id)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_in: WorkspaceCreate,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workspace. The creating user automatically becomes the OWNER."""
    service = WorkspaceService(db)
    return await service.create_workspace(workspace_in, current_user)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve workspace details. Caller must be an authorized member."""
    service = WorkspaceService(db)
    return await service.get_workspace(workspace_id, current_user.id)


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def get_workspace_members(
    workspace_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List members of a workspace. Caller must be an authorized member."""
    service = WorkspaceService(db)
    tuples = await service.get_members(workspace_id, current_user.id)
    results = []
    for member, profile in tuples:
        results.append(
            WorkspaceMemberResponse(
                id=member.id,
                workspace_id=member.workspace_id,
                user_id=member.user_id,
                role=member.role,
                email=profile.email,
                display_name=profile.display_name,
                invited_by=member.invited_by,
                invited_at=member.invited_at,
                joined_at=member.joined_at,
            )
        )
    return results


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_workspace_member(
    workspace_id: UUID,
    invite: MemberInvite,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Invite or add a team collaborator to the workspace by email.
    Caller must be a workspace owner or admin.
    """
    service = WorkspaceService(db)
    member, profile = await service.invite_member(
        workspace_id=workspace_id,
        caller_id=current_user.id,
        email=invite.email,
        role=invite.role,
    )
    return WorkspaceMemberResponse(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role=member.role,
        email=profile.email,
        display_name=profile.display_name,
        invited_by=member.invited_by,
        invited_at=member.invited_at,
        joined_at=member.joined_at,
    )


@router.delete(
    "/{workspace_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_workspace_member(
    workspace_id: UUID,
    member_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a member from the workspace.
    Caller must be a workspace owner or admin.
    """
    service = WorkspaceService(db)
    await service.remove_member(
        workspace_id=workspace_id,
        caller_id=current_user.id,
        member_id=member_id,
    )
