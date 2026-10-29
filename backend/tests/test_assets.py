import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_asset_lifecycle_and_authorization(client: AsyncClient, auth_headers_owner):
    # 1. Create workspace
    ws_res = await client.post("/api/v1/workspaces", json={"name": "Asset Test Org"}, headers=auth_headers_owner)
    assert ws_res.status_code == 201
    workspace_id = ws_res.json()["id"]

    # 2. Add Repository Asset
    asset_payload = {
        "name": "Backend Monorepo",
        "type": "repository",
        "subtype": "github",
        "identifier": "https://github.com/shadowops/backend",
        "environment": "production",
        "criticality": "high",
        "tags": ["core", "api"],
    }
    asset_res = await client.post(
        f"/api/v1/workspaces/{workspace_id}/assets",
        json=asset_payload,
        headers=auth_headers_owner,
    )
    assert asset_res.status_code == 201
    asset_data = asset_res.json()
    assert asset_data["name"] == "Backend Monorepo"
    assert asset_data["type"] == "repository"
    assert asset_data["authorization_status"] == "pending"
    asset_id = asset_data["id"]

    # 3. List assets
    list_res = await client.get(f"/api/v1/workspaces/{workspace_id}/assets", headers=auth_headers_owner)
    assert list_res.status_code == 200
    assets = list_res.json()
    assert len(assets) == 1
    assert assets[0]["id"] == asset_id

    # 4. Record Authorization (Transition to verified)
    auth_payload = {
        "authorization_type": "ownership",
        "authorization_scope": "full_code_and_deps",
        "authorized_by": "SecOps Director",
        "evidence_urls": ["https://github.com/organizations/shadowops/settings/profile"],
        "notes": "Verified repo ownership via GitHub organization admin check.",
    }
    auth_res = await client.post(
        f"/api/v1/assets/{asset_id}/authorization",
        json=auth_payload,
        headers=auth_headers_owner,
    )
    assert auth_res.status_code == 200
    auth_data = auth_res.json()
    assert auth_data["status"] == "verified"
    assert auth_data["asset_id"] == asset_id


@pytest.mark.asyncio
async def test_asset_ssrf_protection(client: AsyncClient, auth_headers_owner):
    # Create workspace
    ws_res = await client.post("/api/v1/workspaces", json={"name": "SSRF Guard Org"}, headers=auth_headers_owner)
    workspace_id = ws_res.json()["id"]

    # Attempt to create asset pointing to loopback / internal metadata
    malicious_payload = {
        "name": "Cloud Metadata Probe",
        "type": "api",
        "identifier": "http://169.254.169.254/latest/meta-data/",
    }
    res = await client.post(
        f"/api/v1/workspaces/{workspace_id}/assets",
        json=malicious_payload,
        headers=auth_headers_owner,
    )
    assert res.status_code == 400
    assert "SSRF blocked" in res.json()["detail"]

    # Attempt to point to localhost
    localhost_payload = {
        "name": "Localhost Probe",
        "type": "api",
        "identifier": "http://localhost:8080/admin",
    }
    res2 = await client.post(
        f"/api/v1/workspaces/{workspace_id}/assets",
        json=localhost_payload,
        headers=auth_headers_owner,
    )
    assert res2.status_code == 400
    assert "restricted loopback" in res2.json()["detail"]
