# ShadowOps v2.0 — Vercel Frontend Deployment Guide

**Deployment Target:** Vercel (Next.js 14 App Router)  
**Document Classification:** Production Deployment Runbook  
**Last Audited:** October 30, 2026  
**Status:** Certified & Ready for Vercel Import  

---

## 1. Executive Architecture Summary

ShadowOps v2.0 utilizes a decoupled multi-cloud architecture:

```
┌─────────────────────────────────┐
│        Vercel Edge/Server       │
│   Next.js 14 Frontend (App Dir) │
└────────────────┬────────────────┘
                 │ HTTPS (NEXT_PUBLIC_API_URL)
                 ▼
┌─────────────────────────────────┐       ┌────────────────────────────────┐
│      Google Cloud Run / Host    │       │     Firebase Authentication    │
│    FastAPI Security Backend     │◄──────┤   (Client JWT Verification)    │
└───────┬─────────────────┬───────┘       └────────────────────────────────┘
        │                 │
        ▼                 ▼
┌────────────────┐  ┌────────────────┐
│  Supabase DB   │  │Supabase Storage│
│ PostgreSQL 16  │  │(Signed URLs S3)│
└────────────────┘  └────────────────┘
```

- **Frontend Hosting:** Vercel (Next.js 14.2.35, App Router, React 18).
- **Backend Compute:** Google Cloud Run / Container Host (Python 3.11+, FastAPI, Semgrep CLI, Gemini 3.1 Flash Lite).
- **Database:** Supabase PostgreSQL 16 (Permanent relational data source of truth).
- **File Storage:** Supabase Storage (Private S3-compatible buckets with HMAC signed URLs).
- **Identity & Auth:** Firebase Authentication (`shadow-ops-6957d`).

---

## 2. Pre-Import Verification Checklist

| Checkpoint | Requirement | Status |
| :--- | :--- | :--- |
| **Frontend Directory** | Dedicated subdirectory: `frontend/` | Verified |
| **Framework Detection** | Next.js 14 App Router | Verified |
| **TypeScript Validation** | `npm --prefix frontend run typecheck` | Passed (0 errors) |
| **Production Build** | `npm --prefix frontend run build` | Passed (24/24 routes compiled) |
| **Backend Isolation** | Zero Semgrep, SAST, or Celery code in frontend | Verified |
| **Secret Leak Audit** | Zero private keys or database passwords in bundle | Verified |
| **CORS Alignment** | Backend accepts Vercel production & preview origins | Verified |
| **Firebase Auth Domain** | Vercel domain registered in Firebase Console | Documented below |

---

## 3. Step-by-Step Vercel Import Procedure

