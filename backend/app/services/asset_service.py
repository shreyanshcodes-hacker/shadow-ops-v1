from typing import List, Optional
from uuid import UUID
import ipaddress
import re
from urllib.parse import urlparse
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.asset_repo import AssetRepository
from app.models.asset import Asset
from app.schemas.asset import AssetCreate
from app.services.audit_service import AuditService
from app.schemas.audit import AuditEventType


class AssetService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.asset_repo = AssetRepository(session)
        self.audit_service = AuditService(session)

    @staticmethod
    def validate_asset_identifier(target: Optional[str]) -> None:
        """
        Anti-SSRF and URI validation:
        Prohibits scanning loopback, private ranges, link-local metadata addresses.
        """
        if not target:
            return

        # Check URL or hostname
        parsed = urlparse(target if "://" in target else f"https://{target}")
        hostname = parsed.hostname or target

        # Check if IP address directly
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target references a private, loopback, or reserved network address (SSRF blocked).",
                )
        except ValueError:
            # Hostname format check
            if hostname.lower() in ["localhost", "127.0.0.1", "metadata.google.internal"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target resolves to a restricted loopback or cloud metadata hostname.",
                )

    async def create_asset(
        self,
        asset_in: AssetCreate,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Asset:
        # Validate target URI against SSRF
        self.validate_asset_identifier(asset_in.identifier)

        asset = await self.asset_repo.create(asset_in, workspace_id=workspace_id, user_id=user_id)
        await self.audit_service.log(
            workspace_id=workspace_id,
            user_id=user_id,
            action=AuditEventType.ASSET_CREATED,
            resource_type="asset",
            resource_id=asset.id,
            new_state={"name": asset.name, "type": asset.type, "criticality": asset.criticality},
        )
        return asset

    async def list_assets(self, workspace_id: UUID) -> List[Asset]:
        return await self.asset_repo.list_by_workspace(workspace_id)

    async def get_asset(self, asset_id: UUID) -> Asset:
        asset = await self.asset_repo.get_by_id(asset_id)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found",
            )
        return asset
