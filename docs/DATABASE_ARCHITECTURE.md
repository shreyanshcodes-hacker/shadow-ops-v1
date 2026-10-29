# DATABASE ARCHITECTURE — SHADOWOPS

## 1. Relational Model Overview & Core Principles

The ShadowOps persistence layer is built on **Supabase PostgreSQL 16+**. It is designed for multi-tenant isolation, tamper-evident auditability, high query performance, and graph-based threat relationship modeling.

### Core Principles
1. **Mandatory Row Level Security (RLS)**: Every tenant-facing table includes `workspace_id` and enforces database-level RLS policies. No tenant query can view or mutate records belonging to another workspace.
2. **Explicit Foreign Key Constraints**: All relational integrity is enforced directly at the database engine level (`ON DELETE CASCADE` or `ON DELETE RESTRICT`).
3. **Immutable Audit Trails**: High-consequence tables (`audit_logs`, `scan_events`, `remediation_approvals`) are append-only.
4. **Structured JSONB for Extensibility**: Rapidly evolving security metadata, Semgrep rule outputs, attack graph coordinates, and AI reasoning traces leverage PostgreSQL `JSONB` with GIN indexes.
5. **Soft Deletes**: Critical assets, workspaces, and findings utilize `deleted_at TIMESTAMPTZ` for compliance retention and recovery.

---

## 2. Comprehensive Table Specifications

---

### 1. `profiles`
- **Purpose**: Extends Firebase Authentication identity with ShadowOps application-level user attributes and platform administration privileges.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `firebase_uid`: `TEXT NOT NULL UNIQUE` (Firebase Auth UID)
  - `email`: `TEXT NOT NULL UNIQUE`
  - `display_name`: `TEXT`
  - `avatar_url`: `TEXT`
  - `system_role`: `TEXT NOT NULL DEFAULT 'user'` ('user', 'super_admin')
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `updated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `last_sign_in_at`: `TIMESTAMPTZ`
- **Relationships**: 1-to-many with `workspace_members`, `audit_logs`, `scans` (triggered_by), `chat_conversations`.
- **Indexes**: `idx_profiles_firebase_uid` (UNIQUE), `idx_profiles_email` (UNIQUE).
- **Security Considerations**: Users can only read/update their own profile record. System role escalation requires platform super-admin privileges.
- **Workspace Ownership**: Global entity; associated with workspaces via `workspace_members`.
- **Lifecycle**: Created automatically on first authenticated login via backend sync trigger.

---

### 2. `workspaces`
- **Purpose**: Top-level multi-tenant boundary. Encloses all assets, scans, findings, attack paths, and team members.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `name`: `TEXT NOT NULL`
  - `slug`: `TEXT NOT NULL UNIQUE` (URL slug)
  - `owner_id`: `UUID NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT`
  - `tier`: `TEXT NOT NULL DEFAULT 'starter'` ('starter', 'growth', 'enterprise')
  - `settings`: `JSONB NOT NULL DEFAULT '{}'` (notification webhooks, scan defaults)
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `updated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `deleted_at`: `TIMESTAMPTZ` (Soft delete)
- **Relationships**: Parent of `workspace_members`, `assets`, `scans`, `findings`, `attack_paths`, `reports`, `audit_logs`.
- **Indexes**: `idx_workspaces_slug` (UNIQUE), `idx_workspaces_owner_id`.
- **Security Considerations**: Deletion restricted to workspace owner. RLS ensures only active members can access workspace data.
- **Workspace Ownership**: Self (Root of hierarchy).
- **Lifecycle**: Created by user onboarding. Soft-deleted on cancellation; hard purge after 90 days.

---

