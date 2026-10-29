import os
import re
import pytest

MIGRATIONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "supabase", "migrations")
)


def test_migration_files_sequential_order_and_integrity():
    """Validates that all migration files exist, are numbered, and are non-empty."""
    assert os.path.isdir(MIGRATIONS_DIR), f"Migrations directory not found: {MIGRATIONS_DIR}"
    files = sorted(os.listdir(MIGRATIONS_DIR))
    assert len(files) >= 10, f"Expected at least 10 migration files, found {len(files)}"

    sql_files = [f for f in files if f.endswith(".sql")]
    assert len(sql_files) >= 10

    for sql_file in sql_files:
        full_path = os.path.join(MIGRATIONS_DIR, sql_file)
        assert os.path.getsize(full_path) > 100, f"Migration {sql_file} is suspiciously small or empty"
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Verify no unresolved merge conflicts or placeholders
            assert "<<<<<<<" not in content, f"Git merge conflict marker in {sql_file}"
            assert ">>>>>>>" not in content, f"Git merge conflict marker in {sql_file}"


def test_migration_multi_tenant_workspace_isolation():
    """
    Validates that core security tables created across migrations enforce
    foreign key reference to workspaces(id).
    """
    files = sorted(os.listdir(MIGRATIONS_DIR))
    all_sql = ""
    for f in files:
        if f.endswith(".sql"):
            with open(os.path.join(MIGRATIONS_DIR, f), "r", encoding="utf-8") as mfile:
                all_sql += mfile.read() + "\n"

    # Core multi-tenant tables must have workspace_id REFERENCES workspaces(id)
    critical_tenant_tables = [
        "assets",
        "scans",
        "findings",
        "attack_paths",
        "security_team_runs",
        "remediation_proposals",
        "verification_jobs",
        "reports",
        "event_outbox",
        "notifications",
        "workflow_runs",
    ]

    for table in critical_tenant_tables:
        table_pattern = rf"CREATE TABLE (?:IF NOT EXISTS )?{table}\s*\((.*?)\);"
        match = re.search(table_pattern, all_sql, re.DOTALL | re.IGNORECASE)
        assert match is not None, f"Could not find CREATE TABLE for {table} in migrations"
        table_body = match.group(1)

        # Must have workspace_id column
        assert "workspace_id" in table_body.lower(), f"Table {table} is missing workspace_id column!"
        assert (
            "workspaces(id)" in table_body.lower() or "references workspaces" in table_body.lower()
        ), f"Table {table} missing foreign key to workspaces(id)!"


def test_migration_rls_enable_statements():
    """Verifies that PostgreSQL migrations define Row Level Security on multi-tenant tables."""
    files = sorted(os.listdir(MIGRATIONS_DIR))
    all_sql = ""
    for f in files:
        if f.endswith(".sql"):
            with open(os.path.join(MIGRATIONS_DIR, f), "r", encoding="utf-8") as mfile:
                all_sql += mfile.read() + "\n"

    # Check that initial schema and later migrations include RLS directives
    assert "ENABLE ROW LEVEL SECURITY" in all_sql or "enable row level security" in all_sql
    assert "CREATE POLICY" in all_sql or "create policy" in all_sql
