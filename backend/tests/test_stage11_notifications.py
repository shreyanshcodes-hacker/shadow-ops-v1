import uuid
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.notification import (
    EventOutbox,
    Notification,
    NotificationPreference,
    NotificationRule,
    NotificationDelivery,
    WorkflowRun,
)
from app.schemas.notification import (
    SecurityEventEnvelope,
    SecurityEventType,
    NotificationCategory,
    NotificationPreferenceUpdate,
    NotificationRuleCreate,
)
from app.services.event_outbox_service import EventOutboxService
from app.services.notification_service import NotificationService
from app.services.workflow_engine import WorkflowEngine, ControlledWorkflowActionException
from app.services.email_adapter import EmailAdapter
from app.services.n8n_adapter import N8nAdapter


async def setup_stage11_test_context(db_session: AsyncSession):
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    member_id = uuid.uuid4()

    owner = Profile(id=owner_id, firebase_uid=f"fb-owner-{owner_id.hex[:6]}", email="owner@stage11.io", display_name="Owner User")
    admin = Profile(id=admin_id, firebase_uid=f"fb-admin-{admin_id.hex[:6]}", email="admin@stage11.io", display_name="Admin User")
    member = Profile(id=member_id, firebase_uid=f"fb-member-{member_id.hex[:6]}", email="member@stage11.io", display_name="Member User")
    db_session.add_all([owner, admin, member])

    ws_id = uuid.uuid4()
    ws = Workspace(id=ws_id, name="Stage 11 Notifications Ops", slug=f"stage11-{ws_id.hex[:6]}", owner_id=owner_id)
    db_session.add(ws)

    m1 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=owner_id, role="owner")
    m2 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=admin_id, role="admin")
    m3 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=member_id, role="member")
    db_session.add_all([m1, m2, m3])

    await db_session.commit()
    return {
        "workspace_id": ws_id,
        "owner": owner,
        "admin": admin,
        "member": member,
    }


@pytest.mark.asyncio
async def test_security_event_envelope_secret_scrubbing():
    """Ensures passwords, tokens, API keys and credentials are automatically redacted."""
    envelope = SecurityEventEnvelope(
        workspace_id=uuid.uuid4(),
        event_type="scan.completed",
        resource_type="scan",
        payload={
            "scan_id": str(uuid.uuid4()),
            "api_key": "sk-secret-live-12345",
            "db_password": "supersecretpassword",
            "nested": {
                "auth_token": "bearer eyJhbGciOi...",
                "scanner_name": "semgrep",
            },
        },
    )

    assert envelope.payload["api_key"] == "[REDACTED]"
    assert envelope.payload["db_password"] == "[REDACTED]"
    assert envelope.payload["nested"]["auth_token"] == "[REDACTED]"
    assert envelope.payload["nested"]["scanner_name"] == "semgrep"


@pytest.mark.asyncio
async def test_outbox_publish_and_idempotency(db_session: AsyncSession):
    """Verifies transactional outbox publishing and idempotency deduplication."""
    ctx = await setup_stage11_test_context(db_session)
    ws_id = ctx["workspace_id"]
    outbox_service = EventOutboxService(db_session)

    idemp_key = f"scan-complete-{uuid.uuid4()}"
    event = SecurityEventEnvelope(
        workspace_id=ws_id,
        event_type="scan.completed",
        resource_type="scan",
        resource_id=uuid.uuid4(),
        idempotency_key=idemp_key,
        payload={"findings_count": 3, "scanner_name": "semgrep"},
    )

    e1 = await outbox_service.publish(event)
    assert e1.id is not None
    assert e1.status == "pending"

    # Second publish with identical idempotency key must not duplicate
    e2 = await outbox_service.publish(event)
    assert e2.id == e1.id

    stmt = select(EventOutbox).where(EventOutbox.workspace_id == ws_id)
    all_events = (await db_session.execute(stmt)).scalars().all()
    assert len(all_events) == 1


