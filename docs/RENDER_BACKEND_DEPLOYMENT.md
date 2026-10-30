# ShadowOps v2.0 — Render FastAPI Backend Deployment Runbook

**Service:** ShadowOps Security Core API  
**Hosting Target:** Render Web Service  
**Associated Frontend:** `https://shadow-ops-v1.vercel.app`  
**Database:** Supabase PostgreSQL 16 (Permanent relational source of truth)  
**Date:** October 30, 2026  
**Status:** Certified & Ready for Deployment  
**Verdict:** READY FOR RENDER DEPLOYMENT  

---

## 1. System Architecture & Topology

```
┌────────────────────────────────────────────────────────┐
│                   Vercel Edge CDN                      │
│        https://shadow-ops-v1.vercel.app                │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS (NEXT_PUBLIC_API_URL)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Render Web Service                   │
│          FastAPI Backend (app.main:app)                │
│         https://shadowops-api.onrender.com             │
├───────────────────────────┬────────────────────────────┤
│   Semgrep SAST Engine     │  Gemini 3.1 Flash Lite AI  │
└─────────────┬─────────────┴─────────────┬──────────────┘
              │                           │
              ▼                           ▼
┌───────────────────────────┐  ┌─────────────────────────┐
│  Supabase PostgreSQL 16   │  │    Supabase Storage     │
│   (39 Tables, RLS Active) │  │  (S3-Compatible Buckets)│
└───────────────────────────┘  └─────────────────────────┘
```

---

## 2. FastAPI Application Entry Point

- **Application Directory:** [`backend/`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend)
- **FastAPI Instance:** `app` defined in [`backend/app/main.py`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/main.py)
- **Exact Module Import Path:** `app.main:app`
- **Uvicorn Start Command:**
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
  ```

---

## 3. Recommended Deployment: Docker Runtime

The containerized approach is **strongly recommended** because it bundles the Semgrep SAST/SCA CLI, C-extension build tools (`build-essential`, `libpq-dev`), non-root execution (`appuser`), and signal forwarding for graceful shutdown.

### 3.1 Render Web Service Settings (Docker)
In the [Render Dashboard](https://dashboard.render.com/):

1. Click **New +** > **Web Service**.
2. Select your connected GitHub repository: **`shadow-ops-v2`**.
3. Configure the following service settings:
   - **Name:** `shadowops-backend` (or your preferred name)
   - **Region:** Frankfurt (EU Central) or Oregon (US West) — *choose the region closest to your Supabase database instance*
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** **Docker**
   - **Dockerfile Path:** `./Dockerfile`
   - **Docker Context:** `.` (relative to Root Directory `backend`)
   - **Instance Type:** Starter (0.5 CPU, 512 MB RAM) or Standard (1 CPU, 2 GB RAM recommended for Semgrep scans)

---

## 4. Alternative Deployment: Native Python Runtime

If you prefer Render's managed Python runtime:

- **Root Directory:** `backend`
- **Runtime:** `Python 3`
- **Python Version:** `3.11.9` (auto-detected via [`backend/.python-version`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/.python-version))
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

> [!NOTE]  
> [`backend/requirements.txt`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/requirements.txt) includes `semgrep>=1.65.0`, ensuring the CLI is installed in native Python environments.

---

## 5. Render Environment Variables Reference

Add the following environment variables in the Render Dashboard (**Environment** tab):

| Variable Name | Example / Production Value | Notes |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Enables production security controls |
| `DEBUG` | `false` | Prevents internal stack traces from leaking |
| `PORT` | `10000` | Render standard port |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:[PASS]@[HOST]:[PORT]/postgres` | Supabase PostgreSQL URI (supports `sslmode=require` / `ssl=require`) |
| `SUPABASE_URL` | `https://[PROJECT].supabase.co` | Supabase API endpoint |
| `SUPABASE_ANON_KEY` | `[SUPABASE_ANON_KEY]` | Public anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | `[SUPABASE_SERVICE_ROLE_KEY]` | Privileged server-side key |
| `FIREBASE_PROJECT_ID` | `shadow-ops-6957d` | Firebase Admin project ID |
| `FIREBASE_CLIENT_EMAIL` | `[SERVICE_ACCOUNT_EMAIL]` | Firebase service account email |
| `FIREBASE_PRIVATE_KEY` | `[SERVICE_ACCOUNT_PRIVATE_KEY]` | PEM string (with `\n` preserved) |
| `GEMINI_API_KEY` | `[GEMINI_API_KEY]` | Google AI Gemini API key |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Production model identifier |
| `SECRET_KEY` | `[GENERATE_RANDOM_32_HEX_STRING]` | Application session security key |
| `FRONTEND_URL` | `https://shadow-ops-v1.vercel.app` | Production frontend origin |
| `CORS_ORIGINS` | `https://shadow-ops-v1.vercel.app,http://localhost:3000` | Allowed cross-origin domains |

