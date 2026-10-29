# PATCH SECURITY ARCHITECTURE — SHADOWOPS
## Stage 8 Defensive Controls & Patch Sandboxing

**Date:** October 27, 2026  
**Status:** ACTIVE SPECIFICATION  

---

## 1. Threat Model for AI-Generated Patches

AI models generate code based on statistical pattern matching and may produce hallucinated, malicious, or destructive file modifications if not strictly constrained.

### Primary Threat Vectors:
1. **Path Traversal Attacks**: Diffs referencing relative escapes (`../../etc/passwd`, `..\..\..\Windows`) to overwrite arbitrary files outside the repository perimeter.
2. **Absolute Path Escapes**: Diffs targeting `/etc/shadow`, `C:\Windows\System32`, or root filesystem paths.
3. **Sensitive File Modification**: Diffs modifying environment secrets (`.env`), private keys (`.pem`, `.key`), CI/CD workflows (`.github/workflows`), database migration scripts (`supabase/migrations/`), or authentication configuration.
4. **Binary & Executable Injection**: Diffs embedding raw binary payloads (`GIT binary patch`).
5. **Denial of Service / Resource Exhaustion**: Oversized diffs exceeding memory/CPU handling capacity.
6. **Self-Loop / Semantic Corruption**: Syntactically invalid code that breaks the compilation or runtime environment.

---

## 2. Defensive Controls Implemented (`PatchProcessor`)

### 1. Canonicalization & Cryptographic Integrity
Every unified diff is normalized before processing:
- Carriage returns (`\r\n`) are stripped and canonicalized to `\n`.
- Trailing whitespace on every line is removed.
- SHA-256 hash is computed over the UTF-8 bytes of the canonicalized diff:
  $$\text{patch\_hash} = \text{SHA256}(\text{canonical\_diff})$$
- The `patch_hash` is immutable and binds directly to human approvals and application commands. If a diff changes by even a single byte, the approval is invalidated.

### 2. Path Traversal & Absolute Escape Defense
- Every path in `--- a/path` and `+++ b/path` is normalized.
- Paths starting with `/` or Windows drive letters (`C:`) are rejected immediately with `PatchSecurityException`.
- Path segments containing `..` or `.` are rejected immediately.
- Null bytes (`\x00`) and ASCII control characters are rejected.

### 3. Sensitive File Blocklist
The following path patterns are strictly forbidden for automated patches:
- `(?i)(^|/)\.env(\..+)?$` (Environment and secret configuration files)
- `(?i)(^|/)\.git(/|$)` (Git repository metadata)
- `(?i)\.(pem|key|pkcs12|pfx|crt|cer|der|jks|kdbx)$` (Cryptographic keys and certificates)
- `(?i)(^|/)(credentials|secrets|passwords?|tokens?)\.(json|ya?ml|toml|txt|py|js)$`
- `(?i)(^|/)migrations?(/|$)` and `supabase/migrations/` (Database schemas and migrations)
- `(?i)(^|/)(\.github|docker-compose|dockerfile|railway\.json|procfile|k8s|helm)(/|$)` (Deployment and CI infrastructure)

### 4. Patch Bounded Limits
- **Maximum Diff Size**: 64 KB (65,536 bytes). Oversized diffs are rejected.
- **Maximum Affected Files**: 5 files per proposal. Complex multi-file refactorings are rejected to enforce minimal targeted fixes.
- **Binary Rejection**: Patches containing `GIT binary patch` or `Binary files ` are rejected.

---

## 3. Sandboxed Application Environment

- **Server-Resolved Working Copy**: The backend only modifies server-authorized working directories. It never accepts arbitrary client-supplied paths.
- **Atomic Pre-Flight Checkpoint**: Before any file is modified, a full snapshot of the target files is saved in `remediation_checkpoints`.
- **Divergence Detection**: If the repository content diverges from the pre-patch state, rollback fails safely rather than overwriting unrelated developer work.
