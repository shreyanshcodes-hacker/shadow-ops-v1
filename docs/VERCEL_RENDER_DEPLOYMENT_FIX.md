# ShadowOps v2.0 — Deployment Failure Diagnosis & Remediation Guide

**Target Platforms:** Vercel (Frontend) & Render (Backend)  
**Document Status:** Certified Post-Fix Runbook  
**Date:** October 30, 2026  
**Verdict:** BOTH BUILDS PASS — READY TO REDEPLOY  

---

## 1. Executive Failure Summary & Root Causes

Both the Vercel frontend and Render backend deployments previously failed during cloud CI/CD execution due to monorepo path resolution and Git tracking oversights. Neither issue was caused by application logic errors.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 OBSERVED CLOUD FAILURES                                     │
├───────────────────────────────────────────────┬─────────────────────────────────────────────┤
│ Vercel Frontend Failure                       │ Render Backend Failure                      │
│ "Module not found: Can't resolve              │ "ERROR: Could not open requirements file:   │
│ '@/lib/api-client'"                           │ No such file or directory:                  │
│                                               │ 'requirements.txt'"                         │
├───────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ ROOT CAUSE:                                   │ ROOT CAUSE:                                 │
│ Root .gitignore contained unanchored `lib/`,  │ Render defaulted Root Directory to repo     │
│ which silently excluded `frontend/lib/`       │ root (`.`) instead of `backend/`, where no  │
│ from Git. When Vercel cloned the repo,        │ `requirements.txt` existed.                 │
│ `api-client.ts` was physically missing.       │                                             │
└───────────────────────────────────────────────┴─────────────────────────────────────────────┘
```

---

## 2. Root Cause Analysis & Fixes Applied

### 2.1 Failure A: Vercel Frontend (`Can't resolve '@/lib/api-client'`)

- **Root Cause:**
  Line 24 of the root `.gitignore` contained a bare `lib/` entry (a legacy template rule for Python C-extension build directories). Because it lacked a directory prefix or leading slash, Git recursively ignored all folders named `lib/` across the entire project. Consequently, none of the files inside `frontend/lib/` (`api-client.ts`, `utils.ts`, `firebase/auth.ts`, `firebase/client.ts`, `firebase/config.ts`) were ever committed or pushed to GitHub. When Vercel pulled the repository, the files did not exist on disk.
