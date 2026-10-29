# ShadowOps — Semgrep Integration Architecture

This document specifies the Semgrep scanner integration, rule mapping, and result normalization in ShadowOps.

---

## 1. Scanner Adapter Pattern

The scanner boundary implements `ScannerAdapter` (`backend/app/scanning/semgrep.py`), isolating the FastAPI service from CLI specifics:
- `is_available()`: Detects whether Semgrep is present in PATH.
- `scan(target_path, timeout_seconds)`: Executes static analysis and returns normalized findings.
- `cancel()`: Terminates running subprocesses safely without orphan processes.

---

## 2. Severity Normalization Matrix

Semgrep raw matches are parsed into ShadowOps standard severities:

| Semgrep Severity | ShadowOps Severity | Tier Action |
|---|---|---|
| `ERROR` | `critical` | Immediate alert; perimeter exposure |
| `WARNING` | `medium` | Security recommendation; review required |
| `INFO` | `low` | Informational hygiene |
| `EXPERIMENT` | `info` | Observability note |

---

## 3. Deduplication & Provenance

Each detected finding is assigned a deterministic SHA-256 fingerprint:
```
fingerprint = sha256(f"{asset_id}:{rule_id}:{file_path}:{line_start}")
```
Raw snippets, CWE IDs, and OWASP categories are persisted into `finding_evidence` for immutable auditability.
