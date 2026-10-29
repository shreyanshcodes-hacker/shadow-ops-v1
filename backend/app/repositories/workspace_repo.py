from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.workspace import Workspace, WorkspaceMember
from app.models.profile import Profile
from app.schemas.workspace import WorkspaceCreate, WorkspaceRole


class WorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, workspace_id: UUID) -> Optional[Workspace]:
        query = select(Workspace).where(
            and_(Workspace.id == workspace_id, Workspace.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Workspace]:
        query = select(Workspace).where(
            and_(Workspace.slug == slug, Workspace.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> List[Workspace]:
        query = (
            select(Workspace)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .where(
                and_(
                    WorkspaceMember.user_id == user_id,
                    Workspace.deleted_at.is_(None),
                )
            )
            .order_by(Workspace.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, workspace_in: WorkspaceCreate, owner_id: UUID) -> Workspace:
        slug = workspace_in.slug or workspace_in.name.lower().replace(" ", "-").replace("_", "-")
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while await self.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        workspace = Workspace(
            name=workspace_in.name,
            slug=slug,
            owner_id=owner_id,
            plan="free",
            settings={},
        )
        self.session.add(workspace)
        await self.session.flush()

        # Add owner as workspace member
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER.value,
            joined_at=datetime.utcnow(),
        )
        self.session.add(membership)
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def get_membership(self, workspace_id: UUID, user_id: UUID) -> Optional[WorkspaceMember]:
        query = select(WorkspaceMember).where(
            and_(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceRole,
        invited_by: Optional[UUID] = None,
    ) -> WorkspaceMember:
        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role.value,
            invited_by=invited_by,
            joined_at=datetime.utcnow(),
        )
        self.session.add(membership)
        await self.session.commit()
        await self.session.refresh(membership)
        return membership

    async def get_member_by_id(self, member_id: UUID) -> Optional[WorkspaceMember]:
        query = select(WorkspaceMember).where(WorkspaceMember.id == member_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def remove_member(self, workspace_id: UUID, member_id: UUID) -> bool:
        stmt = delete(WorkspaceMember).where(
            and_(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.id == member_id,
            )
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0

    async def get_members(self, workspace_id: UUID) -> List[Tuple[WorkspaceMember, Profile]]:
        query = (
            select(WorkspaceMember, Profile)
            .join(Profile, WorkspaceMember.user_id == Profile.id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.all())
