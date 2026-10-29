from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.asset import Asset, AssetAuthorization
from app.schemas.asset import AssetCreate


class AssetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, asset_id: UUID) -> Optional[Asset]:
        query = (
            select(Asset)
            .options(selectinload(Asset.authorization))
            .where(and_(Asset.id == asset_id, Asset.deleted_at.is_(None)))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Asset]:
        query = (
            select(Asset)
            .options(selectinload(Asset.authorization))
            .where(and_(Asset.workspace_id == workspace_id, Asset.deleted_at.is_(None)))
            .order_by(Asset.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, asset_in: AssetCreate, workspace_id: UUID, user_id: UUID) -> Asset:
        config = asset_in.connection_config.copy()
        if asset_in.identifier:
            config["identifier"] = asset_in.identifier

        asset = Asset(
            workspace_id=workspace_id,
            name=asset_in.name,
            type=asset_in.type.value,
            subtype=asset_in.subtype,
            connection_config=config,
            criticality=asset_in.criticality.value,
            status="active",
            tags=asset_in.tags,
            created_by=user_id,
        )
        self.session.add(asset)
        await self.session.flush()

        # Create initial pending authorization record
        auth_record = AssetAuthorization(
            asset_id=asset.id,
            workspace_id=workspace_id,
            authorization_type="ownership",
            status="pending",
        )
        self.session.add(auth_record)
        await self.session.commit()
        return await self.get_by_id(asset.id)
