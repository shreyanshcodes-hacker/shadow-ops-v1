import pytest
from httpx import AsyncClient
from uuid import uuid4
from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.workspace import WorkspaceRole


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    """Verify that unauthenticated requests to protected endpoints return 401 Unauthorized."""
    random_ws_id = uuid4()
    resp = await client.get(f"/api/v1/workspaces/{random_ws_id}")
    assert resp.status_code == 401
    assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_cross_tenant_access_denied_for_foreign_workspace(
    client: AsyncClient,
    db_session,
    auth_headers,
):
    """
    Verify that User A cannot access or query a workspace owned by User B.
    """
    profile_a = Profile(
        id=uuid4(),
        firebase_uid="firebase-user-alpha",
        email="user_a@tenant-alpha.com",
        display_name="User Alpha",
    )
    ws_a = Workspace(
        id=uuid4(),
        name="Workspace Alpha",
        slug="workspace-alpha",
        owner_id=profile_a.id,
    )
    member_a = WorkspaceMember(
        id=uuid4(),
        workspace_id=ws_a.id,
        user_id=profile_a.id,
        role=WorkspaceRole.OWNER.value,
    )

    profile_b = Profile(
        id=uuid4(),
        firebase_uid="firebase-user-bravo",
        email="user_b@tenant-bravo.com",
        display_name="User Bravo",
    )
    ws_b = Workspace(
        id=uuid4(),
        name="Workspace Bravo",
        slug="workspace-bravo",
        owner_id=profile_b.id,
    )
    member_b = WorkspaceMember(
        id=uuid4(),
        workspace_id=ws_b.id,
        user_id=profile_b.id,
        role=WorkspaceRole.OWNER.value,
    )

    db_session.add_all([profile_a, ws_a, member_a, profile_b, ws_b, member_b])
    await db_session.commit()

    headers_a = auth_headers(
        uid=profile_a.firebase_uid,
        email=profile_a.email,
        name=profile_a.display_name,
    )

    # User A attempts to access Workspace B
    resp = await client.get(
        f"/api/v1/workspaces/{ws_b.id}",
        headers=headers_a,
    )
    assert resp.status_code == 403
    assert "denied" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_role_escalation_viewer_cannot_invite_members(
    client: AsyncClient,
    db_session,
    auth_headers,
):
    """
    Verify that a user with 'viewer' role is forbidden from performing administrative actions (inviting members).
    """
    profile = Profile(
        id=uuid4(),
        firebase_uid="firebase-user-viewer",
        email="viewer@company.com",
        display_name="Viewer User",
    )
    ws = Workspace(
        id=uuid4(),
        name="Security Workspace",
        slug="sec-ws",
        owner_id=profile.id,
    )
    member = WorkspaceMember(
        id=uuid4(),
        workspace_id=ws.id,
        user_id=profile.id,
        role=WorkspaceRole.VIEWER.value,
    )

    db_session.add_all([profile, ws, member])
    await db_session.commit()

    headers = auth_headers(
        uid=profile.firebase_uid,
        email=profile.email,
        name=profile.display_name,
    )

    # Viewer attempts to invite another member (requires Owner/Admin)
    resp = await client.post(
        f"/api/v1/workspaces/{ws.id}/members",
        json={"email": "newbie@company.com", "role": "member"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "owners or admins" in resp.json()["detail"].lower()
