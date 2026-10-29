# Stage 11 Baseline Audit: Notifications, Event Processing & Controlled Workflow Automation

**Audit Timestamp:** 2026-10-28T20:17:30+05:30  
**Repository State:** Stages 0–10 complete. Full backend test suite passing (83/83 tests). Next.js 15.5.9 frontend production build passing (18/18 routes).

---

## 1. Existing Audit and Event Infrastructure

### Audit Logging
- **Model:** `AuditLog` in `backend/app/models/audit.py` (columns: `id`, `workspace_id`, `user_id`, `action`, `resource_type`, `resource_id`, `old_state`, `new_state`, `ip_address`, `user_agent`, `request_id`, `created_at`).
- **Service:** `AuditService` in `backend/app/services/audit_service.py` provides `log()` and `log_action()`.
- **Event Types:** Enumerated in `AuditEventType` (`backend/app/schemas/audit.py`), covering:
  - Scans (`SCAN_REQUESTED`, `SCAN_STARTED`, `SCAN_COMPLETED`, `SCAN_FAILED`, `SCAN_CANCELLED`)
  - AI Security Team (`SECURITY_TEAM_STARTED`, `SECURITY_TEAM_COMPLETED`, `SECURITY_TEAM_FAILED`)
  - Attack Paths & Risk (`ATTACK_PATH_CREATED`, `ATTACK_PATH_UPDATED`, `RISK_CALCULATED`)
  - Remediations (`REMEDIATION_PROPOSED`, `REMEDIATION_VALIDATED`, `REMEDIATION_APPROVED`, `REMEDIATION_REJECTED`, `REMEDIATION_APPLIED`, `REMEDIATION_ROLLED_BACK`)
  - Verifications (`verification.reviewed`)
  - Reports (`REPORT_GENERATED`, `REPORT_EXPORTED`, `REPORT_DOWNLOADED`)

### Current Limitations in Eventing
- There is currently **no transactional event outbox**. Events are written directly into `audit_logs` without asynchronous delivery decoupling or retry mechanisms.
- If an external delivery attempt fails, there is no retry worker, dead-letter storage, or poison message circuit breaker.
- Audit logs contain technical change payloads (`old_state`, `new_state`), but there is no dedicated `SecurityEventEnvelope` contract enforcing secret redaction or standard routing headers (`correlation_id`, `actor_id`, `event_type`, `version`).

---

## 2. Security Lifecycle Events across Stages 0–10

| Domain | Lifecycle Events | Key Payload Attributes |
| :--- | :--- | :--- |
| **Scans (Stage 3)** | `scan.completed`, `scan.failed` | `scan_id`, `asset_id`, `scanner_name`, `findings_count`, `duration_seconds` |
| **Findings (Stage 4)** | `finding.created`, `finding.severity_changed` | `finding_id`, `title`, `severity`, `cwe_id`, `file_path` |
| **Attack Paths & Risk (Stage 6)** | `risk.critical_threshold`, `attack_path.detected` | `risk_score`, `risk_band`, `path_id`, `target_node_id` |
| **AI Security Team (Stage 7)** | `security_team.run_completed`, `security_team.failed` | `team_run_id`, `consensus_verdict`, `agents_executed` |
| **Remediation (Stage 8)** | `remediation.proposed`, `remediation.approval_required`, `remediation.applied`, `remediation.rolled_back` | `proposal_id`, `finding_id`, `approval_id`, `patch_hash` |
| **Verification (Stage 9)** | `verification.completed`, `verification.regression_detected`, `verification.human_review_required` | `job_id`, `finding_id`, `policy_verdict`, `regression_status` |
| **Reports (Stage 10)** | `report.ready`, `report.export_failed` | `report_id`, `report_type`, `format`, `storage_object_id` |

---

## 3. Existing Notification State & UI

- **Initial Notification Model:** `backend/app/models/notification.py` contains an early draft `Notification` class with `id`, `workspace_id`, `user_id`, `type`, `title`, `message`, `reference_type`, `reference_id`, `channels`, `read_at`, `sent_at`, `created_at`.
- **Database Table:** Not yet formally created in Supabase PostgreSQL migration (migration stopped at `0010_stage10_reports.sql`).
- **UI Status:** No in-app notification center, unread bell icon, or notification settings preferences page currently exist in the frontend navigation shell.

---

## 4. Existing Worker, Queue & Retry Mechanisms

- **Background Tasks:** Fast background dispatch currently relies on FastAPI's native `BackgroundTasks` and Python `asyncio` routines.
- **Worker/Daemon Infrastructure:** No standalone message brokers (like RabbitMQ or Redis Celery) exist, keeping the deployment lightweight on Railway.
- **Delivery Queues:** No transactional retry queue or delivery status tracker exists.
- **Stage 11 Architectural Solution:** Implement an SQLite/PostgreSQL transactional **Event Outbox** pattern (`event_outbox` and `notification_deliveries` tables) with exponential backoff retries, poison event quarantine, and bounded worker processing.

---

## 5. External Integrations: Email & Automation (n8n)

- **Email:** Currently no external SMTP or transactional email provider (SendGrid/Resend/AWS SES) configured in `.env`.
  - *Requirement:* Create a provider-agnostic `EmailAdapter` that checks configuration and safely handles `NOT_CONFIGURED` status without crashing callers.
- **n8n / Webhooks:** Not installed, not configured, not operational.
  - *Requirement:* External automation must remain **strictly optional and disabled by default**.
  - Must require explicit workspace opt-in, strict endpoint allowlisting (HTTPS only, RFC 1918 / localhost / metadata blocked), HMAC SHA256 payload signing, and strict RBAC isolation.
  - Automation can **never** bypass security controls: cannot auto-approve patches, change risk scores, or close findings.

---

## 6. Workspace Roles & Notification Preferences

- **Workspace Roles:** `OWNER`, `ADMIN`, `ANALYST`, `AUDITOR`.
- **Authorization Enforcement:**
  - High-impact events (e.g. `remediation.approval_required`, `verification.human_review_required`, `risk.critical_threshold`) require resolution to `OWNER` and `ADMIN` roles.
  - Operational events (e.g. `scan.completed`, `report.ready`) can be routed to `ANALYST` and `AUDITOR` based on preference.
- **Required New Models:**
  - `NotificationPreference`: User- and workspace-scoped preference toggles for event categories and delivery channels.
  - `NotificationRule`: Workspace-level routing, severity filtering, and deduplication policies.
  - `WorkflowRun`: Audit log and execution history for controlled workflow actions.
