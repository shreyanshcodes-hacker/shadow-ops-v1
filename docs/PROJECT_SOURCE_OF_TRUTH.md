# PROJECT SOURCE OF TRUTH — SHADOWOPS

## 1. Document Overview & Purpose

This document establishes the canonical source of truth for **ShadowOps** ("Your AI Security Team. Always Watching.") for Stage 0 and all subsequent implementation stages. It catalogs all project materials inspected across the workspace and adjacent development environments, defines an explicit authority hierarchy, and details every architectural conflict and its authoritative resolution.

---

## 2. Source Documents & Assets Inspected

An exhaustive inspection was conducted across the active workspace (`d:\Shreyanshcodes\shadow-ops-v2`) and the adjacent historical repositories (`d:\Shreyanshcodes\shadow-ops` and `d:\Shreyanshcodes\shadow-ops-git`):

| Category | Artifact / Location | Status | Assessment & Historical Context |
|---|---|---|---|
| **Active Workspace** | `d:\Shreyanshcodes\shadow-ops-v2` | Fresh Clean Slate | Zero code, zero build artifacts, dedicated to Stage 0 architecture. |
| **Historical PRD / SRS** | `..\shadow-ops\docs\PRODUCT_ARCHITECTURE.md` | Inspected | Defined the 21-step loop, core promise, target personas, and security boundaries. |
| **System Architecture** | `..\shadow-ops\docs\SYSTEM_ARCHITECTURE.md` | Inspected | Defined FastAPI, Supabase, Celery/Redis, Semgrep, and n8n topology. |
| **Database Architecture** | `..\shadow-ops\docs\DATABASE_ARCHITECTURE.md` | Inspected | Defined schema for 23 tables, RLS policies, indexes, and lifecycle. |
| **AI Architecture** | `..\shadow-ops\docs\AI_ARCHITECTURE.md`, `AI_SECURITY_TEAM.md` | Inspected | Outlined AI Security Manager, Gemini/Grok routing, prompt validation, and cost caps. |
| **Security Architecture** | `..\shadow-ops\docs\SECURITY_ARCHITECTURE.md`, `SCANNER_SECURITY.md` | Inspected | Established 14 non-negotiable principles, backend-enforced auth, and RLS. |
| **Scan Architecture** | `..\shadow-ops\docs\SCAN_ARCHITECTURE.md` | Inspected | Documented scan DAG, Semgrep pipeline, and state transitions. |
| **Remediation & Verification** | `..\shadow-ops\docs\REMEDIATION_ARCHITECTURE.md`, `VERIFICATION_ARCHITECTURE.md` | Inspected | Documented human approval gates and empirical verification engines. |
| **Railway Deployment** | `..\shadow-ops\docs\RAILWAY_DEPLOYMENT_ARCHITECTURE.md`, `railway.json` | Inspected | Mapped multi-service topology (Next.js, FastAPI, Celery, Redis, n8n) on Railway. |
| **Legacy Codebase** | `..\shadow-ops\backend`, `..\shadow-ops\frontend`, `..\shadow-ops\supabase` | Inspected | Contains partial prototypes and migrations (001–009) to be analyzed for lessons learned. |
| **Configuration Files** | `..\shadow-ops\docker-compose.yml`, `vercel.json`, `railway.json` | Inspected | Highlighted configuration divergence between Vercel and Railway. |

---

## 3. Source of Truth Hierarchy

To ensure deterministic decision-making without ambiguity or unrecorded assumptions, the following source-of-truth hierarchy is strictly enforced:

```
┌─────────────────────────────────────────────────────────────────┐
│ LEVEL 1: STAGE 0 USER PROMPT SPECIFICATION                      │
│ (Absolute Supreme Authority - Unchangeable Constraints)         │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ LEVEL 2: STAGE 0 ARCHITECTURAL SPECIFICATIONS                   │
│ (docs/* Created in Stage 0 - Authoritative Blueprints)          │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ LEVEL 3: HISTORICAL REPOSITORY ASSETS (shadow-ops v1)           │
│ (Reference Material Only - Non-binding, Subject to Level 1 & 2) │
└─────────────────────────────────────────────────────────────────┘
```

