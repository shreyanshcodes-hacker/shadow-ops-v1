# ShadowOps Security Architecture & Controls

ShadowOps is a cybersecurity platform designed to protect startups and engineering organizations. Its backend implements zero-trust architecture principles and defense-in-depth controls.

---

## 1. The Core Invariant: `NO AUTHORIZATION → NO SCAN`

The frontend UI is **never** treated as a security boundary. Scanning execution is guarded exclusively by the backend:
- Before any scan job is enqueued or dispatched to workers, the `AuthorizationService.can_scan(asset_id, workspace_id)` method verifies:
  1. An explicit `asset_authorizations` entry exists in Supabase.
  2. The authorization status is strictly `authorized`.
  3. The authorization has not expired (`expires_at > NOW()`).
  4. The asset belongs to the invoking workspace.

If these criteria are not met, the API raises `403 Forbidden` (`AUTHORIZATION_REQUIRED`).

---

## 2. Server-Side Request Forgery (SSRF) Prevention

To prevent malicious tenants from scanning localhost, cloud metadata endpoints, or internal private networks, `AssetService` validates all asset targets:
- Prohibited addresses include:
  - Loopback (`127.0.0.1`, `::1`)
  - Cloud metadata (`169.254.169.254`)
  - Private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
  - Special link-local and multicast addresses

---

## 3. Defense-in-Depth Middleware

Every HTTP response includes hardening headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Referrer-Policy: strict-origin-when-cross-origin`
- Unique `X-Request-ID` attached to all request/response contexts for distributed tracing.
- CORS restricted strictly to configured origins (no wildcard `*` allowed in production).

---

## 4. Immutable Audit Trail

All security-sensitive operations (workspace creation, asset registration, authorization status changes, member role updates) write an immutable record to the `audit_logs` table.
