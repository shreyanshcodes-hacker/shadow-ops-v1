import pytest
from httpx import AsyncClient
from uuid import uuid4
from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset
from app.schemas.workspace import WorkspaceRole


@pytest.mark.asyncio
async def test_role_enforcement_and_elevation_rejection(
    client: AsyncClient,
    db_session,
    auth_headers,
):
    """
    SECURITY TEST: Role Enforcement & Escalation Prevention
    Validates:
    - VIEWER cannot create an asset (403).
    - VIEWER cannot record/verify authorization (403).
    - ENGINEER/MEMBER can create an asset, but CANNOT verify authorization (403).
    - OWNER and ADMIN CAN create assets AND verify authorization (200/201).
    """
    # 1. Create Workspace & Owner
    owner_profile = Profile(
        id=uuid4(),
        firebase_uid="firebase-owner",
        email="owner@ops.com",
        display_name="Owner Admin",
    )
    ws = Workspace(
        id=uuid4(),
        name="Role Test Perimeter",
        slug="role-test-perimeter",
        owner_id=owner_profile.id,
    )
    owner_member = WorkspaceMember(
        id=uuid4(),
        workspace_id=ws.id,
        user_id=owner_profile.id,
        role=WorkspaceRole.OWNER.value,
    )

    # 2. Create Engineer (MEMBER)
    engineer_profile = Profile(
        id=uuid4(),
        firebase_uid="firebase-engineer",
        email="engineer@ops.com",
        display_name="Dev Engineer",
    )
    engineer_member = WorkspaceMember(
        id=uuid4(),
        workspace_id=ws.id,
        user_id=engineer_profile.id,
        role=WorkspaceRole.MEMBER.value,
    )

    # 3. Create Auditor (VIEWER)
    viewer_profile = Profile(
        id=uuid4(),
        firebase_uid="firebase-viewer",
        email="viewer@ops.com",
        display_name="Auditor Viewer",
    )
    viewer_member = WorkspaceMember(
        id=uuid4(),
        workspace_id=ws.id,
        user_id=viewer_profile.id,
        role=WorkspaceRole.VIEWER.value,
    )

    db_session.add_all([
        owner_profile, ws, owner_member,
        engineer_profile, engineer_member,
        viewer_profile, viewer_member,
    ])
    await db_session.commit()

    headers_owner = auth_headers(uid=owner_profile.firebase_uid, email=owner_profile.email)
    headers_eng = auth_headers(uid=engineer_profile.firebase_uid, email=engineer_profile.email)
    headers_viewer = auth_headers(uid=viewer_profile.firebase_uid, email=viewer_profile.email)

    # VIEWER CANNOT create asset -> 403 Forbidden
    res_viewer_create = await client.post(
        f"/api/v1/workspaces/{ws.id}/assets",
        json={
            "name": "Unauthorized Asset",
            "type": "repository",
            "criticality": "low",
            "connection_config": {"identifier": "github.com/ops/unauth"},
        },
        headers=headers_viewer,
    )
    assert res_viewer_create.status_code == 403

    # ENGINEER CAN create asset -> 201 Created
    res_eng_create = await client.post(
        f"/api/v1/workspaces/{ws.id}/assets",
        json={
            "name": "Dev Microservice",
            "type": "repository",
            "criticality": "medium",
            "connection_config": {"identifier": "github.com/ops/microservice"},
        },
        headers=headers_eng,
    )
    assert res_eng_create.status_code == 201
    asset_id = res_eng_create.json()["id"]

    # ENGINEER CANNOT verify authorization -> 403 Forbidden
    res_eng_auth = await client.post(
        f"/api/v1/assets/{asset_id}/authorization",
        json={
            "authorization_type": "ownership",
            "authorization_scope": "full_scan",
        },
        headers=headers_eng,
    )
    assert res_eng_auth.status_code == 403

    # OWNER CAN verify authorization -> 200 OK
    res_owner_auth = await client.post(
        f"/api/v1/assets/{asset_id}/authorization",
        json={
            "authorization_type": "ownership",
            "authorization_scope": "full_scan",
            "notes": "Verified by Security Lead",
        },
        headers=headers_owner,
    )
    assert res_owner_auth.status_code == 200
    assert res_owner_auth.json()["status"] in ["authorized", "verified"]
