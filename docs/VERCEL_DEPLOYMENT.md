# ShadowOps — Vercel Production Deployment Guide

**Document Version:** 2.0  
**Deployment Target:** Vercel (Frontend Edge) + Dedicated Container / PaaS (FastAPI & Semgrep Backend)  
**Status:** Certified & Production Ready  

---

## 1. Production Topology & Architecture

ShadowOps utilizes an optimized decoupled architecture:
1. **Frontend Edge (Vercel):** Hosts the Next.js 14 App Router application with global CDN caching, zero cold-start static generation, and edge routing.
2. **Backend API & Scanner (Dedicated Container):** Hosts the Python FastAPI backend, Semgrep SAST scanner, AI agent orchestrator, and background workers in an isolated, persistent execution environment.
3. **Database Plane (Supabase):** Managed multi-tenant PostgreSQL database with Row-Level Security (RLS).
4. **Identity Plane (Google Firebase):** User authentication and JWT issuance.

```mermaid
flowchart TD
    User["End User / Browser"] -->|HTTPS / Edge CDN| Vercel["Vercel Frontend Edge\n(Next.js 14 App Router)"]
    Vercel -->|Bearer Auth / API Calls| Backend["FastAPI Backend Service\n(Container / Dedicated Host)"]
    
    subgraph ComputeBoundary ["Persistent Container Host"]
        Backend --> SemgrepWorker["Semgrep SAST Scanner\nIsolated /scan-workspace"]
        Backend --> AIEngine["AI Security Orchestrator\n(Gemini 3.1 Flash Lite)"]
        Backend --> PatchApplier["Patch Applier & Rollback\n(SHA-256 Checkpoints)"]
    end
    
    subgraph DataPlane ["Persistence & Identity"]
        Backend --> SupabaseDB[("Supabase PostgreSQL\nMulti-Tenant Schema")]
        Backend --> FirebaseAuth["Firebase Admin SDK\nToken Verification"]
    end
```

---

## 2. Why the Backend Cannot Run on Vercel Serverless

The Python FastAPI backend and Semgrep scanner **cannot** be deployed as standard Vercel Serverless Functions due to strict architectural and security constraints:

| Requirement | Vercel Serverless Limit | ShadowOps Production Requirement | Why It Cannot Run on Vercel |
| :--- | :--- | :--- | :--- |
| **Execution Duration** | 15s (Hobby) / 60s (Pro) | Up to 30 mins (`SCAN_TIMEOUT_SECONDS=1800`) | Serverless functions will time out and fail mid-scan. |
| **Semgrep SAST Engine** | Ephemeral, no native binaries | Requires native `semgrep` CLI + Python AST engine | Vercel runtime does not bundle security scanners or custom toolchains. |
| **Filesystem Persistence** | Read-only except `/tmp` (ephemeral) | Requires persistent `/scan-workspace` | Code cloning, AST caching, and atomic patch rollback require stateful disk access. |
| **Process Isolation** | Single-function sandbox | Multi-process worker and task queue | Subprocess spawning and CPU-intensive scanning require isolated containers. |
| **Worker Concurrency** | Stateless invocation | Background event loops & task control | Active scan cancellation and job tracking require long-lived listeners. |

> [!IMPORTANT]  
> The Next.js frontend deploys to **Vercel**. The FastAPI backend and Semgrep scanner deploy to a persistent container environment (such as Docker, Railway, GCP Cloud Run, AWS ECS, or a dedicated VPS) as detailed in Section 5.

---

## 3. Configuring the Vercel Frontend Deployment

### Option A: Deploy via Vercel Web Dashboard (Recommended)