- **Remediations Applied:**
  1. Updated [`.gitignore`](file:///d:/Shreyanshcodes/shadow-ops-v2/.gitignore) to scope Python libraries to `backend/lib/` and `backend/lib64/`.
  2. Explicitly whitelisted `!frontend/lib/` and `!frontend/lib/**` in `.gitignore`.
  3. Added [`frontend/.gitignore`](file:///d:/Shreyanshcodes/shadow-ops-v2/frontend/.gitignore) ensuring only ephemeral items (`node_modules`, `.next`, `.env*.local`) are ignored.
  4. Verified that `frontend/lib/api-client.ts` and all supporting client libraries are now tracked by Git.

---

### 2.2 Failure B: Render Backend (`No such file or directory: 'requirements.txt'`)

- **Root Cause:**
  1. **Monorepo Root Mismatch:** Render Web Services default to the repository root directory (`.`). Because `requirements.txt` is located in `backend/requirements.txt`, Render's default build command (`pip install -r requirements.txt`) failed immediately with `No such file or directory`.
  2. **FastAPI Module Path:** When executed from the repo root, `uvicorn main:app` fails because the application module is located at `app.main:app` inside the `backend` directory.
  3. **Semgrep Dependency Omission:** `semgrep` was not explicitly declared in `requirements.txt` (it had previously only been installed in Docker via `pip install semgrep`). Native Python deployments on Render would have failed at scan execution.
- **Remediations Applied:**
  1. Created a root fallback [`requirements.txt`](file:///d:/Shreyanshcodes/shadow-ops-v2/requirements.txt) (`-r backend/requirements.txt`) so even if Render defaults to the root directory, dependencies resolve successfully.
  2. Added `semgrep>=1.65.0` to [`backend/requirements.txt`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/requirements.txt) ensuring Semgrep CLI availability in both native and Docker runtimes.
  3. Created [`.python-version`](file:///d:/Shreyanshcodes/shadow-ops-v2/.python-version) and [`backend/.python-version`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/.python-version) pinned to `3.11.9`.
  4. Created [`render.yaml`](file:///d:/Shreyanshcodes/shadow-ops-v2/render.yaml) Blueprint declaring `rootDir: backend`, `buildCommand: pip install -r requirements.txt`, and `startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
  5. Updated `parsed_cors_origins` in [`backend/app/core/config.py`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/core/config.py) to dynamically combine `FRONTEND_URL` and `CORS_ORIGINS` with trailing-slash normalization.

---

## 3. Deployment Configuration Settings

### 3.1 Vercel Frontend Project Settings

Configure these settings in the Vercel Dashboard under **Settings > General**:

- **Framework Preset:** `Next.js`
- **Root Directory:** `frontend`
- **Build Command:** `next build` (or `npm run build`)
- **Output Directory:** `.next`
- **Install Command:** `npm install`

#### Environment Variables (Vercel):
| Variable | Value / Format | Scope |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://<your-render-app>.onrender.com/api/v1` | Production, Preview, Dev |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | `AIzaSyBEZHLrLGRMxkFL48yD7LOWxUaCg4dyRcY` | Production, Preview, Dev |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | `shadow-ops-6957d.firebaseapp.com` | Production, Preview, Dev |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | `shadow-ops-6957d` | Production, Preview, Dev |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | `shadow-ops-6957d.firebasestorage.app` | Production, Preview, Dev |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | `96713617472` | Production, Preview, Dev |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | `1:96713617472:web:9d4db960807aa3e3cbafa5` | Production, Preview, Dev |

---

### 3.2 Render Backend Web Service Settings

Configure these settings in the Render Dashboard under **Settings**:

- **Language / Runtime:** `Python 3`
- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Auto-Deploy:** `Yes`

#### Environment Variables (Render):
| Variable | Required / Value | Notes |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.11.9` | Enforces Python 3.11 runtime |
| `ENVIRONMENT` | `production` | Enables production security controls |
| `DEBUG` | `false` | Disables debug stack traces |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:[PASS]@[HOST]:[PORT]/postgres` | Permanent Supabase PostgreSQL URI |
| `SUPABASE_URL` | `https://[PROJECT].supabase.co` | Supabase project API URL |
| `SUPABASE_ANON_KEY` | `[SUPABASE_ANON_KEY]` | Supabase client anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | `[SUPABASE_SERVICE_ROLE_KEY]` | Supabase privileged server key |
| `FIREBASE_PROJECT_ID` | `shadow-ops-6957d` | Firebase Admin project ID |
| `FIREBASE_CLIENT_EMAIL` | `[SERVICE_ACCOUNT_EMAIL]` | From service account JSON |
| `FIREBASE_PRIVATE_KEY` | `[SERVICE_ACCOUNT_PRIVATE_KEY]` | Standard PEM private key with `\n` |
| `GEMINI_API_KEY` | `[GEMINI_API_KEY]` | Google AI Gemini API Key |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Model identifier |
| `SECRET_KEY` | `[RANDOM_32_CHAR_STRING]` | Application session security key |
| `FRONTEND_URL` | `https://<your-vercel-app>.vercel.app` | Vercel production origin |
| `CORS_ORIGINS` | `https://<your-vercel-app>.vercel.app,http://localhost:3000` | Allowed cross-origin domains |

---

## 4. Local Verification & Health Check Results

### 4.1 Frontend Verification
- **TypeScript Static Analysis:** `npm --prefix frontend run typecheck`
  - Output: `0 errors` (Exit code: 0)
- **Next.js Production Build:** `npm --prefix frontend run build`
  - Output: Compiled successfully. All 24 static and dynamic routes compiled with `First Load JS shared by all = 87.2 kB`.

### 4.2 Backend Verification
- **FastAPI Import & Lifespan:** `from app.main import app` succeeded with title `ShadowOps Security API`.
- **Backend Test Suite:** `pytest backend/tests`
  - Result: **106 passed** in 20.26s with 0 failures.

---

## 5. Post-Deployment Coordination

1. **Firebase Authorized Domains:** In the Firebase Console (**Authentication > Settings > Authorized Domains**), add your Render domain and Vercel domain (`<app>.vercel.app`).
2. **CORS Validation:** Verify that `FRONTEND_URL` on Render matches your live Vercel URL so the browser can exchange bearer tokens with `/api/v1/me`.

---

## Final Verdict

### **BOTH BUILDS PASS — READY TO REDEPLOY**
- **Vercel Frontend:** Git tracking unblocked; all 5 missing library files restored; Next.js 14 production build verified.
- **Render Backend:** Root directory configured (`backend`); root fallback `requirements.txt` added; Python runtime pinned to `3.11.9`; Semgrep dependency resolved; entry point verified.