### 3. `workspace_members`
- **Purpose**: Many-to-many junction joining `profiles` to `workspaces` with role-based access control.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `user_id`: `UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE`
  - `role`: `TEXT NOT NULL DEFAULT 'member'` ('owner', 'admin', 'member', 'viewer')
  - `invited_by`: `UUID REFERENCES profiles(id)`
  - `joined_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `workspaces` and `profiles`.
- **Indexes**: `uq_workspace_member` (UNIQUE `workspace_id, user_id`), `idx_ws_members_user_id`.
- **Security Considerations**: Prevents cross-tenant access. RLS checks membership in this table for every workspace-scoped query.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Created when a user creates a workspace or accepts an invitation; removed on member offboarding.

---

### 4. `roles` (Reference Table)
- **Purpose**: Static catalog defining role capabilities, granular permission bitmasks, and action gates.
- **Important Fields**:
  - `id`: `TEXT PRIMARY KEY` ('owner', 'admin', 'member', 'viewer')
  - `name`: `TEXT NOT NULL`
  - `permissions`: `JSONB NOT NULL` (e.g. `{"can_scan": true, "can_approve_fix": true}`)
  - `description`: `TEXT`
- **Relationships**: Referenced by `workspace_members.role`.
- **Indexes**: `PRIMARY KEY (id)`.
- **Security Considerations**: Read-only reference table. Hardcoded system permissions.
- **Workspace Ownership**: System global.
- **Lifecycle**: Seeded during migration; immutable at runtime.

---

### 5. `assets`
- **Purpose**: Represents digital assets subject to security inspection (git repositories, REST/GraphQL APIs, domain/infrastructure targets, web apps).
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `name`: `TEXT NOT NULL`
  - `asset_type`: `TEXT NOT NULL` ('repository', 'api', 'infrastructure', 'application')
  - `target_uri`: `TEXT NOT NULL` (e.g., git clone URL, base domain, API endpoint)
  - `criticality`: `TEXT NOT NULL DEFAULT 'medium'` ('low', 'medium', 'high', 'critical')
  - `environment`: `TEXT NOT NULL DEFAULT 'production'` ('production', 'staging', 'development')
  - `metadata`: `JSONB NOT NULL DEFAULT '{}'` (branch, language, tech stack hints)
  - `status`: `TEXT NOT NULL DEFAULT 'active'` ('active', 'paused', 'archived')
  - `created_by`: `UUID NOT NULL REFERENCES profiles(id)`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `updated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `deleted_at`: `TIMESTAMPTZ`
- **Relationships**: Belongs to `workspaces`; 1-to-1 with `asset_authorizations`; 1-to-many with `scans`, `findings`.
- **Indexes**: `idx_assets_workspace_id`, `idx_assets_type_status`.
- **Security Considerations**: Target URIs are strictly validated against SSRF blocklists (private IPs, loopback, cloud metadata endpoints).
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Active during lifecycle; soft-deleted when retired by team.

---

