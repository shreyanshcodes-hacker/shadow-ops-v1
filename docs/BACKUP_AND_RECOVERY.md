# ShadowOps Backup, Disaster Recovery & Data Retention Policy

**Document Version:** 1.0  
**Phase:** Stage 12 Production Hardening  
**Target Audience:** SRE, Database Administrators, Security Compliance  

---

## 1. Disaster Recovery Objectives

- **Recovery Point Objective (RPO):** Maximum acceptable data loss duration.
  - Production (GA): **RPO < 15 minutes** (via Continuous WAL archiving / Point-in-Time Recovery).
  - Controlled Pilot: **RPO < 24 hours** (via daily automated database dumps).
- **Recovery Time Objective (RTO):** Maximum acceptable duration to restore service availability.
  - Production (GA): **RTO < 1 hour**.
  - Controlled Pilot: **RTO < 4 hours**.

---

## 2. Backup Schedules & Topology

```mermaid
flowchart TD
    subgraph LiveDB ["Primary PostgreSQL (Supabase)"]
        LiveDB --> WAL["Continuous Write-Ahead Logs (WAL)"]
        LiveDB --> DailyDump["Daily Full Logical Dump (pg_dump)"]
    end
    
    WAL --> S3_Cold["Cold Storage (AWS S3 / GCS)\nEncrypted at Rest (AES-256)"]
    DailyDump --> S3_Cold
    
    subgraph LocalDev ["Pilot / Local Development"]
        SQLiteDB["shadowops.db"] --> SQLiteSnap["Nightly Atomic SQLite Backup"]
    end
```

### Backup Categories:

| Target | Mechanism | Frequency | Retention Period | Encryption |
| :--- | :--- | :---: | :---: | :---: |
| **PostgreSQL DB** | Supabase Point-in-Time Recovery (PITR) | Continuous (WAL) | 7 to 30 days | AES-256 |
| **PostgreSQL Logical Dumps** | `pg_dump -Fc` | Daily at 02:00 UTC | 90 days | Encrypted Bucket |
| **Evidence & Reports** | Supabase Private Storage Versioning | On write | 365 days | Server-Side Encrypted |
| **Local SQLite (Pilot/Dev)** | SQLite Online Backup API | Daily | 14 days | Local BitLocker / LUKS |

---

## 3. Database Restoration Runbooks

### 3.1 Point-in-Time Recovery (PITR) via Supabase
1. In the Supabase Dashboard, navigate to **Database** -> **Backups**.
2. Select **Point in Time**.
3. Choose the target restoration timestamp (prior to corruption or incident).
4. Click **Restore**.
5. Once complete, execute the health check probe:
   ```bash
   curl -I https://api.shadowops.io/api/v1/health/ready
   ```

### 3.2 Restoring from Daily Logical Dump (`pg_dump`)
```bash
# Set connection variables
export PGPASSWORD="[DATABASE_PASSWORD]"
DB_HOST="db.[PROJECT_REF].supabase.co"
DB_USER="postgres"
DB_NAME="postgres"

# Restore database schema and data cleanly
pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -c -v latest_backup.dump

# Validate schema integrity with automated migration test
python backend/tests/test_stage12_migrations_audit.py
```

### 3.3 Local SQLite Backup & Restore Procedure
```python
# To create an atomic online backup of SQLite:
import sqlite3

def backup_sqlite(source_path="shadowops.db", target_path="shadowops_backup.db"):
    src = sqlite3.connect(source_path)
    dst = sqlite3.connect(target_path)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
```

---

## 4. Code Remediation Checkpoint & Rollback System

In addition to database-level recovery, ShadowOps maintains code-level rollback capabilities for all applied security patches:

1. **Pre-Application Checkpoint:** Before applying any patch, `PatchApplicationAdapter` creates an immutable `RemediationCheckpoint` recording:
   - Base git commit SHA (`base_revision`).
   - Clean file snapshots of all files to be modified.
   - SHA256 hashes of original files.
2. **Rollback Execution:**
   - If an applied patch causes syntax failures or breaks tests, an authorized user triggers `/api/v1/remediations/{id}/rollback`.
   - The original file contents are atomically written back, and the `RemediationApplication` record is updated with `status = 'ROLLED_BACK'`.

---

## 5. Annual Disaster Recovery Drill Procedure

1. Schedule drill during a maintenance window with 72 hours notice.
2. Spin up an isolated clone environment in Railway.
3. Restore the latest `pg_dump` into an ephemeral PostgreSQL instance.
4. Run the full 100-test hermetic test suite against the restored database:
   ```bash
   pytest backend/tests/
   ```
5. Document restoration time, verify row counts across key tables (`findings`, `workspaces`, `assets`), and submit report to the compliance committee.
