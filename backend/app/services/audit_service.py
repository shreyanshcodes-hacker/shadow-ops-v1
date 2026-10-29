from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.audit_repo import AuditRepository
from app.schemas.audit import AuditLogCreate, AuditEventType
from app.models.audit import AuditLog
from app.core.logging import logger


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def log(
        self,
        workspace_id: UUID,
        action: AuditEventType,
        resource_type: str,
        user_id: Optional[UUID] = None,
        resource_id: Optional[UUID] = None,
        old_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        log_create = AuditLogCreate(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_state=old_state,
            new_state=new_state,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=uuid4(),
        )
        entry = await self.audit_repo.log_event(log_create)
        logger.info(
            "security_audit_event",
            workspace_id=str(workspace_id),
            action=action.value,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
        )
        return entry

    async def log_action(
        self,
        workspace_id: UUID,
        actor_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        event_name = action.replace(".", "_").upper()
        event_type = getattr(AuditEventType, event_name, AuditEventType.USER_AUTHENTICATED)
        rid = None
        if resource_id:
            try:
                rid = UUID(resource_id)
            except (ValueError, TypeError):
                rid = None

        return await self.log(
            workspace_id=workspace_id,
            action=event_type,
            resource_type=resource_type,
            user_id=actor_id,
            resource_id=rid,
            new_state=details,
        )
