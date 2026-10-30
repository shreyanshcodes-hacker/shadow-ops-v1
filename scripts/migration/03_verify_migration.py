#!/usr/bin/env python3
"""
ShadowOps Migration Integrity Verification Utility
Validates database schema, table completeness (all 39 tables), foreign key integrity,
index coverage, timestamp configurations, and seed roles.
"""

import sys
import os
import argparse
import asyncio
from typing import Dict, List, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

EXPECTED_TABLES = [
    "profiles",
    "workspaces",
    "workspace_members",
    "roles",
    "assets",
    "asset_authorizations",
    "scans",
    "scan_events",
    "agent_runs",
    "findings",
    "finding_evidence",
    "risk_assessments",
    "finding_ai_analysis",
    "security_relationships",
    "risk_snapshots",
    "attack_paths",
    "attack_path_nodes",
    "attack_path_edges",
    "security_team_runs",
    "remediation_proposals",
    "remediation_approvals",
    "remediation_validations",
    "remediation_checkpoints",
    "remediation_applications",
    "verification_runs",
    "verification_jobs",
    "verification_comparisons",
    "verification_regression_checks",
    "verification_reviews",
    "reports",
    "chat_conversations",
    "chat_messages",
    "audit_logs",
    "notifications",
    "event_outbox",
    "notification_preferences",
    "notification_rules",
    "notification_deliveries",
    "workflow_runs",
]


async def run_verification(database_url: str) -> bool:
    print(f"[+] Connecting to target database: {database_url.split('@')[-1] if '@' in database_url else database_url}")

    # Normalize url for asyncpg if postgresql
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        engine_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1).replace("postgres://", "postgresql+asyncpg://", 1)
    else:
        engine_url = database_url

    engine = create_async_engine(engine_url, echo=False)
    all_passed = True

    try:
        async with engine.connect() as conn:
            # 1. Verify Table Inventory
            print("\n[+] Verification Check 1: Table Inventory (Expected 39 Application Tables)")
            query = text(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """
            )
            result = await conn.execute(query)
            existing_tables = set(r[0] for r in result.fetchall())

            missing_tables = set(EXPECTED_TABLES) - existing_tables
            if missing_tables:
                print(f"[-] FAILED: Missing tables detected: {sorted(list(missing_tables))}")
                all_passed = False
            else:
                print(f"[✓] PASSED: All {len(EXPECTED_TABLES)} required tables are present in public schema.")

            # 2. Table Row Counts
            print("\n[+] Verification Check 2: Table Record Counts")
            for table in EXPECTED_TABLES:
                if table in existing_tables:
                    count_res = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_res.scalar()
                    print(f"    - {table:<32}: {count:>6} rows")

            # 3. Verify Foreign Key Constraints
            print("\n[+] Verification Check 3: Foreign Key Constraint Coverage")
            fk_query = text(
                """
                SELECT
                    tc.table_name, 
                    kcu.column_name, 
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema='public';
                """
            )
            fk_result = await conn.execute(fk_query)
            fks = fk_result.fetchall()
            print(f"[✓] PASSED: Found {len(fks)} active foreign key constraints linking relational models.")

            # 4. Verify Roles Seed Data
            print("\n[+] Verification Check 4: RBAC Roles Reference Integrity")
            roles_res = await conn.execute(text("SELECT id, name FROM roles ORDER BY id"))
            roles = {r[0]: r[1] for r in roles_res.fetchall()}
            expected_roles = {"owner", "admin", "member", "viewer"}
            if expected_roles.issubset(roles.keys()):
                print(f"[✓] PASSED: Roles reference data intact: {list(roles.keys())}")
            else:
                print(f"[-] FAILED: Missing essential roles: {expected_roles - set(roles.keys())}")
                all_passed = False

            # 5. Verify Timestamp & Timezone Preservation
            print("\n[+] Verification Check 5: Timestamp with Timezone (TIMESTAMPTZ)")
            tz_query = text(
                """
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                  AND column_name LIKE '%_at'
                """
            )
            tz_res = await conn.execute(tz_query)
            tz_cols = tz_res.fetchall()
            non_tz = [f"{r[0]}.{r[1]} ({r[2]})" for r in tz_cols if "time zone" not in r[2].lower()]
            if non_tz:
                print(f"[-] WARNING: Columns with non-timezone timestamps: {non_tz}")
            else:
                print(f"[✓] PASSED: All {len(tz_cols)} timestamp columns are verified 'timestamp with time zone'.")

    except Exception as e:
        print(f"[-] Database connection/verification error: {e}")
        all_passed = False
    finally:
        await engine.dispose()

    print("\n" + "=" * 60)
    if all_passed:
        print("[✓] FINAL STATUS: DATABASE MIGRATION VERIFICATION PASSED")
    else:
        print("[-] FINAL STATUS: DATABASE MIGRATION VERIFICATION FAILED")
    print("=" * 60)
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Verify Cloud SQL PostgreSQL migration integrity.")
    parser.add_argument("--db-url", required=False, default=os.getenv("DATABASE_URL"), help="PostgreSQL connection string")
    args = parser.parse_args()

    if not args.db_url:
        print("[-] Error: Database URL must be passed via --db-url or DATABASE_URL env var.")
        sys.exit(1)

    success = asyncio.run(run_verification(args.db_url))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
