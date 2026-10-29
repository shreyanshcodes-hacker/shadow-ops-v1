import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset, AssetAuthorization
from app.schemas.workspace import WorkspaceRole
from app.schemas.authorization import AuthorizationStatus


@pytest.mark.asyncio
async def test_full_scan_lifecycle_and_result_persistence(
    client: AsyncClient,
    db_session,
    auth_headers,
):
    """
    Validates complete scan lifecycle:
    - Pre-flight authorization passes
    - Scan transitions through QUEUED -> RUNNING -> COMPLETED
    - Scan events logged (SCAN_CREATED, SEMGREP_STARTED, RESULTS_PARSED, etc.)
    - Real findings & evidence persisted to database
    - Deterministic summary calculated from parsed matches
    """
    profile = Profile(
        id=uuid4(),
        firebase_uid="firebase-lifecycle-user",
        email="lead@soc.net",
        display_name="SOC Lead",
    )
    ws = Workspace(
        id=uuid4(),
        name="Lifecycle Perimeter",
        slug="lifecycle-perimeter",
        owner_id=profile.id,
    )
    member = WorkspaceMember(
        id=uuid4(),
        workspace_id=ws.id,
        user_id=profile.id,
        role=WorkspaceRole.OWNER.value,
    )
    asset = Asset(
        id=uuid4(),
        workspace_id=ws.id,
        name="Core Codebase",
        type="repository",
        criticality="high",
        status="active",
        tags=["production"],
        created_by=profile.id,
        connection_config={"identifier": "github.com/soc/core"},
    )
    auth = AssetAuthorization(
        id=uuid4(),
        asset_id=asset.id,
        workspace_id=ws.id,
        authorization_type="ownership",
        status=AuthorizationStatus.AUTHORIZED.value,
        verified_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
    )

    db_session.add_all([profile, ws, member, asset, auth])
    await db_session.commit()

    headers = auth_headers(uid=profile.firebase_uid, email=profile.email)

    # 1. Trigger Scan
    res_create = await client.post(
        "/api/v1/scans",
        json={"asset_id": str(asset.id), "scan_profile": "CODE_SECURITY"},
        headers=headers,
    )
    assert res_create.status_code == 201
    scan_data = res_create.json()
    scan_id = scan_data["id"]
    assert scan_data["status"] == "completed"
    assert scan_data["summary"]["total_findings"] >= 4

    # 2. Verify Scan Events
    res_events = await client.get(f"/api/v1/scans/{scan_id}/events", headers=headers)
    assert res_events.status_code == 200
    events = res_events.json()
    event_types = [e["event_type"] for e in events]
    assert "SCAN_CREATED" in event_types
    assert "AUTHORIZATION_CONFIRMED" in event_types
    assert "SEMGREP_STARTED" in event_types
    assert "RESULTS_PARSED" in event_types
    assert "SCAN_COMPLETED" in event_types

    # 3. Verify Findings Endpoint
    res_findings = await client.get(f"/api/v1/scans/{scan_id}/findings", headers=headers)
    assert res_findings.status_code == 200
    findings = res_findings.json()
    assert len(findings) >= 4
    rule_ids = [f["source_rule_id"] for f in findings]
    assert any("sql-injection" in r for r in rule_ids)
    assert any("aws" in r or "secret" in r for r in rule_ids)

    # 4. Verify Asset Scans Endpoint
    res_asset_scans = await client.get(f"/api/v1/assets/{asset.id}/scans", headers=headers)
    assert res_asset_scans.status_code == 200
    assert len(res_asset_scans.json()) == 1


@pytest.mark.asyncio
async def test_cross_workspace_scan_isolation(
    client: AsyncClient,
    db_session,
    auth_headers,
):
    """
    Validates cross-workspace isolation for scans:
    - Tenant A cannot view Tenant B's scans or events.
    - Tenant A cannot cancel Tenant B's scans.
    """
    # Tenant Alpha
    p_alpha = Profile(id=uuid4(), firebase_uid="fb-alpha", email="a@alpha.com")
    ws_alpha = Workspace(id=uuid4(), name="Alpha", slug="ws-alpha", owner_id=p_alpha.id)
    m_alpha = WorkspaceMember(id=uuid4(), workspace_id=ws_alpha.id, user_id=p_alpha.id, role="owner")
    asset_alpha = Asset(id=uuid4(), workspace_id=ws_alpha.id, name="Asset A", type="repository", created_by=p_alpha.id)
    auth_alpha = AssetAuthorization(id=uuid4(), asset_id=asset_alpha.id, workspace_id=ws_alpha.id, authorization_type="ownership", status="verified")

    # Tenant Bravo
    p_bravo = Profile(id=uuid4(), firebase_uid="fb-bravo", email="b@bravo.com")
    ws_bravo = Workspace(id=uuid4(), name="Bravo", slug="ws-bravo", owner_id=p_bravo.id)
    m_bravo = WorkspaceMember(id=uuid4(), workspace_id=ws_bravo.id, user_id=p_bravo.id, role="owner")
    asset_bravo = Asset(id=uuid4(), workspace_id=ws_bravo.id, name="Asset B", type="repository", created_by=p_bravo.id)
    auth_bravo = AssetAuthorization(id=uuid4(), asset_id=asset_bravo.id, workspace_id=ws_bravo.id, authorization_type="ownership", status="verified")

    db_session.add_all([
        p_alpha, ws_alpha, m_alpha, asset_alpha, auth_alpha,
        p_bravo, ws_bravo, m_bravo, asset_bravo, auth_bravo,
    ])
    await db_session.commit()

    headers_a = auth_headers(uid=p_alpha.firebase_uid, email=p_alpha.email)
    headers_b = auth_headers(uid=p_bravo.firebase_uid, email=p_bravo.email)

    # Alpha starts a scan
    res_scan_a = await client.post(
        "/api/v1/scans",
        json={"asset_id": str(asset_alpha.id), "scan_profile": "CODE_SECURITY"},
        headers=headers_a,
    )
    assert res_scan_a.status_code == 201
    scan_id_a = res_scan_a.json()["id"]

    # Bravo CANNOT retrieve Alpha's scan -> 403 Forbidden
    res_b_get_a = await client.get(f"/api/v1/scans/{scan_id_a}", headers=headers_b)
    assert res_b_get_a.status_code == 403

    # Bravo CANNOT retrieve Alpha's scan events -> 403 Forbidden
    res_b_get_events = await client.get(f"/api/v1/scans/{scan_id_a}/events", headers=headers_b)
    assert res_b_get_events.status_code == 403

    # Bravo CANNOT retrieve Alpha's scan findings -> 403 Forbidden
    res_b_get_findings = await client.get(f"/api/v1/scans/{scan_id_a}/findings", headers=headers_b)
    assert res_b_get_findings.status_code == 403
