# Independent Fix Verification Architecture

## 1. System Overview

Stage 9 introduces the **Independent Fix Verification & Regression Analysis Engine** for ShadowOps.
The core premise of this architecture is:
> **"No sufficient evidence means no verified fix."**
> Neither patch application, passing unit tests, AI agent claims, nor the absence of a finding in a single scanner run constitutes proof of a fix. Verification requires deterministic baseline comparison, independent rescan, regression checks, conservative evidence matching, and mandatory human sign-off.

```
       APPLIED REMEDIATION PATCH
                   │
                   ▼
     CAPTURE BASELINE EVIDENCE SNAPSHOT
  (Rule ID, File Path, Line Numbers, Fingerprint)
                   │
                   ▼
     EXECUTE INDEPENDENT RESCAN & REGRESSION CHECKS
  (Semgrep scanner adapter + Syntax/AST/Boundary checks)
                   │
                   ▼
       EVIDENCE COMPARISON ENGINE
  (Line shift tolerance, fingerprint & snippet similarity)
                   │
                   ▼
       VERIFICATION POLICY ENGINE (v1)
  (VERIFIED_CANDIDATE, FAILED, INCONCLUSIVE, BLOCKED)
                   │
                   ▼
        HUMAN REVIEW SIGN-OFF GATE
   (Admin / Security Engineer acceptance or rejection)
                   │
                   ▼
        FINDING STATUS TRANSITION
          (Resolved / Fixed or Kept Open)
```

---

## 2. Core Components

### 2.1 Baseline Capture & Snapshot
- Before verification rescan begins, [`EvidenceComparisonEngine`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/evidence_comparison_engine.py) extracts an immutable baseline snapshot:
  - `finding_id`: Target finding identifier.
  - `rule_id`: Semgrep / static analysis rule identifier.
  - `file_path`: Relative file path within repository.
  - `line_start` & `line_end`: Original vulnerability coordinates.
  - `code_snippet`: Matched vulnerable source code.
  - `snippet_hash`: SHA-256 of the trimmed code snippet.
  - `fingerprint`: SHA-256 combining rule, path, lines, and snippet hash.
  - `evidence_items`: Ground truth evidence items collected during scan.

### 2.2 Independent Rescan
- Re-executes the scanner (`SemgrepAdapter`) independently against the authorized codebase.
- The scanner operates in an isolated environment without knowledge of proposed fixes or prior AI assessments.
- Real scanner findings are collected as fresh ground truth.

### 2.3 Evidence Comparison Engine
- Compares the baseline snapshot against findings discovered during the rescan.
- Implements conservative heuristics:
  - **`NO_LONGER_DETECTED`**: No findings in the post-patch scan match the rule ID, target file, or surrounding context.
  - **`STILL_PRESENT`**: Finding matches the same rule and file with line coordinates within tolerance and high code similarity.
  - **`MODIFIED_OR_MOVED`**: Finding matches the rule in the same file but was relocated or slightly altered (e.g., lines shifted or masked).
  - **`POSSIBLE_REGRESSION`**: A new, different vulnerability was introduced in the patched files.
  - **`NEW_FINDING`**: New security flaw detected in the asset.
  - **`UNCOMPARABLE`**: Baseline evidence incomplete, or scanner failed to execute.

### 2.4 Regression Runner
- [`RegressionRunner`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/regression_runner.py) executes multiple checks:
  1. `syntax_integrity`: AST validation for Python, JSON schema verification, UTF-8 non-null byte validation.
  2. `ast_security_invariants`: Scans for newly introduced dangerous sinks (`eval`, `exec`, `os.system`, `shell=True`).
  3. `patch_boundary_integrity`: Ensures modifications do not bleed outside the approved `affected_files`.
  4. `unit_test_suite`: Executes allowlisted test suites.

### 2.5 Verification Policy Engine
- [`VerificationPolicyEngine`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/verification_policy.py) evaluates deterministic rules (`verification-policy-v1`).
- Produces explicit verdicts:
  - `VERIFIED_CANDIDATE`: Rescan confirmed clean + all regression checks PASS.
  - `FAILED`: Flaw still present, moved, or regression detected.
  - `BLOCKED`: Security pattern detected or boundary integrity violated.
  - `INCONCLUSIVE`: Insufficient evidence or uncomparable state.

### 2.6 Mandatory Human Review Gate
- In accordance with the non-negotiable security invariant, software cannot close security vulnerabilities.
- Even upon `VERIFIED_CANDIDATE`, the job status transitions to `PASSED_PENDING_REVIEW`.
- Only an authenticated user with `admin` or `security_engineer` role in the workspace can submit a `review_verification` action (`accepted` or `rejected`).
- Only when `accepted` does `finding.status` transition to `"fixed"` with `finding.fixed_at` timestamp.
