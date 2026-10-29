# RAILWAY DEPLOYMENT ARCHITECTURE — SHADOWOPS

## 1. Unified Railway Topology Overview

ShadowOps is deployed as a multi-service production topology hosted entirely on **Railway**. All compute workloads (Next.js frontend, FastAPI backend, scan workers, Redis queue, and n8n automation) run as isolated services within a unified Railway project connected via **Railway Private Networking**.

Supabase serves as the external managed PostgreSQL database and object storage provider, and Firebase provides external identity authentication.

```
                      [ INTERNET / USERS ]
                                │
               ┌────────────────┴────────────────┐
               │ HTTPS (TLS 1.3)                 │ HTTPS (TLS 1.3)
               ▼                                 ▼
    ┌─────────────────────┐           ┌─────────────────────┐
    │  RAILWAY SERVICE:   │           │  RAILWAY SERVICE:   │
    │  shadowops-frontend │           │  shadowops-backend  │
    │  (Next.js 14 App)   │           │  (FastAPI API Core) │
    │  Port: 3000         │           │  Port: 8000         │
    └──────────┬──────────┘           └──────────┬──────────┘
               │                                 │
               │ Railway Private Network         │ Railway Private Network
               │ (internal DNS: backend:8000)    │ (internal DNS: redis:6379)
               ▼                                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              RAILWAY PRIVATE NETWORKING MESH                │
    └──────────┬───────────────────────────────┬──────────────────┘
               │                               │
               ▼                               ▼
    ┌─────────────────────┐         ┌─────────────────────┐
    │  RAILWAY SERVICE:   │         │  RAILWAY SERVICE:   │
    │  shadowops-worker   │         │  shadowops-redis    │
    │  (Scanner & Semgrep)│         │  (Queue & Pub/Sub)  │
    │  Ephemeral Sandbox  │         │  Port: 6379         │
    └──────────┬──────────┘         └─────────────────────┘
               │
               ▼
    ┌─────────────────────┐
    │  RAILWAY SERVICE:   │
    │  shadowops-n8n      │
    │  (Automation Engine)│
    │  Port: 5678         │
    └─────────────────────┘
               │
    ═══════════╪═══════════════════════════════════════════════════ (External Managed Cloud)
               │
               ├──────────────────────────────┐
               ▼                              ▼
    ┌─────────────────────┐        ┌─────────────────────┐
    │  SUPABASE CLOUD     │        │  FIREBASE AUTH      │
    │  - PostgreSQL 16+   │        │  - JWT Verification │
    │  - Supabase Storage │        │  - OAuth Providers  │
    └─────────────────────┘        └─────────────────────┘
```

---

## 2. Service Specifications & Configuration

---

### Service 1: `shadowops-frontend`
- **Application**: Next.js 14 (App Router, React Server Components).
- **Deployment Strategy**: Dockerfile build (Standalone Next.js output) for optimized image size and fast spin-up.
- **Port**: `3000`
- **Build Command**: `npm run build`
- **Start Command**: `node server.js`
- **Health Check Endpoint**: `/api/health`
- **Environment Variables**:
  - `NODE_ENV`: `production`
  - `PORT`: `3000`
  - `NEXT_PUBLIC_API_URL`: `https://api.shadowops.io` (or Railway public domain)
  - `NEXT_PUBLIC_FIREBASE_API_KEY`: `${{FIREBASE_API_KEY}}`
  - `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`: `${{FIREBASE_AUTH_DOMAIN}}`
  - `NEXT_PUBLIC_FIREBASE_PROJECT_ID`: `${{FIREBASE_PROJECT_ID}}`
  - `NEXT_PUBLIC_SUPABASE_URL`: `${{SUPABASE_URL}}`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: `${{SUPABASE_ANON_KEY}}`

---

