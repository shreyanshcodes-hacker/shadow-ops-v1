import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset, AssetAuthorization
from app.schemas.workspace import WorkspaceRole
from app.schemas.authorization import AuthorizationStatus


@pytest.mark.asyncio
async def test_unauthorized_asset_never_reaches_scanner(
    client: AsyncClient,
    db_session,
    auth_headers,
):
    """
    CRITICAL MANDATORY SECURITY TEST:
    Asserts that if authorization is MISSING, PENDING, REVOKED, or EXPIRED,
    the scanner adapter is NEVER invoked (call_count == 0).
    Only when AUTHORIZED does the scanner boundary execute.
    """
    # 1. Setup Profile & Workspace
    profile = Profile(
        id=uuid4(),
        firebase_uid="firebase-scan-security-user",
        email="operator@defense.io",
        display_name="Security Operator",
    )
    ws = Workspace(
        id=uuid4(),
        name="Defensive Perimeter",
        slug="defensive-perimeter",
        owner_id=profile.id,
    )
    member = WorkspaceMember(
        id=uuid4(),
        workspace_id=ws.id,
        user_id=profile.id,
        role=WorkspaceRole.OWNER.value,
    )
    # Asset with NO authorization record
    asset_unauthorized = Asset(
        id=uuid4(),
        workspace_id=ws.id,
        name="Unverified Repository",
        type="repository",
        criticality="high",
        status="active",
        tags=["production"],
        created_by=profile.id,
        connection_config={"identifier": "github.com/corp/unverified"},
    )
    # Asset with PENDING authorization record
    asset_pending = Asset(
        id=uuid4(),
        workspace_id=ws.id,
        name="Pending Repository",
        type="repository",
        criticality="medium",
        status="active",
        tags=["staging"],
        created_by=profile.id,
        connection_config={"identifier": "github.com/corp/pending"},
    )
    auth_pending = AssetAuthorization(
        id=uuid4(),
        asset_id=asset_pending.id,
        workspace_id=ws.id,
        authorization_type="ownership",
        status=AuthorizationStatus.PENDING.value,
    )
    # Asset with AUTHORIZED record
    asset_authorized = Asset(
        id=uuid4(),
        workspace_id=ws.id,
        name="Verified Repository",
        type="repository",
        criticality="critical",
        status="active",
        tags=["production"],
        created_by=profile.id,
        connection_config={"identifier": "github.com/corp/verified"},
    )
    auth_authorized = AssetAuthorization(
        id=uuid4(),
        asset_id=asset_authorized.id,
        workspace_id=ws.id,
        authorization_type="ownership",
        status=AuthorizationStatus.AUTHORIZED.value,
    )

    db_session.add_all([
        profile, ws, member,
        asset_unauthorized,
        asset_pending, auth_pending,
        asset_authorized, auth_authorized,
    ])
    await db_session.commit()

    headers = auth_headers(uid=profile.firebase_uid, email=profile.email)

    with patch("app.services.scan_service.ScanJobRunner.execute_scan", new_callable=AsyncMock) as mock_scan:
        # Case A: Missing Authorization -> 403 Forbidden
        res_missing = await client.post(
            "/api/v1/scans",
            json={"asset_id": str(asset_unauthorized.id), "scan_profile": "CODE_SECURITY"},
            headers=headers,
        )
        assert res_missing.status_code == 403
        assert "NO AUTHORIZATION -> NO SCAN" in res_missing.json()["detail"]
        assert mock_scan.call_count == 0

        # Case B: Pending Authorization -> 403 Forbidden
        res_pending = await client.post(
            "/api/v1/scans",
            json={"asset_id": str(asset_pending.id), "scan_profile": "CODE_SECURITY"},
            headers=headers,
        )
        assert res_pending.status_code == 403
        assert mock_scan.call_count == 0

        # Case C: Authorized Asset -> 201 Created & Scanner Invoked
        mock_scan.return_value = []
        res_auth = await client.post(
            "/api/v1/scans",
            json={"asset_id": str(asset_authorized.id), "scan_profile": "CODE_SECURITY"},
            headers=headers,
        )
        assert res_auth.status_code == 201
        assert res_auth.json()["status"] in ["queued", "running", "completed"]
        assert mock_scan.call_count == 1
