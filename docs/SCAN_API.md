# ShadowOps — Scan API Reference

Base URL: `/api/v1`

---

## 1. Endpoints

### `POST /api/v1/scans`
Initiates an authorized vulnerability scan.
- **Headers**: `Authorization: Bearer <FIREBASE_ID_TOKEN>`
- **Request Body**:
  ```json
  {
    "asset_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "scan_profile": "CODE_SECURITY"
  }
  ```
- **Responses**:
  - `201 Created`: Scan enqueued and executed.
  - `403 Forbidden`: `NO AUTHORIZATION -> NO SCAN` invariant failure.
  - `404 Not Found`: Asset not in caller's workspace.

### `GET /api/v1/scans?workspace_id={workspace_id}`
Returns all scans belonging to the active workspace.

### `GET /api/v1/scans/{scan_id}`
Retrieves detailed status, summary, and progress for a specific scan.

### `GET /api/v1/scans/{scan_id}/events`
Returns the chronological timeline of execution events (`SCAN_CREATED`, `SEMGREP_STARTED`, `RESULTS_PARSED`, etc.).

### `POST /api/v1/scans/{scan_id}/cancel`
Cancels an active or queued scan.

### `GET /api/v1/scans/{scan_id}/findings`
Returns parsed static analysis findings and code locations.

### `GET /api/v1/assets/{asset_id}/scans`
Returns all scan executions for a specific asset.
