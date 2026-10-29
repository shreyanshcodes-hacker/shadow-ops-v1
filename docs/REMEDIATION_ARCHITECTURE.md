# REMEDIATION ARCHITECTURE — SHADOWOPS
## Stage 8: AI Remediation, Human Approval & Safe Patch Management

## 1. Remediation Philosophy: Human-in-the-Loop Guardrail

Remediating cybersecurity vulnerabilities in production environments requires extreme care. An automated tool that silently applies unreviewed patches can introduce breaking regressions, cause service outages, or inadvertently create new security vulnerabilities.

### Absolute Guardrail
> **AI Proposes $\longrightarrow$ Automated Validation $\longrightarrow$ Human Reviews & Approves $\longrightarrow$ Controlled Application $\longrightarrow$ Verification Handoff**

The AI Remediation Engine is strictly advisory:
- **No Autonomous Code Changes**: The AI never commits, merges, or pushes code autonomously.
- **No AI Self-Approval**: Agents and models cannot approve their own patch proposals.
- **No Automatic Deployment**: Applying a patch applies it strictly to an authorized, server-resolved working copy or creates a recoverable checkpoint.
- **Finding Invariant**: Findings remain **UNRESOLVED** until verified by empirical verification. The status transitions to `APPLIED — VERIFICATION PENDING`.

---

## 2. Complete Remediation State Machine

```
   [ FINDING IDENTIFIED & AUTHORIZED ]
                   │
                   ▼
         [ DRAFT / GENERATING ]
     AI Provider receives fenced prompt
     (minimum necessary AST & rule context)
                   │
                   ▼
               [ PROPOSED ]
     Canonical unified diff & SHA-256 patch_hash generated
                   │
                   ▼
              [ VALIDATING ]
     Automated Bounded Pipeline executes:
     ├── 1. Patch Integrity & Hunk Parsing
     ├── 2. Path Traversal & Sensitive File Allowlist
     ├── 3. Syntax Verification (AST / JSON parser)
     └── 4. Sandbox Isolation Checks
                   │
          ┌────────┴────────┐
          ▼                 ▼
 [ VALIDATION_FAILED ]  [ AWAITING_APPROVAL ]
          │                 │
          │                 ▼
          │         [ HUMAN REVIEW GATE ]
          │     Engineer reviews unified diff side-by-side
          │     Checks compatibility risks & suggested tests
          │                 │
          │         ┌───────┴───────┐
          │         ▼               ▼
          │    [ REJECTED ]    [ APPROVED ]
          │    Permanently     Cryptographic patch hash bound
          │    blocked         to authenticated approval record
          │                         │
          │                         ▼
          │                    [ APPLYING ]
          │              Pre-flight checkpoint created
          │              Atomic patch applied to target copy
          │                         │
          │                 ┌───────┴───────┐
          │                 ▼               ▼
          │             [ FAILED ]     [ APPLIED ]
          │                           Verification Status:
          │                           VERIFICATION_PENDING
          │                                 │
          │                                 ▼
          │                        [ ROLLBACK OPTION ]
          │                        Divergence checked;
          │                        original state restored from
          │                        checkpoint snapshot
          ▼                                 │
     [ ARCHIVED ]                           ▼
                                     [ ROLLED_BACK ]
```

---

## 3. Data Architecture (`remediation_proposals`)

Every proposal maintains an auditable, immutable trail of actions, approvals, and validations:

| Column | Type | Description |
|---|---|---|
| `id` | `UUID PK` | Unique remediation identifier |
| `workspace_id` | `UUID FK` | Multi-tenant workspace boundary |
| `asset_id` | `UUID FK` | Authorized asset scope |
| `finding_id` | `UUID FK` | Targeted finding |
| `source_scan_id` | `UUID FK` | Associated scan execution |
| `proposal_title` | `TEXT` | Concise summary of proposed remediation |
| `problem_summary` | `TEXT` | Root-cause analysis |
| `proposed_solution` | `TEXT` | Technical mechanism of the fix |
| `rationale` | `TEXT` | Expected security improvement |
| `affected_files` | `JSONB` | Relative paths of files modified |
| `unified_diff` | `TEXT` | Canonical unified diff format |
| `patch_hash` | `TEXT` | SHA-256 hash of canonical unified diff |
| `validation_results`| `JSONB` | Output from automated validation suite |
| `risk_assessment` | `JSONB` | Compatibility risks, assumptions, limitations |
| `suggested_tests` | `JSONB` | Recommended verification test cases |
| `status` | `TEXT` | State machine status |
| `version` | `INT` | Proposal revision counter |
| `approved_by` | `UUID FK` | Authenticated human approver |
| `approved_at` | `TIMESTAMPTZ`| Approval timestamp |
| `applied_by` | `UUID FK` | Human operator who triggered application |
| `applied_at` | `TIMESTAMPTZ`| Application timestamp |

---

## 4. Verification Handoff Boundary

A core principle of ShadowOps is that **a code patch does not equal a closed vulnerability**.

When a patch is applied:
1. `remediation_proposals.status` $\longrightarrow$ `APPLIED`
2. `remediation_applications.verification_status` $\longrightarrow$ `VERIFICATION_PENDING`
3. `findings.status` $\longrightarrow$ Remains `open`

The user interface displays:
`APPLIED — VERIFICATION PENDING`

Only an empirical re-scan and verification run in Stage 9 can transition a finding to `verified` / `resolved`.
