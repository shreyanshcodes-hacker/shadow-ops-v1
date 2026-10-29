# ShadowOps Authorization Boundary (`NO AUTHORIZATION → NO SCAN`)

This document defines the core security invariant of ShadowOps: **NO AUTHORIZATION → NO SCAN**.

---

## 1. The Rule

Under no circumstances may an automated scanner, recon agent, or analysis pipeline inspect a target asset unless valid, non-expired authorization proof has been verified and recorded.

---

## 2. Authorization Lifecycle States

1. **`pending`**: Initial state upon asset creation. Scanning is **blocked**.
2. **`authorized` / `verified`**: Explicit proof attested by an authorized workspace `OWNER` or `ADMIN`. Scanning is **permitted** (subject to future scan engine readiness).
3. **`revoked` / `rejected`**: Authorization withdrawn. Scanning is immediately **blocked**.
4. **`expired`**: The authorization timestamp has passed (`expires_at < NOW()`). Scanning is automatically **blocked**.

---

## 3. Supported Proof Types

- **`ownership`**: Direct repository OAuth integration or domain DNS root ownership.
- **`dns_token`**: Verification via unique DNS TXT record challenge.
- **`http_token`**: Verification via `.well-known/shadowops-verify.txt` challenge file.
- **`written_permission` / `admin_override`**: Dual-custody enterprise legal attestation.
