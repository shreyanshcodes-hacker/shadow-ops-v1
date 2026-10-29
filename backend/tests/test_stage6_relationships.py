import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset
from app.models.scan import Scan
from app.models.finding import Finding
from app.models.security_relationship import SecurityRelationship
from app.schemas.workspace import WorkspaceRole
from app.schemas.attack_path import RelationshipType, RelationshipSource, RelationshipStatus
from app.services.correlation_engine import CorrelationEngine


@pytest.mark.asyncio
async def test_deterministic_correlation_engine_rules():
    """Test pure deterministic relationship heuristics between findings."""
    ws_id = uuid4()
    asset_id = uuid4()
    scan_id = uuid4()

    # Finding 1: Hardcoded AWS Secret
    f1 = Finding(
        id=uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan_id,
        source="semgrep",
        title="Hardcoded AWS API Secret Key",
        description="Found AWS credential in configuration",
        severity="high",
        confidence="high",
        cwe_ids=["CWE-798"],
        owasp_categories=["A01:2021"],
    )

    # Finding 2: SQL Injection Sink
    f2 = Finding(
        id=uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan_id,
        source="semgrep",
        title="Raw SQL Query String Injection",
        description="Unparameterized SQL execute call",
        severity="critical",
        confidence="high",
        cwe_ids=["CWE-89"],
        owasp_categories=["A03:2021"],
    )

    ev1 = [{"file_path": "backend/auth.py", "line_start": 40, "line_end": 42}]
    ev2 = [{"file_path": "backend/auth.py", "line_start": 55, "line_end": 60}]

    matches = CorrelationEngine.correlate_pair(f1, f2, ev1, ev2)
    types = [m["relationship_type"] for m in matches]

    # Shared file -> SHARES_COMPONENT
    assert RelationshipType.SHARES_COMPONENT.value in types
    # Line distance (55 - 40 = 15 <= 30) -> AMPLIFIES
    assert RelationshipType.AMPLIFIES.value in types
    # Secret + SQL Injection -> EXPOSES
    assert RelationshipType.EXPOSES.value in types

    # All matches must have source='DETERMINISTIC'
    for m in matches:
        assert m["source"] == RelationshipSource.DETERMINISTIC.value
        assert m["confidence"] >= 0.85


@pytest.mark.asyncio
async def test_security_relationship_api_lifecycle_and_confirmation(
    client: AsyncClient,
    db_session,
    auth_headers,
):
    """
    Test human confirmation and dismissal workflows:
    - Lists relationships for finding
    - Confirms relationship (transitions to HUMAN_CONFIRMED)
    - Dismisses relationship
    - Validates multi-tenant access control
    """
    profile = Profile(
        id=uuid4(),
        firebase_uid="firebase-rel-user",
        email="operator@shadowops.io",
        display_name="Sec Operator",
    )
    ws = Workspace(
        id=uuid4(),
        name="Graph Workspace",
        slug="graph-ws",
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
        name="Target Repo",
        type="repository",
        created_by=profile.id,
    )
    scan = Scan(
        id=uuid4(),
        workspace_id=ws.id,
        asset_id=asset.id,
        scan_type="code",
        status="completed",
        triggered_by=profile.id,
    )
    f_src = Finding(
        id=uuid4(),
        workspace_id=ws.id,
        asset_id=asset.id,
        scan_id=scan.id,
        source="semgrep",
        title="Source Vulnerability",
        description="Auth weakness",
        severity="medium",
        confidence="high",
    )
    f_tgt = Finding(
        id=uuid4(),
        workspace_id=ws.id,
        asset_id=asset.id,
        scan_id=scan.id,
        source="semgrep",
        title="Target Vulnerability",
        description="Target sink",
        severity="high",
        confidence="high",
    )
    rel = SecurityRelationship(
        id=uuid4(),
        workspace_id=ws.id,
        source_finding_id=f_src.id,
        target_finding_id=f_tgt.id,
        relationship_type=RelationshipType.ENABLES.value,
        confidence=0.85,
        source=RelationshipSource.AI_SUGGESTED.value,
        status="active",
        rationale="AI inferred that auth weakness enables target sink access.",
    )

    db_session.add_all([profile, ws, member, asset, scan, f_src, f_tgt, rel])
    await db_session.commit()

    headers = auth_headers(uid=profile.firebase_uid, email=profile.email)

    # 1. Fetch relationships for finding
    res = await client.get(
        f"/api/v1/findings/{f_src.id}/relationships",
        headers=headers,
    )
    assert res.status_code == 200
    rels = res.json()
    assert len(rels) >= 1
    assert rels[0]["id"] == str(rel.id)
    assert rels[0]["source"] == "AI_SUGGESTED"

    # 2. Confirm relationship
    conf_res = await client.post(
        f"/api/v1/relationships/{rel.id}/confirm",
        json={"rationale": "Verified by security lead during manual audit."},
        headers=headers,
    )
    assert conf_res.status_code == 200
    confirmed = conf_res.json()
    assert confirmed["status"] == "confirmed"
    assert confirmed["source"] == "HUMAN_CONFIRMED"
    assert confirmed["confirmed_by"] == str(profile.id)
    assert "Verified by security lead" in confirmed["rationale"]

    # 3. Dismiss relationship
    dism_res = await client.post(
        f"/api/v1/relationships/{rel.id}/dismiss",
        json={"rationale": "False correlation after code inspection."},
        headers=headers,
    )
    assert dism_res.status_code == 200
    dismissed = dism_res.json()
    assert dismissed["status"] == "dismissed"


