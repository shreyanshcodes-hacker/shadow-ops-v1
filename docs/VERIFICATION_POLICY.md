# Verification Policy Reference: verification-policy-v1

## 1. Core Principle

> **"No sufficient evidence means no verified fix."**

`verification-policy-v1` is the authoritative deterministic decision engine that evaluates fix verification outcomes.
It prevents false positives, regression introduction, and premature vulnerability closure by evaluating:
1. Scanner completion status
2. Regression check outcomes
3. Vulnerability evidence comparison category
4. Test suite execution results

---

## 2. Decision Matrix

| Vulnerability Status | Scanner Status | Regression Status | Test Status | Verdict | Outcome Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `NO_LONGER_DETECTED` | `COMPLETED` | `PASS` | `PASS` | **`VERIFIED_CANDIDATE`** | Transition job to `PASSED_PENDING_REVIEW`. Await human review. |
| `NO_LONGER_DETECTED` | `COMPLETED` | `SKIPPED` | `SKIPPED` | **`VERIFIED_CANDIDATE`** | Transition job to `PASSED_PENDING_REVIEW`. |
| `STILL_PRESENT` | *Any* | *Any* | *Any* | **`FAILED`** | Vulnerability still detectable. Fix failed. |
| `MODIFIED_OR_MOVED` | *Any* | *Any* | *Any* | **`FAILED`** | Vulnerability relocated or masked; not eliminated. |
| `POSSIBLE_REGRESSION` | *Any* | *Any* | *Any* | **`FAILED`** | New flaw introduced in patched files. |
| `NEW_FINDING` | *Any* | *Any* | *Any* | **`FAILED`** | New flaw discovered during rescan. |
| `UNCOMPARABLE` | *Any* | *Any* | *Any* | **`INCONCLUSIVE`** | Inadequate evidence. Do not verify. |
| *Any* | `FAILED` / `TIMEOUT` | *Any* | *Any* | **`FAILED`** | Rescan could not execute. |
| *Any* | `BLOCKED` / `UNAVAILABLE` | *Any* | *Any* | **`BLOCKED`** | Scanner unavailable or execution forbidden. |
| *Any* | *Any* | `FAIL` / `ERROR` | *Any* | **`FAILED`** | Syntax or unit test failure. |
| *Any* | *Any* | `BLOCKED` | *Any* | **`BLOCKED`** | Boundary violation detected (files outside patch). |

---

## 3. Human Gate Invariants

1. **Software cannot set finding status to fixed**:
   - `VERIFIED_CANDIDATE` only unlocks the human review action.
   - It is strictly impossible for a scan, agent, or service to set `finding.status = "fixed"` autonomously.
2. **Mandatory RBAC**:
   - Only `admin` and `security_engineer` workspace roles may sign off.
   - Viewers and external agents are rejected with HTTP 400/403.
3. **Mandatory Rationale**:
   - Every human review decision must record a non-empty rationale (minimum 5 characters) for auditable compliance.
4. **Rejection Safety**:
   - If a human operator rejects the fix, `finding.status` remains `"open"` and the remediation application is marked `"FAILED"`.
