# ShadowOps Environment & Configuration

All environment variables used by the backend and frontend are centrally declared and typed via Pydantic Settings in `backend/app/core/config.py`.

---

## 1. Required Variables

| Variable | Target | Description | Example |
|---|---|---|---|
| `DATABASE_URL` | Backend | PostgreSQL connection string with asyncpg driver | `postgresql+asyncpg://postgres:pass@db.ref.supabase.co:5432/postgres` |
| `SUPABASE_URL` | Backend | URL of the Supabase project | `https://xyz.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend | Privileged key for server-side operations | `eyJhbGciOi...` |
| `SUPABASE_ANON_KEY` | Backend/Frontend | Public anonymous key | `eyJhbGciOi...` |
| `FIREBASE_PROJECT_ID` | Backend | Google Firebase project ID | `shadowops-prod` |
| `FIREBASE_CLIENT_EMAIL` | Backend | Firebase admin service account email | `firebase-adminsdk@...` |
| `FIREBASE_PRIVATE_KEY` | Backend | Firebase admin private key | `"-----BEGIN PRIVATE KEY-----\n..."` |
| `GEMINI_API_KEY` | Backend | Google Gemini API Key | `AIzaSy...` |
| `GROK_API_KEY` | Backend | xAI Grok API Key | `xai-...` |
| `FRONTEND_URL` | Backend | Allowed CORS origin for the frontend | `http://localhost:3000` |
| `ENVIRONMENT` | Backend | Current environment (`development`, `staging`, `production`) | `development` |
| `SECRET_KEY` | Backend | Internal cryptographic signature key | `secure-random-token` |
| `NEXT_PUBLIC_API_URL` | Frontend | Base URL of the FastAPI backend | `http://localhost:8000/api/v1` |

---

## 2. Security Rules for Secrets

1. **Never commit `.env`**: `.gitignore` explicitly ignores `.env`, `.env.local`, `.env.*.local`, and service account JSON keys.
2. **Never expose server secrets to Next.js**: Only variables prefixed with `NEXT_PUBLIC_` are bundled into client-side JavaScript.
