from typing import Optional, List
from uuid import UUID
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.profile import Profile
from app.models.workspace import WorkspaceMember
from app.schemas.workspace import WorkspaceRole
from app.security.firebase import verify_firebase_id_token
from app.services.auth_service import AuthService
from app.repositories.workspace_repo import WorkspaceRepository

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Profile:
    """
    Core authentication dependency:
    Verifies incoming Firebase Bearer token and resolves/creates ShadowOps user Profile.
    Identity is strictly derived from the verified token.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = verify_firebase_id_token(credentials.credentials)
    auth_service = AuthService(db)
    profile = await auth_service.sync_firebase_user(claims)
    return profile


class RequireWorkspaceMember:
    """
    Verifies that the authenticated user is an active member of the specified workspace.
    """
    def __init__(self, allowed_roles: Optional[List[WorkspaceRole]] = None):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        workspace_id: UUID,
        current_user: Profile = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> WorkspaceMember:
        workspace_repo = WorkspaceRepository(db)
        membership = await workspace_repo.get_membership(workspace_id, current_user.id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workspace",
            )

        if self.allowed_roles:
            allowed_values = [r.value for r in self.allowed_roles]
            if membership.role not in allowed_values:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Action requires one of roles: {[r.value for r in self.allowed_roles]}",
                )

        return membership
