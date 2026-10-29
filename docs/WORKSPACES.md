# ShadowOps Workspaces Architecture & Tenancy

This document describes the multi-tenant workspace architecture in ShadowOps.

---

## 1. Multi-Tenant Model

In ShadowOps, the **Workspace** is the primary isolation and security perimeter:
- All target assets (`repository`, `api`, `infrastructure`, `application`) belong strictly to a single `workspace_id`.
- Members belong to workspaces through `workspace_members` association records with assigned RBAC roles.
- Cross-tenant requests are denied at both the FastAPI dependency injection layer and Supabase Row Level Security (RLS) policies.

---

## 2. Workspace Endpoints

- `GET /api/v1/workspaces`: Lists all workspaces where the authenticated user is an active member. Never returns global workspaces.
- `POST /api/v1/workspaces`: Creates a new workspace. The authenticated caller automatically becomes the `OWNER`.
- `GET /api/v1/workspaces/{workspace_id}`: Returns workspace details if and only if the caller is a member. Returns `403 Forbidden` for unauthorized tenants without revealing resource state.
- `GET /api/v1/workspaces/{workspace_id}/members`: Lists member collaborators with their email, display name, role, and joined date.

---

## 3. Frontend Persistence & Context

- The active workspace is managed globally by `WorkspaceContext`.
- The user's selection is remembered in `localStorage` (`shadowops_active_workspace`) for UI continuity across refreshes.
- **Security Invariant**: `localStorage` is purely a client-side preference; the backend independently re-validates workspace membership on every single API request.
