from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.profile_repo import ProfileRepository
from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileResponse
from app.core.logging import logger


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.profile_repo = ProfileRepository(session)

    async def sync_firebase_user(self, firebase_claims: Dict[str, Any]) -> Profile:
        """
        Sync or retrieve a ShadowOps Profile from cryptographically verified Firebase claims.
        Never trust client-supplied identity attributes.
        """
        firebase_uid = firebase_claims.get("uid") or firebase_claims.get("sub")
        if not firebase_uid:
            raise ValueError("Firebase token missing subject/UID claim")

        email = firebase_claims.get("email")
        if not email:
            email = f"{firebase_uid}@shadowops.internal"

        # Check existing profile
        profile = await self.profile_repo.get_by_firebase_uid(firebase_uid)
        if profile:
            await self.profile_repo.touch_last_login(profile.id)
            await self.session.refresh(profile)
            return profile

        # First-time profile creation
        display_name = firebase_claims.get("name") or firebase_claims.get("display_name") or email.split("@")[0]
        avatar_url = firebase_claims.get("picture") or firebase_claims.get("avatar_url")

        profile_create = ProfileCreate(
            firebase_uid=firebase_uid,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            role="user",
        )
        profile = await self.profile_repo.create(profile_create)
        logger.info("user_profile_created", profile_id=str(profile.id), email=email)
        return profile
