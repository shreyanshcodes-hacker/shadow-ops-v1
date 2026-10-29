# SHADOWOPS — STAGE 7 BASELINE REPORT
**Date:** 2026-10-27  
**Stage:** STAGE 7 — AI SECURITY TEAM & MULTI-AGENT ORCHESTRATION  
**Baseline Status:** VERIFIED & AUDITED  

---

## 1. Existing System Audit

### 1.1 Finding & Scanner Facts Architecture (Stages 3 & 4)
- **Authoritative Scanner Output:** Semgrep engine executes strictly under the `NO AUTHORIZATION -> NO SCAN` invariant. Raw findings are normalized into `findings` with immutable scanner facts: `title`, `description`, `severity`, `confidence`, `cwe_ids`, `owasp_categories`, and `location`.
- **Finding Evidence:** Static AST snippets, line ranges, and matched rules are stored in `finding_evidence`.
- **Advisory AI Analysis:** Previous Stage 5 implemented `finding_ai_analysis` supporting advisory explanations, exploitability evaluations, attack preconditions, and grounded citations, without altering authoritative scanner facts.

### 1.2 Attack Path & Deterministic Risk Engine (Stage 6)
- **Security Relationships (`security_relationships`):** Stores directed relationships between findings (`DEPENDS_ON`, `ENABLES`, `EXPOSES`, `LEADS_TO`, `SHARES_COMPONENT`, `SHARES_ENTRY_POINT`, `SHARES_DATA_FLOW`, `AMPLIFIES`) with strict confidence, status, and source tags (`DETERMINISTIC`, `AI_SUGGESTED`, `HUMAN_CONFIRMED`).
- **Attack Paths (`attack_paths`, `attack_path_nodes`, `attack_path_edges`):** Multi-step exploit chains bounded by `MAX_ATTACK_PATH_NODES = 8` with DFS cycle detection.
- **Deterministic Risk Engine (Model: `risk-v1`):** Pure mathematical risk scoring ($0.00 – 100.00$) calculated deterministically based on Finding Severity (30%), Exploitability (20%), Asset Criticality (20%), Confidence (15%), Exposure (10%), and Path Complexity (5%). All scores are logged in immutable `risk_snapshots`.
- **Core Invariant Verified:** *"AI MAY SUGGEST RELATIONSHIPS. DETERMINISTIC CODE DECIDES THE FINAL SCORE."*

### 1.3 AI Provider Abstraction
- Abstract base class `AIProvider` in `app/ai/provider.py` with factory `get_ai_provider()`.
- Implemented providers:
  - `GeminiProvider`: Google GenAI integration with structured JSON schemas.
  - `GrokProvider`: X.AI Grok provider with structured JSON outputs.
  - `FakeAIProvider`: Deterministic in-memory test double supporting hermetic unit tests.
- Safety and sanitization:
  - `redact_secrets()` in `app/ai/safety.py` purges AWS keys, private keys, bearer tokens, database URIs, and passwords before prompt assembly.
  - Structural prompt fencing (`<system_instructions>`, `<untrusted_security_data>`, `<task>`).

### 1.4 Job & Worker Infrastructure
- Abstract job interfaces in `app/workers/jobs.py` (`BaseJob`, `JobStatus`).
- Async database transactions via `AsyncSession` (PostgreSQL / Supabase in production, SQLite in automated tests).
- Audit trail logging via `AuditService` in `app/services/audit_service.py` recording structured security events.

---

## 2. Reusable Components for Stage 7
1. `AIProvider` / `get_ai_provider()` / `FakeAIProvider`: Fully reusable for all 5 specialized agents.
2. `redact_secrets()`: Reusable for all agent context builders to enforce zero credential leakage.
3. `AuditService`: Reusable for recording `security_team.*` and `agent.*` lifecycle events.
4. `WorkspaceService`: Reusable for tenant membership and role-based access validation.
5. `RiskEngine` / `risk_snapshots`: Reusable as authoritative inputs to `RISK_ANALYST_AGENT` and `SECURITY_REVIEWER_AGENT`.
6. `AttackPathRepository`: Reusable for querying nodes, edges, and paths.

---

## 3. Stage 7 Additions & Architectural Scope

### 3.1 The 5 Specialized Analytical Agents
1. `RECON_AGENT`: Analyzes asset architecture, entry points, perimeter boundaries, and exposed services without claiming ungrounded facts.
2. `VULNERABILITY_ANALYST_AGENT`: Evaluates finding depth, attack preconditions, exploit feasibility, and missing evidence.
3. `ATTACK_PATH_AGENT`: Analyzes relationships and lateral movement across findings; never overrides deterministic scores.
4. `RISK_ANALYST_AGENT`: Interprets deterministic `risk-v1` score factors and translates mathematical weights into actionable risk explanations.
5. `SECURITY_REVIEWER_AGENT`: Synthesizes outputs from the 4 upstream agents into an authoritative `TeamAssessment` with key concerns, uncertainties, and human action items.

### 3.2 Common Typed Agent Contract
- `AgentRequest`: Structured input including run IDs, workspace ID, scope, context payload, task definition, and constraints.
- `AgentResponse`: Typed result including agent name, status (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `BLOCKED`), summary, structured output, confidence, uncertainty, evidence references, duration, provider, and model metadata.

### 3.3 Centralized Registry & Deterministic Orchestration
- `AgentRegistry`: Central registration and discovery of analytical agents.
- `SecurityTeamOrchestrator`: Coordinates execution flow with deterministic dependency sequencing:
  $$\text{RECON} \longrightarrow \text{VULNERABILITY ANALYST} \longrightarrow \text{ATTACK PATH ANALYST} \longrightarrow \text{RISK ANALYST} \longrightarrow \text{SECURITY REVIEWER}$$
- Supports independent parallel evaluations where appropriate (e.g., individual finding analyses) while keeping dependent tasks serialized.
- Idempotency guards prevent duplicate concurrent runs on the same scope.
- Durable persistence in `security_team_runs` and `agent_runs`.

### 3.4 Non-Negotiable Human-in-the-Loop Review Boundary
- Agents are strictly **analytical workers**. They cannot commit code, patch vulnerabilities, accept risks, deploy changes, or close findings.
- Team run status: `AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED`.
- Explicit human review action: `POST /api/v1/security-team/runs/{id}/review` captures `reviewed_by` and `reviewed_at`.
