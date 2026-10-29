# ShadowOps — Security Reporting Architecture (Stage 10)

## 1. Overview & Objective

Stage 10 provides an enterprise-grade reporting and executive dashboard subsystem for ShadowOps.
The reporting workflow enforces strict auditability, deterministic computation, sensitive data redaction, and workspace isolation:

```
Workspace Security Data → Validated Metrics → Executive Dashboard → Detailed Security Report → PDF/JSON Export → Audit Trail
```

### Core Security Invariants
1. **Never Fabricate Security Facts**: Reports and metrics are strictly compiled from actual persisted database records (scans, findings, evidence, attack paths, risk snapshots, remediations, verifications).
2. **Distinguish Missing Data From Zero**: If a workspace has 0 completed scans, it does NOT report 0 risk or safe perimeter. The system sets `has_completed_scans = False` and outputs a prominent perimeter disclaimer.
3. **Immutable Point-in-Time Snapshots**: Once generated, every report freezes a complete snapshot of all findings, metrics, and evidence as of `data_cutoff_at` (UTC). Historical reports never drift when findings later change.
4. **Advisory AI Narratives**: AI summaries (Gemini/Grok) are strictly advisory. They are explicitly watermarked and disclaimed. They can never alter deterministic scores, override scanner facts, or fabricate compliance claims. If AI fails or is disabled, deterministic fallback summaries are automatically used.
5. **Non-Public Authenticated Exports**: All report exports and downloads require verified workspace authorization and log audit trail events (`report.generated`, `report.exported`, `report.downloaded`).

---

## 2. Core Components

### 2.1 Backend Services
- [`DashboardService`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/dashboard_service.py):
  - Aggregates workspace metrics for assets, scans, findings, risk scores, remediation proposals, and verification jobs.
  - Implements 30-day time-series bucketing for findings velocity, risk score trajectories, and patch velocity.
- [`ReportGeneratorService`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/report_generator_service.py):
  - Compiles point-in-time snapshots across the 5 canonical report types.
  - Applies automated secret redaction to code snippets and logs.
  - Coordinates optional advisory AI executive summaries with timeout guardrails.
- [`ReportExportService`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/report_export_service.py):
  - Generates reproducible, structured JSON exports.
  - Generates executive PDF documents using ReportLab with confidentiality headers, metrics tables, priority findings, and invariant notices.
- [`AuditService`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/audit_service.py):
  - Records immutable audit events on generation, export, and download.

### 2.2 REST API Endpoints (`/api/v1/reports`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/reports/dashboard?workspace_id=...` | Returns real-time validated dashboard metrics. |
| `GET` | `/reports/dashboard/trends?workspace_id=...&days=30` | Returns 30-day security trends. |
| `POST` | `/reports?workspace_id=...` | Generates a persistent report snapshot. |
| `GET` | `/reports?workspace_id=...` | Lists historical reports with pagination and filtering. |
| `GET` | `/reports/{id}?workspace_id=...` | Fetches a frozen report snapshot. |
| `POST` | `/reports/{id}/export?workspace_id=...&format=...` | Prepares export metadata. |
| `GET` | `/reports/{id}/download?workspace_id=...&format=pdf\|json` | Authenticated file stream download with audit logging. |

### 2.3 Frontend User Interface
- Main Dashboard ([`frontend/app/dashboard/page.tsx`](file:///d:/Shreyanshcodes/shadow-ops-v2/frontend/app/dashboard/page.tsx)):
  - Validated metrics grid, missing data banner, 30-day trends trajectory, and direct CTA to generate reports.
- Reports Archive ([`frontend/app/reports/page.tsx`](file:///d:/Shreyanshcodes/shadow-ops-v2/frontend/app/reports/page.tsx)):
  - Filterable table of past report snapshots with quick download links.
- Report Generator ([`frontend/app/reports/new/page.tsx`](file:///d:/Shreyanshcodes/shadow-ops-v2/frontend/app/reports/new/page.tsx)):
  - Report type selection, scope filtering (assets, severities), and format toggle.
- Report Viewer ([`frontend/app/reports/[id]/page.tsx`](file:///d:/Shreyanshcodes/shadow-ops-v2/frontend/app/reports/[id]/page.tsx)):
  - Full executive and technical inspection, sanitized snippet previews, and raw snapshot JSON viewer.
