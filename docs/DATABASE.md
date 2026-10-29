# ShadowOps Database Documentation

ShadowOps uses **Supabase PostgreSQL** as its canonical persistent database.

---

## 1. Schema Overview

The database migration is located at [`supabase/migrations/001_initial_schema.sql`](file:///d:/Shreyanshcodes/shadow-ops-v2/supabase/migrations/001_initial_schema.sql).

### Canonical Tables (23 Entities)

1. **`profiles`**: User profiles synchronized with Firebase Authentication.
2. **`workspaces`**: Tenancy boundary for all operations and assets.
3. **`workspace_members`**: RBAC association (`owner`, `admin`, `security_lead`, `engineer`, `viewer`).
4. **`roles`**: Formal RBAC definitions and privilege matrices.
5. **`assets`**: Target systems (`repository`, `api`, `infrastructure`, `application`, `container`).
6. **`asset_authorizations`**: Critical `NO AUTHORIZATION → NO SCAN` ownership and consent proofs.
7. **`scans`**: Scan execution runs with strict pre-conditions.
8. **`scan_events`**: Time-series log and state transitions for scans.
9. **`agent_runs`**: Execution lifecycle tracking for autonomous AI agents.
10. **`findings`**: Identified security findings with SHA-256 deduplication fingerprints.
11. **`finding_evidence`**: Evidence payloads, line numbers, and request/response records.
12. **`risk_assessments`**: Composite business risk, impact, and reachability evaluations.
13. **`attack_paths`**: Correlated multi-hop lateral movement chains.
14. **`attack_path_nodes`**: Step nodes in the attack graph.
15. **`attack_path_edges`**: Directional vulnerabilities connecting graph nodes.
16. **`remediation_proposals`**: AI-generated remediation patches and PR blueprints.
17. **`remediation_approvals`**: Explicit human dual-custody approval gates.
18. **`verification_runs`**: Automated verification scans validating patch efficacy.
19. **`reports`**: Generated compliance and executive security reports.
20. **`chat_conversations`**: AI Security Chat sessions.
21. **`chat_messages`**: Contextual reasoning thread messages.
22. **`audit_logs`**: Immutable security action audit logs.
23. **`notifications`**: User and workspace security alerts.

---

## 2. Row Level Security (RLS) & Multi-Tenancy

Every table containing sensitive workspace data enforces Supabase RLS.
- Multi-tenancy isolation is enforced at the database layer via `workspace_id`.
- Helper function `auth.is_workspace_member(ws_id)` verifies membership before granting access.

---

## 3. Storage Buckets

Storage buckets and workspace-scoped RLS policies are declared in [`supabase/storage.sql`](file:///d:/Shreyanshcodes/shadow-ops-v2/supabase/storage.sql):
- `scan-artifacts`: Raw scan intermediate results.
- `evidence-files`: Screenshots, HTTP captures, proofs.
- `security-reports`: Exported PDFs and compliance summaries.
- `remediation-artifacts`: Generated patch diffs and branch payloads.
- `verification-artifacts`: Re-test outputs and verification logs.
