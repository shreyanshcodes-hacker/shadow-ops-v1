# AGENT ORCHESTRATION — SHADOWOPS (STAGE 7)

## 1. Orchestration Architecture

ShadowOps implements a sequential multi-agent orchestration pipeline managed by `SecurityTeamOrchestrator` (`backend/app/services/security_team_orchestrator.py`).

```
Trigger Request (POST /security-team/runs)
                  │
          Idempotency Guard
                  │
   [Status: QUEUED -> RUNNING]
                  │
                  ▼
         1. RECON_AGENT
                  │
                  ▼
    2. VULNERABILITY_ANALYST_AGENT
                  │
                  ▼
        3. ATTACK_PATH_AGENT
                  │
                  ▼
         4. RISK_ANALYST_AGENT
                  │
                  ▼
      5. SECURITY_REVIEWER_AGENT
                  │
                  ▼
  [Status: SUCCEEDED (or PARTIAL)]
                  │
  [Human Review Sign-Off Boundary]
```

---

## 2. Orchestration Invariants & State Transitions

### Team Run Lifecycle States
- `QUEUED`: Evaluation registered, pending execution.
- `RUNNING`: Agents actively analyzing scanner facts.
- `SUCCEEDED`: All 5 agents completed successfully and produced a unified assessment.
- `PARTIAL`: One or more intermediate agents encountered a non-critical failure, but the Security Reviewer produced an advisory summary noting degraded confidence.
- `FAILED`: Critical failure (e.g. database error, invalid target scope).
- `CANCELED`: Evaluation halted by user (`POST /security-team/runs/{id}/cancel`).

### Agent State Contract
Each individual agent invocation is recorded in `agent_runs` table with:
- `team_run_id`: Foreign key link to `security_team_runs(id)`
- `agent_name`: Name from `AgentRegistry` (`recon`, `vulnerability_analyst`, etc.)
- `status`: `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `BLOCKED`
- `confidence`: Bounded float `[0.0, 1.0]`
- `attempt`: Current attempt number (bounded by `MAX_AGENT_RETRIES = 2`)
- `input_reference`: Sanitized inputs provided to the agent
- `output`: Structured JSON adhering to the agent's Pydantic response schema
- `tokens_input`, `tokens_output`, `cost_usd`: Exact token usage tracking

---

## 3. Idempotency & Concurrency Guard

To prevent duplicate runs or resource exhaustion:
1. `create_team_run` checks for existing runs with `(workspace_id, asset_id, scan_id, orchestration_version)` in state `QUEUED` or `RUNNING`.
2. If an active run exists, the orchestrator immediately returns the existing run without triggering new agent executions.

---

## 4. Partial Failure & Retry Strategy

- **Retry Limit**: Each agent has a maximum of `MAX_AGENT_RETRIES = 2`.
- **Failure Resilience**: If an intermediate agent (`recon`, `vulnerability_analyst`, `attack_path`, `risk_analyst`) fails after retries:
  - The error is logged and audited (`AGENT_FAILED`).
  - An empty fallback payload is passed to subsequent agents.
  - The `SECURITY_REVIEWER_AGENT` is informed of the upstream failure and incorporates the missing data as an explicit uncertainty.
  - The overall run status is marked `PARTIAL` rather than crashing the entire pipeline.