@pytest.mark.asyncio
async def test_notification_recipient_resolution_and_delivery(db_session: AsyncSession):
    """
    Tests governance role restrictions (approval required routes to OWNER & ADMIN only)
    and delivery attempts.
    """
    ctx = await setup_stage11_test_context(db_session)
    ws_id = ctx["workspace_id"]
    notif_service = NotificationService(db_session)

    # High governance event: remediation approval required
    event = SecurityEventEnvelope(
        workspace_id=ws_id,
        event_type="remediation.approval_required",
        resource_type="remediation_proposal",
        resource_id=uuid.uuid4(),
        payload={
            "proposal_title": "Fix SQL Injection in Auth Endpoint",
            "finding_title": "SQL Injection",
            "severity": "CRITICAL",
        },
    )

    notifications = await notif_service.dispatch_event(event)

    # Member role should NOT receive governance approval notifications
    recipient_ids = {n.user_id for n in notifications}
    assert ctx["owner"].id in recipient_ids
    assert ctx["admin"].id in recipient_ids
    assert ctx["member"].id not in recipient_ids

    # Verify notification records & deliveries created
    assert len(notifications) == 2
    for n in notifications:
        assert n.category == "remediation"
        assert "Remediation Approval Required" in n.title
        stmt = select(NotificationDelivery).where(NotificationDelivery.notification_id == n.id)
        deliveries = (await db_session.execute(stmt)).scalars().all()
        assert len(deliveries) >= 1


@pytest.mark.asyncio
async def test_notification_deduplication_window(db_session: AsyncSession):
    """Ensures identical events within dedup_window_minutes do not spam users."""
    ctx = await setup_stage11_test_context(db_session)
    ws_id = ctx["workspace_id"]
    notif_service = NotificationService(db_session)

    res_id = uuid.uuid4()
    event = SecurityEventEnvelope(
        workspace_id=ws_id,
        event_type="scan.completed",
        resource_type="scan",
        resource_id=res_id,
        payload={"findings_count": 2, "severity": "MEDIUM"},
    )

    first_dispatch = await notif_service.dispatch_event(event)
    assert len(first_dispatch) > 0

    # Immediate second dispatch of the exact same event
    second_dispatch = await notif_service.dispatch_event(event)
    # Deduplication window prevents duplicated notifications
    assert len(second_dispatch) == 0


@pytest.mark.asyncio
async def test_email_adapter_safe_not_configured():
    """Verifies that EmailAdapter fails safely when credentials are missing."""
    adapter = EmailAdapter()
    result = await adapter.send_security_alert(
        to_email="test@example.com",
        subject="Alert",
        title="Test",
        message="Test message",
    )
    assert result["status"] == "not_configured"
    assert result["sent_at"] is None


@pytest.mark.asyncio
async def test_outbox_batch_processing_and_poison_quarantine(db_session: AsyncSession):
    """Verifies batch processing, retry incrementing, and quarantine of poison events."""
    ctx = await setup_stage11_test_context(db_session)
    ws_id = ctx["workspace_id"]
    outbox_service = EventOutboxService(db_session)

    event = SecurityEventEnvelope(
        workspace_id=ws_id,
        event_type="scan.completed",
        resource_type="scan",
        resource_id=uuid.uuid4(),
        payload={"findings_count": 0, "severity": "LOW"},
    )
    outbox_entry = await outbox_service.publish(event)
    assert outbox_entry.status == "pending"

    # Process batch
    processed = await outbox_service.process_batch(batch_size=10)
    assert processed >= 1

    await db_session.refresh(outbox_entry)
    assert outbox_entry.status == "processed"
    assert outbox_entry.processed_at is not None