### Service 2: `shadowops-backend`
- **Application**: Python 3.11+ / FastAPI Core API server.
- **Deployment Strategy**: Multi-stage Dockerfile containing Python virtual environment and dependencies.
- **Port**: `8000`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`
- **Health Check Endpoint**: `/health` (Returns JSON `{"status": "healthy", "database": "connected"}`)
- **Environment Variables**:
  - `DATABASE_URL`: `postgresql://postgres.[ref]:[pwd]@aws-0-[region].pooler.supabase.com:6543/postgres?pgbouncer=true` (Supabase Supavisor pooler)
  - `DIRECT_URL`: `postgresql://postgres.[ref]:[pwd]@aws-0-[region].pooler.supabase.com:5432/postgres` (Direct connection for migrations)
  - `SUPABASE_URL`: `${{SUPABASE_URL}}`
  - `SUPABASE_SERVICE_ROLE_KEY`: `${{SUPABASE_SERVICE_ROLE_KEY}}`
  - `FIREBASE_PROJECT_ID`: `${{FIREBASE_PROJECT_ID}}`
  - `FIREBASE_ADMIN_CREDENTIALS_JSON`: `${{FIREBASE_ADMIN_CREDENTIALS_JSON}}`
  - `GEMINI_API_KEY`: `${{GEMINI_API_KEY}}`
  - `GROK_API_KEY`: `${{GROK_API_KEY}}`
  - `REDIS_URL`: `redis://shadowops-redis.railway.internal:6379`
  - `CORS_ORIGINS`: `https://app.shadowops.io,https://shadowops-frontend.railway.app`
  - `N8N_WEBHOOK_URL`: `http://shadowops-n8n.railway.internal:5678/webhook`
  - `N8N_HMAC_SECRET`: `${{N8N_HMAC_SECRET}}`

---

### Service 3: `shadowops-worker` (Scanner Engine)
- **Application**: Background Scan & Semgrep Execution Worker.
- **Deployment Strategy**: Dockerfile based on `python:3.11-slim` with Semgrep CLI (`pip install semgrep`), git, and ca-certificates pre-installed.
- **Start Command**: `python -m app.workers.scan_worker`
- **Environment Variables**:
  - `DATABASE_URL`: `${{DATABASE_URL}}`
  - `REDIS_URL`: `redis://shadowops-redis.railway.internal:6379`
  - `SUPABASE_URL`: `${{SUPABASE_URL}}`
  - `SUPABASE_SERVICE_ROLE_KEY`: `${{SUPABASE_SERVICE_ROLE_KEY}}`
  - `GEMINI_API_KEY`: `${{GEMINI_API_KEY}}`
  - `GROK_API_KEY`: `${{GROK_API_KEY}}`
  - `TMPDIR`: `/tmp/shadowops-scans`
- **Isolation Boundaries**: Runs with unprivileged user `scanner`, ephemeral `/tmp` filesystem wiped per scan.

---

### Service 4: `shadowops-redis`
- **Application**: Redis 7.2 Alpine image from Railway Marketplace.
- **Port**: `6379`
- **Networking**: Strictly internal. Exposed solely on `shadowops-redis.railway.internal:6379` to backend and worker services. Zero public internet exposure.

---

### Service 5: `shadowops-n8n`
- **Application**: n8n Official Docker Image (`n8nio/n8n:latest`).
- **Port**: `5678`
- **Start Command**: Native container entrypoint.
- **Health Check Endpoint**: `/healthz`
- **Environment Variables**:
  - `N8N_PORT`: `5678`
  - `N8N_PROTOCOL`: `https`
  - `WEBHOOK_URL`: `https://n8n.shadowops.io/`
  - `N8N_ENCRYPTION_KEY`: `${{N8N_ENCRYPTION_KEY}}`

---

## 3. Networking, CORS & Internal Routing

1. **Railway Private Network**: Services communicate directly over internal IPv6/IPv4 private DNS hostnames (`*.railway.internal`). Backend-to-Redis and Backend-to-Worker traffic remains entirely within Railway's private mesh, avoiding internet transit latency and egress fees.
2. **CORS Restrictions**: The FastAPI backend implements `CORSMiddleware` permitting requests exclusively from verified frontend domains:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=settings.CORS_ORIGINS.split(","),
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
       allow_headers=["Authorization", "Content-Type", "X-Workspace-Id"],
   )
   ```
3. **Database Pooling**: Supabase PostgreSQL connections run through the Supavisor connection pooler on port `6543` in transaction mode, preventing pool exhaustion across auto-scaling backend replicas.

---

## 4. Secrets Management & Zero-Browser Policy

- **No Secrets in Bundles**: Only variables prefixed with `NEXT_PUBLIC_` are bundled into the client browser. These are strictly limited to public identifiers (Firebase Project ID, Supabase Anon Key).
- **Railway Secret Variables**: All critical credentials (Firebase Admin Key, Supabase Service Role Key, Gemini/Grok API keys, Database connection URLs) are managed via Railway Project Secrets, injected at container launch, and never written to source repositories.
- **Log Masking**: Backend logging middleware intercepts structured log payloads to redact authorization tokens, passwords, and API keys matching high-entropy regex patterns.
