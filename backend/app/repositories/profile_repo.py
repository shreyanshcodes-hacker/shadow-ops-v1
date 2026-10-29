from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileUpdate


class ProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, profile_id: UUID) -> Optional[Profile]:
        query = select(Profile).where(Profile.id == profile_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_firebase_uid(self, firebase_uid: str) -> Optional[Profile]:
        query = select(Profile).where(Profile.firebase_uid == firebase_uid)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Profile]:
        query = select(Profile).where(Profile.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, profile_in: ProfileCreate) -> Profile:
        profile = Profile(
            firebase_uid=profile_in.firebase_uid,
            email=profile_in.email,
            display_name=profile_in.display_name,
            avatar_url=profile_in.avatar_url,
            role=profile_in.role,
            last_login_at=datetime.utcnow(),
        )
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update(self, profile_id: UUID, profile_in: ProfileUpdate) -> Optional[Profile]:
        data = profile_in.model_dump(exclude_unset=True)
        if not data:
            return await self.get_by_id(profile_id)

        query = (
            update(Profile)
            .where(Profile.id == profile_id)
            .values(**data)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(query)
        await self.session.commit()
        return await self.get_by_id(profile_id)

    async def touch_last_login(self, profile_id: UUID) -> None:
        query = (
            update(Profile)
            .where(Profile.id == profile_id)
            .values(last_login_at=datetime.utcnow())
        )
        await self.session.execute(query)
        await self.session.commit()