### 6. `asset_authorizations`
- **Purpose**: Cryptographic and factual proof of scan authorization. Enforces **NO AUTHORIZATION $\longrightarrow$ NO SCAN**.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `asset_id`: `UUID NOT NULL UNIQUE REFERENCES assets(id) ON DELETE CASCADE`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `authorization_method`: `TEXT NOT NULL` ('dns_txt_token', 'http_challenge', 'github_oauth_app', 'signed_agreement')
  - `verification_token`: `TEXT` (Randomized challenge string)
  - `verification_data`: `JSONB NOT NULL DEFAULT '{}'` (DNS records, OAuth installation ID, signed signature)
  - `status`: `TEXT NOT NULL DEFAULT 'pending'` ('pending', 'verified', 'revoked', 'expired')
  - `verified_at`: `TIMESTAMPTZ`
  - `expires_at`: `TIMESTAMPTZ`
  - `verified_by`: `UUID REFERENCES profiles(id)`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `updated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: 1-to-1 with `assets`.
- **Indexes**: `idx_asset_auth_asset_id` (UNIQUE), `idx_asset_auth_status`.
- **Security Considerations**: The backend scan runner queries this table directly. If `status != 'verified'` or `expires_at < now()`, the scan execution is strictly aborted.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Created when asset is added; marked `verified` upon proof validation; revoked on request or expiration.

---

### 7. `scans`
- **Purpose**: Records individual security scan operations, lifecycle states, phase progression, and execution summaries.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `asset_id`: `UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE`
  - `scan_type`: `TEXT NOT NULL` ('full', 'code_sast', 'recon', 'dependency_sca')
  - `status`: `TEXT NOT NULL DEFAULT 'queued'` ('queued', 'running', 'completed', 'failed', 'cancelled')
  - `current_phase`: `TEXT NOT NULL DEFAULT 'initialization'`
  - `progress_pct`: `INT NOT NULL DEFAULT 0`
  - `triggered_by`: `UUID NOT NULL REFERENCES profiles(id)`
  - `started_at`: `TIMESTAMPTZ`
  - `completed_at`: `TIMESTAMPTZ`
  - `duration_ms`: `INT`
  - `findings_summary`: `JSONB NOT NULL DEFAULT '{"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}'`
  - `error_message`: `TEXT`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `updated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `workspaces` and `assets`; 1-to-many with `scan_events`, `agent_runs`, `findings`, `attack_paths`.
- **Indexes**: `idx_scans_workspace_id`, `idx_scans_asset_id`, `idx_scans_status_created`.
- **Security Considerations**: Authorization verification is checked at creation and re-verified at execution start.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Initiated as `queued`; transitions to `running`, ending in `completed`, `failed`, or `cancelled`. Retained based on workspace plan.

---

### 8. `scan_events`
- **Purpose**: Append-only event stream recording fine-grained progress, agent transitions, and real-time logs for SSE UI streaming.
- **Important Fields**:
  - `id`: `BIGSERIAL PRIMARY KEY`
  - `scan_id`: `UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `phase`: `TEXT NOT NULL` ('authorization_check', 'recon', 'code_analysis', 'ai_analysis', 'risk_scoring')
  - `event_type`: `TEXT NOT NULL` ('phase_start', 'phase_end', 'agent_started', 'finding_discovered', 'log', 'error')
  - `message`: `TEXT NOT NULL`
  - `payload`: `JSONB NOT NULL DEFAULT '{}'`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `scans`.
- **Indexes**: `idx_scan_events_scan_id_id` (`scan_id, id ASC`).
- **Security Considerations**: Append-only; contains sanitized telemetry with no secret tokens or raw credentials.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Inserted continuously during scan execution; purged with parent scan or after 90 days.

---

### 9. `agent_runs`
- **Purpose**: Audits the execution, model usage, token consumption, and outputs of individual specialized AI security agents.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `scan_id`: `UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `agent_type`: `TEXT NOT NULL` ('recon', 'code_security', 'dependency', 'threat_analyst', 'risk_analyst', 'remediation', 'verification', 'reporting')
  - `model_name`: `TEXT NOT NULL` ('gemini-1.5-pro', 'gemini-1.5-flash', 'grok')
  - `status`: `TEXT NOT NULL DEFAULT 'running'` ('running', 'completed', 'failed', 'timed_out')
  - `prompt_tokens`: `INT NOT NULL DEFAULT 0`
  - `completion_tokens`: `INT NOT NULL DEFAULT 0`
  - `cost_usd`: `NUMERIC(10, 6) NOT NULL DEFAULT 0.0`
  - `input_context_summary`: `JSONB`
  - `raw_output_summary`: `JSONB`
  - `duration_ms`: `INT`
  - `error_message`: `TEXT`
  - `started_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `completed_at`: `TIMESTAMPTZ`
- **Relationships**: Belongs to `scans` and `workspaces`.
- **Indexes**: `idx_agent_runs_scan_id`, `idx_agent_runs_workspace_id`.
- **Security Considerations**: Tracks LLM token usage and enforces cost capping. Sanitizes sensitive data before recording input context summaries.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Created when agent begins processing; marked completed upon output schema validation.

---

### 10. `findings`
- **Purpose**: Canonical, normalized security findings discovered by tools (Semgrep, Recon) or synthesized by AI agents.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `scan_id`: `UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE`
  - `asset_id`: `UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE`
  - `fingerprint`: `TEXT NOT NULL` (Deterministic SHA-256 hash for deduplication)
  - `title`: `TEXT NOT NULL`
  - `description`: `TEXT NOT NULL`
  - `severity`: `TEXT NOT NULL` ('critical', 'high', 'medium', 'low', 'info')
  - `source`: `TEXT NOT NULL` ('semgrep_sast', 'dependency_sca', 'recon', 'ai_synthesis')
  - `rule_id`: `TEXT` (e.g., 'python.django.security.injection.sql')
  - `cwe_ids`: `TEXT[] NOT NULL DEFAULT '{}'`
  - `cve_ids`: `TEXT[] NOT NULL DEFAULT '{}'`
  - `owasp_category`: `TEXT`
  - `file_path`: `TEXT`
  - `line_start`: `INT`
  - `line_end`: `INT`
  - `status`: `TEXT NOT NULL DEFAULT 'open'` ('open', 'triaged', 'in_remediation', 'fixed', 'false_positive', 'accepted')
  - `risk_score`: `NUMERIC(5, 2)` (0.00 - 100.00)
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `updated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `scans`, `assets`; 1-to-many with `finding_evidence`, `remediation_proposals`, `verification_runs`; 1-to-1 with `risk_assessments`.
- **Indexes**: `idx_findings_workspace_status`, `idx_findings_scan_id`, `idx_findings_fingerprint_asset` (`asset_id, fingerprint`).
- **Security Considerations**: Strict RLS. Deduplicated per asset using fingerprint hashing.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Created upon scan normalization; transitions through triage and remediation; closed upon empirical verification.

