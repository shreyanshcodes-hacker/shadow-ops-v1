# ShadowOps Security Event Catalog

## 1. Event Envelope Specification

All events within the ShadowOps ecosystem conform to the versioned `SecurityEventEnvelope` contract:

```json
{
  "id": "e3b0c442-98fc-1c14-9af0-2a3b957977a1",
  "event_type": "scan.completed",
  "event_version": "1.0",
  "workspace_id": "8f8b3c9b-6489-4e78-9582-123456789abc",
  "actor_id": "01234567-89ab-cdef-0123-456789abcdef",
  "correlation_id": "11223344-5566-7788-99aa-bbccddeeff00",
  "resource_type": "scan",
  "resource_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "timestamp": "2026-10-28T20:15:00Z",
  "idempotency_key": "scan-complete-a1b2c3d4",
  "payload": {
    "scanner_name": "semgrep",
    "findings_count": 4,
    "severity": "HIGH",
    "duration_seconds": 12.4
  }
}
```

---

## 2. Canonical Security Event Types

### 2.1 Scanning Lifecycle (`category: scans`)

| Event Type | Trigger Condition | Severity | Default Roles |
| :--- | :--- | :--- | :--- |
| `scan.completed` | Security scan finishes successfully | `INFO` / `LOW` | `OWNER`, `ADMIN`, `ANALYST`, `MEMBER` |
| `scan.failed` | Scanner binary or network error | `HIGH` | `OWNER`, `ADMIN`, `ANALYST` |

### 2.2 Finding Management (`category: findings`)

| Event Type | Trigger Condition | Severity | Default Roles |
| :--- | :--- | :--- | :--- |
| `finding.created` | New vulnerability identified | Dynamic (`LOW` to `CRITICAL`) | `OWNER`, `ADMIN`, `ANALYST` |
| `finding.severity_changed` | Finding re-scored by deterministic risk engine | `MEDIUM` | `OWNER`, `ADMIN`, `ANALYST` |

### 2.3 Attack Path & Risk Metrics (`category: risk`)

| Event Type | Trigger Condition | Severity | Default Roles |
| :--- | :--- | :--- | :--- |
| `attack_path.detected` | Multi-hop exploit path identified to crown jewel | `HIGH` / `CRITICAL` | `OWNER`, `ADMIN` |
| `risk.critical_threshold` | Workspace risk score breaches threshold | `CRITICAL` | `OWNER`, `ADMIN` |

### 2.4 AI Security Team (`category: general`)

| Event Type | Trigger Condition | Severity | Default Roles |
| :--- | :--- | :--- | :--- |
| `security_team.completed` | Multi-agent assessment run completes | `LOW` | `OWNER`, `ADMIN`, `ANALYST` |
| `security_team.failed` | Multi-agent execution error or timeout | `MEDIUM` | `OWNER`, `ADMIN`, `ANALYST` |

### 2.5 Remediation & Approval (`category: remediation`)

| Event Type | Trigger Condition | Severity | Default Roles |
| :--- | :--- | :--- | :--- |
| `remediation.proposed` | AI Remediation engine generates code patch | `INFO` | `OWNER`, `ADMIN`, `ANALYST` |
| `remediation.approval_required` | Validated patch is awaiting human sign-off | `HIGH` / `CRITICAL` | **`OWNER`, `ADMIN` ONLY** |
| `remediation.applied` | Patch successfully applied to target repository | `INFO` | `OWNER`, `ADMIN`, `ANALYST` |
| `remediation.rolled_back` | Patch reverted to safety checkpoint | `HIGH` | `OWNER`, `ADMIN` |

### 2.6 Fix Verification & Regression (`category: verification`)

| Event Type | Trigger Condition | Severity | Default Roles |
| :--- | :--- | :--- | :--- |
| `verification.completed` | Independent verification job completes | `INFO` | `OWNER`, `ADMIN`, `ANALYST` |
| `verification.regression_detected` | New vulnerabilities or test breakages detected | `CRITICAL` | `OWNER`, `ADMIN` |
| `verification.human_review_required` | Verification passed; finding closure sign-off needed | `HIGH` | **`OWNER`, `ADMIN` ONLY** |

### 2.7 Security Reports (`category: reports`)

| Event Type | Trigger Condition | Severity | Default Roles |
| :--- | :--- | :--- | :--- |
| `report.ready` | Executive or technical PDF/JSON report generated | `LOW` | `OWNER`, `ADMIN`, `ANALYST`, `MEMBER` |
| `report.export_failed` | PDF compilation error or storage timeout | `MEDIUM` | `OWNER`, `ADMIN` |

---

## 3. Secret Scrubbing Enforcement

The following keywords are automatically sanitized to `"[REDACTED]"` at the model validation boundary before any event enters the database or outbox:
- `password`, `token`, `secret`, `api_key`, `authorization`, `private_key`
- Any key containing forbidden tokens (e.g. `github_token`, `db_password`, `client_secret`) is systematically stripped.
