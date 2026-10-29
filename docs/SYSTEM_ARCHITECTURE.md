# SYSTEM ARCHITECTURE — SHADOWOPS

## 1. High-Level Architectural Diagram

```
                                  ┌────────────────────────┐
                                  │      SECURITY USER     │
                                  └───────────┬────────────┘
                                              │ HTTPS (Web Browser)
                                              ▼
                             ┌─────────────────────────────────┐
                             │    NEXT.JS 14 FRONTEND (App)    │
                             │ (TypeScript, Tailwind, Shadcn)  │
                             └────────────────┬────────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      │ Authenticate                                  │ API Calls (Bearer Token)
                      ▼                                               ▼
         ┌────────────────────────┐                      ┌─────────────────────────┐
         │     FIREBASE AUTH      │                      │     PYTHON BACKEND      │
         │ (Identity, JWT Issuer) │                      │     (FastAPI Core)      │
         └────────────────────────┘                      └────────────┬────────────┘
                                                                      │
                      ┌───────────────────────────────────────────────┼───────────────────────────────────────────────┐
                      │                                               │                                               │
                      ▼                                               ▼                                               ▼
       ┌──────────────────────────────┐                ┌──────────────────────────────┐                ┌──────────────────────────────┐
       │      BUSINESS SERVICES       │                │      AI AGENT SUBSYSTEM      │                │      SECURITY CONTROLS       │
       │  - Workspace Manager         │                │  - AI Security Manager       │                │  - AuthZ Validator           │
       │  - Asset Management          │                │  - Recon / Code / Dep Agents │                │  - Boundary Enforcer         │
       │  - Findings Engine           │                │  - Threat / Risk Analysts    │                │  - Input Sanitizer / WAF     │
       │  - Risk / Attack Path Engine │                │  - Remediation / Verifier    │                │  - Audit Logger              │
       └──────────────┬───────────────┘                └──────────────┬───────────────┘                └──────────────┬───────────────┘
                      │                                               │                                               │
                      │                                               │                                               │
                      ▼                                               ▼                                               ▼
        ┌───────────────────────────┐                   ┌───────────────────────────┐                   ┌───────────────────────────┐
        │    SUPABASE POSTGRESQL    │                   │   AI MODEL ORCHESTRATION  │                   │      SEMGREP SCANNER      │
        │ - Relational Data & Enums │                   │ - Gemini 1.5 Pro / Flash  │                   │ - SAST Rule Runner        │
        │ - Row Level Security(RLS) │                   │ - Grok AI Engine          │                   │ - Lockfile SCA Inspector  │
        │ - pgvector (Future RAG)   │                   │ - Structured Pydantic V2  │                   │ - Isolated Sandbox        │
        └─────────────┬─────────────┘                   └───────────────────────────┘                   └───────────────────────────┘
                      │
                      ▼
        ┌───────────────────────────┐
        │     SUPABASE STORAGE      │
        │ - Raw SARIF / Scan Logs   │
        │ - Screenshots & Evidence  │
        │ - PDF / Technical Reports │
        └───────────────────────────┘
                      │
                      ▼
        ┌───────────────────────────┐
        │      N8N AUTOMATION       │
        │ - Webhooks & Alerts       │
        │ - Slack / Discord Pushes  │
        │ - Scheduled Workflows     │
        └───────────────────────────┘
```

---

## 2. Component Subsystems & Responsibilities

### 2.1 Next.js 14 Frontend
- **Framework**: Next.js 14 App Router with React Server Components (RSC) and Client Components.
- **Language & Styling**: TypeScript (Strict Mode) and Tailwind CSS with custom ShadowOps cybersecurity tokens (deep charcoal `#0a0b0e`, crimson security accent `#e11d48` / `#ff2442`, muted borders, high contrast data tables).
- **Client Auth**: Firebase Client SDK handles user sign-in (email/password, GitHub OAuth, SSO), manages JWT token refresh cycles, and passes short-lived Bearer tokens in headers.
- **Realtime UX**: Server-Sent Events (SSE) and polling hooks for live scan execution graphs, agent activity indicators, and streaming AI Security Chat responses.
- **Boundary Rule**: Frontend state is strictly display-only; no security or authorization decisions are made in client code.

### 2.2 Python Backend (FastAPI Core)
- **Framework**: Python 3.11+ with FastAPI, structured with modular routers, dependency injection, and Pydantic v2 schemas.
- **Authentication Dependency**: Firebase Admin SDK parses, cryptographically validates, and decodes incoming Firebase JWTs on every protected route.
- **Authorization & Workspace Context**: Injects active workspace context, verifies caller roles against `workspace_members`, and ensures tenant isolation before any business logic executes.
- **API Surface**: RESTful endpoints adhering to OpenAPI specifications, versioned under `/api/v1/*`.
- **Event Streaming**: SSE endpoints under `/api/v1/scans/{id}/events` stream real-time phase updates, agent status changes, and newly identified findings directly to the UI.

