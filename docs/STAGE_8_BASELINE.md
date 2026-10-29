# SHADOWOPS — STAGE 8 BASELINE REPORT
## AI Remediation, Human Approval & Safe Patch Management

**Date:** October 27, 2026  
**Project:** ShadowOps — AI-Native Cybersecurity SaaS for Startups  
**Status:** BASELINE AUDITED — PROCEEDING TO IMPLEMENTATION  

---

## 1. Existing System Audit (Stages 0–7)

### Stage 0: Architecture & Documentation
- **Status:** Verified and Complete.
- **Artifacts:** `docs/PROJECT_SOURCE_OF_TRUTH.md`, `docs/REMEDIATION_ARCHITECTURE.md`, `docs/SYSTEM_ARCHITECTURE.md`, `docs/SECURITY_ARCHITECTURE.md`.
- **Invariants Defined:** "AI Proposes → Human Reviews & Approves → System Executes → Empirical Verification Validates".

### Stage 1: Production Foundation
- **Status:** Verified and Operational.
- **Components:** FastAPI backend (`app.main:app`), Next.js 15.5.9 frontend, async database sessions (PostgreSQL / SQLite compatibility for hermetic test execution), structured logging with request ID tracing, security middleware (HSTS, CSP, X-Frame-Options, CORS).

### Stage 2: Authentication, Multi-Tenant Workspaces, Assets & Roles
- **Status:** Verified and Operational.
- **Components:** Firebase Authentication verification with local development bypass (`test-token-*`), Workspace membership, Role-based access control (`owner`, `admin`, `analyst`, `viewer`), Asset onboarding with SSRF protection, strict `NO AUTHORIZATION → NO SCAN` boundary.

