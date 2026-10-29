# ShadowOps — Report Export Security & Redaction Architecture (Stage 10)

## 1. Threat Model & Security Requirements

Security reports often consolidate sensitive architectural details, vulnerability patterns, and evidence snippets. Without rigorous export protections, reports present a severe vector for credential exfiltration, authorization bypass, and accidental exposure.

### Non-Negotiable Controls
1. **Multi-Tenant Workspace Isolation**: Every report generation, viewing, and export request strictly verifies workspace membership using `WorkspaceService.get_workspace(workspace_id, current_user.id)`. Requests for cross-workspace reports return `404 Not Found`.
2. **Automated Secret & Token Redaction**: Code snippets, logs, and stack traces included in reports are filtered through regex patterns to redact credentials before writing to the database snapshot and before PDF/JSON generation.
3. **No Unauthenticated or Public URLs**: Reports are NEVER hosted via public S3/GCS signed URLs without auth. All downloads stream through `/api/v1/reports/{id}/download` requiring a valid Firebase Bearer token.
4. **Non-Repudiation & Audit Trail**: Every generation, export, and download action creates an append-only record in `audit_logs` tracking the actor ID, workspace ID, timestamp, format, and byte size.

---

## 2. Automated Redaction Engine

The redaction engine is implemented in [`report_generator_service.py`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/report_generator_service.py) via `redact_sensitive_data()`.

### Patterns Redacted
| Pattern Class | Matching Rule | Replacement |
|---|---|---|
| **API Keys & Secrets** | `(?:api[_-]?key\|secret\|token\|password)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.+=]{8,}["\']?` | `[REDACTED_SECRET]` |
| **Bearer Tokens** | `Bearer\s+[a-zA-Z0-9_\-\.\/+=]{10,}` | `Bearer [REDACTED_SECRET]` |
| **Private Keys** | `-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----` | `[REDACTED_SECRET]` |
| **Database URIs** | `(postgres\|mysql\|mongodb\|redis)://[^:\s]+:([^@\s]+)@` | Protocol and host preserved; password replaced with `[REDACTED_SECRET]` |
| **GitHub Tokens** | `(ghp_[a-zA-Z0-9]{36}\|github_pat_[a-zA-Z0-9]{82})` | `[REDACTED_SECRET]` |
| **AWS Access Keys** | `AKIA[0-9A-Z]{16}` | `[REDACTED_SECRET]` |

---

## 3. PDF Generation Security & ReportLab Styling

PDF generation via [`ReportExportService`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/report_export_service.py) executes entirely in memory (`io.BytesIO`) without writing temporary files to disk.

### Document Protections
- **Confidentiality Header**: Prominent classification warning ("CONFIDENTIAL // FOR AUTHORIZED PERSONNEL ONLY").
- **Audit Metadata**: Embeds Report ID, Workspace ID, and Data Cutoff Timestamp in the header and footer of every page.
- **Sanitized Flowables**: All dynamic string inputs from database records are escaped to prevent Platypus/ReportLab XML injection.
- **Strict Media Type & Headers**: Download responses enforce `Content-Type: application/pdf`, `Content-Disposition: attachment; filename="..."`, and `Cache-Control: no-cache, no-store, must-revalidate`.
