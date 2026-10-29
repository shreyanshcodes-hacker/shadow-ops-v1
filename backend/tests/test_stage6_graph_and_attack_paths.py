import pytest
from httpx import AsyncClient
from uuid import uuid4
from sqlalchemy import select

from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset
from app.models.scan import Scan
from app.models.finding import Finding
from app.models.security_relationship import SecurityRelationship
from app.models.attack_path import AttackPath, RiskSnapshot
from app.schemas.workspace import WorkspaceRole
from app.services.graph_service import GraphService, MAX_ATTACK_PATH_NODES


def test_cycle_detection_in_relationship_graph():
    """Verify that cycle detection detects cycles and safely handles DAGs."""
    n1, n2, n3, n4 = uuid4(), uuid4(), uuid4(), uuid4()

    # Acyclic graph: 1 -> 2 -> 3 -> 4
    acyclic = {
        n1: [n2],
        n2: [n3],
        n3: [n4],
        n4: [],
    }
    assert GraphService.detect_cycles(acyclic) is False

    # Cyclic graph: 1 -> 2 -> 3 -> 1
    cyclic = {
        n1: [n2],
        n2: [n3],
        n3: [n1],
    }
    assert GraphService.detect_cycles(cyclic) is True


@pytest.mark.asyncio
async def test_attack_path_synthesis_and_risk_recalculation_api(
    client: AsyncClient,
    db_session,
    auth_headers,
):
    """
    Test end-to-end Attack Path synthesis from relationships:
    - Synthesizes multi-node path
    - Confirms node ordering and deterministic risk score
    - Confirms RiskSnapshot created
    - Calls recalculate-risk API endpoint and verifies score update and history
    """
    profile = Profile(
        id=uuid4(),
        firebase_uid="firebase-path-user",
        email="pathlead@shadowops.io",
        display_name="Path Lead",
    )
    ws = Workspace(
        id=uuid4(),
        name="Path Synthesis Workspace",
        slug="path-ws",
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
        name="Critical Core API",
        type="repository",
        criticality="critical",
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
    f1 = Finding(
        id=uuid4(),
        workspace_id=ws.id,
        asset_id=asset.id,
        scan_id=scan.id,
        source="semgrep",
        title="Unauthenticated Endpoint Access",
        description="Publicly reachable without session token",
        severity="medium",
        confidence="high",
    )
    f2 = Finding(
        id=uuid4(),
        workspace_id=ws.id,
        asset_id=asset.id,
        scan_id=scan.id,
        source="semgrep",
        title="Database Query Injection",
        description="SQL command execution via unsanitized parameter",
        severity="critical",
        confidence="high",
    )
    rel = SecurityRelationship(
        id=uuid4(),
        workspace_id=ws.id,
        source_finding_id=f1.id,
        target_finding_id=f2.id,
        relationship_type="ENABLES",
        confidence=0.95,
        source="DETERMINISTIC",
        status="active",
        rationale="Unauthenticated endpoint enables direct parameter tampering on query injection.",
    )

    db_session.add_all([profile, ws, member, asset, scan, f1, f2, rel])
    await db_session.commit()

    headers = auth_headers(uid=profile.firebase_uid, email=profile.email)

    # 1. Synthesize attack paths
    synth_res = await client.post(
        f"/api/v1/attack-paths/synthesize?workspace_id={ws.id}&scan_id={scan.id}",
        headers=headers,
    )
    assert synth_res.status_code == 200
    paths = synth_res.json()
    assert len(paths) >= 1

    path_data = paths[0]
    path_id = path_data["id"]
    assert path_data["node_count"] == 2
    assert path_data["edge_count"] == 1
    assert path_data["risk_score"] is not None
    assert path_data["risk_band"] in ["HIGH", "CRITICAL"]
    assert path_data["model_version"] == "risk-v1"

    # 2. Get detailed path view
    detail_res = await client.get(
        f"/api/v1/attack-paths/{path_id}",
        headers=headers,
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["nodes"]) == 2
    assert detail["nodes"][0]["node_order"] == 0
    assert detail["nodes"][1]["node_order"] == 1
    assert len(detail["edges"]) == 1
    assert len(detail["risk_snapshots"]) >= 1

    # 3. Recalculate risk on demand
    recalc_res = await client.post(
        f"/api/v1/attack-paths/{path_id}/recalculate-risk",
        headers=headers,
    )
    assert recalc_res.status_code == 200
    recalc_data = recalc_res.json()
    assert recalc_data["attack_path_id"] == path_id
    assert recalc_data["new_score"] == path_data["risk_score"]
    assert recalc_data["model_version"] == "risk-v1"
    assert "snapshot_id" in recalc_data


@pytest.mark.asyncio
async def test_attack_path_max_nodes_boundary():
    """Verify that MAX_ATTACK_PATH_NODES is enforced and does not exceed 8."""
    assert MAX_ATTACK_PATH_NODES == 8