@pytest.mark.asyncio
async def test_cross_workspace_relationship_isolation(
    client: AsyncClient,
    db_session,
    auth_headers,
):
    """Verify tenant isolation: a user cannot view or confirm relationships in another workspace."""
    user = Profile(
        id=uuid4(),
        firebase_uid="firebase-tenant-user",
        email="tenant@shadowops.io",
        display_name="Tenant User",
    )
    user_ws = Workspace(
        id=uuid4(),
        name="User Workspace",
        slug="user-ws",
        owner_id=user.id,
    )
    member = WorkspaceMember(
        id=uuid4(),
        workspace_id=user_ws.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER.value,
    )

    other_ws = Workspace(
        id=uuid4(),
        name="Foreign Workspace",
        slug="foreign-ws",
        owner_id=uuid4(),
    )
    f1 = Finding(
        id=uuid4(),
        workspace_id=other_ws.id,
        asset_id=uuid4(),
        scan_id=uuid4(),
        source="semgrep",
        title="Foreign Finding 1",
        description="desc",
        severity="high",
    )
    f2 = Finding(
        id=uuid4(),
        workspace_id=other_ws.id,
        asset_id=uuid4(),
        scan_id=uuid4(),
        source="semgrep",
        title="Foreign Finding 2",
        description="desc",
        severity="critical",
    )
    foreign_rel = SecurityRelationship(
        id=uuid4(),
        workspace_id=other_ws.id,
        source_finding_id=f1.id,
        target_finding_id=f2.id,
        relationship_type=RelationshipType.LEADS_TO.value,
        confidence=0.9,
        source=RelationshipSource.DETERMINISTIC.value,
        status="active",
    )
    db_session.add_all([user, user_ws, member, other_ws, f1, f2, foreign_rel])
    await db_session.commit()

    headers = auth_headers(uid=user.firebase_uid, email=user.email)

    # Attempt to access foreign relationship
    res = await client.get(
        f"/api/v1/relationships/{foreign_rel.id}",
        headers=headers,
    )
    assert res.status_code in [403, 404]

    # Attempt to confirm foreign relationship
    confirm_res = await client.post(
        f"/api/v1/relationships/{foreign_rel.id}/confirm",
        headers=headers,
    )
    assert confirm_res.status_code in [403, 404]
