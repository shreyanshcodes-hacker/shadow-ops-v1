# ShadowOps — Scan Testing Guide

This document describes the test suite covering the controlled scan engine, authorization boundary invariants, lifecycle transitions, Semgrep parsing, and cross-workspace isolation.

---

## 1. Test Architecture

The Stage 3 tests reside in [`backend/tests/`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/tests/):

1. **`test_scanner_security_invariant.py`**:
   - Explicitly asserts that when authorization is `MISSING`, `PENDING`, `REVOKED`, or `EXPIRED`, the Semgrep scanner boundary is never invoked (`call_count == 0`).
   - Only when authorization is verified active does execution proceed.
2. **`test_scans_lifecycle.py`**:
   - `test_full_scan_lifecycle_and_result_persistence`: Triggers scan on authorized target, validates state progression (`queued` -> `running` -> `completed`), checks chronological scan events, verifies persisted findings with CWE tags, and validates deterministic summary counting.
   - `test_cross_workspace_scan_isolation`: Verifies that Tenant Alpha's scans, events, and findings return `403 Forbidden` to Tenant Bravo.
3. **`test_semgrep_abstraction.py`**:
   - Validates CLI argument array construction and JSON finding normalization with SHA-256 fingerprinting.

---

## 2. Running Backend Tests

```bash
$env:PYTHONPATH="backend"
backend\venv\Scripts\pytest.exe backend/tests -v
```

All 24 tests pass hermetically in memory.
