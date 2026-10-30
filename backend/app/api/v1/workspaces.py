from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.profile import Profile
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceMemberResponse,
    MemberInvite,
    WorkspaceDirectoryItem,
    EmployeeJoinRequest,
    CompanyOnboardingRequest,
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


@router.get("/directory", response_model=List[WorkspaceDirectoryItem])
async def list_workspace_directory(
    q: Optional[str] = Query(default=None, description="Search companies by name"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List or search registered companies for employee onboarding."""
    service = WorkspaceService(db)
    return await service.get_directory(q)


@router.post("/onboarding/company", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def onboard_company_endpoint(
    req: CompanyOnboardingRequest,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Onboarding endpoint: Registers a company workspace and sets up initial assets."""
    service = WorkspaceService(db)
    workspace, _asset = await service.onboard_company(req, current_user)
    return workspace


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_in: WorkspaceCreate,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workspace. The creating user automatically becomes the OWNER."""
    service = WorkspaceService(db)
    return await service.create_workspace(workspace_in, current_user)


@router.post("/{workspace_id}/join", response_model=WorkspaceResponse)
async def join_company_workspace(
    workspace_id: UUID,
    req: Optional[EmployeeJoinRequest] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Allows an employee to join an existing registered company workspace."""
    service = WorkspaceService(db)
    display_name = req.display_name if req else None
    job_title = req.job_title if req else None
    return await service.join_workspace(
        workspace_id=workspace_id,
        user=current_user,
        display_name=display_name,
        job_title=job_title,
    )


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