---

### 11. `finding_evidence`
- **Purpose**: Stores concrete proof, AST snippets, HTTP transcripts, and provenance linking findings to physical evidence.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `finding_id`: `UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `evidence_type`: `TEXT NOT NULL` ('code_snippet', 'ast_dump', 'http_request_response', 'dns_log', 'sarif_raw')
  - `content`: `JSONB NOT NULL` (Structured evidence payload)
  - `storage_path`: `TEXT` (Supabase Storage reference if large binary/screenshot)
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `findings`.
- **Indexes**: `idx_evidence_finding_id`, `idx_evidence_workspace_id`.
- **Security Considerations**: Secrets and authorization tokens discovered in dumps are redacted/masked before storage.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Immutable once created; destroyed if parent finding is deleted.

---

### 12. `risk_assessments`
- **Purpose**: Stores the deterministic mathematical risk calculation breakdown and formula factors for every finding.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `finding_id`: `UUID NOT NULL UNIQUE REFERENCES findings(id) ON DELETE CASCADE`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `base_severity_score`: `NUMERIC(5, 2) NOT NULL` (0 - 100)
  - `exploitability_factor`: `NUMERIC(5, 2) NOT NULL` (0 - 100)
  - `exposure_factor`: `NUMERIC(5, 2) NOT NULL` (0 - 100)
  - `asset_criticality_factor`: `NUMERIC(5, 2) NOT NULL` (0 - 100)
  - `confidence_factor`: `NUMERIC(5, 2) NOT NULL` (0 - 100)
  - `attack_path_impact`: `NUMERIC(5, 2) NOT NULL DEFAULT 0.0` (0 - 100)
  - `final_score`: `NUMERIC(5, 2) NOT NULL` (0 - 100)
  - `factor_breakdown`: `JSONB NOT NULL` (Traceable weights and variables)
  - `formula_version`: `TEXT NOT NULL DEFAULT 'v1.0'`
  - `calculated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: 1-to-1 with `findings`.
