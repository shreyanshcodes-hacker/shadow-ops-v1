-- ==============================================================================
-- SHADOWOPS — GOOGLE CLOUD SQL POSTGRESQL CANONICAL SCHEMA
-- Target Engine: PostgreSQL 15 / 16 (Google Cloud SQL)
-- Completely sanitized of Supabase-proprietary schemas and auth.uid() functions.
-- All 39 Application Tables, Constraints, Indexes, Triggers, and Roles Seed.
-- ==============================================================================

-- 1. Extensions (Cloud SQL supported)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- SECTION 1: IDENTITY, WORKSPACES & RBAC
-- ==============================================================================

-- 1. Profiles Table (Synchronized from Firebase Authentication)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    role TEXT DEFAULT 'user' NOT NULL CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    last_login_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_firebase_uid ON profiles(firebase_uid);
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- 2. Workspaces Table
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    owner_id UUID NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
    plan TEXT DEFAULT 'free' NOT NULL,
    settings JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_workspaces_owner_id ON workspaces(owner_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_slug ON workspaces(slug);

-- 3. Workspace Members Table
CREATE TABLE IF NOT EXISTS workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    invited_by UUID REFERENCES profiles(id),
    invited_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    joined_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_members_ws_user ON workspace_members(workspace_id, user_id);
CREATE INDEX IF NOT EXISTS idx_ws_members_ws_id ON workspace_members(workspace_id);
CREATE INDEX IF NOT EXISTS idx_ws_members_user_id ON workspace_members(user_id);

-- 4. Roles Reference Table
CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    permissions JSONB NOT NULL,
    description TEXT
);

INSERT INTO roles (id, name, permissions, description) VALUES
('owner', 'Owner', '{"all": true}', 'Full workspace access including deletion'),
('admin', 'Admin', '{"manage_members": true, "manage_assets": true, "manage_scans": true, "manage_findings": true, "manage_remediation": true, "manage_reports": true, "view_audit_logs": true}', 'Workspace administration'),
('member', 'Member', '{"create_assets": true, "manage_own_assets": true, "run_scans": true, "view_findings": true, "propose_remediation": true, "view_reports": true}', 'Active team member'),
('viewer', 'Viewer', '{"view_findings": true, "view_reports": true}', 'Read-only access')
ON CONFLICT (id) DO NOTHING;

-- ==============================================================================
-- SECTION 2: ASSETS & AUTHORIZATIONS
-- ==============================================================================