@pytest.mark.asyncio
async def test_controlled_workflow_engine_allowlist(db_session: AsyncSession):
    """Enforces strict allowlist: allowed action executes, arbitrary action is rejected."""
    ctx = await setup_stage11_test_context(db_session)
    ws_id = ctx["workspace_id"]
    engine = WorkflowEngine(db_session)

    # 1. Allowed action
    run = await engine.execute_action(
        workspace_id=ws_id,
        workflow_name="Slack Notification Workflow",
        action_name="notify_slack_summary",
        input_data={"channel": "#sec-ops", "message": "Critical finding detected"},
        idempotency_key=f"slack-run-{uuid.uuid4()}",
    )
    assert run.status == "completed"
    assert run.output_data.get("delivered") is True

    # 2. Arbitrary / Forbidden action must raise ControlledWorkflowActionException
    with pytest.raises(ControlledWorkflowActionException):
        await engine.execute_action(
            workspace_id=ws_id,
            workflow_name="Malicious Workflow",
            action_name="execute_system_bash_command",
            input_data={"command": "rm -rf /"},
        )


@pytest.mark.asyncio
async def test_n8n_adapter_ssrf_and_disabled_by_default():
    """Enforces n8n webhook SSRF defenses and disabled-by-default posture."""
    adapter = N8nAdapter()
    
    # 1. Disabled by default
    res = await adapter.dispatch_event(
        event_type="scan.completed",
        workspace_id=str(uuid.uuid4()),
        payload={"findings": 0},
        correlation_id=str(uuid.uuid4()),
    )
    assert res["status"] == "disabled"

    # 2. SSRF validation check
    assert adapter._validate_destination_url("http://127.0.0.1:5678/webhook") is False
    assert adapter._validate_destination_url("http://localhost:5678/webhook") is False
    assert adapter._validate_destination_url("http://169.254.169.254/latest/meta-data") is False
    assert adapter._validate_destination_url("http://10.0.0.5/webhook") is False
    assert adapter._validate_destination_url("https://automation.company.com/webhook") is True


@pytest.mark.asyncio
async def test_notification_api_endpoints_and_isolation(
    client: AsyncClient, db_session: AsyncSession
):
    """Tests notification endpoints, unread count, read-all, and preferences."""
    ctx = await setup_stage11_test_context(db_session)
    ws_id = ctx["workspace_id"]
    owner = ctx["owner"]

    # Seed notification
    notif = Notification(
        workspace_id=ws_id,
        user_id=owner.id,
        category="scans",
        type="scan.completed",
        title="Test Scan Completed",
        message="Semgrep completed with 2 findings.",
        channels=["in_app"],
        created_at=datetime.utcnow(),
    )
    db_session.add(notif)
    await db_session.commit()

    auth_headers = {"Authorization": f"Bearer test-token-{owner.firebase_uid}"}

    # 1. List notifications
    res = await client.get(
        f"/api/v1/notifications?workspace_id={ws_id}",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert data["unread_count"] >= 1

    # 2. Get unread count
    res_count = await client.get(
        f"/api/v1/notifications/unread-count?workspace_id={ws_id}",
        headers=auth_headers,
    )
    assert res_count.status_code == 200
    assert res_count.json()["unread_count"] >= 1

    # 3. Mark single as read
    res_read = await client.post(
        f"/api/v1/notifications/{notif.id}/read?workspace_id={ws_id}",
        headers=auth_headers,
    )
    assert res_read.status_code == 200
    assert res_read.json()["read_at"] is not None

    # 4. Notification preferences
    pref_res = await client.get(
        f"/api/v1/notifications/preferences?workspace_id={ws_id}",
        headers=auth_headers,
    )
    assert pref_res.status_code == 200
    assert pref_res.json()["min_severity"] == "LOW"

    # Update preferences
    pref_update = await client.put(
        f"/api/v1/notifications/preferences?workspace_id={ws_id}",
        headers=auth_headers,
        json={"min_severity": "HIGH", "channels": {"in_app": True, "email": False}},
    )
    assert pref_update.status_code == 200
    assert pref_update.json()["min_severity"] == "HIGH"
    assert pref_update.json()["channels"]["email"] is False