> [!CAUTION]
> **Database Safety Invariant:**  
> Never run destructive migrations (`DROP TABLE`, `TRUNCATE`, `ALTER TABLE ... DROP`) against the production Supabase database. The database is already live with all 39 tables, indexes, and RLS policies active.

---

## 6. Health & Readiness Observability Endpoints

The backend exposes lightweight, zero-credential health endpoints:

### 6.1 Liveness Probe (`GET /health`)
- **URL:** `https://<your-render-url>/health`
- **Render Setting:** Set **Health Check Path** to `/health`
- **Response (HTTP 200):**
  ```json
  {
    "status": "healthy",
    "service": "ShadowOps Security API",
    "environment": "production",
    "version": "1.0.0"
  }
  ```

### 6.2 Readiness Probe (`GET /ready`)
- **URL:** `https://<your-render-url>/ready`
- **Behavior:** Executes `SELECT 1` against Supabase and checks Semgrep CLI availability.
- **Security:** Leaks no connection strings, passwords, or hostnames.
- **Response (HTTP 200):**
  ```json
  {
    "status": "ready",
    "database": {
      "connected": true
    },
    "scanner": {
      "engine": "semgrep",
      "available": true
    },
    "environment": "production"
  }
  ```

---

## 7. Production CORS & Vercel Interconnection

The backend includes explicit CORS protection for the deployed frontend origin:
- **Allowed Origin:** `https://shadow-ops-v1.vercel.app`
- **Allowed Methods:** `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`
- **Allowed Headers:** `Authorization`, `Content-Type`, `X-Workspace-Id`, `X-Request-Id`
- **Credentials:** `true` (Wildcard `*` origins are strictly prohibited)

### Connect Vercel to Render:
Once Render gives you your service URL (e.g. `https://shadowops-api.onrender.com`):
1. Go to [Vercel Dashboard](https://vercel.com/) > Project `shadow-ops-v1` > **Settings** > **Environment Variables**.
2. Update `NEXT_PUBLIC_API_URL` to:
   ```
   https://shadowops-api.onrender.com/api/v1
   ```
3. Trigger a **Redeploy** on Vercel so the client bundles point to the live Render backend.

---

## 8. Verification & Pre-Flight Validation Results

All checks passed locally in test and production emulation modes:

```bash
# 1. FastAPI Startup & Endpoint Health
GET /       -> HTTP 200 {"service": "ShadowOps Security API", "status": "online"}
GET /health -> HTTP 200 {"status": "healthy"}
GET /ready  -> HTTP 200 {"status": "ready", "database": {"connected": true}}

# 2. Automated Test Suite Regression
pytest backend/tests
# Result: 106 passed in 19.86s (Exit code: 0)

# 3. Dockerfile Build Validation
- Base Image: python:3.11-slim
- Non-root user: appuser (UID 1000)
- Signal forwarding: exec uvicorn ...
- Dynamic PORT binding: --port ${PORT:-8000}
```

---

## Final Verdict

### **READY FOR RENDER DEPLOYMENT**
- **Import Path:** Verified as `app.main:app`.
- **Dockerfile:** Hardened with non-root user, Semgrep, and dynamic `$PORT` binding.
- **Database:** Fully configured for Supabase PostgreSQL with `asyncpg` and SSL normalization.
- **CORS:** Configured for `https://shadow-ops-v1.vercel.app`.
- **Health Checks:** `/health` and `/ready` verified.
