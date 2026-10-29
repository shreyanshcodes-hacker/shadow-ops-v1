# ShadowOps Development Guide

Welcome to the ShadowOps development environment. This guide documents how to set up, run, and test ShadowOps locally across both the Next.js frontend and FastAPI backend.

---

## 1. Prerequisites

- **Python**: 3.11+ (Python 3.15 tested)
- **Node.js**: v18+ (Node v24 tested)
- **npm**: v9+ (npm v12 tested)
- **Supabase Account**: PostgreSQL instance & Storage buckets
- **Firebase Project**: Firebase Auth enabled

---

## 2. Environment Configuration

Copy `.env.example` to `.env` in the project root:
```bash
cp .env.example .env
```

Ensure the following variables are configured:
```bash
# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_SERVICE_ROLE_KEY=[YOUR-SERVICE-ROLE-KEY]
SUPABASE_ANON_KEY=[YOUR-ANON-KEY]

# Firebase Auth
FIREBASE_PROJECT_ID=[YOUR-FIREBASE-PROJECT-ID]
FIREBASE_CLIENT_EMAIL=[YOUR-FIREBASE-SERVICE-ACCOUNT-EMAIL]
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."

# AI Providers
GEMINI_API_KEY=[YOUR-GEMINI-KEY]
GROK_API_KEY=[YOUR-GROK-KEY]

# Application URLs & Secret
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=development
SECRET_KEY=generate-a-secure-random-key-for-development
```

---

## 3. Backend Setup & Local Server

1. **Activate Python Virtual Environment**:
   ```bash
   # Windows PowerShell
   backend\venv\Scripts\Activate.ps1
   # macOS/Linux
   source backend/venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Run Database Migrations (Supabase)**:
   Apply `supabase/migrations/001_initial_schema.sql` and `supabase/storage.sql` to your Supabase project SQL Editor.

4. **Start FastAPI Development Server**:
   ```bash
   python -m uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
   Interactive API documentation will be available at: `http://localhost:8000/docs`.

---

## 4. Frontend Setup & Local Server

1. **Install Frontend Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start Next.js Development Server**:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` to view the Dark Cybersecurity Command Center.

---

## 5. Running Automated Tests

Run backend tests using pytest:
```bash
$env:PYTHONPATH="backend"
backend\venv\Scripts\pytest.exe backend/tests -v
```

Run frontend type check & build verification:
```bash
cd frontend
npm run typecheck
npm run build
```