### 2.3 Database & Storage Layer (Supabase)
- **Supabase PostgreSQL 16+**: High-performance relational database with strict foreign keys, cascade rules, and check constraints.
- **Row Level Security (RLS)**: Enforces workspace isolation directly at the database engine layer. All queries executed on behalf of a user are scoped to their authorized `workspace_id`.
- **Supabase Storage**: S3-compatible encrypted object store containing:
  - `scan-artifacts`: Raw Semgrep JSON/SARIF output, raw reconnaissance logs.
  - `finding-evidence`: HTTP request/response dumps, AST code excerpts, screenshots.
  - `security-reports`: Compiled PDF, Markdown, and HTML reports.
  - Signed URLs with short lifespans (15 minutes) prevent unauthorized asset access.

### 2.4 Code Analysis Engine (Semgrep)
- **Role**: High-speed, AST-aware static application security testing (SAST) and software composition analysis (SCA).
- **Execution Model**: Runs in a sandboxed, ephemeral subprocess or container worker with strict resource constraints (CPU/memory caps, no outbound network access).
- **Rule Management**: Curated rulesets for OWASP Top 10, CWE Top 25, secret leakage, and framework-specific anti-patterns (Python, TypeScript, Go, Java).
- **Normalization**: Translates raw Semgrep JSON outputs into the canonical ShadowOps `Finding` and `FindingEvidence` schemas.

### 2.5 AI Model Orchestration (Gemini & Grok)
- **Multi-Model Routing**: Intelligently routes tasks to either Google Gemini (1.5 Pro / Flash) or xAI Grok based on analytical strengths, context window requirements, latency, and cost constraints.
- **Structured Output Engine**: Enforces strict JSON schema generation using Pydantic schemas, validating responses before downstream consumption.
- **Context Builders**: Assembles strictly scoped, sanitized context (findings, verified evidence, asset metadata) while stripping API keys and PII to prevent context pollution and data leakage.

### 2.6 Automation Layer (n8n)
- **Role**: Pluggable operational automation, external notification routing, and recurring pipeline orchestration.
- **Interactions**:
  - Backend dispatches signed HTTP POST webhooks to n8n upon security events (e.g., `SCAN_COMPLETED`, `CRITICAL_FINDING_DETECTED`, `REMEDIATION_APPROVED`).
  - n8n triggers outbound notifications (Slack alerts, Discord webhooks, PagerDuty incidents, Jira ticket generation).
  - Webhooks validate cryptographic HMAC signatures (`X-ShadowOps-Signature`) generated by the backend.

---

## 3. Communication Protocols & Data Flow

| Interaction | Protocol | Payload Type | Security Controls |
|---|---|---|---|
| **Frontend $\leftrightarrow$ Backend** | HTTPS (TLS 1.3) / SSE | JSON / EventStream | Firebase JWT Bearer Token, CORS restriction, Rate limiting |
| **Backend $\leftrightarrow$ Firebase** | HTTPS | TLS Cert / Admin SDK | Service account private key stored in backend secrets |
| **Backend $\leftrightarrow$ Supabase DB** | PostgreSQL Protocol (TCP) | Prepared SQL / Pooler | Supavisor connection pooling (port 6543/5432), SSL mode `require`, RLS |
| **Backend $\leftrightarrow$ Supabase Storage** | HTTPS | REST / Signed S3 APIs | Service role secret key, signed expiring URLs for client access |
| **Backend $\leftrightarrow$ Semgrep** | Local Subprocess / IPC | CLI args / JSON pipes | Chrooted sandboxing, temp directory mounts, process timeouts |
| **Backend $\leftrightarrow$ Gemini / Grok** | HTTPS | JSON REST / Streaming | Model API keys in server environment, strict prompt schemas |
| **Backend $\leftrightarrow$ n8n** | HTTPS Webhooks | Signed JSON | HMAC-SHA256 signature verification, retry backoff |

---

## 4. Scalability & System Boundaries

1. **Stateless Backend**: The FastAPI backend contains no local in-memory session state, allowing horizontal scaling across Railway replicas.
2. **Scan Queueing**: Scan tasks and intensive AI workflows are queued and decoupled from web request threads, preventing HTTP request timeouts.
3. **Database Connection Pooling**: Utilizes Supabase Supavisor transaction pooler to efficiently handle concurrent connections without PostgreSQL connection exhaustion.
4. **Isolated Scanner Worker**: Scanner workloads run in isolated execution environments with zero write access to production database credentials, enforcing least-privilege security.
