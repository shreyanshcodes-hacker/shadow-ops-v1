from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.profile import Profile
from app.schemas.attack_path import (
    AttackPathRead,
    AttackPathDetailRead,
    AttackPathNodeRead,
    AttackPathEdgeRead,
    AttackPathRecalculateResponse,
    RiskSnapshotRead,
)
from app.security.dependencies import get_current_user
from app.services.workspace_service import WorkspaceService
from app.services.audit_service import AuditService
from app.schemas.audit import AuditEventType
from app.repositories.attack_path_repo import AttackPathRepository
from app.services.graph_service import GraphService

router = APIRouter(tags=["Attack Paths & Risk Engine"])


@router.get("/attack-paths", response_model=List[AttackPathRead])
async def list_attack_paths(
    workspace_id: UUID = Query(...),
    scan_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all attack paths discovered in a workspace.
    Enforces workspace boundary isolation.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    repo = AttackPathRepository(db)
    paths = await repo.list_attack_paths_by_workspace(
        workspace_id=workspace_id,
        scan_id=scan_id,
        status=status_filter,
    )
    return paths


@router.get("/attack-paths/{path_id}", response_model=AttackPathDetailRead)
async def get_attack_path_details(
    path_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full attack path detail including ordered nodes, edges, and risk factor breakdown.
    """
    repo = AttackPathRepository(db)
    path = await repo.get_attack_path_by_id(path_id)
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attack path not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(path.workspace_id, current_user.id)

    # Transform nodes and edges for rich representation
    nodes_read = []
    for n in path.nodes or []:
        nodes_read.append(
            AttackPathNodeRead(
                id=n.id,
                attack_path_id=n.attack_path_id,
                workspace_id=n.workspace_id,
                node_type=n.node_type,
                node_order=n.node_order,
                label=n.label,
                description=n.description,
                asset_id=n.asset_id,
                finding_id=n.finding_id,
                risk_contribution=float(n.risk_contribution or 0.0),
                metadata_=n.metadata_ or {},
                created_at=n.created_at,
                finding_title=n.finding.title if n.finding else None,
                finding_severity=n.finding.severity if n.finding else None,
            )
        )

    edges_read = []
    for e in path.edges or []:
        edges_read.append(
            AttackPathEdgeRead(
                id=e.id,
                attack_path_id=e.attack_path_id,
                workspace_id=e.workspace_id,
                source_node_id=e.source_node_id,
                target_node_id=e.target_node_id,
                edge_type=e.edge_type,
                description=e.description,
                evidence_refs=e.evidence_refs or [],
                likelihood=float(e.likelihood) if e.likelihood is not None else None,
                created_at=e.created_at,
            )
        )

    snapshots_read = [
        RiskSnapshotRead(
            id=s.id,
            workspace_id=s.workspace_id,
            attack_path_id=s.attack_path_id,
            finding_id=s.finding_id,
            score=float(s.score),
            risk_band=s.risk_band,
            model_version=s.model_version,
            factors=s.factors,
            calculated_at=s.calculated_at,
            calculated_by=s.calculated_by,
        )
        for s in path.risk_snapshots or []
    ]

    return AttackPathDetailRead(
        id=path.id,
        workspace_id=path.workspace_id,
        scan_id=path.scan_id,
        name=path.name,
        title=path.title or path.name,
        description=path.description,
        entry_point=path.entry_point,
        target_asset=path.target_asset,
        risk_score=float(path.risk_score) if path.risk_score is not None else None,
        risk_band=path.risk_band,
        confidence=float(path.confidence or 1.0),
        node_count=path.node_count,
        edge_count=path.edge_count,
        is_critical=path.is_critical,
        status=path.status,
        factors=path.factors or {},
        model_version=path.model_version,
        created_at=path.created_at,
        updated_at=path.updated_at,
        nodes=nodes_read,
        edges=edges_read,
        risk_snapshots=snapshots_read,
    )


@router.post("/attack-paths/{path_id}/recalculate-risk", response_model=AttackPathRecalculateResponse)
async def recalculate_risk(
    path_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deterministically recalculates the risk score for an attack path based on Model risk-v1.
    AI output is advisory; this calculation is purely authoritative and deterministic.
    """
    repo = AttackPathRepository(db)
    path = await repo.get_attack_path_by_id(path_id)
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attack path not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(path.workspace_id, current_user.id)

    previous_score = float(path.risk_score) if path.risk_score is not None else None

    # Run deterministic graph risk recalculation
    snapshot = await GraphService.recalculate_path_risk(db, path)

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        workspace_id=path.workspace_id,
        user_id=current_user.id,
        action=AuditEventType.RISK_CALCULATED,
        resource_type="attack_path",
        resource_id=path.id,
        old_state={"risk_score": previous_score},
        new_state={"risk_score": float(snapshot.score), "risk_band": snapshot.risk_band},
    )

    return AttackPathRecalculateResponse(
        attack_path_id=path.id,
        previous_score=previous_score,
        new_score=float(snapshot.score),
        risk_band=snapshot.risk_band,
        model_version=snapshot.model_version,
        factors=snapshot.factors,
        snapshot_id=snapshot.id,
    )


@router.post("/attack-paths/synthesize", response_model=List[AttackPathRead])
async def synthesize_attack_paths(
    workspace_id: UUID = Query(...),
    scan_id: Optional[UUID] = Query(None),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Assembles directed attack paths from confirmed and active relationships within the workspace.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    created_paths = await GraphService.build_attack_paths_from_relationships(
        db=db,
        workspace_id=workspace_id,
        scan_id=scan_id,
    )

    if created_paths:
        audit_service = AuditService(db)
        for p in created_paths:
            await audit_service.log(
                workspace_id=workspace_id,
                user_id=current_user.id,
                action=AuditEventType.ATTACK_PATH_CREATED,
                resource_type="attack_path",
                resource_id=p.id,
                new_state={"name": p.name, "risk_score": float(p.risk_score or 0.0)},
            )

    return created_paths