- **Indexes**: `idx_risk_assessments_finding_id` (UNIQUE), `idx_risk_assessments_final_score`.
- **Security Considerations**: Fully deterministic and explainable; AI provides input attributes, but math is computed server-side.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Calculated during scan risk phase; recalculated when finding context changes.

---

### 13. `attack_paths`
- **Purpose**: Graph containers representing multi-hop breach chains leading from attacker entry points to critical assets.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `scan_id`: `UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE`
  - `title`: `TEXT NOT NULL`
  - `description`: `TEXT NOT NULL`
  - `entry_point`: `TEXT NOT NULL`
  - `target_crown_jewel`: `TEXT NOT NULL`
  - `aggregate_risk_score`: `NUMERIC(5, 2) NOT NULL` (0 - 100)
  - `node_count`: `INT NOT NULL DEFAULT 0`
  - `edge_count`: `INT NOT NULL DEFAULT 0`
  - `status`: `TEXT NOT NULL DEFAULT 'active'` ('active', 'mitigated', 'broken')
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `updated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `scans`; 1-to-many with `attack_path_nodes`, `attack_path_edges`.
- **Indexes**: `idx_attack_paths_workspace_id`, `idx_attack_paths_scan_id`.
- **Security Considerations**: Visualizes cross-finding exploitation risks for prioritizing top bottlenecks.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Constructed during correlation phase; marked `mitigated` when any bottleneck node is verified fixed.

---

### 14. `attack_path_nodes`
- **Purpose**: Individual vertices in an attack path graph (representing an entry point, an asset, a finding, or a credential store).
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `attack_path_id`: `UUID NOT NULL REFERENCES attack_paths(id) ON DELETE CASCADE`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `node_type`: `TEXT NOT NULL` ('entry_point', 'vulnerability', 'asset', 'credential', 'data_store')
  - `label`: `TEXT NOT NULL`
  - `asset_id`: `UUID REFERENCES assets(id)`
  - `finding_id`: `UUID REFERENCES findings(id)`
  - `metadata`: `JSONB NOT NULL DEFAULT '{}'` (UI graph coordinates, technical attributes)
- **Relationships**: Belongs to `attack_paths`.
- **Indexes**: `idx_ap_nodes_path_id`.
- **Security Considerations**: Foreign keys ensure node pointers cascade cleanly on resource deletion.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Created when path is generated; removed if path is pruned.

---

### 15. `attack_path_edges`
- **Purpose**: Directed edges representing attack transitions, exploitation hops, or lateral movement vectors between nodes.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `attack_path_id`: `UUID NOT NULL REFERENCES attack_paths(id) ON DELETE CASCADE`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `source_node_id`: `UUID NOT NULL REFERENCES attack_path_nodes(id) ON DELETE CASCADE`
  - `target_node_id`: `UUID NOT NULL REFERENCES attack_path_nodes(id) ON DELETE CASCADE`
  - `relation_type`: `TEXT NOT NULL` ('exploits', 'accesses', 'escalates_to', 'reads_secret')
  - `traversal_likelihood`: `NUMERIC(4, 2) NOT NULL DEFAULT 1.0`
- **Relationships**: Connects two `attack_path_nodes` within an `attack_path`.
- **Indexes**: `idx_ap_edges_path_id`, `idx_ap_edges_source_target` (`source_node_id, target_node_id`).
- **Security Considerations**: Defines attacker trajectory for mitigation planning.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Created alongside attack path nodes.

---

### 16. `remediation_proposals`
- **Purpose**: AI-generated, actionable remediation proposals (code patches, dependency updates, config fixes) awaiting human review.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `finding_id`: `UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE`
  - `title`: `TEXT NOT NULL`
  - `explanation`: `TEXT NOT NULL`
  - `fix_type`: `TEXT NOT NULL` ('code_patch', 'dependency_upgrade', 'config_update')
  - `diff_content`: `TEXT` (Unified diff format)
  - `suggested_action_payload`: `JSONB NOT NULL DEFAULT '{}'`
  - `confidence_score`: `NUMERIC(4, 2) NOT NULL` (0.00 - 1.00)
  - `status`: `TEXT NOT NULL DEFAULT 'pending_review'` ('pending_review', 'approved', 'rejected', 'applied')
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `updated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `findings`; 1-to-many with `remediation_approvals`, `verification_runs`.
- **Indexes**: `idx_remediation_proposals_finding_id`, `idx_remediation_proposals_status`.
- **Security Considerations**: Remediations are strictly proposals. No automated writes occur without human approval.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Created by Remediation Agent; transitions to `approved` or `rejected` upon human action.

