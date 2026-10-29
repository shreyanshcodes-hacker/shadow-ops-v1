# ShadowOps — Scanner Execution Security & Isolation Boundary

This document defines the security architecture, sandbox restrictions, and isolation controls governing static analysis and Semgrep scanner execution in ShadowOps.

---

## 1. Core Security Principle: `NO AUTHORIZATION → NO SCAN`

ShadowOps enforces a zero-trust model where no scanner process may execute against an asset without verified, active, and unexpired legal authorization:
- Pre-flight checks are strictly performed server-side (`verify_scan_authorization`).
- Statuses `pending`, `revoked`, `rejected`, or `expired` immediately terminate execution with `403 Forbidden`.
- Client requests cannot forge authorization attributes, requester identity, or workspace tenancy.

---

## 2. Process & Execution Security Controls

1. **No `shell=True` Subprocesses**:
   - Process invocations use argument arrays directly (`asyncio.create_subprocess_exec(*cmd)`), preventing command injection, shell metacharacter manipulation, and argument splitting attacks.
2. **Path Traversal Protection**:
   - Target paths are strictly resolved and validated against an approved sandbox directory boundary using `ScanPathPolicy.sanitize_and_validate_target`.
   - Prohibited targets include system directories (`/etc`, `/bin`, `C:\Windows`, etc.) and backend source code itself.
3. **Execution Timeouts**:
   - Scans enforce a strict 60-second execution window. Processes that exceed this threshold are terminated and killed, transitioning the scan to `failed`.
4. **No Code Execution**:
   - Semgrep performs strictly static AST analysis. Target repositories and scripts are **never** executed, compiled, or loaded into runtime memory.
5. **Secret Redaction**:
   - Sensitive credentials (AWS access keys, tokens, passwords) are scrubbed and redacted via `redact_sensitive_strings` before persistence into finding or evidence records.

---

## 3. Worker Isolation & Future Containerization

- Current Stage: Local controlled sandbox execution against authorized fixtures.
- Target Architecture: Dedicated isolated container worker (`Dockerfile.scanner`) running non-root on an ephemeral Railway worker mesh with network access completely disabled.
