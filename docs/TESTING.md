# ShadowOps Testing Guide

ShadowOps enforces rigorous testing for all core security invariants, API endpoints, AI provider contracts, and scanner normalizers.

---

## 1. Test Architecture

The automated test suite resides in [`backend/tests/`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/tests/):

- **`conftest.py`**: SQLite in-memory async database fixture, mocked auth client, and pre-seeded test data.
- **`test_health.py`**: System and database ping health check verification.
- **`test_auth.py`**: Firebase ID token validation, invalid token rejection, and profile synchronization.
- **`test_workspaces.py`**: Workspace isolation, tenancy boundaries, and role enforcement.
- **`test_assets.py`**: Asset registration, lifecycle transitions, and SSRF prevention filters.
- **`test_authorization_boundary.py`**: Strict enforcement of `NO AUTHORIZATION → NO SCAN`.
- **`test_security_middleware.py`**: Verification of security headers, request IDs, and CORS preflight.
- **`test_ai_abstraction.py`**: Dual-provider contracts for Gemini and Grok, structured outputs, and agent lifecycle state machines.
- **`test_semgrep_abstraction.py`**: Sandboxed command generation and JSON output normalizer with SHA-256 finding deduplication.

---

## 2. Running the Test Suite

```bash
# In project root:
$env:PYTHONPATH="backend"
backend\venv\Scripts\pytest.exe backend/tests -v
```

All 19 test cases execute hermetically with zero external dependencies.
