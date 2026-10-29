# ShadowOps API Documentation

The ShadowOps API is built with **FastAPI** using asynchronous handlers, Pydantic v2 schemas, and strict security middleware.

Base URL: `/api/v1`

---

## 1. System Endpoints

### `GET /api/v1/health`
Returns the status of the API server, timestamp, and environment.

### `GET /api/v1/health/database`
Checks live database connectivity and latency against the PostgreSQL database.

---

## 2. Authentication & Identity Endpoints

### `GET /api/v1/auth/me`
Returns the current authenticated user's profile and workspace memberships.
- **Headers**: `Authorization: Bearer <FIREBASE_ID_TOKEN>`

---

## 3. Workspace Management Endpoints

### `GET /api/v1/workspaces`
Lists all workspaces that the authenticated user belongs to.

### `POST /api/v1/workspaces`
Creates a new workspace, assigns the creator as `owner`, and logs an audit trail event.

---

## 4. Asset Management & Security Boundary Endpoints

### `GET /api/v1/workspaces/{workspace_id}/assets`
Lists all registered assets for a workspace with their authorization status.

### `POST /api/v1/workspaces/{workspace_id}/assets`
Registers a new asset (repository, API, infrastructure, or application).
- Validates target domain/IP to prevent SSRF against internal/loopback IPs.

### `POST /api/v1/workspaces/{workspace_id}/assets/{asset_id}/authorize`
Submits ownership authorization proofs (DNS token, file upload, or admin consent).

### `GET /api/v1/workspaces/{workspace_id}/assets/{asset_id}/authorization-status`
Returns the verified authorization status. Enforces `NO AUTHORIZATION → NO SCAN`.
