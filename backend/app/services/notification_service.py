import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update
from sqlalchemy.orm import selectinload

from app.models.notification import (
    Notification,
    NotificationPreference,
    NotificationRule,
    NotificationDelivery,
)
from app.models.workspace import WorkspaceMember, Role
from app.models.profile import Profile
from app.schemas.notification import (
    SecurityEventEnvelope,
    NotificationPreferenceUpdate,
    NotificationRuleCreate,
)
from app.services.email_adapter import EmailAdapter
from app.core.logging import logger


class NotificationService:
    """
    Manages workspace recipient resolution, preference evaluation,
    in-app notification creation, and multi-channel delivery attempts.
    """

    SEVERITY_WEIGHTS = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    CATEGORY_MAP = {
        "scan.completed": "scans",
        "scan.failed": "scans",
        "finding.created": "findings",
        "finding.severity_changed": "findings",
        "attack_path.detected": "risk",
        "risk.critical_threshold": "risk",
        "security_team.completed": "general",
        "security_team.failed": "general",
        "remediation.proposed": "remediation",
        "remediation.approval_required": "remediation",
        "remediation.applied": "remediation",
        "remediation.rolled_back": "remediation",
        "verification.completed": "verification",
        "verification.regression_detected": "verification",
        "verification.human_review_required": "verification",
        "report.ready": "reports",
        "report.export_failed": "reports",
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_adapter = EmailAdapter()

    async def get_or_create_preferences(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> NotificationPreference:
        """Retrieves or initializes a user's notification preferences for a workspace."""
        stmt = select(NotificationPreference).where(
            NotificationPreference.workspace_id == workspace_id,
            NotificationPreference.user_id == user_id,
        )
        pref = (await self.db.execute(stmt)).scalar_one_or_none()
        if not pref:
            pref = NotificationPreference(
                workspace_id=workspace_id,
                user_id=user_id,
                categories={
                    "scans": True,
                    "findings": True,
                    "remediation": True,
                    "verification": True,
                    "reports": True,
                    "risk": True,
                },
                channels={"in_app": True, "email": True},
                min_severity="LOW",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(pref)
            await self.db.commit()
            await self.db.refresh(pref)
        return pref

    async def update_preferences(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        update_data: NotificationPreferenceUpdate,
    ) -> NotificationPreference:
        pref = await self.get_or_create_preferences(workspace_id, user_id)
        if update_data.categories is not None:
            current = dict(pref.categories)
            current.update(update_data.categories)
            pref.categories = current
        if update_data.channels is not None:
            current_ch = dict(pref.channels)
            current_ch.update(update_data.channels)
            pref.channels = current_ch
        if update_data.min_severity is not None:
            pref.min_severity = update_data.min_severity.upper()
        pref.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    async def dispatch_event(self, event: SecurityEventEnvelope) -> List[Notification]:
        """
        Processes a verified SecurityEventEnvelope, evaluates routing rules,
        determines eligible workspace recipients, and records notifications & deliveries.
        """
        category = self.CATEGORY_MAP.get(event.event_type, "general")
        severity = event.payload.get("severity", "MEDIUM").upper()
        event_weight = self.SEVERITY_WEIGHTS.get(severity, 2)

        # 1. Fetch workspace notification rules
        rule_stmt = select(NotificationRule).where(
            NotificationRule.workspace_id == event.workspace_id,
            NotificationRule.event_type == event.event_type,
            NotificationRule.enabled == True,
        )
        rule = (await self.db.execute(rule_stmt)).scalar_one_or_none()

        allowed_roles = rule.recipient_roles if rule else ["OWNER", "ADMIN", "ANALYST", "MEMBER"]
        dedup_window = rule.dedup_window_minutes if rule else 10

        # Critical actions restrict to governance roles
        if event.event_type in ("remediation.approval_required", "verification.human_review_required"):
            allowed_roles = [r for r in allowed_roles if r.upper() in ("OWNER", "ADMIN")]

        allowed_roles_lower = [r.lower() for r in allowed_roles]

        # 2. Resolve workspace members
        members_stmt = (
            select(WorkspaceMember, Profile)
            .join(Profile, WorkspaceMember.user_id == Profile.id)
            .where(
                WorkspaceMember.workspace_id == event.workspace_id,
                func.lower(WorkspaceMember.role).in_(allowed_roles_lower),
            )
        )
        members = (await self.db.execute(members_stmt)).all()

        created_notifications: List[Notification] = []

        for member_row in members:
            member = member_row[0]
            profile = member_row[1]
            user_id = member.user_id

            # 3. Preference check
            pref = await self.get_or_create_preferences(event.workspace_id, user_id)
            if not pref.categories.get(category, True):
                continue

            pref_weight = self.SEVERITY_WEIGHTS.get(pref.min_severity, 1)
            if event_weight < pref_weight:
                continue

            # 4. Deduplication window check
            if dedup_window > 0:
                cutoff = datetime.utcnow() - timedelta(minutes=dedup_window)
                dup_stmt = select(Notification).where(
                    Notification.workspace_id == event.workspace_id,
                    Notification.user_id == user_id,
                    Notification.type == event.event_type,
                    Notification.created_at >= cutoff,
                )
                if event.resource_id:
                    dup_stmt = dup_stmt.where(Notification.resource_id == event.resource_id)
                existing_dup = (await self.db.execute(dup_stmt)).first()
                if existing_dup:
                    logger.info("notification_deduplicated", user_id=str(user_id), event_type=event.event_type)
                    continue

            # 5. Build title and message
            title, message, link_url = self._format_notification_content(event)

            # Determine delivery channels
            channels_to_deliver = []
            if pref.channels.get("in_app", True):
                channels_to_deliver.append("in_app")
            if pref.channels.get("email", True):
                channels_to_deliver.append("email")

            if not channels_to_deliver:
                channels_to_deliver = ["in_app"]

            notification = Notification(
                workspace_id=event.workspace_id,
                user_id=user_id,
                event_id=event.id,
                category=category,
                type=event.event_type,
                title=title,
                message=message,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                link_url=link_url,
                channels=channels_to_deliver,
                read_at=None,
                created_at=datetime.utcnow(),
            )
            self.db.add(notification)
            await self.db.flush()

            # 6. Record Deliveries & Trigger Adapters
            for ch in channels_to_deliver:
                recipient_addr = profile.email if ch == "email" else str(user_id)
                delivery = NotificationDelivery(
                    notification_id=notification.id,
                    channel=ch,
                    recipient_address=recipient_addr,
                    status="pending",
                    attempt_count=1,
                    created_at=datetime.utcnow(),
                )

                if ch == "in_app":
                    delivery.status = "sent"
                    delivery.sent_at = datetime.utcnow()
                elif ch == "email" and profile.email:
                    email_result = await self.email_adapter.send_security_alert(
                        to_email=profile.email,
                        subject=f"[ShadowOps] {title}",
                        title=title,
                        message=message,
                        link_url=link_url,
                        event_metadata=event.payload,
                    )
                    delivery.status = email_result["status"]
                    delivery.last_error = email_result.get("error")
                    if email_result["status"] == "sent":
                        delivery.sent_at = datetime.utcnow()

                self.db.add(delivery)

            created_notifications.append(notification)

        await self.db.commit()
        return created_notifications

    def _format_notification_content(
        self, event: SecurityEventEnvelope
    ) -> Tuple[str, str, Optional[str]]:
        t = event.event_type
        p = event.payload

        if t == "remediation.approval_required":
            title = f"Remediation Approval Required: {p.get('proposal_title', 'Security Patch')}"
            message = (
                f"A new patch proposal for finding {p.get('finding_title', 'Vulnerability')} "
                "is awaiting human authorization before application."
            )
            link_url = f"/remediation/{event.resource_id}" if event.resource_id else "/remediation"

        elif t == "verification.human_review_required":
            title = "Verification Review Required: Fix Awaiting Sign-off"
            message = (
                f"Patch verification completed for finding {p.get('finding_id', '')}. "
                "A human reviewer must sign off before the finding can be closed."
            )
            link_url = f"/findings/{event.resource_id}" if event.resource_id else "/findings"

        elif t == "verification.regression_detected":
            title = "WARNING: Regression Detected During Patch Verification"
            message = (
                f"Verification detected new vulnerabilities or test failures for finding {p.get('finding_id', '')}."
            )
            link_url = "/findings"

        elif t == "risk.critical_threshold":
            title = "CRITICAL: Workspace Risk Score Threshold Exceeded"
            message = f"Workspace risk score has surged to {p.get('risk_score', 'N/A')} ({p.get('risk_band', 'CRITICAL')}). Immediate review is recommended."
            link_url = "/dashboard"

        elif t == "scan.completed":
            title = f"Scan Completed: {p.get('scanner_name', 'Security Scanner')}"
            message = f"Found {p.get('findings_count', 0)} issues across scanned targets."
            link_url = f"/scans/{event.resource_id}" if event.resource_id else "/scans"

        elif t == "scan.failed":
            title = "Scan Execution Failed"
            message = f"A security scan encountered an error: {p.get('error', 'Unknown failure')}."
            link_url = "/scans"

        elif t == "report.ready":
            title = f"Security Report Ready: {p.get('report_title', 'Export')}"
            message = f"The {p.get('report_type', 'security')} report is ready for download."
            link_url = f"/reports/{event.resource_id}" if event.resource_id else "/reports"

        else:
            title = f"Security Event: {t}"
            message = p.get("message", "A new security event occurred in your workspace.")
            link_url = "/dashboard"

        return title, message, link_url

    async def list_notifications(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        unread_only: bool = False,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Notification], int, int]:
        """Returns paginated notifications, total matching count, and overall unread count."""
        base_filters = [
            Notification.workspace_id == workspace_id,
            Notification.user_id == user_id,
        ]

        # Total unread count for user in workspace
        unread_count_stmt = select(func.count(Notification.id)).where(
            *base_filters, Notification.read_at.is_(None)
        )
        unread_count = (await self.db.execute(unread_count_stmt)).scalar() or 0

        # Filtered query
        query_filters = list(base_filters)
        if unread_only:
            query_filters.append(Notification.read_at.is_(None))
        if category:
            query_filters.append(Notification.category == category)

        total_stmt = select(func.count(Notification.id)).where(*query_filters)
        total = (await self.db.execute(total_stmt)).scalar() or 0

        stmt = (
            select(Notification)
            .where(*query_filters)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = (await self.db.execute(stmt)).scalars().all()
        return items, total, unread_count

    async def mark_as_read(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Optional[Notification]:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.workspace_id == workspace_id,
            Notification.user_id == user_id,
        )
        notif = (await self.db.execute(stmt)).scalar_one_or_none()
        if notif:
            notif.read_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(notif)
        return notif

    async def mark_all_as_read(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> int:
        now = datetime.utcnow()
        stmt = (
            update(Notification)
            .where(
                Notification.workspace_id == workspace_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=now)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount

    async def list_rules(self, workspace_id: uuid.UUID) -> List[NotificationRule]:
        stmt = select(NotificationRule).where(NotificationRule.workspace_id == workspace_id)
        return (await self.db.execute(stmt)).scalars().all()

    async def create_rule(
        self, workspace_id: uuid.UUID, rule_data: NotificationRuleCreate
    ) -> NotificationRule:
        rule = NotificationRule(
            workspace_id=workspace_id,
            name=rule_data.name,
            event_type=rule_data.event_type,
            enabled=rule_data.enabled,
            channels=rule_data.channels,
            recipient_roles=rule_data.recipient_roles,
            severity_filter=rule_data.severity_filter,
            dedup_window_minutes=rule_data.dedup_window_minutes,
            rate_limit_per_hour=rule_data.rate_limit_per_hour,
            created_at=datetime.utcnow(),
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule
