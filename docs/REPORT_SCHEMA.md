# ShadowOps — Report Schema Specification (Stage 10)

## 1. Data Models & Constraints

### 1.1 Database Table: `reports`
```sql
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
    report_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT,
    format VARCHAR NOT NULL DEFAULT 'json',
    status VARCHAR NOT NULL DEFAULT 'generating',
    storage_object_id UUID,
    generated_by VARCHAR NOT NULL,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    data_cutoff_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    schema_version VARCHAR NOT NULL DEFAULT 'report-v1',
    completeness_status VARCHAR NOT NULL DEFAULT 'COMPLETE',
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    snapshot_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    CONSTRAINT check_report_type CHECK (
        report_type IN (
            'executive_summary', 'technical_vulnerability',
            'remediation_progress', 'verification_regression',
            'asset_security_posture', 'executive', 'technical',
            'scan', 'compliance', 'custom'
        )
    ),
    CONSTRAINT check_report_format CHECK (
        format IN ('pdf', 'html', 'json', 'markdown')
    ),
    CONSTRAINT check_report_status CHECK (
        status IN ('generating', 'completed', 'ready', 'failed')
    )
);
```

---

## 2. Five Canonical Report Types & Snapshot JSON Schemas

### Type 1: `executive_summary`
- **Audience**: Founders, executives, engineering directors, investors.
- **Fields in `snapshot_data`**:
  ```json
  {
    "report_type": "executive_summary",
    "generated_at": "ISO-8601 UTC",
    "scope": {
      "total_assets": 5,
      "authorized_assets": 4,
      "unauthorized_assets": 1,
      "has_completed_scans": true,
      "completed_scans_count": 3
    },
    "disclaimer": "Data reflects verified scans.",
    "executive_narrative": {
      "narrative": "Executive posture summary text...",
      "is_ai_generated": true,
      "disclaimer": "Advisory only. Deterministic findings take precedence.",
      "generated_at": "ISO-8601 UTC"
    },
    "metrics": {
      "risk_score": 78.5,
      "risk_band": "CRITICAL",
      "formula_version": "risk-v1",
      "open_findings_count": 8,
      "fixed_findings_count": 4,
      "by_severity": { "critical": 2, "high": 3, "medium": 3 },
      "critical_attack_paths_count": 1,
      "remediations_applied": 3,
      "verifications_completed": 2
    },
    "top_critical_findings": [
      {
        "finding_id": "UUID",
        "title": "Hardcoded JWT Secret Token",
        "severity": "critical",
        "rule_id": "python.jwt.hardcoded-jwt-secret",
        "file_path": "backend/auth/jwt_service.py",
        "line_start": 45,
        "cwe_id": "CWE-798",
        "status": "open"
      }
    ],
    "attack_paths_summary": [
      {
        "path_id": "UUID",
        "title": "Public Internet to Payments DB via Hardcoded JWT",
        "risk_tier": "CRITICAL",
        "target_node": "payments_db",
        "step_count": 3,
        "status": "active"
      }
    ]
  }
  ```

### Type 2: `technical_vulnerability`
- **Audience**: Security engineers, backend developers, DevSecOps.
- **Fields in `snapshot_data`**:
  - `total_findings`: Number of findings matching scope.
  - `severity_distribution`: Count map by severity.
  - `top_rules`: Frequency ranking of Semgrep / scanner rules triggered.
  - `findings`: Array of detailed findings:
    - `finding_id`, `title`, `description`, `rule_id`, `severity`, `confidence`, `status`
    - `file_path`, `line_start`, `line_end`, `cwe_id`, `owasp_category`
    - `asset_id`, `asset_name`
    - `evidence_items`: Array of evidence objects with `snippet_redacted` (sensitive credentials replaced with `[REDACTED_SECRET]`).
    - `remediation`: Proposal reference and status (if proposed).

### Type 3: `remediation_progress`
- **Audience**: Engineering leads, DevOps, release managers.
- **Fields in `snapshot_data`**:
  - `total_proposals`: Count of remediation proposals.
  - `status_distribution`: Counts by proposal lifecycle status.
  - `proposals`: Array of proposals with:
    - `proposal_id`, `finding_id`, `asset_id`, `title`, `problem_summary`
    - `affected_files`, `patch_reference`
    - `approved_by`, `approved_at`, `applied_by`, `applied_at`
    - `application`: Revision commit hash and rollback availability
    - `verification`: Associated Stage 9 verification job ID and verdict

### Type 4: `verification_regression`
- **Audience**: Security auditors, compliance officers, staff engineers.
- **Fields in `snapshot_data`**:
  - `total_verification_jobs`: Total independent verification runs.
  - `status_distribution`: Distribution of verification job statuses.
  - `comparison_outcomes`: Breakdown of rescan outcomes (`NO_LONGER_DETECTED`, `STILL_PRESENT`, `MODIFIED_PERSISTENT`, `INCONCLUSIVE`).
  - `regression_failures_count`: Number of patches failing regression checks.
  - `human_signoffs_count`: Number of human review sign-offs recorded.
  - `verification_invariant`: "No sufficient evidence means no verified fix."
  - `jobs`: Array of verification jobs with policy verdicts, evidence comparisons, and human review decisions (`accepted` / `rejected`).

### Type 5: `asset_security_posture`
- **Audience**: Cloud architects, infrastructure leads, security managers.
- **Fields in `snapshot_data`**:
  - `total_assets`: Registered assets count.
  - `assets`: Array of assets with:
    - `asset_id`, `name`, `asset_type`, `criticality`, `environment`, `target`
    - `authorization`: Authorization status (`authorized`, `verified`, `pending`, `expired`), authorized timestamp, expiry.
    - `scans`: Total runs, latest scan status, latest scan timestamp.
    - `open_findings_count`, `severity_breakdown`.
