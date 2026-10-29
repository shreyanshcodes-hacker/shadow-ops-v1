from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogCreate


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(self, log_in: AuditLogCreate) -> AuditLog:
        audit_entry = AuditLog(
            workspace_id=log_in.workspace_id,
            user_id=log_in.user_id,
            action=log_in.action.value,
            resource_type=log_in.resource_type,
            resource_id=log_in.resource_id,
            old_state=log_in.old_state,
            new_state=log_in.new_state,
            ip_address=log_in.ip_address,
            user_agent=log_in.user_agent,
            request_id=log_in.request_id,
            created_at=datetime.utcnow(),
        )
        self.session.add(audit_entry)
        await self.session.commit()
        await self.session.refresh(audit_entry)
        return audit_entry

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[AuditLog]:
        query = (
            select(AuditLog)
            .where(AuditLog.workspace_id == workspace_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
