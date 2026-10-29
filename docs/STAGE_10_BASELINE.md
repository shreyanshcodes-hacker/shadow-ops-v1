# Stage 10 Baseline Audit: Security Reports & Executive Dashboard

## 1. Executive Summary

This baseline document audits the persisted data models, query capabilities, frontend components, and export mechanisms across Stages 0 through 9 of ShadowOps. It establishes the factual foundation for **Stage 10: Security Reports & Executive Dashboard**.

Stage 10 transforms persisted security facts into an auditable executive and technical reporting platform.
The primary directive for this stage:
> **"Reports must reflect actual persisted data. Never fabricate scans, findings, vulnerabilities, risk reductions, AI assessments, remediation outcomes, or verification results. Clearly distinguish missing data from zero (e.g. no scans != 0 vulnerabilities)."**

---

## 2. Audit of Existing Persisted Data & Models

### 2.1 Workspace & Authorization Boundaries (Stages 1–2)
- **Models**: `Workspace`, `WorkspaceMember`, `Profile`, `Asset`, `AssetAuthorization`.
- **Persisted Fields**:
  - `Workspace`: `id`, `name`, `slug`, `owner_id`, `plan`, `settings`, `created_at`.
  - `WorkspaceMember`: `workspace_id`, `user_id`, `role` (`owner`, `admin`, `security_lead`, `engineer`, `viewer`).
  - `Asset`: `id`, `workspace_id`, `name`, `type`, `criticality` (`critical`, `high`, `medium`, `low`), `status`, `created_at`.
  - `AssetAuthorization`: `id`, `asset_id`, `workspace_id`, `status` (`authorized`, `verified`, `pending`, `revoked`, `expired`), `expires_at`.
- **Query Reality**:
  - Asset count and authorized asset count can be computed reliably via `SELECT COUNT(*) WHERE workspace_id = :ws`.

### 2.2 Scans, Findings & Evidence (Stages 3–4)
- **Models**: `Scan`, `ScanEvent`, `Finding`, `FindingEvidence`, `FindingAIAnalysis`.
- **Persisted Fields**:
  - `Scan`: `id`, `workspace_id`, `asset_id`, `scan_type`, `status` (`pending`, `running`, `completed`, `failed`), `started_at`, `completed_at`.
  - `Finding`: `id`, `workspace_id`, `scan_id`, `asset_id`, `source`, `source_rule_id`, `title`, `description`, `severity` (`critical`, `high`, `medium`, `low`, `info`), `status` (`open`, `triaged`, `in_progress`, `fixed`, `false_positive`, `wont_fix`, `risk_accepted`), `code_snippet`, `location`, `first_seen_at`, `last_seen_at`, `fixed_at`.
  - `FindingEvidence`: `id`, `finding_id`, `evidence_type`, `title`, `file_path`, `line_start`, `line_end`, `content`.
- **Query Reality**:
  - Finding distribution by severity and status is derived from database records.
  - Scan state breakdown (`completed`, `failed`, `running`) is authoritative.

### 2.3 Attack Paths & Deterministic Risk Engine (Stage 6)
- **Models**: `AttackPath`, `AttackPathNode`, `AttackPathEdge`, `RiskSnapshot`, `SecurityRelationship`.
- **Persisted Fields**:
  - `AttackPath`: `id`, `workspace_id`, `name`, `risk_score` (0–100), `risk_band` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), `status` (`active`, `mitigated`), `is_critical`.
  - `RiskSnapshot`: `id`, `workspace_id`, `overall_score`, `model_version`, `factors`, `calculated_at`.
- **Query Reality**:
  - Current risk score and scoring formula version (`risk-v1`) come directly from `RiskSnapshot` or the latest active critical path. No secondary formula may be invented.

### 2.4 AI Security Team Orchestration (Stage 7)
- **Models**: `SecurityTeamRun`, `AgentRun`.
- **Persisted Fields**:
  - `SecurityTeamRun`: `workspace_id`, `status` (`SUCCEEDED`, `FAILED`), `orchestration_version`, `confidence`, `team_summary` (JSONB).
  - `AgentRun`: `agent_name` (`recon`, `vulnerability_analyst`, `attack_path`, `risk_analyst`, `security_reviewer`), `output` (JSONB).
- **Query Reality**:
  - Multi-agent synthesis and consensus outputs are available for inclusion in executive summaries, strictly labeled as advisory AI assessments.