---

### 17. `remediation_approvals`
- **Purpose**: Cryptographic and audit-compliant log of human review and authorization for a proposed remediation.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `proposal_id`: `UUID NOT NULL REFERENCES remediation_proposals(id) ON DELETE CASCADE`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `reviewed_by`: `UUID NOT NULL REFERENCES profiles(id)`
  - `action`: `TEXT NOT NULL` ('approved', 'rejected')
  - `review_notes`: `TEXT`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `remediation_proposals` and `profiles`.
- **Indexes**: `idx_remediation_approvals_proposal_id`.
- **Security Considerations**: Append-only audit record. Requires `admin` or `owner` role in workspace.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Immutable once recorded.

---

### 18. `verification_runs`
- **Purpose**: Tracks empirical validation jobs executing re-scans and reproduction checks to prove a fix worked.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `finding_id`: `UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE`
  - `proposal_id`: `UUID REFERENCES remediation_proposals(id)`
  - `verification_method`: `TEXT NOT NULL` ('semgrep_rescan', 'reproduction_probe', 'dependency_check')
  - `status`: `TEXT NOT NULL DEFAULT 'queued'` ('queued', 'running', 'passed', 'failed', 'inconclusive')
  - `result_details`: `JSONB NOT NULL DEFAULT '{}'`
  - `executed_at`: `TIMESTAMPTZ`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `findings` and `remediation_proposals`.
- **Indexes**: `idx_verification_runs_finding_id`, `idx_verification_runs_status`.
- **Security Considerations**: Prevents cosmetic status changes. Finding status is updated to `fixed` only if `status = 'passed'`.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Triggered post-remediation; closes finding upon success or flags regression upon failure.

---

### 19. `reports`
- **Purpose**: Manages generated security reports (Executive, Technical, Scan-specific, Compliance) and stored document artifacts.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `scan_id`: `UUID REFERENCES scans(id) ON DELETE SET NULL`
  - `report_type`: `TEXT NOT NULL` ('executive', 'technical', 'scan_summary', 'compliance_soc2')
  - `title`: `TEXT NOT NULL`
  - `summary`: `TEXT NOT NULL`
  - `content_json`: `JSONB NOT NULL` (Structured report data)
  - `storage_path_pdf`: `TEXT` (Supabase Storage reference for downloadable PDF)
  - `generated_by`: `UUID NOT NULL REFERENCES profiles(id)`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `workspaces`; optionally linked to `scans`.
- **Indexes**: `idx_reports_workspace_id_created`.
- **Security Considerations**: Stored documents inherit workspace RLS. Download URLs are time-limited signed URLs.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Generated on demand or scheduled; retained for compliance periods (1–7 years).

---

