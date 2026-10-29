# IMPLEMENTATION ROADMAP — SHADOWOPS (STAGES 0 TO 24)

## Master Implementation Plan Overview

This document defines the 25-stage implementation roadmap for ShadowOps. Each stage represents a discrete, verifiable engineering milestone. For every stage, the technical contracts, schema migrations, backend tasks, frontend views, AI capabilities, security considerations, test suites, and acceptance criteria are specified.

---

### Master Stage Index

| Stage | Name | Target Focus | Dependencies |
|:---:|---|---|:---:|
| **0** | **Product Ingestion, Architecture & Planning** | Architecture blueprints, system design, source of truth | None |
| **1** | **Foundation** | Repositories, toolchains, base configs, database extensions | Stage 0 |
| **2** | **UI/UX Command Center Foundation** | Cybersecurity theme, design tokens, dashboard shell, navigation | Stage 1 |
| **3** | **Authentication & Identity** | Firebase Auth integration, user sync, backend JWT verification | Stage 1 |
| **4** | **Workspace Management & Isolation** | Multi-tenancy, workspace creation, member invites, RBAC | Stage 3 |
| **5** | **Assets & Authorization Engine** | Asset catalog, SSRF protection, DNS/HTTP verification engine | Stage 4 |
| **6** | **Scan Engine Core** | Scan state machine, event bus, job queue, progress streaming | Stage 5 |
| **7** | **Semgrep Code Analysis Integration** | Ephemeral runner, SAST rule packs, SARIF normalization | Stage 6 |
| **8** | **AI Security Manager Core** | Orchestrator, Gemini/Grok router, Pydantic schema validation | Stage 6 |
| **9** | **Specialized Security Agents** | Implementation of 8 specialized agents, DAG workflows | Stage 8 |
| **10** | **Findings & Evidence Management** | Normalized findings catalog, deduplication, evidence viewer | Stages 7, 9 |
| **11** | **Deterministic Risk Engine** | Algorithmic scoring, factor weighting, explainability modal | Stage 10 |
| **12** | **Attack Path Engine** | Threat reachability graphs, node/edge persistence, ReactFlow | Stages 10, 11 |
| **13** | **Remediation System & Approval Gates** | AI diff generation, human approval gate, PR creation | Stages 10, 11 |
| **14** | **Empirical Verification Engine** | Automated re-scan, reproduction testing, posture recalculation | Stage 13 |
| **15** | **Executive & Technical Reporting** | PDF/Markdown generation, SOC 2 compliance summaries | Stages 10, 12, 14 |
| **16** | **Contextual AI Security Chat** | Workspace-grounded RAG, evidence citations, streaming UI | Stages 10, 15 |
| **17** | **Operational Automation (n8n)** | Webhook dispatch, Slack/Discord alerts, scheduled scans | Stages 6, 13 |
| **18** | **Third-Party Integrations** | GitHub App, GitLab, AWS, Jira issue syncing | Stages 5, 13 |
| **19** | **Security Hardening & Boundary Defense** | Pen-testing defenses, rate limiting, WAF, secret scrubbing | Stages 1–18 |
| **20** | **End-to-End Testing & QA** | Automated integration test suite, cross-tenant leak checks | Stages 1–19 |
| **21** | **Railway Production Deployment** | Multi-service Railway setup, private mesh, secrets, TLS | Stages 1–20 |
| **22** | **Documentation & Developer Hub** | Architecture docs, user manuals, API reference, runbooks | Stages 0–21 |
| **23** | **AI Governance & Usage Auditing** | Token tracking, cost monitoring, hallucination metrics | Stages 8, 9, 16 |
| **24** | **Final QA & Hackathon Demo Delivery** | Controlled end-to-end demo rehearsal, video walkthrough | Stages 0–23 |

---

## Detailed Specifications by Stage

---