1. **Import Repository:**
   - Log into [Vercel](https://vercel.com/) and click **"Add New Project"** > **"Project"**.
   - Select your `shadow-ops-v2` Git repository.

2. **Configure Project Settings:**
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Click **Edit** and set to `frontend`
   - **Build Command:** `npm run build` (or leave default `next build`)
   - **Output Directory:** `.next` (default)
   - **Install Command:** `npm install` (default)

3. **Configure Environment Variables:**
   Under **Environment Variables**, add the following keys:

   | Key | Value Description | Example |
   | :--- | :--- | :--- |
   | `NEXT_PUBLIC_API_URL` | Deployed Backend API URL | `https://api.yourcompany.com/api/v1` |
   | `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase Web API Key | `AIzaSyBEZHLrLGRMxkFL48yD7LOWxUaCg4dyRcY` |
   | `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase Auth Domain | `shadow-ops-6957d.firebaseapp.com` |
   | `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase Project ID | `shadow-ops-6957d` |
   | `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Firebase Storage Bucket | `shadow-ops-6957d.firebasestorage.app` |
   | `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Firebase Sender ID | `96713617472` |
   | `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase Web App ID | `1:96713617472:web:9d4db960807aa3e3cbafa5` |

4. **Deploy:**
   - Click **Deploy**. Vercel will build and publish your Next.js application to an edge URL (e.g., `https://shadow-ops.vercel.app`).

---

### Option B: Deploy via Vercel CLI

1. Install the Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. From the repository root, deploy:
   ```bash
   vercel
   ```
   Follow the CLI prompts:
   - **Link to existing project?** No (or select your team)
   - **What's your project's name?** `shadowops`
   - **In which directory is your code located?** `./frontend`

3. Deploy to production:
   ```bash
   vercel --prod
   ```

---

## 4. Frontend Security & Vercel Configuration Files

The repository includes pre-configured Vercel deployment descriptors:

### 4.1 Root `vercel.json`
Ensures that deployment triggered from the monorepo root correctly builds the `frontend` workspace:
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs",
  "buildCommand": "npm --prefix frontend run build",
  "outputDirectory": "frontend/.next",
  "installCommand": "npm --prefix frontend install"
}
```

### 4.2 Frontend `frontend/vercel.json`
Injects essential HTTP security headers into all responses:
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs",
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

> [!CAUTION]  
> **Zero-Leakage Policy:** Backend service keys (`SUPABASE_SERVICE_ROLE_KEY`, `FIREBASE_PRIVATE_KEY`, `GEMINI_API_KEY`, database credentials) must **NEVER** be entered into Vercel environment variables or prefixed with `NEXT_PUBLIC_`.

---

## 5. Backend Hosting & Deployment Guide

To support the Vercel frontend, deploy the Python FastAPI backend to any container host using the provided Docker toolchain.

### 5.1 Backend Environment Configuration
Configure these environment variables on your backend container host:

```bash
# Core Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
SECRET_KEY=generate-with-openssl-rand-hex-32

# CORS Configuration (Must include your Vercel deployment domain)
CORS_ORIGINS=https://your-shadowops-app.vercel.app,https://yourcustomdomain.com

# Database (Supabase PostgreSQL Connection Pooler)
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres

# Firebase Admin SDK (Server-side Authentication)
FIREBASE_PROJECT_ID=shadow-ops-6957d
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-fbsvc@shadow-ops-6957d.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# AI Provider Configuration
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.1-flash-lite
AI_TIMEOUT_SECONDS=25
AI_MAX_RETRIES=1

# Scanner Configuration
SCAN_WORKSPACE_ROOT=/scan-workspace
SEMGREP_BINARY=semgrep
SCAN_TIMEOUT_SECONDS=1800
```

### 5.2 Launch Command (Docker / Container)
```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers
```

### 5.3 Health Check & Probe Endpoints
Configure your container health checks to poll:
- **Liveness Probe:** `GET /api/v1/health/live`
- **Readiness Probe:** `GET /api/v1/health/ready`

---

## 6. End-to-End Verification Protocol

After deploying the Vercel frontend and connecting it to your backend API:

1. **Verify Public Access:**
   - Navigate to `https://your-app.vercel.app/`. Ensure the landing page loads with all assets and branding intact.
   - Navigate to `https://your-app.vercel.app/about` to verify developer credentials and branding.
2. **Verify Authentication & Routing:**
   - Log in using Google Sign-in or email credentials on `https://your-app.vercel.app/login`.
   - Verify that existing users are routed to `/dashboard`, and new users are routed to `/onboarding`.
3. **Verify Security Command Center:**
   - Verify that posture score and open vulnerabilities load on `/dashboard`.
4. **Verify AI Security Chat:**
   - Open `/chat` and send a message. Verify that ShadowOps Sentinel answers in under 4 seconds with rich Markdown formatting (bold, italic, code blocks).

---

## 7. Rollback Reference (Railway / Containerized)

If you need to roll back or maintain an all-container deployment topology, refer to [`docs/RAILWAY_DEPLOYMENT.md`](file:///d:/Shreyanshcodes/shadow-ops-v2/docs/RAILWAY_DEPLOYMENT.md). The Docker configurations (`Dockerfile`, `Dockerfile.scanner`, `docker-compose.yml`) remain fully intact and backward-compatible.
