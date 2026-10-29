# ShadowOps Railway Deployment Blueprint

This document details the configuration for deploying ShadowOps to Railway as separate services.

---

## 1. Services Topology on Railway

```
┌─────────────────────────┐
│     Next.js Frontend    │ (Railway Web Service)
│   Node.js 18+ runtime   │
└────────────┬────────────┘
             │
             │ HTTPS / Bearer Auth
             ▼
┌─────────────────────────┐
│     FastAPI Backend     │ (Railway Web Service)
│    Python 3.11+ / Uvicorn│
└────────────┬────────────┘
             │
             ├──► Supabase PostgreSQL (Managed DB)
             ├──► Supabase Storage (Managed Buckets)
             ├──► Firebase Auth (Google Cloud)
             └──► Gemini & Grok APIs (AI Providers)
```

---

## 2. Backend Railway Configuration

- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/api/v1/health`

---

## 3. Frontend Railway Configuration

- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Start Command**: `npm run start`
- **Environment Variables**:
  - `NEXT_PUBLIC_API_URL`: `https://${{backend.RAILWAY_PUBLIC_DOMAIN}}/api/v1`

---

## 4. Production Hardening Checklist

- [ ] Set `ENVIRONMENT=production` in backend Railway variables.
- [ ] Configure custom domain with Railway TLS termination.
- [ ] Verify `FRONTEND_URL` matches the production custom domain.
- [ ] Ensure Supabase database connection pooling (Port 6543 / PgBouncer mode) is enabled for high concurrency.