### Stage 3: Controlled Scan Engine & Semgrep Integration Boundary
- **Status:** Verified and Operational.
- **Components:** Asynchronous scan execution lifecycle (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`), Semgrep CLI abstraction boundary, scan events persistence, immutable scanner facts.

### Stage 4: Findings & Evidence Intelligence
- **Status:** Verified and Operational.
- **Components:** Finding normalization, CWE/OWASP mapping, evidence AST snippets, multi-tenant workspace isolation on findings.

### Stage 5: AI Security Analyst
- **Status:** Verified and Operational.
- **Components:** Advisory-only AI analysis layer with structured Pydantic schema validation, fallback handling (Gemini / Grok / Heuristic fallback), prompt injection mitigation via XML-tag fencing, prompt secret redaction.

### Stage 6: Attack Path Intelligence & Deterministic Risk Engine
- **Status:** Verified and Operational.
- **Components:** Directional security graph relationships (`ENABLES`, `LEADS_TO`, etc.), deterministic scoring engine (`risk-v1`), attack path generation, critical vulnerability chain correlation.

### Stage 7: AI Security Team & Multi-Agent Orchestration
- **Status:** Verified and Operational (58 backend tests passing, frontend builds cleanly).
- **Components:** Multi-agent pipeline with 5 analytical agents (`RECON`, `VULNERABILITY_ANALYST`, `ATTACK_PATH`, `RISK_ANALYST`, `SECURITY_REVIEWER`), agent run persistence, executive assessment briefs with mandatory human review boundaries.

---

## 2. Reusable Services & Abstractions for Stage 8

| Service / Abstraction | Source File | Reusability in Stage 8 |
|---|---|---|
| **AI Provider Abstraction** | `app.services.ai_analysis_service` / Gemini & Grok | Direct reuse for generating typed remediation patch proposals. |
| **Safety & Redaction Engine** | `app.ai.safety` | Direct reuse for prompt fencing `<system_instructions>`, `<untrusted_security_data>` and secret sanitization. |
| **Audit Logging Service** | `app.services.audit_service` | Direct reuse for immutable audit trail (`remediation.proposed`, `remediation.validated`, `remediation.approved`, etc.). |
| **Workspace & Role Enforcement** | `app.security.dependencies` (`RequireWorkspaceMember`) | Direct reuse for verifying user identity, workspace isolation, and approval role policies. |
| **Authorization Boundary** | `app.services.authorization_service` | Direct reuse for verifying asset ownership and active authorization before generating or applying patches. |
| **Database Session & Base** | `app.db.base`, `app.db.session` | Direct reuse for ORM models, migrations, and transactions. |

---

## 3. Missing, Unverified, or Incomplete Stage 8 Capabilities

Prior to Stage 8 implementation, the following components are either missing or exist only as stubs:

1. **Database Schema:**
   - `backend/app/models/remediation.py` contains a rudimentary stub from Stage 0/1 (`RemediationProposal` with only 5 statuses: `proposed`, `approved`, `rejected`, `applied`, `superseded`).
   - Missing: Full Stage 8 state machine (`DRAFT`, `GENERATING`, `PROPOSED`, `VALIDATING`, `VALIDATION_FAILED`, `AWAITING_APPROVAL`, `APPROVED`, `APPLYING`, `APPLIED`, `REJECTED`, `EXPIRED`, `ROLLED_BACK`, `FAILED`).
   - Missing: Cryptographic patch hash binding (`patch_hash`), base commit / revision tracking, unified diff content, affected files list, validation records, recoverable checkpoints, and application records.
   - Missing: Sequential migration `supabase/migrations/0008_stage8_remediation.sql`.

2. **Patch Safety & Traversal Prevention:**
   - No dedicated patch-processing service exists to parse unified diffs, validate filepaths, reject directory traversal (`../`), reject absolute paths, reject symlinks, and block sensitive system/secret files (`.env`, `.git`, `credentials`, private keys, database migrations).

3. **Isolated Validation Pipeline:**
   - No bounded validation runner exists to verify syntax, check patch integrity, run unit tests, or execute isolated Semgrep rules in a temporary, disposable workspace.

4. **Human Approval Gate:**
   - No server-side approval service exists to enforce that approval is strictly bound to the specific patch hash and version, preventing applying modified or stale patches.

5. **Safe Application & Rollback Adapter:**
   - No controlled application adapter with pre-apply snapshot/checkpointing and clean rollback on divergence exists.
   - No verification handoff mechanism ("APPLIED — VERIFICATION PENDING").

6. **API Endpoints & Router:**
   - No remediation endpoints are registered in `app/api/v1/api.py`.

7. **Frontend Remediation Dashboard:**
   - No `/remediations` list or `/remediations/[id]` detail page exists in Next.js.
   - Code diff viewer with unified diff syntax highlighting is missing.

---

## 4. Implementation Plan for Stage 8

1. **Database Migration & Models:**
   - Create `supabase/migrations/0008_stage8_remediation.sql`.
   - Update `backend/app/models/remediation.py` with `RemediationProposal`, `RemediationValidation`, `RemediationApproval`, `RemediationCheckpoint`, `RemediationApplication`.
2. **Patch Safety Engine (`PatchProcessor`):**
   - Path traversal defenses, strict file allowlists/blocklists, unified diff parser, diff size limits, patch hash calculation (`SHA-256`).
3. **AI Remediation Service (`RemediationService`):**
   - Prompt construction with strict fencing, minimal context injection, Pydantic response validation, error recovery.
4. **Validation Pipeline (`ValidationService`):**
   - Syntactic AST verification, patch parsing, test execution within timeout and resource constraints, Semgrep re-check on isolated working copy.
5. **Approval Service (`ApprovalService`):**
   - Role enforcement (Admin/Owner), patch hash binding, validation check prerequisite, audit logging.
6. **Controlled Application & Rollback Adapter (`PatchApplicationAdapter`):**
   - Checkpoint creation, atomic patch application in isolated workspace, diff verification, rollback support, status update to `APPLIED` with handoff `APPLIED — VERIFICATION PENDING`. Finding remains UNRESOLVED.
7. **FastAPI Endpoints:**
   - `/api/v1/remediations` and `/api/v1/findings/{id}/remediations`.
8. **Frontend Implementation:**
   - `/remediations` and `/remediations/[id]` with side-by-side / unified diff viewer, status badges, action controls.
9. **Automated Testing Suite:**
   - Comprehensive backend tests covering all positive and negative security invariants.
