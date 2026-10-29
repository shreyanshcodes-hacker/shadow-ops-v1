# Controlled Workflow Automation Security Boundary

## 1. Security Philosophy & Invariants

Workflow automation in ShadowOps is designed with **zero-trust, deterministic constraints**. In contrast to unconstrained webhook platforms or dynamic script interpreters, ShadowOps strictly prohibits user-submitted scripts, bash commands, arbitrary URLs, or unsupervised state mutation.

### Mandatory Security Invariants

1. **No User-Authored Code Execution:**
   - The workflow engine contains no eval, shell exec, python dynamic import, or container breakout vectors.
   - Only pre-compiled, statically typed action handlers registered in `WorkflowEngine.ALLOWED_ACTIONS` may be executed.

2. **No Bypassing Governance Controls:**
   - Automation **cannot** approve code remediations.
   - Automation **cannot** close or suppress finding records without verified human sign-off.
   - Automation **cannot** unilaterally alter deterministic risk formulas or snapshot baselines.

3. **Strict Workspace Isolation:**
   - Workflow runs, execution contexts, and outputs are strictly isolated by foreign key constraint to `workspace_id`.
   - Cross-workspace triggering or parameter leakage is impossible.

---

## 2. Action Allowlist Registry

Every workflow execution must reference an explicitly approved action identifier from the following registry:

| Action Identifier | Capability | Security Constraints |
| :--- | :--- | :--- |
| `dispatch_n8n_telemetry` | Dispatches outbound telemetry to registered n8n endpoint | Read-only telemetry; HTTPS destination required; RFC 1918 & metadata blocked; HMAC signed |
| `notify_slack_summary` | Dispatches structured summary alert to Slack webhook | Sanitized markdown only; credentials and token fields scrubbed |
| `generate_compliance_snapshot` | Enqueues automated periodic compliance report generation | Employs existing ReportGeneratorService with frozen timestamp |
| `flag_stale_findings` | Identifies findings exceeding age threshold | Evaluates status; flags candidates for review without mutating core security state |

Any invocation attempting an unlisted action (e.g. `execute_bash`, `run_query`, `download_script`) immediately raises `ControlledWorkflowActionException` and records a security audit anomaly.

---

## 3. Idempotency & Replay Protection

Each workflow execution supports an optional `idempotency_key`:
- Before commencing work, the engine queries `workflow_runs` for an existing completed record matching `(workspace_id, idempotency_key)`.
- If a match is found, the previous execution result is returned immediately without duplicate external calls or processing.
- Re-executing failed runs is permitted only via the explicit, authenticated `POST /workflows/runs/{id}/retry` endpoint.

---

## 4. Audit Trail & Observability

Every workflow run transitions through explicit lifecycle states:
`QUEUED` → `RUNNING` → `COMPLETED` or `FAILED`

All state transitions, input parameters, and output payloads are persisted append-only in the `workflow_runs` table, providing immediate auditing and forensic visibility in the Command Center UI.