### Stage 0: Product Ingestion, Architecture & Planning
- **Objective**: Ingest requirements, catalog source documents, resolve architectural conflicts, and create comprehensive design specifications.
- **Dependencies**: None.
- **Inputs**: User request specifications, adjacent historical workspace reference artifacts.
- **Outputs**: 15 authoritative architecture documents in `docs/*`.
- **Database Changes**: Conceptual schema design for 23 tables and RLS policies (no migrations executed).
- **Backend Changes**: Blueprinting API routes, middleware, and worker topology.
- **Frontend Changes**: Blueprinting component hierarchy and command center theme tokens.
- **AI Changes**: Designing AI Security Manager, 8 specialized agents, model routing rules.
- **Security Considerations**: Defining the 14 mandatory security principles and `NO AUTH → NO SCAN` boundary.
- **Testing**: Peer review of architecture documents and conflict matrix verification.
- **Acceptance Criteria**: All 15 documents authored with complete specifications; zero code or mock backends generated; explicit STOP.

---

### Stage 1: Foundation
- **Objective**: Establish development environments, initialize Next.js and FastAPI projects, configure Supabase database extensions, and establish CI linting.
- **Dependencies**: Stage 0.
- **Inputs**: Architecture specifications (`SYSTEM_ARCHITECTURE.md`, `DATABASE_ARCHITECTURE.md`).
- **Outputs**: Initialized frontend and backend monorepo/polyrepo structure with working dev servers.
- **Database Changes**: Run extension scripts (`uuid-ossp`, `pgcrypto`).
- **Backend Changes**: FastAPI scaffolding, Pydantic settings config, health check endpoint (`/health`), structured logging.
- **Frontend Changes**: Next.js 14 App Router, TypeScript strict configuration, Tailwind CSS setup.
- **AI Changes**: None.
- **Security Considerations**: Environment variable isolation, `.gitignore` validation for secrets.
- **Testing**: Unit tests verifying `/health` returns 200 OK; frontend renders initial placeholder.
- **Acceptance Criteria**: Backend and frontend local dev environments spin up cleanly with zero errors.

---

### Stage 2: UI/UX Command Center Foundation
- **Objective**: Construct the ShadowOps cybersecurity command center visual identity and master dashboard shell.
- **Dependencies**: Stage 1.
- **Inputs**: UI design tokens (deep charcoal `#0a0b0e`, crimson security accent `#e11d48`, dark glassmorphism).
- **Outputs**: Reusable UI component library (cards, tables, badges, modals, charts) and root navigation.
- **Database Changes**: None.
- **Backend Changes**: None.
- **Frontend Changes**: Implement sidebar navigation (Dashboard, Scans, Findings, Attack Paths, Agents, Remediation, Reports, AI Chat, Assets, Team, Settings), topbar header with workspace switcher, theme providers.
- **AI Changes**: None.
- **Security Considerations**: Sanitization of rendered markdown and code snippets to prevent XSS.
- **Testing**: Component render testing with Jest/React Testing Library.
- **Acceptance Criteria**: Fully responsive navigation layout rendering dark enterprise theme without layout shifts.

---

### Stage 3: Authentication & Identity
- **Objective**: Implement user authentication via Firebase Auth and establish backend JWT validation.
- **Dependencies**: Stage 1.
- **Inputs**: Firebase project credentials.
- **Outputs**: End-to-end login/register flow, JWT verification middleware.
- **Database Changes**: Create `profiles` table with Firebase UID unique index.
- **Backend Changes**: FastAPI `get_current_user` dependency leveraging Firebase Admin SDK to decode and verify JWTs.
- **Frontend Changes**: Firebase Auth Client integration, login screen, signup screen, session provider, token refresh handler.
- **AI Changes**: None.
- **Security Considerations**: HttpOnly cookies / secure in-memory tokens; clock skew tolerance (60s); token revocation checks.
- **Testing**: Test suite verifying valid token grants access and expired/tampered token returns 401.
- **Acceptance Criteria**: User can authenticate; backend correctly identifies user profile from Bearer token.

---

