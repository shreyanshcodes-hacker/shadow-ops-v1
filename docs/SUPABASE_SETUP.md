# ShadowOps — Supabase Setup Guide

ShadowOps utilizes **Supabase PostgreSQL** as its canonical persistent database and **Supabase Storage** for scan artifacts, evidence files, reports, and remediation diffs.

---

## 1. Supabase Project Setup

1. Create an account at [Supabase](https://supabase.com/).
2. Create a new organization and project (e.g. `shadowops-production`).
3. Set a strong database password and record it securely.
4. Select your primary region (e.g., `us-east-1` or `eu-central-1`).

---

## 2. Execute Database Migrations

1. In the Supabase project dashboard, navigate to the **SQL Editor**.
2. Open [`supabase/migrations/001_initial_schema.sql`](file:///d:/Shreyanshcodes/shadow-ops-v2/supabase/migrations/001_initial_schema.sql).
3. Paste and run the entire script.
   - This provisions all 23 tables, foreign keys, check constraints, indexes, triggers, and Row Level Security (RLS) policies.
4. Open [`supabase/storage.sql`](file:///d:/Shreyanshcodes/shadow-ops-v2/supabase/storage.sql).
5. Paste and run the storage provisioning script.
   - This creates 5 buckets: `scan-artifacts`, `evidence-files`, `security-reports`, `remediation-artifacts`, `verification-artifacts`.

---

## 3. Configure Connection Pooling

1. Under **Project Settings** → **Database**:
2. Find the **Connection string** section.
3. Switch the tab to **URI** with **Transaction pooler (port 6543 / Supavisor)**.
4. Copy the URL into your `.env` as `DATABASE_URL`:
   ```bash
   DATABASE_URL="postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true"
   ```

---

## 4. API Keys & Service Role Security

Under **Project Settings** → **API**:
- `URL`: Copy into `SUPABASE_URL`.
- `anon public`: Copy into `SUPABASE_ANON_KEY`.
- `service_role secret`: Copy into `SUPABASE_SERVICE_ROLE_KEY`.

> [!CAUTION]
> The `service_role` key bypasses all Row Level Security policies. It is used strictly on the FastAPI backend and must **never** be exposed in the frontend or public repositories.
