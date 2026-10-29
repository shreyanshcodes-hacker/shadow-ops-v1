# VALIDATION & ROLLBACK ARCHITECTURE — SHADOWOPS
## Stage 8 Bounded Validation Pipeline & Atomic Recovery

**Date:** October 27, 2026  
**Status:** ACTIVE SPECIFICATION  

---

## 1. Bounded Validation Pipeline (`ValidationService`)

Before any remediation patch is submitted to human engineers for review, it must pass an automated validation pipeline.

### Four Core Validation Checks:

| Check Name | Target Scope | Execution Environment | Failure Condition |
|---|---|---|---|
| **`patch_integrity`** | Unified diff formatting | In-memory parser | Malformed headers, missing hunks, invalid line markers, binary headers, size > 64KB |
| **`path_policy`** | Relative filepaths | In-memory path validator | Directory traversal (`../`), absolute paths, sensitive files (`.env`, `.pem`, `migrations/`) |
| **`syntax_check`** | Code language parse | Python AST / JSON parser | SyntaxError in added python code blocks, invalid JSON parse |
| **`isolated_regression_test`** | Sandbox execution | Disposable worktree | If container sandbox is unavailable on host, marked `BLOCKED` rather than fake `PASS` |

### Bounded Limits:
- Every check runs with a maximum timeout of 10,000 ms.
- Output from checks is sanitized to prevent leaking file contents into error messages.
- Results are stored in `remediation_validations` with duration in milliseconds.

---

## 2. Atomic Pre-Flight Checkpointing (`RemediationCheckpoint`)

Before a single byte is modified in the target working directory, the system captures a recoverable snapshot:

1. **File Snapshotting**: Every file declared in `affected_files` is read from disk.
2. **Snapshot Persistence**: Original contents and filepaths are stored in `remediation_checkpoints.snapshot_data`.
3. **Foreign Key Link**: The resulting `checkpoint_id` is linked directly to the `remediation_applications` record.

---

## 3. Rollback Mechanics & Divergence Defense

If an applied patch causes an integration issue or fails functional verification, an operator can invoke rollback.

### Divergence Detection Principle:
> **Never blindly reset a repository or overwrite unrelated user work.**

When `rollback_proposal` is invoked:
1. The system loads the checkpoint snapshot from `remediation_checkpoints`.
2. Target files are inspected on disk.
3. If files have diverged beyond the applied patch (e.g., subsequent manual commits or edits), rollback fails safely and alerts the operator to perform manual inspection.
4. If safe, the original file content is restored atomically.
5. `remediation_applications.status` transitions to `ROLLED_BACK`.
6. `remediation_proposals.status` transitions to `ROLLED_BACK`.
7. An immutable audit log entry is recorded with actor ID and reason.
