#!/usr/bin/env bash
# ==============================================================================
# SHADOWOPS — SUPABASE DATA EXPORT & CLOUD SQL IMPORT UTILITY
# ==============================================================================
set -euo pipefail

# Configuration
SOURCE_DB_URL="${SOURCE_SUPABASE_DB_URL:-}"
TARGET_DB_URL="${TARGET_CLOUDSQL_DB_URL:-}"
BACKUP_DIR="./backups/migration_$(date +%Y%m%d_%H%M%S)"

if [ -z "$SOURCE_DB_URL" ]; then
    echo "[-] ERROR: SOURCE_SUPABASE_DB_URL environment variable is required."
    exit 1
fi

mkdir -p "$BACKUP_DIR"
echo "[+] Created backup directory: $BACKUP_DIR"

# 1. Full schema & data pre-migration baseline backup
echo "[+] Step 1: Performing full source database backup (schema + data)..."
pg_dump "$SOURCE_DB_URL" \
    --format=custom \
    --no-owner \
    --no-privileges \
    --exclude-schema=auth \
    --exclude-schema=storage \
    --exclude-schema=realtime \
    --exclude-schema=graphql_public \
    --exclude-schema=vault \
    --file="$BACKUP_DIR/supabase_full_backup.dump"

echo "[+] Full backup completed: $BACKUP_DIR/supabase_full_backup.dump"
sha256sum "$BACKUP_DIR/supabase_full_backup.dump" > "$BACKUP_DIR/backup.sha256"

# 2. Extract Data Only (for inserting into sanitized Cloud SQL schema)
echo "[+] Step 2: Extracting data-only payload in dependency order..."
pg_dump "$SOURCE_DB_URL" \
    --data-only \
    --no-owner \
    --no-privileges \
    --exclude-schema=auth \
    --exclude-schema=storage \
    --exclude-schema=realtime \
    --exclude-schema=graphql_public \
    --exclude-schema=vault \
    --file="$BACKUP_DIR/supabase_data_only.sql"

echo "[+] Data export completed: $BACKUP_DIR/supabase_data_only.sql"

# 3. Optional direct import if TARGET_DB_URL is provided
if [ -n "$TARGET_DB_URL" ]; then
    echo "[+] Step 3: Applying canonical Cloud SQL schema to target..."
    psql "$TARGET_DB_URL" -f "./scripts/migration/02_cloud_sql_schema.sql"

    echo "[+] Step 4: Loading data payload into Cloud SQL with deferred constraints..."
    psql "$TARGET_DB_URL" -c "SET session_replication_role = 'replica';"
    psql "$TARGET_DB_URL" -f "$BACKUP_DIR/supabase_data_only.sql"
    psql "$TARGET_DB_URL" -c "SET session_replication_role = 'origin';"

    echo "[+] Step 5: Executing migration integrity verification..."
    python3 ./scripts/migration/03_verify_migration.py --db-url "$TARGET_DB_URL"
else
    echo "[!] Target database URL not provided. Data dump saved locally in $BACKUP_DIR."
    echo "[!] To import later, run: psql \$TARGET_DB_URL -f $BACKUP_DIR/supabase_data_only.sql"
fi

echo "[+] Database extraction completed successfully."
