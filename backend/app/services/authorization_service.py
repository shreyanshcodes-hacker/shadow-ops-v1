from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.authorization_repo import AuthorizationRepository
from app.models.asset import AssetAuthorization
from app.schemas.authorization import AuthorizationCreate, AuthorizationStatus
from app.services.audit_service import AuditService
from app.schemas.audit import AuditEventType


class AuthorizationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.auth_repo = AuthorizationRepository(session)
        self.audit_service = AuditService(session)

    async def get_by_asset(self, asset_id: UUID) -> Optional[AssetAuthorization]:
        return await self.auth_repo.get_by_asset_id(asset_id)

    async def record_authorization(
        self,
        asset_id: UUID,
        workspace_id: UUID,
        auth_in: AuthorizationCreate,
        user_id: UUID,
        status_val: AuthorizationStatus = AuthorizationStatus.AUTHORIZED,
    ) -> AssetAuthorization:
        record = await self.auth_repo.create_or_update(
            asset_id=asset_id,
            workspace_id=workspace_id,
            auth_in=auth_in,
            verified_by=user_id,
            status=status_val,
        )
        await self.audit_service.log(
            workspace_id=workspace_id,
            user_id=user_id,
            action=AuditEventType.AUTHORIZATION_CREATED,
            resource_type="asset_authorization",
            resource_id=record.id,
            new_state={
                "asset_id": str(asset_id),
                "status": record.status,
                "type": record.authorization_type,
            },
        )
        return record

    async def verify_scan_authorization(self, asset_id: UUID, workspace_id: UUID) -> bool:
        """
        MANDATORY SECURITY GATE: NO AUTHORIZATION -> NO SCAN
        Strictly rejects:
        - Missing authorization records
        - Pending verification
        - Explicitly revoked permission
        - Expired authorizations
        """
        record = await self.auth_repo.get_by_asset_id(asset_id)
        if not record:
            await self.audit_service.log(
                workspace_id=workspace_id,
                action=AuditEventType.SCAN_BLOCKED,
                resource_type="asset",
                resource_id=asset_id,
                new_state={"reason": "MISSING_AUTHORIZATION"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="NO AUTHORIZATION -> NO SCAN: Asset has no authorization record on file.",
            )

        if record.status == "pending":
            await self.audit_service.log(
                workspace_id=workspace_id,
                action=AuditEventType.SCAN_BLOCKED,
                resource_type="asset",
                resource_id=asset_id,
                new_state={"reason": "PENDING_AUTHORIZATION"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="NO AUTHORIZATION -> NO SCAN: Asset authorization verification is still pending.",
            )

        if record.status in ["rejected", "revoked"]:
            await self.audit_service.log(
                workspace_id=workspace_id,
                action=AuditEventType.SCAN_BLOCKED,
                resource_type="asset",
                resource_id=asset_id,
                new_state={"reason": "REVOKED_AUTHORIZATION"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="NO AUTHORIZATION -> NO SCAN: Scan authorization has been revoked for this target.",
            )

        if record.expires_at:
            exp = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                await self.audit_service.log(
                    workspace_id=workspace_id,
                    action=AuditEventType.SCAN_BLOCKED,
                    resource_type="asset",
                    resource_id=asset_id,
                    new_state={"reason": "EXPIRED_AUTHORIZATION"},
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="NO AUTHORIZATION -> NO SCAN: Authorization for this target has expired.",
                )

        if record.status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="NO AUTHORIZATION -> NO SCAN: Unverified target authorization.",
            )

        return True
