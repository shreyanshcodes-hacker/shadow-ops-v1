import pytest
from httpx import AsyncClient
from uuid import uuid4
from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset
from app.schemas.workspace import WorkspaceRole


@pytest.mark.asyncio
async def test_cross_workspace_multi_tenant_isolation(
    client: AsyncClient,
    db_session,
    auth_headers,
):
    """
    SECURITY TEST: Cross-Workspace Multi-Tenant Isolation
    Validates:
    - User A (in Workspace A with Asset A) CANNOT access Asset B or Workspace B.
    - User B (in Workspace B with Asset B) CANNOT access Asset A or Workspace A.
    - User A CANNOT create authorization for Asset B.
    - User B CANNOT create authorization for Asset A.
    """
    # 1. Setup User A and Workspace A
    profile_a = Profile(
        id=uuid4(),
        firebase_uid="firebase-user-a",
        email="usera@tenant-alpha.com",
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
    asset_a = Asset(
        id=uuid4(),
        workspace_id=ws_a.id,
        name="Repo Alpha",
        type="repository",
        criticality="critical",
        status="active",
        tags=["production"],
        created_by=profile_a.id,
        connection_config={"identifier": "github.com/alpha/repo"},
    )

    # 2. Setup User B and Workspace B
    profile_b = Profile(
        id=uuid4(),
        firebase_uid="firebase-user-b",
        email="userb@tenant-bravo.com",
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
    asset_b = Asset(
        id=uuid4(),
        workspace_id=ws_b.id,
        name="Repo Bravo",
        type="repository",
        criticality="high",
        status="active",
        tags=["production"],
        created_by=profile_b.id,
        connection_config={"identifier": "github.com/bravo/repo"},
    )

    db_session.add_all([
        profile_a, ws_a, member_a, asset_a,
        profile_b, ws_b, member_b, asset_b,
    ])
    await db_session.commit()

    headers_a = auth_headers(
        uid=profile_a.firebase_uid,
        email=profile_a.email,
        name=profile_a.display_name,
    )
    headers_b = auth_headers(
        uid=profile_b.firebase_uid,
        email=profile_b.email,
        name=profile_b.display_name,
    )

    # 3. User A can access Workspace A & Asset A
    res_a_own_ws = await client.get(f"/api/v1/workspaces/{ws_a.id}", headers=headers_a)
    assert res_a_own_ws.status_code == 200
    assert res_a_own_ws.json()["name"] == "Workspace Alpha"

    res_a_own_asset = await client.get(f"/api/v1/assets/{asset_a.id}", headers=headers_a)
    assert res_a_own_asset.status_code == 200
    assert res_a_own_asset.json()["name"] == "Repo Alpha"

    # 4. User A CANNOT access Workspace B (403 Forbidden)
    res_a_leak_ws = await client.get(f"/api/v1/workspaces/{ws_b.id}", headers=headers_a)
    assert res_a_leak_ws.status_code == 403

    # 5. User A CANNOT access Asset B (403 Forbidden)
    res_a_leak_asset = await client.get(f"/api/v1/assets/{asset_b.id}", headers=headers_a)
    assert res_a_leak_asset.status_code == 403

    # 6. User A CANNOT list Asset B by targeting Workspace B
    res_a_list_b = await client.get(f"/api/v1/workspaces/{ws_b.id}/assets", headers=headers_a)
    assert res_a_list_b.status_code == 403

    # 7. User B CANNOT access Workspace A or Asset A
    res_b_leak_ws = await client.get(f"/api/v1/workspaces/{ws_a.id}", headers=headers_b)
    assert res_b_leak_ws.status_code == 403

    res_b_leak_asset = await client.get(f"/api/v1/assets/{asset_a.id}", headers=headers_b)
    assert res_b_leak_asset.status_code == 403

    # 8. User A CANNOT authorize Asset B
    res_a_auth_b = await client.post(
        f"/api/v1/assets/{asset_b.id}/authorization",
        json={
            "authorization_type": "ownership",
            "authorization_scope": "full_scan",
            "notes": "Malicious attempt to authorize rival tenant asset",
        },
        headers=headers_a,
    )
    assert res_a_auth_b.status_code == 403

    # 9. User B CANNOT authorize Asset A
    res_b_auth_a = await client.post(
        f"/api/v1/assets/{asset_a.id}/authorization",
        json={
            "authorization_type": "ownership",
            "authorization_scope": "full_scan",
            "notes": "Malicious attempt to authorize rival tenant asset",
        },
        headers=headers_b,
    )
    assert res_b_auth_a.status_code == 403
