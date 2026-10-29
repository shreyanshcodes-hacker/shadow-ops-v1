# SHADOWOPS — STAGE 5 ARCHITECTURAL BASELINE & AUDIT REPORT
## Audit of Stage 4 Intelligence & Transition to AI Security Analyst

```
====================================================================================
PRODUCT:         SHADOWOPS
TAGLINE:         "Your AI Security Team. Always Watching."
PHASE:           STAGE 5 AUDIT & BASELINE SPECIFICATION
AUDIT DATE:      2026-10-26
====================================================================================
```

---

## 1. Stage 4 Architecture Audit

### 1.1 Finding & Evidence Model (`backend/app/models/finding.py`)
- **Finding (`findings` table)**:
  - Columns: `id`, `workspace_id`, `scan_id`, `asset_id`, `source` (semgrep, etc.), `source_rule_id`, `title`, `description`, `severity` (critical, high, medium, low, info), `confidence` (low, medium, high), `cwe_ids`, `cve_ids`, `owasp_categories`, `location` (JSONB with file, lines), `code_snippet`, `remediation_guidance`, `status` (open, fixed, etc.), `risk_score`, `risk_factors`, `first_seen_at`, `last_seen_at`.
  - Relationship `evidence`: Mapped 1-to-many to `FindingEvidence`.
- **FindingEvidence (`finding_evidence` table)**:
  - Columns: `id`, `finding_id`, `workspace_id`, `evidence_type`, `title`, `description`, `content` (JSONB), `file_path`, `line_start`, `line_end`, `metadata_`, `created_at`.
- **FindingAIAnalysis (`finding_ai_analysis` table)**:
  - Introduced in Stage 4: stores advisory AI interpretation (`summary`, `technical_explanation`, `impact`, `confidence`, `classification`, `uncertainty`, `supporting_evidence`, `model`, `provider`, `prompt_version`, `input_hash`).

### 1.2 Scan & AgentRun Models (`backend/app/models/scan.py`)
- **Scan (`scans` table)**:
  - Tracks lifecycle (`queued`, `running`, `completed`, `failed`, `cancelled`), profile (`CODE_SECURITY`), asset, workspace, timings.
- **ScanEvent (`scan_events` table)**:
  - Immutable chronological audit trail of scanner lifecycle transitions.
- **AgentRun (`agent_runs` table)**:
  - Tracks execution runs of AI agents and scanners (`agent_name`, `provider`, `model_used`, `prompt_version`, `input_hash`, `tokens_input`, `tokens_output`, `cost_usd`, `error_code`, `status`).

### 1.3 Workspace Authorization & Access Control
- Deterministic multi-tenant isolation enforced via PostgreSQL RLS and FastAPI dependency `RequireWorkspaceMember(min_role)` and `WorkspaceService.get_workspace(workspace_id, user_id)`.
- Core invariant `NO AUTHORIZATION -> NO SCAN` strictly maintained.

### 1.4 AI Provider Contracts & Existing Adapters (`backend/app/ai/`)
- `app.ai.provider.AIProvider`: Abstract base class with `generate_text` and `generate_structured`.
- `app.ai.gemini.GeminiProvider`: Async HTTP integration with Google Generative Language API (`gemini-1.5-pro` default) via `httpx`.
- `app.ai.grok.GrokProvider`: OpenAI-compatible async HTTP integration with xAI Grok API (`grok-beta` default).
- `app.ai.safety`: Implements `redact_secrets()`, prompt boundary fencing (`<TRUSTED_SYSTEM_INSTRUCTIONS>`, `<UNTRUSTED_SECURITY_EVIDENCE>`), and anti-hallucination evidence ID filtering.
- `app.ai.cost`: Deterministic SHA-256 `compute_input_hash()` for duplicate call suppression, `truncate_context()` for token limits, and `calculate_cost()`.

### 1.5 Frontend State (`frontend/app/`)
- Scan detail page ([`frontend/app/scans/[id]/page.tsx`](file:///d:/Shreyanshcodes/shadow-ops-v2/frontend/app/scans/[id]/page.tsx)) displays findings list with inline advisory cards and "Run AI Security Manager".
- A dedicated finding detail page (`frontend/app/findings/[id]/page.tsx`) does **not yet exist** and must be created for Stage 5.

---

## 2. Reusable Services & Modules for Stage 5

1. **Provider Abstraction (`app.ai.provider.AIProvider`)**:
   - Reused directly. No secondary or parallel AI layer will be created.
2. **Secret Redaction (`app.ai.safety.redact_secrets`)**:
   - Reused to strip API keys, private keys, AWS tokens, bearer tokens, and passwords from code snippets and evidence before AI context construction.
3. **Audit Service (`app.services.audit_service.AuditService`)**:
   - Reused to record immutable audit logs: `ai_analysis.requested`, `ai_analysis.started`, `ai_analysis.completed`, `ai_analysis.failed`.
4. **Input Hashing & Deduplication (`app.ai.cost`)**:
   - Reused to provide idempotency and cache reuse for identical prompt/model/finding inputs.

---

## 3. Gap Analysis: Missing Pieces for Stage 5

1. **Strict Typed Security Analysis Schema (`SecurityAnalysis`)**:
   - Stage 5 requires a comprehensive schema with mandatory distinction between **OBSERVED**, **INFERRED**, and **UNCERTAIN** components:
     - `summary`
     - `vulnerability_type`
     - `severity_assessment`
     - `confidence` (float 0.0–1.0)
     - `exploitability_assessment`
     - `impact_assessment`
     - `affected_component`
     - `attack_preconditions`
     - `evidence_interpretation` (containing explicit `observed`, `inferred`, `uncertain` breakdown)
     - `reasoning`
     - `recommended_next_steps`
     - `uncertainty`
2. **Dedicated Context Builder (`SecurityAnalysisContextBuilder`)**:
   - Builds a minimized, sanitized data context containing only necessary finding and evidence facts.
   - Strictly omits sensitive credentials, service-role keys, tokens, or unrelated workspace files.
3. **AI Result Versioning (Multiple Analyses per Finding)**:
   - In Stage 4, `finding_ai_analysis.finding_id` was unique (1-to-1).
   - Stage 5 requires **historical versioning** (a finding can have multiple analyses: Gemini vs Grok, prompt v1 vs v2, re-analyses over time).
   - Migration `0005_stage5_ai_analyst.sql` must remove the unique constraint on `finding_id` and add `status`, `created_by`, and analysis breakdown fields.
4. **Dedicated Backend Service (`AIAnalysisService`)**:
   - Encapsulates the 12-step analysis lifecycle: auth check, workspace check, finding access, evidence loading, context minimization, safe prompt fencing, provider invocation, schema validation, persistence, audit logging, and result return.
5. **Deterministic Test Double (`FakeAIProvider`)**:
   - A clean test double for hermetic automated tests, completely separated from Gemini/Grok and disabled in production.
6. **Dedicated Finding Detail Page (`/findings/[id]`)**:
   - Displays clear separation between **SECURITY FINDING (Authoritative Scanner Facts)** and **AI SECURITY ANALYSIS (Advisory Interpretation)**.
   - Interactive states: `NOT ANALYZED`, `ANALYZING`, `ANALYSIS AVAILABLE`, `ANALYSIS FAILED`.
   - Explicit "Analyze with AI" and "Re-analyze" controls.
   - Clear advisory disclaimers and human-review notices.