-- 5. Assets Table
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('repo', 'domain', 'ip', 'cloud')),
    target TEXT NOT NULL,
    environment TEXT DEFAULT 'production' NOT NULL CHECK (environment IN ('production', 'staging', 'development')),
    criticality TEXT DEFAULT 'medium' NOT NULL CHECK (criticality IN ('critical', 'high', 'medium', 'low')),
    is_active BOOLEAN DEFAULT true NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL,
    created_by UUID NOT NULL REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_assets_ws_id ON assets(workspace_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
CREATE INDEX IF NOT EXISTS idx_assets_active ON assets(is_active);

-- 6. Asset Authorizations Table
CREATE TABLE IF NOT EXISTS asset_authorizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'verified', 'rejected', 'expired')),
    evidence_type TEXT NOT NULL,
    evidence_payload JSONB DEFAULT '{}' NOT NULL,
    authorized_by UUID NOT NULL REFERENCES profiles(id),
    verified_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_asset_auth_asset_id ON asset_authorizations(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_auth_ws_id ON asset_authorizations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_asset_auth_status ON asset_authorizations(status);

-- ==============================================================================
-- SECTION 3: SCANS, SCAN EVENTS & AGENT RUNS
-- ==============================================================================

-- 7. Scans Table
CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_type TEXT DEFAULT 'full' NOT NULL CHECK (scan_type IN ('sast', 'dependency', 'secret', 'full')),
    status TEXT DEFAULT 'queued' NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    summary JSONB DEFAULT '{}' NOT NULL,
    findings_count INT DEFAULT 0,
    critical_count INT DEFAULT 0,
    high_count INT DEFAULT 0,
    medium_count INT DEFAULT 0,
    low_count INT DEFAULT 0,
    initiated_by UUID NOT NULL REFERENCES profiles(id),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scans_ws_id ON scans(workspace_id);
CREATE INDEX IF NOT EXISTS idx_scans_asset_id ON scans(asset_id);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans(created_at DESC);

-- 8. Scan Events Table
CREATE TABLE IF NOT EXISTS scan_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    level TEXT DEFAULT 'info' NOT NULL CHECK (level IN ('debug', 'info', 'warn', 'error')),
    message TEXT NOT NULL,
    payload JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scan_events_scan_id ON scan_events(scan_id);
CREATE INDEX IF NOT EXISTS idx_scan_events_ws_id ON scan_events(workspace_id);
CREATE INDEX IF NOT EXISTS idx_scan_events_scan_created ON scan_events(scan_id, created_at ASC);

-- 9. Agent Runs Table
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    agent_version TEXT DEFAULT 'v1.0' NOT NULL,
    status TEXT DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    inputs JSONB DEFAULT '{}' NOT NULL,
    outputs JSONB DEFAULT '{}' NOT NULL,
    cost_estimate_usd NUMERIC(10,4) DEFAULT 0.0000,
    duration_ms INT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_scan_id ON agent_runs(scan_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_ws_id ON agent_runs(workspace_id);

-- ==============================================================================
-- SECTION 4: FINDINGS, EVIDENCE, RISK & AI ANALYSIS
-- ==============================================================================

-- 10. Findings Table
CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    status TEXT DEFAULT 'open' NOT NULL CHECK (status IN ('open', 'in_review', 'remediated', 'accepted_risk', 'false_positive')),
    cwe_id TEXT,
    cve_id TEXT,
    fingerprint TEXT NOT NULL,
    file_path TEXT,
    line_number INT,
    code_snippet TEXT,
    raw_finding JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_findings_ws_fingerprint ON findings(workspace_id, fingerprint);
CREATE INDEX IF NOT EXISTS idx_findings_ws_id ON findings(workspace_id);
CREATE INDEX IF NOT EXISTS idx_findings_asset_id ON findings(asset_id);
CREATE INDEX IF NOT EXISTS idx_findings_scan_id ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(status);

-- 11. Finding Evidence Table
CREATE TABLE IF NOT EXISTS finding_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    data JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_finding_evidence_finding_id ON finding_evidence(finding_id);
CREATE INDEX IF NOT EXISTS idx_finding_evidence_ws_id ON finding_evidence(workspace_id);

-- 12. Risk Assessments Table
CREATE TABLE IF NOT EXISTS risk_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    score NUMERIC(5,2) NOT NULL,
    vector TEXT,
    factors JSONB DEFAULT '{}' NOT NULL,
    assessed_by TEXT DEFAULT 'system' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_risk_assess_finding_id ON risk_assessments(finding_id);
CREATE INDEX IF NOT EXISTS idx_risk_assess_ws_id ON risk_assessments(workspace_id);

-- 13. Finding AI Analysis Table
CREATE TABLE IF NOT EXISTS finding_ai_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    analysis_text TEXT NOT NULL,
    suggested_fix TEXT,
    confidence_score NUMERIC(3,2),
    model_used TEXT,
    tokens_used INT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_finding_ai_finding_id ON finding_ai_analysis(finding_id);
CREATE INDEX IF NOT EXISTS idx_finding_ai_ws_id ON finding_ai_analysis(workspace_id);

-- ==============================================================================
-- SECTION 5: ATTACK PATHS, RELATIONSHIPS & AI SECURITY TEAM
-- ==============================================================================

-- 14. Security Relationships Table
CREATE TABLE IF NOT EXISTS security_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    attributes JSONB DEFAULT '{}' NOT NULL,
    confidence NUMERIC(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sec_rel_ws_id ON security_relationships(workspace_id);
CREATE INDEX IF NOT EXISTS idx_sec_rel_source ON security_relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_sec_rel_target ON security_relationships(target_id);

-- 15. Risk Snapshots Table
CREATE TABLE IF NOT EXISTS risk_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    risk_score NUMERIC(5,2) NOT NULL,
    total_findings INT DEFAULT 0 NOT NULL,
    critical_findings INT DEFAULT 0 NOT NULL,
    attack_paths_count INT DEFAULT 0 NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_risk_snap_ws_id ON risk_snapshots(workspace_id);
CREATE INDEX IF NOT EXISTS idx_risk_snap_created ON risk_snapshots(created_at DESC);

-- 16. Attack Paths Table
CREATE TABLE IF NOT EXISTS attack_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    exploitability_score NUMERIC(5,2) NOT NULL,
    impact_score NUMERIC(5,2) NOT NULL,
    risk_score NUMERIC(5,2) NOT NULL,
    entry_point_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    target_asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'mitigated', 'accepted_risk')),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attack_paths_ws_id ON attack_paths(workspace_id);
CREATE INDEX IF NOT EXISTS idx_attack_paths_severity ON attack_paths(severity);

-- 17. Attack Path Nodes Table
CREATE TABLE IF NOT EXISTS attack_path_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attack_path_id UUID NOT NULL REFERENCES attack_paths(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    node_type TEXT NOT NULL CHECK (node_type IN ('asset', 'finding', 'threat_actor', 'privilege')),
    reference_id UUID NOT NULL,
    label TEXT NOT NULL,
    order_index INT NOT NULL,
    attributes JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ap_nodes_path_id ON attack_path_nodes(attack_path_id);
CREATE INDEX IF NOT EXISTS idx_ap_nodes_ws_id ON attack_path_nodes(workspace_id);

-- 18. Attack Path Edges Table
CREATE TABLE IF NOT EXISTS attack_path_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attack_path_id UUID NOT NULL REFERENCES attack_paths(id) ON DELETE CASCADE,
    source_node_id UUID NOT NULL REFERENCES attack_path_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES attack_path_nodes(id) ON DELETE CASCADE,
    relationship TEXT NOT NULL,
    weight NUMERIC(5,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ap_edges_path_id ON attack_path_edges(attack_path_id);

-- 19. Security Team Runs Table
CREATE TABLE IF NOT EXISTS security_team_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    agents_executed TEXT[] NOT NULL,
    findings_evaluated INT DEFAULT 0 NOT NULL,
    recommendations JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sec_team_ws_id ON security_team_runs(workspace_id);

-- ==============================================================================
-- SECTION 6: REMEDIATION & ROLLBACK
-- ==============================================================================

-- 20. Remediation Proposals Table
CREATE TABLE IF NOT EXISTS remediation_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    explanation TEXT NOT NULL,
    diff_content TEXT NOT NULL,
    fix_type TEXT NOT NULL CHECK (fix_type IN ('code_change', 'config_change', 'dependency_update', 'infrastructure_change', 'waf_rule', 'network_policy')),
    breaking_change_risk TEXT DEFAULT 'low' NOT NULL CHECK (breaking_change_risk IN ('low', 'medium', 'high')),
    status TEXT DEFAULT 'proposed' NOT NULL CHECK (status IN ('draft', 'proposed', 'approved', 'rejected', 'applied', 'reverted')),
    created_by TEXT DEFAULT 'ai_agent' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rem_prop_finding_id ON remediation_proposals(finding_id);
CREATE INDEX IF NOT EXISTS idx_rem_prop_ws_id ON remediation_proposals(workspace_id);
CREATE INDEX IF NOT EXISTS idx_rem_prop_status ON remediation_proposals(status);

-- 21. Remediation Approvals Table
CREATE TABLE IF NOT EXISTS remediation_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES remediation_proposals(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    approved_by UUID NOT NULL REFERENCES profiles(id),
    status TEXT NOT NULL CHECK (status IN ('approved', 'rejected')),
    comments TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rem_appr_proposal_id ON remediation_approvals(proposal_id);
CREATE INDEX IF NOT EXISTS idx_rem_appr_ws_id ON remediation_approvals(workspace_id);

-- 22. Remediation Validations Table
CREATE TABLE IF NOT EXISTS remediation_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES remediation_proposals(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    syntax_valid BOOLEAN DEFAULT false NOT NULL,
    tests_passed BOOLEAN DEFAULT false NOT NULL,
    validation_logs TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rem_val_proposal_id ON remediation_validations(proposal_id);
CREATE INDEX IF NOT EXISTS idx_rem_val_ws_id ON remediation_validations(workspace_id);

-- 23. Remediation Checkpoints Table
CREATE TABLE IF NOT EXISTS remediation_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES remediation_proposals(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    git_commit_sha TEXT NOT NULL,
    snapshot_sha256 TEXT NOT NULL,
    rollback_payload JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rem_chk_proposal_id ON remediation_checkpoints(proposal_id);
CREATE INDEX IF NOT EXISTS idx_rem_chk_ws_id ON remediation_checkpoints(workspace_id);

-- 24. Remediation Applications Table
CREATE TABLE IF NOT EXISTS remediation_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES remediation_proposals(id) ON DELETE CASCADE,
    applied_by UUID NOT NULL REFERENCES profiles(id),
    status TEXT NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    reverted_at TIMESTAMPTZ,
    logs TEXT
);

CREATE INDEX IF NOT EXISTS idx_rem_apply_proposal_id ON remediation_applications(proposal_id);

-- ==============================================================================
-- SECTION 7: INDEPENDENT VERIFICATION ENGINE
-- ==============================================================================

-- 25. Verification Runs Table (Legacy Stage 1)
CREATE TABLE IF NOT EXISTS verification_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES remediation_proposals(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    verification_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'passed', 'failed')),
    evidence JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_verif_runs_proposal_id ON verification_runs(proposal_id);
CREATE INDEX IF NOT EXISTS idx_verif_runs_ws_id ON verification_runs(workspace_id);

-- 26. Verification Jobs Table (Stage 9 Architecture)
CREATE TABLE IF NOT EXISTS verification_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    remediation_id UUID NOT NULL REFERENCES remediation_proposals(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'QUEUED' NOT NULL CHECK (status IN ('QUEUED', 'SCANNING', 'COMPARING', 'REGRESSION_CHECK', 'COMPLETED', 'FAILED')),
    policy_verdict TEXT DEFAULT 'INCONCLUSIVE' NOT NULL CHECK (policy_verdict IN ('VERIFIED_CANDIDATE', 'FAILED', 'INCONCLUSIVE', 'BLOCKED')),
    policy_version TEXT DEFAULT 'verification-policy-v1' NOT NULL,
    policy_reasons JSONB DEFAULT '[]' NOT NULL,
    initiated_by UUID NOT NULL REFERENCES profiles(id),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_verif_jobs_ws_id ON verification_jobs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_verif_jobs_rem_id ON verification_jobs(remediation_id);
CREATE INDEX IF NOT EXISTS idx_verif_jobs_status ON verification_jobs(status);
CREATE INDEX IF NOT EXISTS idx_verif_jobs_verdict ON verification_jobs(policy_verdict);

-- 27. Verification Comparisons Table
CREATE TABLE IF NOT EXISTS verification_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verification_job_id UUID NOT NULL REFERENCES verification_jobs(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    baseline_scan_id UUID REFERENCES scans(id),
    verification_scan_id UUID REFERENCES scans(id),
    baseline_finding_count INT DEFAULT 0 NOT NULL,
    reverified_finding_count INT DEFAULT 0 NOT NULL,
    eliminated_findings UUID[] DEFAULT '{}' NOT NULL,
    new_findings UUID[] DEFAULT '{}' NOT NULL,
    comparison_summary JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_verif_comp_job_id ON verification_comparisons(verification_job_id);
CREATE INDEX IF NOT EXISTS idx_verif_comp_ws_id ON verification_comparisons(workspace_id);

-- 28. Verification Regression Checks Table
CREATE TABLE IF NOT EXISTS verification_regression_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verification_job_id UUID NOT NULL REFERENCES verification_jobs(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    test_suite_status TEXT DEFAULT 'PENDING' NOT NULL,
    regressions_detected INT DEFAULT 0 NOT NULL,
    details JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_verif_reg_job_id ON verification_regression_checks(verification_job_id);
CREATE INDEX IF NOT EXISTS idx_verif_reg_ws_id ON verification_regression_checks(workspace_id);

-- 29. Verification Reviews Table
CREATE TABLE IF NOT EXISTS verification_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verification_job_id UUID NOT NULL REFERENCES verification_jobs(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    reviewed_by UUID NOT NULL REFERENCES profiles(id),
    decision TEXT NOT NULL CHECK (decision IN ('VERIFIED_APPROVED', 'REJECTED')),
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_verif_rev_job_id ON verification_reviews(verification_job_id);
CREATE INDEX IF NOT EXISTS idx_verif_rev_ws_id ON verification_reviews(workspace_id);

-- ==============================================================================
-- SECTION 8: REPORTS, CHAT, AUDIT & NOTIFICATIONS
-- ==============================================================================

-- 30. Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    report_type TEXT DEFAULT 'executive' NOT NULL CHECK (report_type IN ('executive', 'technical', 'compliance', 'delta')),
    format TEXT DEFAULT 'pdf' NOT NULL CHECK (format IN ('pdf', 'json', 'csv', 'html')),
    storage_object_id UUID,
    generated_by UUID NOT NULL REFERENCES profiles(id),
    metadata JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_ws_id ON reports(workspace_id);

-- 31. Chat Conversations Table
CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT,
    context_type TEXT CHECK (context_type IN ('general', 'finding', 'asset', 'scan', 'attack_path', 'report')),
    context_id UUID,
    message_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_conv_ws_id ON chat_conversations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chat_conv_user_id ON chat_conversations(user_id);

-- 32. Chat Messages Table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations UUID[],
    model_used TEXT,
    tokens_input INT,
    tokens_output INT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_msg_conv_id ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_msg_ws_id ON chat_messages(workspace_id);

-- 33. Audit Logs Table (Immutable append-only ledger)
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id UUID,
    old_state JSONB,
    new_state JSONB,
    ip_address INET,
    user_agent TEXT,
    request_id UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_ws_id_created ON audit_logs(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

-- 34. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    reference_type TEXT,
    reference_id UUID,
    channels TEXT[] DEFAULT '{in_app}',
    read_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, read_at);
CREATE INDEX IF NOT EXISTS idx_notifications_ws_created ON notifications(workspace_id, created_at);

-- 35. Event Outbox Table (Transactional Outbox Pattern)
CREATE TABLE IF NOT EXISTS event_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    event_name TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'processing', 'delivered', 'failed')),
    retry_count INT DEFAULT 0 NOT NULL,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_event_outbox_status ON event_outbox(status);
CREATE INDEX IF NOT EXISTS idx_event_outbox_ws_id ON event_outbox(workspace_id);

-- 36. Notification Preferences Table
CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    channels JSONB DEFAULT '{"email": true, "in_app": true, "webhook": false}' NOT NULL,
    mute_low_severity BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_notif_pref_ws_user ON notification_preferences(workspace_id, user_id);

-- 37. Notification Rules Table
CREATE TABLE IF NOT EXISTS notification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    event_filter TEXT NOT NULL,
    target_channel TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    config JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notif_rules_ws_id ON notification_rules(workspace_id);

-- 38. Notification Deliveries Table
CREATE TABLE IF NOT EXISTS notification_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outbox_id UUID NOT NULL REFERENCES event_outbox(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    destination TEXT NOT NULL,
    response_code INT,
    error_message TEXT,
    delivered_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notif_deliv_outbox ON notification_deliveries(outbox_id);
CREATE INDEX IF NOT EXISTS idx_notif_deliv_ws_id ON notification_deliveries(workspace_id);

-- 39. Workflow Runs Table
CREATE TABLE IF NOT EXISTS workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    workflow_name TEXT NOT NULL,
    status TEXT DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    input_data JSONB DEFAULT '{}' NOT NULL,
    output_data JSONB DEFAULT '{}' NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_ws_id ON workflow_runs(workspace_id);

-- ==============================================================================
-- SECTION 9: TRIGGERS & FUNCTIONS
-- ==============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DO $$
BEGIN
    DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
    DROP TRIGGER IF EXISTS update_workspaces_updated_at ON workspaces;
    DROP TRIGGER IF EXISTS update_assets_updated_at ON assets;
    DROP TRIGGER IF EXISTS update_asset_authorizations_updated_at ON asset_authorizations;
    DROP TRIGGER IF EXISTS update_scans_updated_at ON scans;
    DROP TRIGGER IF EXISTS update_findings_updated_at ON findings;
    DROP TRIGGER IF EXISTS update_attack_paths_updated_at ON attack_paths;
    DROP TRIGGER IF EXISTS update_remediation_proposals_updated_at ON remediation_proposals;
    DROP TRIGGER IF EXISTS update_chat_conversations_updated_at ON chat_conversations;
    DROP TRIGGER IF EXISTS update_verification_jobs_updated_at ON verification_jobs;
    DROP TRIGGER IF EXISTS update_notification_preferences_updated_at ON notification_preferences;
END $$;

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_assets_updated_at BEFORE UPDATE ON assets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_asset_authorizations_updated_at BEFORE UPDATE ON asset_authorizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_scans_updated_at BEFORE UPDATE ON scans FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_findings_updated_at BEFORE UPDATE ON findings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_attack_paths_updated_at BEFORE UPDATE ON attack_paths FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_remediation_proposals_updated_at BEFORE UPDATE ON remediation_proposals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_chat_conversations_updated_at BEFORE UPDATE ON chat_conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_verification_jobs_updated_at BEFORE UPDATE ON verification_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_notification_preferences_updated_at BEFORE UPDATE ON notification_preferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
