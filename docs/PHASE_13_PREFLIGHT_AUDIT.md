# ShadowOps — Phase 13 Preflight Audit Report

**Document Version:** 1.0  
**Date:** October 30, 2026  
**Project:** ShadowOps v2.0  
**GCP Project ID:** `shadow-ops-6957d` (Project Number: `96713617472`)  
**Auditor:** Senior Google Cloud Architect & Application Security Engineer  
**Status:** Preflight Audit Complete — Awaiting Provisioning Approval  

---

## 1. Executive Summary

This preflight audit inspects the readiness of project `shadow-ops-6957d` to provision a dedicated, isolated **Staging Environment** on Google Cloud Platform without disrupting the existing Supabase production database or redirecting production traffic.

All pre-migration schemas, FastAPI connection handlers, and Firebase Data Connect artifacts were audited. In accordance with **Non-Negotiable Safety Rule 10**, no billable infrastructure has been created.

---

## 2. CLI Tooling & Authentication Status

| Tool | Status | Authentication / Target | Details |
| :--- | :--- | :--- | :--- |
| **Firebase CLI** | **AVAILABLE (v15.34.1)** | Authenticated | Active Google account with direct access to project `shadow-ops-6957d`. |
| **Google Cloud CLI (`gcloud`)** | **NOT INSTALLED LOCALLY** | Pending Installation / Cloud Shell | `gcloud` is not in the local PATH. Commands must be run in Google Cloud Shell or after installing the Google Cloud SDK. |
| **Python Test Runner** | **AVAILABLE (v3.15.0)** | Local Virtual Environment | All 106 automated tests passing in `backend/venv`. |
| **Node.js / npm** | **AVAILABLE** | Local | Next.js 14 frontend typecheck and build verified. |

---

## 3. Migration Sequence & Authoritative Schema Audit

### 3.1 Migration File Sequence Analysis
The repository migration directory (`supabase/migrations/`) contains **11 canonical SQL files**:

1. `0001_initial_schema.sql` (Stage 1 Foundation & Stage 2 Asset Inventory — 23 core tables)
2. `0003_stage3_scanning.sql` (Stage 3 Scanner Events & Telemetry)
3. `0004_stage4_ai.sql` (Stage 4 AI Finding Analysis)
4. `0005_stage5_ai_analyst.sql` (Stage 5 AI Security Telemetry)
5. `0006_stage6_attack_paths.sql` (Stage 6 Relationships & Risk Snapshots)
6. `0007_stage7_ai_security_team.sql` (Stage 7 Multi-Agent Orchestrator)
7. `0008_stage8_remediation.sql` (Stage 8 Validations, Checkpoints & Applications)
8. `0009_stage9_verification.sql` (Stage 9 Empirical Verification Engine)
9. `0010_stage10_reports.sql` (Stage 10 Compliance Reporting)
10. `0011_stage11_notifications.sql` (Stage 11 Transactional Outbox & Webhooks)
11. `0012_storage.sql` (Stage 12 Storage Specification & Policies)

> [!NOTE]  
> **Migration Gap Explanation:** `0002` is intentionally not present in the sequence because Stage 1 (Foundation) and Stage 2 (Asset Inventory) were consolidated into `0001_initial_schema.sql` prior to Stage 3 deployment.

### 3.2 Canonical Target Schema
All 39 tables, foreign-key relationships, unique constraints, check constraints, indexes, triggers, and seed roles (`owner`, `admin`, `member`, `viewer`) are synthesized in:
[`scripts/migration/02_cloud_sql_schema.sql`](file:///d:/Shreyanshcodes/shadow-ops-v2/scripts/migration/02_cloud_sql_schema.sql)

All Supabase-proprietary schemas (`auth`, `storage`, `realtime`) and `auth.uid()` functions have been sanitized for 100% native PostgreSQL 16 compatibility on Google Cloud SQL.

---

## 4. Required Google Cloud APIs

Before provisioning staging, the following APIs must be enabled on project `shadow-ops-6957d`:

```bash
gcloud services enable \
  sqladmin.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  firebasedataconnect.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  vpcaccess.googleapis.com \
  iam.googleapis.com \
  --project=shadow-ops-6957d
```

---

## 5. Billing & Region Verification

1. **Target Region:** `us-central1` (Iowa)
   - Chosen consistently across Cloud SQL, Cloud Run, Secret Manager, Serverless VPC Access, and Firebase Data Connect for lowest network latency and maximum regional feature availability.
2. **Billing Requirement:**
   - Cloud SQL, Cloud Run, and Serverless VPC Access connectors require an active Google Cloud Billing Account linked to project `shadow-ops-6957d`.
   - Because `gcloud` is not locally installed, billing status cannot be checked programmatically. **User confirmation of billing linkage is mandatory before running provisioning commands.**

---

## 6. Preflight Readiness Checklist

- [x] Canonical 39-table schema sanitized and verified ([`02_cloud_sql_schema.sql`](file:///d:/Shreyanshcodes/shadow-ops-v2/scripts/migration/02_cloud_sql_schema.sql))
- [x] Migration integrity verification utility ready ([`03_verify_migration.py`](file:///d:/Shreyanshcodes/shadow-ops-v2/scripts/migration/03_verify_migration.py))
- [x] Dual-mode FastAPI database session implemented ([`backend/app/db/session.py`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/db/session.py))
- [x] 106 automated backend tests passing locally
- [x] Firebase CLI active and authenticated on project `shadow-ops-6957d`
- [ ] Google Cloud SDK installed locally OR Cloud Shell authorized
- [ ] Billing account confirmed active on `shadow-ops-6957d`
- [ ] Staging provisioning approval granted
