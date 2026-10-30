import uuid
from typing import List, Optional, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.workspace_repo import WorkspaceRepository
from app.repositories.profile_repo import ProfileRepository
from app.schemas.profile import ProfileCreate, ProfileUpdate
from app.models.workspace import Workspace, WorkspaceMember
from app.models.profile import Profile
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceRole,
    CompanyOnboardingRequest,
)
from app.services.audit_service import AuditService
from app.schemas.audit import AuditEventType


class WorkspaceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.workspace_repo = WorkspaceRepository(session)
        self.audit_service = AuditService(session)

    async def create_workspace(self, workspace_in: WorkspaceCreate, user: Profile) -> Workspace:
        workspace = await self.workspace_repo.create(workspace_in, owner_id=user.id)
        await self.audit_service.log(
            workspace_id=workspace.id,
            user_id=user.id,
            action=AuditEventType.WORKSPACE_CREATED,
            resource_type="workspace",
            resource_id=workspace.id,
            new_state={"name": workspace.name, "slug": workspace.slug},
        )
        return workspace

    async def list_workspaces(self, user_id: UUID) -> List[Workspace]:
        return await self.workspace_repo.list_for_user(user_id)

    async def get_workspace(self, workspace_id: UUID, user_id: UUID) -> Workspace:
        membership = await self.workspace_repo.get_membership(workspace_id, user_id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this workspace",
            )
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )
        return workspace

    async def get_members(self, workspace_id: UUID, user_id: UUID) -> List[Tuple[WorkspaceMember, Profile]]:
        # Verify caller has membership
        membership = await self.workspace_repo.get_membership(workspace_id, user_id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this workspace",
            )
        return await self.workspace_repo.get_members(workspace_id)

    async def add_member(
        self,
        workspace_id: UUID,
        caller_id: UUID,
        target_user_id: UUID,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        # Caller must be owner or admin
        caller_membership = await self.workspace_repo.get_membership(workspace_id, caller_id)
        if not caller_membership or caller_membership.role not in [WorkspaceRole.OWNER.value, WorkspaceRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace owners or admins can manage members",
            )
        member = await self.workspace_repo.add_member(
            workspace_id=workspace_id,
            user_id=target_user_id,
            role=role,
            invited_by=caller_id,
        )
        await self.audit_service.log(
            workspace_id=workspace_id,
            user_id=caller_id,
            action=AuditEventType.MEMBER_ADDED,
            resource_type="workspace_member",
            resource_id=member.id,
            new_state={"target_user_id": str(target_user_id), "role": role.value},
        )
        return member

    async def invite_member(
        self,
        workspace_id: UUID,
        caller_id: UUID,
        email: str,
        role: WorkspaceRole,
    ) -> Tuple[WorkspaceMember, Profile]:
        # Caller must be owner or admin
        caller_membership = await self.workspace_repo.get_membership(workspace_id, caller_id)
        if not caller_membership or caller_membership.role not in [WorkspaceRole.OWNER.value, WorkspaceRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace owners or admins can invite team members",
            )
        
        email_clean = email.strip().lower()
        if not email_clean or "@" not in email_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid collaborator email address is required",
            )

        # Lookup or create profile for invited user
        profile_repo = ProfileRepository(self.session)
        profile = await profile_repo.get_by_email(email_clean)
        if not profile:
            profile = await profile_repo.create(
                ProfileCreate(
                    firebase_uid=f"invited_{uuid.uuid4().hex[:12]}",
                    email=email_clean,
                    display_name=email_clean.split("@")[0].replace(".", " ").capitalize(),
                    role="user",
                )
            )

        # Check if already a member
        existing = await self.workspace_repo.get_membership(workspace_id, profile.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {email_clean} is already a member of this workspace",
            )

        member = await self.workspace_repo.add_member(
            workspace_id=workspace_id,
            user_id=profile.id,
            role=role,
            invited_by=caller_id,
        )

        await self.audit_service.log(
            workspace_id=workspace_id,
            user_id=caller_id,
            action=AuditEventType.MEMBER_ADDED,
            resource_type="workspace_member",
            resource_id=member.id,
            new_state={"target_email": email_clean, "role": role.value},
        )
        return member, profile

    async def remove_member(
        self,
        workspace_id: UUID,
        caller_id: UUID,
        member_id: UUID,
    ) -> None:
        caller_membership = await self.workspace_repo.get_membership(workspace_id, caller_id)
        if not caller_membership or caller_membership.role not in [WorkspaceRole.OWNER.value, WorkspaceRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace owners or admins can remove team members",
            )

        target = await self.workspace_repo.get_member_by_id(member_id)
        if not target or target.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        if target.role == WorkspaceRole.OWNER.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove workspace owner")

        await self.workspace_repo.remove_member(workspace_id, member_id)
        await self.audit_service.log(
            workspace_id=workspace_id,
            user_id=caller_id,
            action=AuditEventType.MEMBER_REMOVED,
            resource_type="workspace_member",
            resource_id=member_id,
        )

    async def get_directory(self, search: Optional[str] = None) -> List[dict]:
        return await self.workspace_repo.list_directory(search)

    async def join_workspace(
        self,
        workspace_id: UUID,
        user: Profile,
        display_name: Optional[str] = None,
        job_title: Optional[str] = None,
    ) -> Workspace:
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company workspace not found")

        existing = await self.workspace_repo.get_membership(workspace_id, user.id)
        if not existing:
            await self.workspace_repo.add_member(
                workspace_id=workspace_id,
                user_id=user.id,
                role=WorkspaceRole.MEMBER,
            )
            await self.audit_service.log(
                workspace_id=workspace_id,
                user_id=user.id,
                action=AuditEventType.MEMBER_ADDED,
                resource_type="workspace_member",
                resource_id=workspace.id,
                new_state={"role": "member", "joined_via": "employee_onboarding", "job_title": job_title},
            )

        if display_name and display_name.strip():
            profile_repo = ProfileRepository(self.session)
            await profile_repo.update(user.id, ProfileUpdate(display_name=display_name.strip()))

        return workspace

    async def onboard_company(self, req: CompanyOnboardingRequest, user: Profile) -> Tuple[Workspace, Optional[Any]]:
        # 1. Update display name if provided
        if req.display_name and req.display_name.strip():
            profile_repo = ProfileRepository(self.session)
            await profile_repo.update(user.id, ProfileUpdate(display_name=req.display_name.strip()))

        # 2. Create workspace
        settings_dict = {}
        if req.industry:
            settings_dict["industry"] = req.industry
        if req.team_size:
            settings_dict["team_size"] = req.team_size

        ws_create = WorkspaceCreate(name=req.company_name, slug=req.slug)
        workspace = await self.create_workspace(ws_create, user)
        if settings_dict:
            workspace.settings = settings_dict
            await self.session.commit()
            await self.session.refresh(workspace)

        # 3. If asset details provided, create and authorize initial asset
        created_asset = None
        if req.asset_name and req.asset_name.strip():
            from app.services.asset_service import AssetService
            from app.services.authorization_service import AuthorizationService
            from app.schemas.asset import AssetCreate, AssetType, AssetCriticality
            from app.schemas.authorization import AuthorizationCreate, AuthorizationStatus

            asset_service = AssetService(self.session)
            atype = req.asset_type or "repository"
            try:
                asset_type_enum = AssetType(atype)
            except Exception:
                asset_type_enum = AssetType.REPOSITORY

            crit = req.asset_criticality or "high"
            try:
                crit_enum = AssetCriticality(crit)
            except Exception:
                crit_enum = AssetCriticality.HIGH

            asset_in = AssetCreate(
                name=req.asset_name.strip(),
                type=asset_type_enum,
                identifier=req.asset_identifier or "https://github.com/company/repo",
                environment=req.asset_environment or "production",
                criticality=crit_enum,
                description=f"Initial onboarding asset for {req.company_name}",
            )
            created_asset = await asset_service.create_asset(asset_in, workspace_id=workspace.id, user_id=user.id)

            # Auto-authorize asset for workspace owner
            auth_service = AuthorizationService(self.session)
            await auth_service.record_authorization(
                asset_id=created_asset.id,
                workspace_id=workspace.id,
                auth_in=AuthorizationCreate(
                    status=AuthorizationStatus.AUTHORIZED,
                    scope_limits={"environment": req.asset_environment or "production"},
                ),
                user_id=user.id,
            )

        return workspace, created_asset
