# ShadowOps Authentication Architecture

ShadowOps implements **Firebase Authentication** combined with a stateless JWT verification layer in FastAPI and synchronized database identities in Supabase.

---

## 1. Authentication Flow

1. **Client Authentication**:
   - The user authenticates against Firebase Auth (Google, GitHub, or Email/Password) in the Next.js frontend.
   - Firebase returns an ID token (JWT) signed by Google's private key.

2. **Bearer Token Transmission**:
   - The frontend API client attaches the ID token as an `Authorization: Bearer <ID_TOKEN>` header for all backend requests.

3. **Backend Verification**:
   - The FastAPI backend validates the token using the `firebase-admin` SDK (`firebase_admin.auth.verify_id_token`).
   - The token's claims (`uid`, `email`, `name`, `picture`) are extracted.

4. **Just-In-Time Profile Synchronization**:
   - The backend looks up the profile by `firebase_uid`.
   - If no profile exists, a new record is created in the `profiles` table.
   - If a profile exists, its `last_login_at` timestamp is updated.

---

## 2. Workspace Access Control & RBAC

All workspace-level endpoints enforce multi-tenant authorization using FastAPI dependency injection:

```python
_membership = Depends(RequireWorkspaceMember(allowed_roles=[WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
```

The system verifies:
1. The authenticated profile is an active member of the requested workspace.
2. The user possesses a role that meets or exceeds the required privilege level.
3. Access is logged to the immutable `audit_logs` table.