### Stage 4: Workspace Management & Isolation
- **Objective**: Implement multi-tenant workspace creation, membership association, and role-based access control.
- **Dependencies**: Stage 3.
- **Inputs**: Workspace models and RBAC specifications.
- **Outputs**: Workspace CRUD API, member invitation system, workspace context switcher.
- **Database Changes**: Create `workspaces`, `workspace_members`, `roles` tables; initial RLS policies.
- **Backend Changes**: Workspace context middleware (`X-Workspace-Id` header validation), RBAC permission dependency (`require_role`).
- **Frontend Changes**: Workspace creation modal, team member invitation UI, role management table.
- **AI Changes**: None.
- **Security Considerations**: Strict verification that user belongs to requested workspace; RLS policy enforcement.
- **Testing**: Cross-tenant leak tests (verifying User A cannot query User B's workspace).
- **Acceptance Criteria**: Workspaces are isolated; non-members receive 403 Forbidden.

---

### Stage 5: Assets & Authorization Engine
- **Objective**: Implement digital asset management and the mandatory authorization verification engine (`NO AUTH → NO SCAN`).
- **Dependencies**: Stage 4.
- **Inputs**: Asset schemas and verification protocols (DNS TXT, HTTP challenge, GitHub OAuth).
- **Outputs**: Asset catalog UI, challenge issuance service, automated verification worker.
- **Database Changes**: Create `assets` and `asset_authorizations` tables.
- **Backend Changes**: Asset CRUD endpoints, anti-SSRF target validator, DNS TXT resolver, HTTP challenge validator.
- **Frontend Changes**: Asset onboarding wizard, challenge token display modal, real-time verification status badge.
- **AI Changes**: None.
- **Security Considerations**: Anti-SSRF private IP blocking; DNS rebinding protection; strict authorization status check.
- **Testing**: Unit tests verifying authorization validation passes only on matching tokens; mock DNS tests.
- **Acceptance Criteria**: Asset cannot be scanned unless authorization status is verified by backend.

---

### Stage 6: Scan Engine Core
- **Objective**: Build the asynchronous scan pipeline state machine, task queue, and real-time event streaming bus.
- **Dependencies**: Stage 5.
- **Inputs**: Scan state pipeline specification (`SCAN_ARCHITECTURE.md`).
- **Outputs**: Working scan orchestrator executing queued, running, completed, and failed transitions.
- **Database Changes**: Create `scans` and `scan_events` tables.
- **Backend Changes**: Scan initiation endpoint with mandatory authorization check; SSE streaming endpoint (`/scans/{id}/events`); Redis task dispatcher.
- **Frontend Changes**: Live scan progress view with phase indicators, elapsed timer, and live log console.
- **AI Changes**: None.
- **Security Considerations**: Re-verification of authorization at job start; scan cancellation handling.
- **Testing**: Pipeline state machine transitions; simulated failure recovery.
- **Acceptance Criteria**: Scan triggers, streams real-time events over SSE, and completes with state persisted.

---

### Stage 7: Semgrep Code Analysis Integration
- **Objective**: Integrate Semgrep SAST into the scan pipeline running in an ephemeral worker container.
- **Dependencies**: Stage 6.
- **Inputs**: Curated Semgrep rulesets (OWASP Top 10, CWE Top 25).
- **Outputs**: Automated repository clone, language detection, Semgrep execution, and raw SARIF capture.
- **Database Changes**: Configure Supabase Storage `scan-artifacts` bucket.
- **Backend Changes**: Semgrep execution wrapper, subprocess runner with cgroup limits (CPU/memory), timeout watchdog.
- **Frontend Changes**: Code scan configuration settings view (select branch, toggle rule packs).
- **AI Changes**: None.
- **Security Considerations**: Sandbox isolation; non-root worker execution; immediate disk cleanup after scan.
- **Testing**: Execution of Semgrep against test vulnerable code repository; validation of SARIF output format.
- **Acceptance Criteria**: Semgrep executes automatically against authorized repo and produces parsed JSON/SARIF.

---

### Stage 8: AI Security Manager Core
- **Objective**: Build the AI Security Manager orchestration layer with multi-model routing and strict schema enforcement.
- **Dependencies**: Stage 6.
- **Inputs**: Gemini and Grok API keys, Pydantic response schemas.
- **Outputs**: Working LLM client wrapper supporting structured JSON mode and automated schema validation.
- **Database Changes**: Create `agent_runs` table.
- **Backend Changes**: `AIManager` service, model router (routing tasks between Gemini Pro/Flash and Grok), prompt sanitizers.
- **Frontend Changes**: None.
- **AI Changes**: Model routing abstraction, retry on schema parse error, canary token injection for prompt injection defense.
- **Security Considerations**: Token cost limits, PII/secret redaction before prompt transmission.
- **Testing**: Mock LLM schema conformance tests; prompt injection resilience tests.
- **Acceptance Criteria**: AI Manager successfully prompts models and returns guaranteed Pydantic objects.

---

### Stage 9: Specialized Security Agents
- **Objective**: Implement the 8 specialized security agents and their directed acyclic graph (DAG) workflow.
- **Dependencies**: Stage 8.
- **Inputs**: Agent specifications (`AGENT_ARCHITECTURE.md`).
- **Outputs**: Executable agents: Recon, Code Security, Dependency, Threat Analyst, Risk Analyst, Remediation, Verification, Reporting.
- **Database Changes**: Update `agent_runs` logging.
- **Backend Changes**: Agent classes adhering to `BaseAgent` interface, parallel DAG executor.
- **Frontend Changes**: Agent activity visualizer (showing real-time active agent, token usage, execution status).
- **AI Changes**: Specialized system prompts, evidence citation validation.
- **Security Considerations**: Strict evidence reference checks (hallucinations rejected if evidence ID missing).
- **Testing**: Agent unit tests with mock tool inputs; DAG dependency order verification.
- **Acceptance Criteria**: All 8 agents execute in specified order and produce validated typed outputs.

---

### Stage 10: Findings & Evidence Management
- **Objective**: Build the unified vulnerability catalog, deduplication engine, and evidence provenance viewer.
- **Dependencies**: Stages 7, 9.
- **Inputs**: Semgrep findings and AI agent outputs.
- **Outputs**: Deduplicated finding records, evidence attachments, findings explorer UI.
- **Database Changes**: Create `findings` and `finding_evidence` tables.
- **Backend Changes**: Fingerprint calculation service (`hash(asset_id + rule_id + path + line)`), findings REST API.
- **Frontend Changes**: Findings table with severity filters, search, drawer detail view displaying code snippets and AST evidence.
- **AI Changes**: None.
- **Security Considerations**: Sanitization of code snippets in evidence; masking of captured secrets.
- **Testing**: Deduplication test (verifying same vulnerability across 2 scans updates `last_seen_at` without duplicate row).
- **Acceptance Criteria**: Findings correctly populated, deduplicated, and displayed with linked evidence.

---

### Stage 11: Deterministic Risk Engine
- **Objective**: Implement the mathematical, explainable risk calculation formula.
- **Dependencies**: Stage 10.
- **Inputs**: Risk factor weights and scoring rules (`RISK_ARCHITECTURE.md`).
- **Outputs**: Algorithmic risk scores (0–100) and factor breakdowns for every finding.
- **Database Changes**: Create `risk_assessments` table.
- **Backend Changes**: Python `RiskEngine` calculating weighted composite scores from severity, exploitability, exposure, criticality, and confidence.
- **Frontend Changes**: Interactive Risk Factor Breakdown Modal displaying weights, variables, and math formulas.
- **AI Changes**: Risk Analyst Agent provides qualitative exploitability ratings used as formula inputs.
- **Security Considerations**: Engine is strictly deterministic; zero arbitrary AI score hallucination.
- **Testing**: Unit tests checking boundary values (0.0 to 100.0) across 50 simulated vulnerability configurations.
- **Acceptance Criteria**: Every finding receives a verifiable, explainable mathematical risk score.

---

### Stage 12: Attack Path Engine
- **Objective**: Implement graph-based threat reachability intelligence and interactive attack path visualization.
- **Dependencies**: Stages 10, 11.
- **Inputs**: Normalized findings and Threat Analyst Agent chain scenarios.
- **Outputs**: Directed attack graph models, node/edge persistence, ReactFlow graph canvas.
- **Database Changes**: Create `attack_paths`, `attack_path_nodes`, `attack_path_edges` tables.
- **Backend Changes**: Graph traversal algorithms, bottleneck node detection, attack path API.
- **Frontend Changes**: Interactive attack path graph component (ReactFlow) with custom dark cybersecurity nodes, risk badges, and edge animations.
- **AI Changes**: Threat Analyst synthesizes viable breach paths from entry points to crown jewels.
- **Security Considerations**: Workspace scoping for all graph queries.
- **Testing**: Graph generation tests; cycle detection; bottleneck recalculation tests.
- **Acceptance Criteria**: Vulnerability chains render as intuitive directed attack paths highlighting critical bottlenecks.

---

### Stage 13: Remediation System & Approval Gates
- **Objective**: Build the AI remediation proposal generator, human review gate, and automated delivery workflow.
- **Dependencies**: Stages 10, 11.
- **Inputs**: Remediation Agent prompts, GitHub OAuth app integration.
- **Outputs**: Verified code patch diffs, human approval UI, automated Git Pull Request generation.
- **Database Changes**: Create `remediation_proposals` and `remediation_approvals` tables.
- **Backend Changes**: Remediation proposal generator, AST syntax validator for diffs, GitHub API PR creator.
- **Frontend Changes**: Side-by-side unified code diff viewer, "Approve Fix" modal with mandatory notes, "Download Patch" button.
- **AI Changes**: Remediation Agent generates syntactically valid patches tailored to existing code.
- **Security Considerations**: Human approval is mandatory; system never commits to main branch directly.
- **Testing**: Verification that patch applies cleanly with `patch --check`; approval audit logging verification.
- **Acceptance Criteria**: User reviews diff, clicks approve, and backend automatically creates GitHub PR on isolated branch.

---

### Stage 14: Empirical Verification Engine
- **Objective**: Implement automated, empirical re-testing to confirm fixes worked before closing vulnerabilities.
- **Dependencies**: Stage 13.
- **Inputs**: Applied remediation records, verification methodologies (`VERIFICATION_ARCHITECTURE.md`).
- **Outputs**: Automated re-scan jobs, verification records, posture score recalculation.
- **Database Changes**: Create `verification_runs` table.
- **Backend Changes**: `VerificationOrchestrator` executing targeted Semgrep rescans, reproduction probes, and dependency checks.
- **Frontend Changes**: Verification status indicator on finding cards; "Re-Verify Now" manual trigger button.
- **AI Changes**: Verification Agent analyzes test output and confirms absence of regression.
- **Security Considerations**: Finding is marked fixed only upon empirical proof (zero rule matches).
- **Testing**: Test against both fixed and intentionally un-fixed code; confirm proper pass/fail detection.
- **Acceptance Criteria**: Fixed vulnerability automatically transitions to `fixed`, updates attack paths, and boosts workspace security score.

---

### Stage 15: Executive & Technical Reporting
- **Objective**: Build the automated reporting engine generating executive summaries, SOC 2 compliance briefs, and technical scan exports.
- **Dependencies**: Stages 10, 12, 14.
- **Inputs**: Workspace security data, findings, risk trends, verification logs.
- **Outputs**: Downloadable PDF, Markdown, and JSON security reports.
- **Database Changes**: Create `reports` table; configure Supabase Storage `security-reports` bucket.
- **Backend Changes**: Report generation service compiling structured JSON and rendering PDF documents.
- **Frontend Changes**: Reports dashboard, report generator modal (select type: Executive, Technical, Compliance), previewer and download buttons.
- **AI Changes**: Reporting Agent synthesizes executive narratives and compliance readiness summaries.
- **Security Considerations**: Signed, time-expiring URLs for report downloads; workspace tenant isolation.
- **Testing**: PDF generation speed and format verification; data completeness validation.
- **Acceptance Criteria**: Executive and technical reports generate reliably with accurate charts and metrics.

---

### Stage 16: Contextual AI Security Chat
- **Objective**: Build an interactive, workspace-scoped AI security assistant answering natural language questions about findings and posture.
- **Dependencies**: Stages 10, 15.
- **Inputs**: User prompts, workspace security database context.
- **Outputs**: Streaming AI chat interface with interactive citations to concrete findings and evidence.
- **Database Changes**: Create `chat_conversations` and `chat_messages` tables.
- **Backend Changes**: RAG pipeline retrieving workspace-scoped findings, prompt assembler, streaming response endpoint.
- **Frontend Changes**: AI Security Chat view, streaming markdown renderer, clickable finding citation badges.
- **AI Changes**: Strict system prompt enforcing workspace grounding; explicit refusal to invent unrecorded findings.
- **Security Considerations**: Prompt injection defense; strict scoping to user's active workspace data.
- **Testing**: Verify AI cannot answer questions about other workspaces; verify citations link to real DB records.
- **Acceptance Criteria**: User asks "What is my highest risk vulnerability?", AI provides accurate answer with clickable citation.

---

### Stage 17: Operational Automation (n8n)
- **Objective**: Deploy and integrate n8n workflows for event-driven alerts and recurring operational automation.
- **Dependencies**: Stages 6, 13.
- **Inputs**: Backend event webhook catalog.
- **Outputs**: Working n8n workflows for Slack/Discord alerts, PagerDuty incident creation, and scheduled weekly scans.
- **Database Changes**: None.
- **Backend Changes**: Webhook dispatcher service sending signed HMAC payloads to n8n upon security events.
- **Frontend Changes**: Webhook notification settings UI in workspace settings.
- **AI Changes**: None.
- **Security Considerations**: HMAC-SHA256 signature verification on all outbound webhooks.
- **Testing**: Triggering scan event and confirming Slack notification delivery via n8n.
- **Acceptance Criteria**: Critical findings and scan completions successfully dispatch notifications through n8n.

---

### Stage 18: Third-Party Integrations
- **Objective**: Implement native connectors for GitHub, GitLab, and Jira.
- **Dependencies**: Stages 5, 13.
- **Inputs**: OAuth app client credentials.
- **Outputs**: One-click repo importing, bi-directional Jira ticket synchronization.
- **Database Changes**: Store encrypted OAuth tokens in `assets.metadata` or integration configs.
- **Backend Changes**: GitHub App webhook handlers, Jira issue creation API client.
- **Frontend Changes**: Integrations management page with connect/disconnect status toggles.
- **AI Changes**: None.
- **Security Considerations**: AES-256 encryption of external API tokens at rest.
- **Testing**: Full OAuth dance with GitHub; mock Jira ticket sync test.
- **Acceptance Criteria**: Repositories can be imported directly via GitHub App with automated token rotation.

---

### Stage 19: Security Hardening & Boundary Defense
- **Objective**: Conduct comprehensive defense-in-depth hardening across API, database, and scanner environments.
- **Dependencies**: Stages 1–18.
- **Inputs**: Security architecture specifications (`SECURITY_ARCHITECTURE.md`).
- **Outputs**: Production-grade WAF rules, strict CSP headers, rate limiters, anti-tampering guards.
- **Database Changes**: Verification of RLS policies on all tables; denial of direct table mutations.
- **Backend Changes**: SlowAPI rate limiting (100 req/min), input sanitization, security headers middleware (`HSTS`, `CSP`, `X-Frame-Options`).
- **Frontend Changes**: Implementation of strict Content Security Policy meta tags.
- **AI Changes**: Automated canary token leakage verification and prompt abuse rate limiting.
- **Security Considerations**: Comprehensive review against OWASP Top 10 API Security Risks.
- **Testing**: Automated vulnerability scan against backend API endpoints using OWASP ZAP.
- **Acceptance Criteria**: Zero high or critical vulnerabilities identified during API self-assessment.

---

### Stage 20: End-to-End Testing & QA
- **Objective**: Build an exhaustive automated end-to-end integration test suite validating the entire product lifecycle.
- **Dependencies**: Stages 1–19.
- **Inputs**: Test matrices and scenario specifications.
- **Outputs**: Automated test suites in Playwright (E2E) and Pytest (Integration).
- **Database Changes**: Test database fixtures and cleanup scripts.
- **Backend Changes**: Test factories for generating mock assets, findings, and scan runs.
- **Frontend Changes**: Test attributes (`data-testid`) added to key UI interactive elements.
- **AI Changes**: Deterministic mock provider for CI testing without incurring external LLM costs.
- **Security Considerations**: Automated cross-tenant penetration tests (attempting cross-workspace access).
- **Testing**: Continuous integration pipeline running 100% of integration test suite.
- **Acceptance Criteria**: Complete 21-step product loop executes successfully in automated test runner with 0 failures.

---

### Stage 21: Railway Production Deployment
- **Objective**: Deploy the full production multi-service architecture onto Railway.
- **Dependencies**: Stages 1–20.
- **Inputs**: Railway deployment blueprints (`RAILWAY_DEPLOYMENT_ARCHITECTURE.md`).
- **Outputs**: Live production deployment with custom domains, TLS certificates, and health monitoring.
- **Database Changes**: Execute database migrations against production Supabase PostgreSQL instance.
- **Backend Changes**: Dockerfiles optimized for production; Railway configuration files (`railway.json`).
- **Frontend Changes**: Next.js standalone build configuration.
- **AI Changes**: Live production API keys configured in Railway secrets.
- **Security Considerations**: Production secrets injection; Railway Private Network isolation for Redis and workers.
- **Testing**: Live production health checks (`/health`, `/api/health`, `/healthz`).
- **Acceptance Criteria**: All Railway services report healthy status; frontend accessible on public HTTPS domain.

---

### Stage 22: Documentation & Developer Hub
- **Objective**: Author comprehensive user guides, API documentation, deployment runbooks, and operator manuals.
- **Dependencies**: Stages 0–21.
- **Inputs**: Implemented system architecture and user workflows.
- **Outputs**: Published documentation in `/docs` and interactive OpenAPI documentation.
- **Database Changes**: None.
- **Backend Changes**: OpenAPI `/docs` endpoint configured with detailed operation descriptions.
- **Frontend Changes**: In-app "Help & Documentation" links.
- **AI Changes**: None.
- **Security Considerations**: Sanitization of docs (ensuring no internal IPs or secret keys appear in examples).
- **Testing**: Documentation link checking and formatting validation.
- **Acceptance Criteria**: Full documentation suite available covering onboarding, API usage, and operations.

---

### Stage 23: AI Governance & Usage Auditing
- **Objective**: Deploy granular token usage analytics, cost dashboards, and AI safety monitoring.
- **Dependencies**: Stages 8, 9, 16.
- **Inputs**: `agent_runs` telemetry data.
- **Outputs**: AI Usage & Governance Dashboard for workspace administrators.
- **Database Changes**: Aggregation views for monthly token expenditure.
- **Backend Changes**: Analytics endpoints calculating token volume, cost per agent, and average latency.
- **Frontend Changes**: AI Analytics page in Settings displaying burn charts and model breakdown.
- **AI Changes**: None.
- **Security Considerations**: Auditability of AI costs and prompt versions.
- **Testing**: Verification of cost calculation against provider billing rates.
- **Acceptance Criteria**: Workspace admins can inspect token consumption and cost down to individual agent executions.

---

### Stage 24: Final QA & Hackathon Demo Delivery
- **Objective**: Execute a flawless end-to-end rehearsal and deliver the live hackathon demonstration using a controlled, authorized target.
- **Dependencies**: Stages 0–23.
- **Inputs**: Controlled vulnerable test target repository (e.g. `shadowops-demo-app`).
- **Outputs**: Recorded video walkthrough, presentation slide deck, and live working demo.
- **Database Changes**: Pre-seeded demo workspace with verified authorization.
- **Backend Changes**: None.
- **Frontend Changes**: Polished demo presentation mode.
- **AI Changes**: Rehearsed agent workflows on target repository.
- **Security Considerations**: 100% compliant demo on authorized test asset; zero scans on unauthorized third-party hosts.
- **Testing**: Full dry run of 21-step narrative from login to verified remediation and score improvement.
- **Acceptance Criteria**: Seamless demonstration of the complete core product loop within 5 minutes.