### 2.5 Remediation Proposals & Patch Lifecycle (Stage 8)
- **Models**: `RemediationProposal`, `RemediationValidation`, `RemediationApproval`, `RemediationCheckpoint`, `RemediationApplication`.
- **Persisted Fields**:
  - `RemediationProposal`: `status` (`PROPOSED`, `VALIDATING`, `AWAITING_APPROVAL`, `APPROVED`, `APPLIED`, `REJECTED`, `ROLLED_BACK`), `affected_files`, `patch_hash`, `unified_diff`.
  - `RemediationApproval`: `approved_by`, `decision`, `approved_at`, `justification`.
  - `RemediationApplication`: `status`, `applied_at`, `verification_status`.

### 2.6 Independent Fix Verification & Regression Analysis (Stage 9)
- **Models**: `VerificationJob`, `VerificationComparison`, `VerificationRegressionCheck`, `VerificationReview`.
- **Persisted Fields**:
  - `VerificationJob`: `status` (`PASSED_PENDING_REVIEW`, `FAILED`, `INCONCLUSIVE`, `BLOCKED`), `vulnerability_status`, `regression_status`, `scanner_status`, `policy_verdict` (`VERIFIED_CANDIDATE`, `FAILED`, `INCONCLUSIVE`, `BLOCKED`), `policy_version` (`verification-policy-v1`), `started_at`, `completed_at`.
  - `VerificationReview`: `reviewer_id`, `decision` (`accepted`, `rejected`), `rationale`, `finding_status_after` (`fixed`, `open`), `reviewed_at`.
- **Query Reality**:
  - Genuinely distinguishes between `VERIFIED_CANDIDATE` (automated rescan clean, awaiting review) and human-accepted fix (`finding.status = 'fixed'`).

### 2.7 Existing Report Model (Legacy Migration 001)
- **Current Model**: `backend/app/models/report.py` (`Report`):
  - Defined with legacy columns: `workspace_id`, `scan_id`, `report_type`, `title`, `description`, `format`, `status`, `storage_object_id`, `generated_by`, `period_start`, `period_end`, `metadata`.
  - Needs sequential extension (`supabase/migrations/0010_stage10_reports.sql`) to persist immutable report snapshots (`snapshot_data`), data cutoff timestamps, schema versions, and filter parameters.

---

## 3. Gap Analysis for Stage 10

| Stage 10 Requirement | Current State | Implementation Plan |
| :--- | :--- | :--- |
| **Executive Dashboard Service** | Partial metrics in dashboard frontend (`/dashboard`) computed via ad-hoc client calls | Implement `DashboardMetricsService` (`backend/app/services/dashboard_service.py`) returning validated, workspace-scoped metrics with explicit missing vs zero distinction. |
| **Historical Trends** | None | Implement `get_workspace_trends` computing reliable historical snapshots from `findings.first_seen_at`, `findings.fixed_at`, `scans.completed_at`, and `risk_snapshots`. |
| **Report Generation Service** | Basic DB model with no service implementation | Implement `ReportGeneratorService` supporting all 5 report types (Executive Summary, Technical Vulnerability, Remediation Progress, Verification & Regression, Asset Security Posture) with reproducible immutable snapshots. |
| **Advisory AI Executive Narrative** | Not integrated into reports | Integrate optional Gemini/Grok narrative generator strictly summarizing persisted metrics with deterministic fallback and no metrics alteration. |
| **PDF & JSON Export** | None | Implement `ReportExportService` generating structured JSON downloads and formatted PDF reports via `reportlab`. |
| **Audit Events** | Audit logging exists for auth, scans, remediations, verifications | Register `report.requested`, `report.generated`, `report.exported`, `report.downloaded` events in `AuditService`. |
| **Frontend UI Routes** | `/dashboard` partially populated; `/reports` not implemented | Upgrade `/dashboard` with comprehensive metrics and trend charts; build `/reports`, `/reports/new`, and `/reports/[id]`. |

---

## 4. Architectural Invariants for Stage 10

1. **Persisted Ground Truth**: No metric, count, or status may be rendered that is not supported by database records.
2. **Missing vs Zero Disclosure**: A workspace with 0 completed scans has "Unknown" vulnerability posture, NOT "0 vulnerabilities".
3. **Point-in-Time Cutoff**: Every generated report must fix an immutable `data_cutoff_at` timestamp.
4. **Advisory AI Boundary**: AI summaries must be labeled `AI-assisted` and cannot change numbers or compliance statuses.
5. **Strict Multi-Tenant Isolation**: All reports, downloads, and metrics are bound to `workspace_id`.
