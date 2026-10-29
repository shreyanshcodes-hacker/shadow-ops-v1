# Verification Security & Invariant Enforcements

## 1. Security Boundaries & Invariants

Stage 9 is designed to prevent autonomous AI error propagation into production systems. The following non-negotiable security boundaries are implemented:

### 1.1 Invariant: No Automatic Finding Closure
- Scanners and automated check runners only generate advisory signals.
- The outcome `VERIFIED_CANDIDATE` places the job in `PASSED_PENDING_REVIEW`.
- The database finding status **never** changes to `"fixed"` without an authenticated human operator calling `POST /verifications/{id}/review` with `decision: "accepted"`.

### 1.2 Invariant: Role-Based Human Sign-Off (RBAC)
- Only users with `admin` or `security_engineer` membership in the workspace can review verification jobs.
- Attempting sign-off with `viewer` or unauthorized roles raises `VerificationServiceException` and is blocked by the backend API.

### 1.3 Invariant: Multi-Tenant Workspace Isolation
- All verification jobs, baseline snapshots, rescan data, comparisons, regression checks, and reviews are strictly keyed by `workspace_id`.
- Tenant A cannot access or manipulate verification jobs belonging to Tenant B (returns HTTP 404/403).

### 1.4 Invariant: Complete Audit Trail
- Every verification trigger and every human sign-off decision is permanently recorded in `audit_logs` with actor ID, timestamp, decision, rationale, and finding state before/after.

### 1.5 Invariant: Regression Immunity
- Patches that introduce syntax corruption, forbidden sinks (`eval`, `exec`, `os.system`), or modify files outside the approved patch boundary are immediately marked `BLOCKED` or `FAILED`.
