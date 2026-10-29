# Stage 9 Baseline Audit: Independent Fix Verification & Regression Analysis

## 1. Executive Summary

This document establishes the verified baseline for **Stage 9: Independent Fix Verification & Regression Analysis** in the ShadowOps platform. ShadowOps is an AI-native cybersecurity SaaS platform for startups. Stages 0 through 8 have been implemented and verified with 71 passing backend integration tests and a clean Next.js 15 frontend build.

Stage 9 builds upon the safe remediation pipeline established in Stage 8, enforcing the core security invariant:
> **"No sufficient evidence means no verified fix."**
> Neither patch application, passing tests, AI approvals, nor the disappearance of a finding from a single scanner run constitutes proof of a fix. Verification requires deterministic baseline comparison, independent rescan, regression checks, conservative evidence matching, and mandatory human sign-off before finding status can transition.

---

## 2. Audit of Existing Stages & Reusable Capabilities

### Stage 3: Controlled Scanning & Semgrep
- **Scan Service (`backend/app/services/scan_service.py`)**:
  - Manages scan lifecycles (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`).
  - Enforces workspace isolation and verified authorization token check prior to triggering scanner.
- **Semgrep Adapter (`backend/app/scanning/semgrep.py`)**:
  - Executes isolated Semgrep rulesets against authorized asset targets.
  - Generates raw JSON findings with rule IDs, file locations, line ranges, and matched code snippets.
- **Scanner Invariant**:
  - Scanner output is authoritative evidence; scans cannot be forged or bypassed.

### Stage 4: Findings & Evidence Model
- **Findings (`backend/app/models/finding.py`)**:
  - Fields: `id`, `workspace_id`, `scan_id`, `asset_id`, `title`, `description`, `severity`, `cwe_ids`, `location`, `code_snippet`, `status`, `remediation_advice`.
  - Finding statuses: `OPEN`, `FIXED`, `FALSE_POSITIVE`, `ACCEPTED_RISK` (and lowercase equivalents `open`, `triaged`, `resolved`, `dismissed`).
- **Evidence (`backend/app/models/finding.py`)**:
  - `Evidence` model: `finding_id`, `evidence_type` (`semgrep_match`, `file_content`, `ast_fingerprint`), `data`, `hash`.
  - Finding Normalizer (`backend/app/scanners/normalizer.py`): Extracts and hashes deterministic evidence.

### Stage 5: AI Security Analyst
- **AI Security Analyst (`backend/app/services/ai_analysis_service.py`)**:
  - Generates contextual risk explanations, attack scenarios, and remediation suggestions.
  - **Boundary Invariant**: Advisory only. AI cannot modify finding state or claim a finding is fixed.

### Stage 6: Attack Paths & Deterministic Risk Engine
- **Graph & Attack Paths (`backend/app/services/graph_service.py`, `backend/app/models/attack_path.py`)**:
  - Relates assets, findings, and exploits into directed attack graphs.
- **Deterministic Risk Engine (`backend/app/services/risk_engine.py`)**:
  - Strict mathematical risk scoring (0-100) based on CVSS, reachability, asset criticality, and environment context. AI never computes numbers.

### Stage 7: AI Security Team Orchestration
- **Specialized Agents (`backend/app/services/security_agents.py`, `backend/app/services/security_team_orchestrator.py`)**:
  - AppSec, CloudSec, Compliance, and Triage agents collaborate over normalized findings.

### Stage 8: AI Remediation, Human Approval & Safe Patch Management
- **Remediation Proposal (`backend/app/models/remediation.py`)**:
  - Fields: `workspace_id`, `asset_id`, `finding_id`, `source_scan_id`, `proposal_title`, `problem_summary`, `proposed_solution`, `rationale`, `affected_files`, `patch_reference`, `unified_diff`, `patch_hash`, `target_base_revision`, `status`, `version`.
- **Validation Pipeline (`backend/app/services/validation_service.py`)**:
  - Syntactic validation (`ast.parse`), diff parsing, forbidden pattern detection (`eval`, `system`, credential hardcoding), regression check allowlisting.
- **Human Approval Gate (`backend/app/services/approval_service.py`)**:
  - Cryptographically binds approval decision to exact `patch_hash` and `proposal_version`. Enforces RBAC (`admin` / `security_engineer`). AI cannot approve.
- **Safe Patch Applier & Checkpoints (`backend/app/services/patch_applier.py`)**:
  - Generates immutable snapshot checkpoints before modifying files; atomic application; safe rollback on failure.
- **Initial Verification Stub (`VerificationRun`)**:
  - Existed as an initial stub in Stage 8 models (`backend/app/models/remediation.py`).
  - Must now be upgraded to the full Stage 9 Verification Architecture.

---

## 3. Gap Analysis for Stage 9

| Required Stage 9 Capability | Current State in Repository | Implementation Plan |
| :--- | :--- | :--- |
| **Verification Execution Lifecycle** | Basic `VerificationRun` stub in `remediation.py` | Create dedicated `VerificationJob` model with explicit lifecycle states: `QUEUED`, `RUNNING`, `BASELINE_CHECK`, `RESCANNING`, `REGRESSION_CHECK`, `COMPARING_EVIDENCE`, `PASSED_PENDING_REVIEW`, `FAILED`, `INCONCLUSIVE`, `BLOCKED`, `CANCELED`. |
| **Independent Sub-Outcomes** | Single `passed` boolean flag | Multi-dimensional outcome tracking: `vulnerability_status`, `regression_status`, `scanner_status`, `test_status`, `policy_verdict`. |
| **Evidence Comparison Engine** | None | Build `EvidenceComparisonEngine` implementing conservative fingerprint computation, line shift handling, and categorization (`STILL_PRESENT`, `NO_LONGER_DETECTED`, `MODIFIED_OR_MOVED`, `POSSIBLE_REGRESSION`, `NEW_FINDING`, `UNCOMPARABLE`). |
| **Regression Runner** | Validation checks in Stage 8 | Build `RegressionRunner` to execute syntax checks, AST verification, test suite allowlist execution, and integrity validation. |
| **Deterministic Verification Policy** | None | Implement `verification-policy-v1` rule engine. Strictly blocks verification if scanner failed, regressions detected, or evidence is inconclusive. |
| **Human Review Sign-Off Gate** | Human approval exists for patch, but not for fix verification | Implement `VerificationReview` with human approval (`accepted` / `rejected`) requirement before finding status can transition to `resolved`/`fixed`. |
| **API Endpoints** | Proposal verify stub in Stage 8 | Implement `/verifications`, `/verifications/{id}`, `/verifications/{id}/comparisons`, `/verifications/{id}/checks`, `/verifications/{id}/review`, `/verifications/{id}/rerun`. |
| **Frontend UI** | Verification status badge only | Create `/verifications` list page, `/verifications/[id]` detail page with side-by-side evidence diff, check breakdown, and sign-off dialog. |

---

## 4. Architectural Invariants for Stage 9

1. **Independent Verification Execution**: Verification rescans and checks must run independently of the proposal generator.
2. **Deterministic Evidence Matching**: Never assume a vulnerability is resolved because line numbers changed. Compare AST rules, code hashes, and surrounding context.
3. **Multi-Check Regression Guarantee**: No patch is verified if any regression check or syntax test fails.
4. **Mandatory Human Sign-off**: Software and policies can declare `VERIFIED_CANDIDATE`. Only an authorized human user (`admin` or `security_engineer`) can declare the vulnerability `resolved`.
5. **Strict Multi-Tenant Isolation**: Verification jobs, rescans, comparisons, and audit records must be strictly scoped to `workspace_id`.
