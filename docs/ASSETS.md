# ShadowOps Asset Onboarding & Management

This document details the asset registration and lifecycle management model in ShadowOps.

---

## 1. Supported Asset Types

- **`repository`**: Git repositories (e.g., GitHub, GitLab, Bitbucket). Primary focus of Stage 2.
- **`api`**: REST/GraphQL API endpoints.
- **`application`**: Web applications.
- **`infrastructure`**: Cloud VMs, Kubernetes clusters, networks.
- **`container`**: Container images and registries.

---

## 2. Onboarding Lifecycle

1. **Registration (`POST /api/v1/workspaces/{workspace_id}/assets`)**:
   - Operator supplies name, identifier, environment (`production`, `staging`, `development`), criticality tier, and metadata.
   - Target is validated against SSRF prevention rules (blocking `127.0.0.1`, `169.254.169.254`, `10.0.0.0/8`, etc.).
   - Asset is saved in PostgreSQL with an initial `pending` authorization record.
2. **Authorization Gate**:
   - The asset remains in `pending` status until an `OWNER` or `ADMIN` signs verification.
   - Future scanning is blocked until verified.
