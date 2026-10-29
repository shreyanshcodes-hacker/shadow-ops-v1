# ShadowOps Role-Based Access Control (RBAC)

This document specifies the role hierarchy and privilege enforcement model implemented in ShadowOps.

---

## 1. Role Hierarchy

| Role | Operational Scope | Capabilities |
|---|---|---|
| **`OWNER`** | Full Workspace Administration | Create/delete workspace, manage team members & roles, onboard assets, sign & verify authorization proofs, approve remediation proposals. |
| **`ADMIN`** | Security Operations Management | Manage assets, sign & verify authorization proofs, view members, approve remediation proposals. Cannot delete workspace or remove owner. |
| **`MEMBER` / `ENGINEER`** | Development & Asset Registration | Register repositories and assets, view scan results, view assigned findings. **CANNOT** verify authorization or approve remediation. |
| **`VIEWER`** | Read-Only Audit & Compliance | View dashboards, assets, and reports. **CANNOT** create assets, change authorizations, or trigger actions. |

---

## 2. Server-Side Role Enforcement

Role checks are strictly enforced on the FastAPI backend using `RequireWorkspaceMember(allowed_roles=[...])`:
- Attempted asset creation by a `VIEWER` returns `403 Forbidden`.
- Attempted authorization verification by a `MEMBER` or `VIEWER` returns `403 Forbidden`.
- All role enforcement events are audited.
