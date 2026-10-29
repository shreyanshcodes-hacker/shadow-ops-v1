# SECURITY ARCHITECTURE — SHADOWOPS

## 1. The 14 Mandatory Security Principles

ShadowOps is built around 14 non-negotiable security principles embedded into every layer of the system:

1. **Authentication is Required**: Every incoming API request (except public health endpoints) must present a cryptographically verified Firebase Authentication ID token. Unauthenticated requests are rejected immediately with HTTP 401.
2. **Backend Authorization is Mandatory**: Access control checks are computed solely on the backend. Client-side state, UI flags, or query parameters are never trusted for permission boundaries.
3. **Frontend State is Never Trusted**: The browser is treated as an insecure, potentially hostile execution environment. All inputs are re-validated server-side.
4. **Workspace Isolation is Mandatory**: Multi-tenant isolation is enforced at both the API routing layer and the database engine layer via PostgreSQL Row Level Security (RLS). Zero cross-tenant data leakage is tolerated.
5. **Assets Belong to Workspaces**: Digital assets (repositories, domains, APIs) are strictly scoped to a single workspace. Scans, findings, and remediations inherit this boundary.
6. **Scan Requests Must Validate Authorization Server-Side**: Initiating a scan requires a server-side lookup verifying that an active, validated authorization record exists for the asset.
7. **No Authorization Means No Scan (`NO AUTH → NO SCAN`)**: If authorization is absent, pending, expired, or invalid, the backend immediately refuses scan execution and records a security audit event.
8. **Secrets Never Reach the Browser**: Database connection strings, AI provider API keys, Firebase Admin credentials, and repository access tokens are stored in Railway secrets or backend key vaults. No secret is ever exposed in client bundles or public endpoints.
9. **AI Output Must Be Validated Before Use**: All LLM outputs must pass schema validation, confidence bounds checking, and evidence verification before being stored in the database or presented to users.
10. **AI Must Never Directly Perform Uncontrolled Destructive Actions**: The AI Security Manager and its agents are analytical advisory entities. They are architecturally incapable of directly mutating infrastructure, pushing code to default branches, or deleting data.
11. **Human Approval is Required Before Sensitive Remediation**: Applying a code patch, merging a branch, or deploying a configuration change requires an authenticated human user with `admin` or `owner` privileges.
12. **Every Important Security Action Must Be Auditable**: Scan triggers, authorization changes, remediation approvals, role assignments, and exports are immutably logged to `audit_logs`.
13. **Security Evidence Must Have Provenance**: Every finding must retain its source attribution, tool version, raw AST/SARIF log, and cryptographic fingerprint to prove physical existence and reproducibility.
14. **External Targets Must Never Be Scanned Without Explicit Authorization**: Scanning arbitrary third-party infrastructure is strictly forbidden. Proof of ownership must be established before external reconnaissance or testing occurs.

---

## 2. Asset Authorization & Verification Engine

To prevent abuse, illegal scanning, or accidental reconnaissance against unauthorized infrastructure, ShadowOps implements an authorization gate:

```
[ User Adds Asset ]
         │
         ▼
[ Issue Verification Challenge ]
   ├── Code Repository  ──► GitHub App OAuth Installation / Read-Permission Verification
   ├── Web Application  ──► HTTP Well-Known Challenge (`/.well-known/shadowops-challenge.txt`)
   └── Infrastructure   ──► DNS TXT Record Challenge (`_shadowops-challenge.example.com`)
         │
         ▼
[ Backend Verification Service ]
   ├── Resolves DNS / HTTP GET / Validates OAuth Token
   ├── Verifies Randomized Challenge Token
   └── Updates `asset_authorizations.status = 'verified'`
         │
         ▼
[ Scan Pipeline Gate ]
   └── Reads status from DB: Verified & Not Expired? 
         ├── YES ──► Scan Queued
         └── NO  ──► Scan Aborted (HTTP 403 / E_UNAUTHORIZED_TARGET)
```

