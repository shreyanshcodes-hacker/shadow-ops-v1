import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_workspace_creation_and_listing(client: AsyncClient, auth_headers_owner):
    # 1. Create workspace
    payload = {"name": "Security Operations Inc", "slug": "sec-ops"}
    response = await client.post("/api/v1/workspaces", json=payload, headers=auth_headers_owner)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Security Operations Inc"
    assert data["slug"] == "sec-ops"
    workspace_id = data["id"]

    # 2. List workspaces
    list_res = await client.get("/api/v1/workspaces", headers=auth_headers_owner)
    assert list_res.status_code == 200
    workspaces = list_res.json()
    assert len(workspaces) >= 1
    assert any(w["id"] == workspace_id for w in workspaces)

    # 3. Get single workspace
    get_res = await client.get(f"/api/v1/workspaces/{workspace_id}", headers=auth_headers_owner)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == workspace_id

    # 4. Get members (owner should be automatic member)
    members_res = await client.get(f"/api/v1/workspaces/{workspace_id}/members", headers=auth_headers_owner)
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_cross_workspace_isolation(client: AsyncClient, auth_headers_owner, auth_headers_other):
    # User A creates workspace
    payload = {"name": "User A Workspace", "slug": "user-a-ws"}
    res = await client.post("/api/v1/workspaces", json=payload, headers=auth_headers_owner)
    assert res.status_code == 201
    workspace_id = res.json()["id"]

    # User B attempts to access User A's workspace -> Must return 403 Forbidden
    unauthorized_res = await client.get(f"/api/v1/workspaces/{workspace_id}", headers=auth_headers_other)
    assert unauthorized_res.status_code == 403
    assert "Access denied" in unauthorized_res.json()["detail"]

    # User B attempts to view members -> 403 Forbidden
    members_res = await client.get(f"/api/v1/workspaces/{workspace_id}/members", headers=auth_headers_other)
    assert members_res.status_code == 403


@pytest.mark.asyncio
async def test_invite_and_remove_member(client: AsyncClient, auth_headers_owner, auth_headers_other):
    # 1. Owner creates workspace
    ws_res = await client.post("/api/v1/workspaces", json={"name": "Team Collab WS"}, headers=auth_headers_owner)
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    # 2. Owner invites a new collaborator
    invite_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "alice.security@example.com", "role": "admin"},
        headers=auth_headers_owner,
    )
    assert invite_res.status_code == 201
    member_data = invite_res.json()
    assert member_data["email"] == "alice.security@example.com"
    assert member_data["role"] == "admin"
    member_id = member_data["id"]

    # 3. Verify member list now includes alice
    list_res = await client.get(f"/api/v1/workspaces/{ws_id}/members", headers=auth_headers_owner)
    assert list_res.status_code == 200
    members = list_res.json()
    assert len(members) == 2
    assert any(m["email"] == "alice.security@example.com" for m in members)

    # 4. Duplicate invite rejected
    dup_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "alice.security@example.com", "role": "member"},
        headers=auth_headers_owner,
    )
    assert dup_res.status_code == 400

    # 5. Non-member cannot invite -> 403
    unauth_invite = await client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "intruder@example.com", "role": "member"},
        headers=auth_headers_other,
    )
    assert unauth_invite.status_code == 403

    # 6. Owner removes member
    del_res = await client.delete(f"/api/v1/workspaces/{ws_id}/members/{member_id}", headers=auth_headers_owner)
    assert del_res.status_code == 204

    # 7. Member is no longer in workspace
    after_res = await client.get(f"/api/v1/workspaces/{ws_id}/members", headers=auth_headers_owner)
    assert after_res.status_code == 200
    assert len(after_res.json()) == 1