### Step 3.1: Log in to Vercel and Import Repository
1. Navigate to [vercel.com](https://vercel.com) and log in.
2. From the Vercel Dashboard, click **Add New...** > **Project**.
3. Select your Git provider (GitHub / GitLab / Bitbucket) and import the **`shadow-ops-v2`** repository.

---

### Step 3.2: Configure Monorepo Project Settings

> [!IMPORTANT]
> The Next.js application is located in the `frontend` subfolder of the repository. You **must** set the Root Directory to `frontend`.

In the **Configure Project** screen:

1. **Project Name:** `shadow-ops` (or your preferred name).
2. **Framework Preset:** **Next.js** (automatically detected).
3. **Root Directory:** Click **Edit** and select or type:
   ```
   frontend
   ```
4. **Build and Output Settings:**
   - **Build Command:** Leave default (`next build`) or override with `npm run build`.
   - **Output Directory:** Leave default (`.next`).
   - **Install Command:** Leave default (`npm install`).

---

### Step 3.3: Configure Production & Preview Environment Variables

In the **Environment Variables** section of the Vercel project configuration, add the following client variables. Select all target environments: **Production**, **Preview**, and **Development**.

| Variable Name | Example / Production Value | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://api.yourdomain.com/api/v1` | **FastAPI Backend Endpoint.** Must point to your deployed Cloud Run or backend service URL (always append `/api/v1`). |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | `AIzaSyBEZHLrLGRMxkFL48yD7LOWxUaCg4dyRcY` | Public Firebase Web SDK API key. |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | `shadow-ops-6957d.firebaseapp.com` | Firebase Authentication domain. |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | `shadow-ops-6957d` | Firebase Project identifier. |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`| `shadow-ops-6957d.firebasestorage.app` | Firebase Storage bucket URI. |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | `96713617472` | Firebase Cloud Messaging Sender ID. |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | `1:96713617472:web:9d4db960807aa3e3cbafa5` | Firebase Web App client ID. |

> [!CAUTION]
> **Zero Server Secrets Policy:**
> NEVER add `DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `FIREBASE_ADMIN_CREDENTIALS`, or `SECRET_KEY` to the Vercel project. Those secrets belong exclusively to the FastAPI backend service (e.g. Google Secret Manager / Cloud Run).

---

### Step 3.4: Deploy
Click **Deploy**. Vercel will:
1. Clone the repository into an isolated build container.
2. Navigate to `frontend/`.
3. Execute `npm install`.
4. Run `npm run build`.
5. Deploy static assets to the Vercel Global Edge Network and server components to Edge/Serverless functions.

---

## 4. Post-Deployment Configuration

### 4.1: Register Vercel Origin in Firebase Authentication
To permit users to sign in via Google OAuth, email verification, or popup dialogs on your deployed frontend:

1. Open the [Firebase Console](https://console.firebase.google.com/).
2. Select project **`shadow-ops-6957d`**.
3. In the left navigation, click **Build** > **Authentication**.
4. Go to the **Settings** tab > **Authorized domains**.
5. Click **Add domain** and enter your Vercel deployment domain:
   - Production domain: `shadow-ops.vercel.app` (or your custom domain `app.shadowops.io`).
   - If using preview deployments: `*.vercel.app` or specific preview domains.

---

### 4.2: Update Backend CORS Configuration
Your deployed FastAPI backend must permit cross-origin requests from your Vercel frontend domain:

In your backend deployment configuration (e.g., Google Cloud Run environment variables):
```bash
# Production environment
ENVIRONMENT=production
FRONTEND_URL=https://shadow-ops.vercel.app

# Multiple allowed origins (if using staging or preview branches)
CORS_ORIGINS=https://shadow-ops.vercel.app,https://shadowops.io,http://localhost:3000
```

The backend CORS middleware automatically permits the configured `FRONTEND_URL` and `CORS_ORIGINS` with credentials and standard security headers.

---

## 5. Security & Header Specifications

The repository includes a production-grade `frontend/vercel.json` enforcing defensive HTTP response headers across all routes:

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

---

## 6. Verification and Smoke Testing Checklist

After your Vercel deployment completes:

1. **Route Smoke Test:**
   - [ ] Navigate to `https://<your-project>.vercel.app/login` — verify login form renders.
   - [ ] Navigate to `https://<your-project>.vercel.app/about` — verify static page loads.
   - [ ] Test Firebase Authentication sign-in — verify token exchange with `/me`.
2. **Dashboard & Telemetry:**
   - [ ] Navigate to `/dashboard` — confirm workspace stats load via `NEXT_PUBLIC_API_URL`.
   - [ ] Open AI Security Chat at `/chat` — verify Sentinel assistant stream and markdown font formatting (bold, italic, underline).
3. **Security Invariant Verification:**
   - [ ] Navigate to `/assets` — ensure assets are isolated to active workspace.
   - [ ] Verify that unauthorized assets cannot trigger scans (`NO AUTHORIZATION -> NO SCAN`).

---

## 7. Troubleshooting & FAQ

### Issue: `Cross-Origin Request Blocked (CORS)`
- **Symptom:** Browser console shows `Access-Control-Allow-Origin` error when calling `/api/v1/*`.
- **Resolution:** Verify that `FRONTEND_URL` on your FastAPI backend exactly matches your Vercel domain (including `https://` with no trailing slash).

### Issue: `auth/unauthorized-domain` in Firebase Auth
- **Symptom:** Google sign-in or popup auth fails immediately.
- **Resolution:** Add your Vercel domain (e.g. `your-app.vercel.app`) to Firebase Console > Authentication > Settings > Authorized Domains.

### Issue: Build Fails with Peer Dependency Warnings
- **Resolution:** The repository includes a `.npmrc` file with `legacy-peer-deps=true` inside `frontend/` to ensure smooth reproducible installs.