1. **Level 1: Stage 0 User Prompt Specification**
   - The primary instruction set provided for Stage 0. Defines mandatory stack, strict non-negotiable rules (e.g., `NO AUTHORIZATION → NO SCAN`, Railway deployment, Supabase DB/storage, Firebase auth, Gemini/Grok AI, Semgrep SAST/SCA).
2. **Level 2: Stage 0 Architectural Specifications (`docs/*`)**
   - The 15 comprehensive architectural blueprints generated in this stage. Once verified and accepted, all implementation across Stages 1–24 must adhere strictly to these designs.
3. **Level 3: Historical Repository Assets (`..\shadow-ops`)**
   - Used purely as advisory historical reference. Any pattern or code snippet in the legacy directory that conflicts with Level 1 or Level 2 is deprecated and superseded.

---

## 4. Conflict Identification & Authoritative Resolutions

During inspection of the legacy workspace (`..\shadow-ops`), several discrepancies with the Stage 0 specification were detected. These conflicts are explicitly identified and resolved below:

### Conflict 1: Deployment Platform Divergence (Vercel vs. Railway)
- **Legacy Artifact**: `..\shadow-ops\vercel.json` exists, indicating a previous attempt to host the Next.js frontend on Vercel while running the backend elsewhere.
- **Stage 0 Mandate**: *"The final deployment target is Railway. Design deployment architecture around Railway from the beginning... Do not assume Vercel or Render. Railway is the deployment target."*
- **Authoritative Resolution**: `vercel.json` is completely rejected. The frontend, backend, worker containers, Redis broker, and n8n automation will all be deployed exclusively within a unified Railway project using Railway Private Networking and Railway Dockerfile/Nixpacks builders.

### Conflict 2: Scan Pipeline Execution & Worker Broker
- **Legacy Artifact**: Legacy implementation used Celery with Redis for asynchronous background tasks.
- **Stage 0 Mandate**: Python backend orchestrating structured workflows, scan pipelines, and AI agents.
- **Authoritative Resolution**: In Railway deployment, scan jobs and AI agent workloads require isolated execution to prevent resource starvation or scanner breakout. The backend will enqueue scan tasks using a lightweight, resilient task worker backed by Redis on Railway, with Semgrep running in an isolated container/sandbox.

### Conflict 3: Database & Storage Boundaries
- **Legacy Artifact**: Legacy codebase used local Supabase migrations alongside direct PostgreSQL connections.
- **Stage 0 Mandate**: Supabase PostgreSQL and Supabase Storage remain the dedicated managed database and object storage platform.
- **Authoritative Resolution**: All relational data and RLS policies reside in Supabase PostgreSQL; all raw scan artifacts, Semgrep SARIF logs, evidence screenshots, and generated PDF reports are persisted in Supabase Storage buckets with signed URL access controls.

### Conflict 4: Authentication & Workspace Association
- **Legacy Artifact**: Discrepancies in how Firebase Auth UIDs were mapped to internal database profiles.
- **Stage 0 Mandate**: Firebase Authentication provides identity (JWT), but backend authorization and workspace membership verification are mandatory on every single request.
- **Authoritative Resolution**: A strict PostgreSQL table `profiles` maps `firebase_uid` to internal `user_id`. Every API request must pass through backend token verification and workspace permission checks. Frontend session state is explicitly untrusted.

---

## 5. Architectural Integrity Mandate

In strict accordance with the Stage 0 charter:
- No application code, UI scaffolding, or mock endpoints may be created in Stage 0.
- All technical and functional requirements must be completely specified in `docs/` prior to any code generation.