### 20. `chat_conversations`
- **Purpose**: Sessions for contextual, workspace-scoped AI Security Chat interactions.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `user_id`: `UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE`
  - `title`: `TEXT NOT NULL DEFAULT 'Security Inquiry'`
  - `context_scope`: `JSONB NOT NULL DEFAULT '{}'` (Optional filters: specific asset_id, finding_id, or scan_id)
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `updated_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `workspaces` and `profiles`; 1-to-many with `chat_messages`.
- **Indexes**: `idx_chat_conv_user_workspace` (`workspace_id, user_id`).
- **Security Considerations**: Scoped strictly to the authenticated user and their active workspace.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Retained until deleted by the user.

---

### 21. `chat_messages`
- **Purpose**: Individual messages within a chat conversation, including citations to verified findings and evidence.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `conversation_id`: `UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `role`: `TEXT NOT NULL` ('user', 'assistant', 'system')
  - `content`: `TEXT NOT NULL`
  - `citations`: `JSONB NOT NULL DEFAULT '[]'` (Array of referenced finding IDs and evidence IDs)
  - `model_used`: `TEXT`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `chat_conversations`.
- **Indexes**: `idx_chat_messages_conv_id` (`conversation_id, created_at ASC`).
- **Security Considerations**: AI messages must only cite verified workspace findings. System prompt prevents cross-tenant data leaks.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Append-only per conversation.

---

### 22. `audit_logs`
- **Purpose**: Immutable, tamper-evident regulatory audit trail recording all security-sensitive actions in the workspace.
- **Important Fields**:
  - `id`: `BIGSERIAL PRIMARY KEY`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `actor_id`: `UUID REFERENCES profiles(id)`
  - `action`: `TEXT NOT NULL` (e.g., 'asset.created', 'scan.triggered', 'remediation.approved', 'auth.verified')
  - `target_type`: `TEXT NOT NULL` ('asset', 'scan', 'finding', 'remediation', 'member')
  - `target_id`: `UUID`
  - `ip_address`: `INET`
  - `user_agent`: `TEXT`
  - `changes`: `JSONB NOT NULL DEFAULT '{}'` (Previous and updated states)
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `workspaces` and `profiles`.
- **Indexes**: `idx_audit_logs_workspace_created` (`workspace_id, created_at DESC`), `idx_audit_logs_actor`.
- **Security Considerations**: Completely append-only. No UPDATE or DELETE allowed via RLS policies.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Retained permanently or for compliance windows (minimum 7 years for SOC 2).

---

### 23. `notifications`
- **Purpose**: Real-time alerts, email notifications, and in-app updates dispatched to workspace team members.
- **Important Fields**:
  - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `workspace_id`: `UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
  - `user_id`: `UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE`
  - `title`: `TEXT NOT NULL`
  - `body`: `TEXT NOT NULL`
  - `severity`: `TEXT NOT NULL DEFAULT 'info'` ('info', 'warning', 'critical')
  - `link_url`: `TEXT`
  - `is_read`: `BOOLEAN NOT NULL DEFAULT false`
  - `read_at`: `TIMESTAMPTZ`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
- **Relationships**: Belongs to `workspaces` and `profiles`.
- **Indexes**: `idx_notifications_user_unread` (`user_id, is_read, created_at DESC`).
- **Security Considerations**: Recipient can only access their own notifications.
- **Workspace Ownership**: `workspace_id`.
- **Lifecycle**: Marked read by user; auto-archived after 30 days.

---

## 3. RLS Strategy & Multi-Tenant Isolation

Every tenant query executed by the backend enforces workspace scoping. For direct client access (Supabase Client SDK with JWT), PostgreSQL Row Level Security is applied:

```sql
-- Helper function to extract user's workspaces
CREATE OR REPLACE FUNCTION get_user_workspace_ids()
RETURNS SETOF UUID AS $$
  SELECT workspace_id FROM workspace_members
  WHERE user_id = (SELECT id FROM profiles WHERE firebase_uid = auth.uid());
$$ LANGUAGE sql SECURITY DEFINER;

-- Universal Policy Pattern for Workspace Isolation
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Workspace Members can view findings"
  ON findings FOR SELECT
  USING (workspace_id IN (SELECT get_user_workspace_ids()));
```
