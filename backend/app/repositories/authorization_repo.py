from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.asset import AssetAuthorization
from app.schemas.authorization import AuthorizationCreate, AuthorizationStatus


class AuthorizationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_asset_id(self, asset_id: UUID) -> Optional[AssetAuthorization]:
        query = select(AssetAuthorization).where(AssetAuthorization.asset_id == asset_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        asset_id: UUID,
        workspace_id: UUID,
        auth_in: AuthorizationCreate,
        verified_by: Optional[UUID] = None,
        status: AuthorizationStatus = AuthorizationStatus.AUTHORIZED,
    ) -> AssetAuthorization:
        existing = await self.get_by_asset_id(asset_id)
        if existing:
            existing.authorization_type = auth_in.authorization_type.value
            existing.authorized_by = auth_in.authorized_by
            existing.evidence_urls = auth_in.evidence_urls
            existing.notes = auth_in.notes
            existing.expires_at = auth_in.expires_at
            existing.status = status.value
            existing.verified_by = verified_by
            existing.verified_at = datetime.utcnow() if status == AuthorizationStatus.AUTHORIZED else None
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        record = AssetAuthorization(
            asset_id=asset_id,
            workspace_id=workspace_id,
            authorization_type=auth_in.authorization_type.value,
            authorized_by=auth_in.authorized_by,
            evidence_urls=auth_in.evidence_urls,
            notes=auth_in.notes,
            expires_at=auth_in.expires_at,
            status=status.value,
            verified_by=verified_by,
            verified_at=datetime.utcnow() if status == AuthorizationStatus.AUTHORIZED else None,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def update_status(self, asset_id: UUID, status: AuthorizationStatus) -> Optional[AssetAuthorization]:
        query = (
            update(AssetAuthorization)
            .where(AssetAuthorization.asset_id == asset_id)
            .values(
                status=status.value,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.execute(query)
        await self.session.commit()
        return await self.get_by_asset_id(asset_id)