### Authorization Challenge Protocols
- **DNS TXT Challenge**: A unique cryptographically generated token (`shadowops-verify=<random_hex_32>`) must be published under the domain's DNS zone. The backend queries authoritative nameservers to confirm presence.
- **HTTP Challenge**: A challenge token must be served from `https://<domain>/.well-known/shadowops-challenge.txt` with a valid TLS certificate.
- **Repository Verification**: For GitHub/GitLab assets, verification occurs via OAuth App integration where the authenticated user must possess repository `admin` or `write` permissions.

---

## 3. Row Level Security (RLS) & Tenant Isolation

Tenant isolation is enforced directly in PostgreSQL. Even in the event of an application logic bug, the database engine prevents cross-tenant access.

### Session Context Injection
On every backend database interaction, the caller's verified `user_id` and active `workspace_id` are set within the database transaction:

```sql
-- Executed inside transaction before tenant query:
SET LOCAL app.current_user_id = 'c4b8b6e2-7e2a-4315-992a-81a17f223129';
SET LOCAL app.current_workspace_id = '8f3e2d1c-4b5a-6789-0123-abcdef456789';
```

### RLS Policy Matrix
- **`workspaces`**: Users can only `SELECT` workspaces where they have an active record in `workspace_members`. Only the `owner` can `UPDATE` or `DELETE`.
- **`assets` & `scans`**: `SELECT`, `INSERT`, `UPDATE` are restricted to rows where `workspace_id = current_setting('app.current_workspace_id')::uuid`.
- **`findings` & `finding_evidence`**: Inherits workspace scoping.
- **`audit_logs`**: Strictly append-only. No `UPDATE` or `DELETE` policies are defined. `SELECT` is restricted to `admin` and `owner` roles.

---

## 4. Role-Based Access Control (RBAC) Matrix

| Action / Capability | Workspace Owner | Workspace Admin | Security Engineer / Member | Read-Only Viewer |
|---|:---:|:---:|:---:|:---:|
| **Delete Workspace / Billing** | ✅ | ❌ | ❌ | ❌ |
| **Manage Members & Roles** | ✅ | ✅ | ❌ | ❌ |
| **Add / Delete Assets** | ✅ | ✅ | ✅ | ❌ |
| **Manage Asset Authorization**| ✅ | ✅ | ❌ | ❌ |
| **Trigger Scans** | ✅ | ✅ | ✅ | ❌ |
| **Cancel Active Scans** | ✅ | ✅ | ✅ (Own) | ❌ |
| **View Scans, Findings, Paths**| ✅ | ✅ | ✅ | ✅ |
| **Triage Findings (Status)** | ✅ | ✅ | ✅ | ❌ |
| **Approve AI Remediation** | ✅ | ✅ | ❌ | ❌ |
| **Apply Remediation (PR / Fix)**| ✅ | ✅ | ❌ | ❌ |
| **Run Empirical Verification** | ✅ | ✅ | ✅ | ❌ |
| **Generate & Export Reports** | ✅ | ✅ | ✅ | ✅ |
| **Use AI Security Chat** | ✅ | ✅ | ✅ | ✅ |
| **View Regulatory Audit Logs** | ✅ | ✅ | ❌ | ❌ |

---

## 5. Defense-in-Depth & Network Hardening

### 5.1 Server-Side Request Forgery (SSRF) Protection
Scanner and Recon workers perform network probes. To prevent attackers from using ShadowOps as a proxy to attack internal infrastructure or cloud metadata services:
- **Strict IP Blacklisting**: Probes to private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16` - AWS/GCP metadata), and IPv6 equivalents are rejected at DNS resolution time before any TCP connection is established.
- **DNS Rebinding Protection**: DNS queries are resolved immediately prior to connection, and the resolved IP is verified against the blocklist.

### 5.2 Secret Protection & Key Management
- Database credentials and AI API keys exist solely in Railway environment variables.
- Git access tokens supplied by users for repository cloning are encrypted at rest using AES-256-GCM.
- Secrets are decrypted only in memory during the scan job and wiped from memory immediately upon clone completion.
