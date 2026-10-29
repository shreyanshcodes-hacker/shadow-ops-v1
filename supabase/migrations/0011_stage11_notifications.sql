-- Stage 11: Notifications, Event Processing & Controlled Workflow Automation
-- Migration 0011_stage11_notifications.sql

-- 1. Event Outbox Table (Transactional Event Sourcing & Reliability)
CREATE TABLE IF NOT EXISTS event_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    event_version VARCHAR(20) NOT NULL DEFAULT '1.0',
    actor_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    correlation_id UUID NOT NULL DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(255),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    next_retry_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_event_outbox_status_retry ON event_outbox(status, next_retry_at);
CREATE INDEX IF NOT EXISTS idx_event_outbox_workspace ON event_outbox(workspace_id);
CREATE INDEX IF NOT EXISTS idx_event_outbox_idempotency ON event_outbox(workspace_id, idempotency_key);

-- 2. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    event_id UUID REFERENCES event_outbox(id) ON DELETE SET NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    link_url TEXT,
    channels JSONB NOT NULL DEFAULT '["in_app"]'::jsonb,
    read_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_workspace ON notifications(user_id, workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, workspace_id) WHERE read_at IS NULL;

-- 3. Notification Preferences Table
CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    categories JSONB NOT NULL DEFAULT '{"scans": true, "findings": true, "remediation": true, "verification": true, "reports": true, "risk": true}'::jsonb,
    channels JSONB NOT NULL DEFAULT '{"in_app": true, "email": true}'::jsonb,
    min_severity VARCHAR(20) NOT NULL DEFAULT 'LOW',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    UNIQUE(workspace_id, user_id)
);

-- 4. Notification Rules Table (Workspace level policy & routing)
CREATE TABLE IF NOT EXISTS notification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    channels JSONB NOT NULL DEFAULT '["in_app"]'::jsonb,
    recipient_roles JSONB NOT NULL DEFAULT '["OWNER", "ADMIN", "ANALYST"]'::jsonb,
    severity_filter JSONB NOT NULL DEFAULT '["CRITICAL", "HIGH", "MEDIUM", "LOW"]'::jsonb,
    dedup_window_minutes INTEGER NOT NULL DEFAULT 10,
    rate_limit_per_hour INTEGER NOT NULL DEFAULT 60,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_notification_rules_ws_event ON notification_rules(workspace_id, event_type);

-- 5. Notification Deliveries Table
CREATE TABLE IF NOT EXISTS notification_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL,
    recipient_address VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_notification_deliveries_status ON notification_deliveries(status);

-- 6. Workflow Runs Table (Controlled Automation Audit Trail)
CREATE TABLE IF NOT EXISTS workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    workflow_name VARCHAR(100) NOT NULL,
    trigger_event_id UUID REFERENCES event_outbox(id) ON DELETE SET NULL,
    action_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    idempotency_key VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_workspace ON workflow_runs(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_idempotency ON workflow_runs(workspace_id, idempotency_key);
