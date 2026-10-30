# ShadowOps — Phase 13 Staging Verification Report

**Document Version:** 1.0  
**Date:** October 30, 2026  
**Target Environment:** Staging  
**GCP Project ID:** `shadow-ops-6957d` (Project Number: `96713617472`)  
**Region:** `us-central1`  
**Status:** Preflight Audited — Awaiting Explicit Provisioning Authorization  

---

## 1. Environment & Preflight Audit Results

| Audit Check | Target / Status | Finding |
| :--- | :--- | :--- |
| **GCP Project** | `shadow-ops-6957d` | Verified via Firebase CLI project inventory. |
| **Google Cloud CLI** | `gcloud` command line | **Not installed in local system PATH.** Scripts prepared for Google Cloud Shell / Cloud SDK. |
| **Firebase CLI** | Version `15.34.1` | **Installed and authenticated** with direct project permissions. |
| **Database Schema** | 39 application tables | Verified reproducible via [`scripts/migration/02_cloud_sql_schema.sql`](file:///d:/Shreyanshcodes/shadow-ops-v2/scripts/migration/02_cloud_sql_schema.sql). |
| **Automated Tests** | 106 backend tests | **106 passed, 0 failed** in `backend/tests` (including tenant isolation). |
| **Frontend Health** | Next.js 14 App Router | Typecheck passing, zero production bundle errors. |
| **Billable Cloud Resources** | None provisioned | Preserved in adherence to Non-Negotiable Safety Rule 10. |

---

## 2. Planned Staging Cloud Resources

| Resource Type | Resource Name | Sizing & Specifications | Estimated Cost |
| :--- | :--- | :--- | :--- |
| **Cloud SQL PostgreSQL 16** | `shadowops-staging-pg` | `db-custom-1-3840` (1 vCPU, 3.75 GB RAM), 20 GB SSD, Zonal (`us-central1-a`), PITR enabled | ~$55.00 / month (~$0.08 / hr) |
| **Serverless VPC Access** | `staging-vpc-conn` | 2 `e2-micro` instances, IP range `10.8.0.0/28` | ~$7.50 / month |
| **Cloud Run API Service** | `shadowops-staging-api` | Python 3.11 container, Min: 0, Max: 3 | ~$0.00 – $3.00 / month |
| **Cloud Storage Bucket** | `shadow-ops-6957d-staging-artifacts` | Standard Multi-Regional/Regional Bucket | <$0.50 / month |
| **Secret Manager Secrets** | `shadowops-staging-*` | 2 secrets (DB password, backend secret key) | <$0.20 / month |
| **Firebase Data Connect** | `shadowops-staging-connector` | Service linked to `shadowops-staging-pg` | Free tier quota |

---

## 3. Provisioning Runbook (Prepared for Execution)

### Step 1: Enable Google Cloud APIs
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

### Step 2: Establish Private Service Access & Serverless VPC Connector
```bash
# 1. Allocate VPC Peering range for Cloud SQL
gcloud compute addresses create google-managed-services-staging \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --description="Private Service Access for Staging Cloud SQL" \
  --network=default \
  --project=shadow-ops-6957d

# 2. Connect VPC peering
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-staging \
  --network=default \
  --project=shadow-ops-6957d

# 3. Create Serverless VPC Access connector for Cloud Run
gcloud compute networks vpc-access connectors create staging-vpc-conn \
  --region=us-central1 \
  --network=default \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=3 \
  --project=shadow-ops-6957d
```

### Step 3: Provision Staging Cloud SQL Instance
```bash
gcloud sql instances create shadowops-staging-pg \
  --project=shadow-ops-6957d \
  --database-version=POSTGRES_16 \
  --tier=db-custom-1-3840 \
  --region=us-central1 \
  --zone=us-central1-a \
  --availability-type=ZONAL \
  --storage-type=SSD \
  --storage-size=20GB \
  --storage-auto-increase \
  --backup \
  --backup-start-time=04:00 \
  --enable-point-in-time-recovery \
  --retained-backups-count=7 \
  --deletion-protection \
  --network=projects/shadow-ops-6957d/global/networks/default \
  --no-assign-ip \
  --database-flags=max_connections=100,statement_timeout=30000
```

### Step 4: Create Staging Database & Users
```bash
# Create database
gcloud sql databases create shadowops \
  --instance=shadowops-staging-pg \
  --project=shadow-ops-6957d

# Create users
gcloud sql users create shadowops_migrator \
  --instance=shadowops-staging-pg \
  --project=shadow-ops-6957d \
  --password="[STAGING_MIGRATOR_STRONG_PASSWORD]"

gcloud sql users create shadowops_app \
  --instance=shadowops-staging-pg \
  --project=shadow-ops-6957d \
  --password="[STAGING_APP_STRONG_PASSWORD]"
```

### Step 5: Store Staging Secrets in Secret Manager
```bash
echo -n "[STAGING_APP_STRONG_PASSWORD]" | \
  gcloud secrets create shadowops-staging-db-password \
    --data-file=- \
    --replication-policy="automatic" \
    --project=shadow-ops-6957d

echo -n "shadowops-staging-session-secret-key-32chars" | \
  gcloud secrets create shadowops-staging-secret-key \
    --data-file=- \
    --replication-policy="automatic" \
    --project=shadow-ops-6957d
```

### Step 6: Deploy Canonical Staging Schema & Seed
```bash
# Apply sanitized 39-table schema to staging instance via Cloud SQL Auth Proxy or bastion
psql "postgresql://shadowops_migrator:[STAGING_MIGRATOR_STRONG_PASSWORD]@127.0.0.1:5432/shadowops" \
  -f ./scripts/migration/02_cloud_sql_schema.sql

# Execute verification script
python3 ./scripts/migration/03_verify_migration.py \
  --db-url "postgresql://shadowops_app:[STAGING_APP_STRONG_PASSWORD]@127.0.0.1:5432/shadowops"
```

### Step 7: Deploy Staging Cloud Run Service
```bash
gcloud run deploy shadowops-staging-api \
  --image="gcr.io/shadow-ops-6957d/backend:staging" \
  --region=us-central1 \
  --service-account="shadowops-staging-sa@shadow-ops-6957d.iam.gserviceaccount.com" \
  --add-cloudsql-instances="shadow-ops-6957d:us-central1:shadowops-staging-pg" \
  --vpc-connector="staging-vpc-conn" \
  --set-env-vars="USE_CLOUD_SQL_CONNECTOR=True,CLOUD_SQL_CONNECTION_NAME=shadow-ops-6957d:us-central1:shadowops-staging-pg,CLOUD_SQL_DATABASE=shadowops,CLOUD_SQL_USER=shadowops_app,ENVIRONMENT=staging" \
  --set-secrets="CLOUD_SQL_PASSWORD=shadowops-staging-db-password:latest,SECRET_KEY=shadowops-staging-secret-key:latest" \
  --min-instances=0 \
  --max-instances=3 \
  --project=shadow-ops-6957d
```

### Step 8: Deploy Staging Firebase Data Connect
```bash
firebase deploy --only dataconnect --project=shadow-ops-6957d
```

---

## 4. Rollback and Teardown Safeguards

- **Supabase Integrity:** Supabase PostgreSQL remains completely operational and isolated. Zero traffic redirected.
- **Immediate Staging Destruction:** If required, the entire staging environment can be wiped without affecting any user traffic:
  ```bash
  gcloud sql instances delete shadowops-staging-pg --project=shadow-ops-6957d
  gcloud run services delete shadowops-staging-api --region=us-central1 --project=shadow-ops-6957d
  gcloud compute networks vpc-access connectors delete staging-vpc-conn --region=us-central1 --project=shadow-ops-6957d
  ```

---

## 5. Formal Phase 13 Verdict

```
=====================================================
  VERDICT: PREFLIGHT COMPLETE — APPROVAL REQUIRED
=====================================================
```
*Preflight auditing, migration sequencing, cost estimation, and provisioning runbooks are complete. In strict adherence to Non-Negotiable Safety Rule 10, billable Google Cloud infrastructure provisioning has not been initiated without explicit developer authorization.*
