from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.profile import Profile
from app.models.finding import Finding
from app.models.security_relationship import SecurityRelationship
from app.schemas.attack_path import (
    SecurityRelationshipRead,
    SecurityRelationshipUpdate,
    RelationshipStatus,
)
from app.security.dependencies import get_current_user
from app.services.workspace_service import WorkspaceService
from app.services.audit_service import AuditService
from app.schemas.audit import AuditEventType
from app.repositories.attack_path_repo import AttackPathRepository
from app.services.correlation_engine import CorrelationEngine
from app.services.ai_correlation import AICorrelationService

router = APIRouter(tags=["Security Relationships"])


def _serialize_relationship(rel: SecurityRelationship) -> SecurityRelationshipRead:
    return SecurityRelationshipRead(
        id=rel.id,
        workspace_id=rel.workspace_id,
        source_finding_id=rel.source_finding_id,
        target_finding_id=rel.target_finding_id,
        relationship_type=rel.relationship_type,
        confidence=float(rel.confidence),
        source=rel.source,
        status=rel.status,
        rationale=rel.rationale,
        evidence_reference=rel.evidence_reference or {},
        confirmed_by=rel.confirmed_by,
        confirmed_at=rel.confirmed_at,
        created_at=rel.created_at,
        updated_at=rel.updated_at,
        source_finding_title=rel.source_finding.title if rel.source_finding else None,
        target_finding_title=rel.target_finding.title if rel.target_finding else None,
    )


@router.get("/findings/{finding_id}/relationships", response_model=List[SecurityRelationshipRead])
async def list_finding_relationships(
    finding_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all active, confirmed, or suggested security relationships involving this finding.
    """
    stmt = select(Finding).where(Finding.id == finding_id)
    res = await db.execute(stmt)
    finding = res.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(finding.workspace_id, current_user.id)

    repo = AttackPathRepository(db)
    rels = await repo.list_relationships_by_finding(finding_id, finding.workspace_id)
    return [_serialize_relationship(r) for r in rels]


@router.get("/relationships/{relationship_id}", response_model=SecurityRelationshipRead)
async def get_relationship(
    relationship_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve specific security relationship details.
    """
    repo = AttackPathRepository(db)
    rel = await repo.get_relationship_by_id(relationship_id)
    if not rel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(rel.workspace_id, current_user.id)

    return _serialize_relationship(rel)


@router.post("/relationships/{relationship_id}/confirm", response_model=SecurityRelationshipRead)
async def confirm_relationship(
    relationship_id: UUID,
    update_data: Optional[SecurityRelationshipUpdate] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirms a suggested security relationship by a human security operator.
    Marks source as 'HUMAN_CONFIRMED' and records the reviewer's profile ID.
    """
    repo = AttackPathRepository(db)
    rel = await repo.get_relationship_by_id(relationship_id)
    if not rel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(rel.workspace_id, current_user.id)

    updated = await repo.update_relationship_status(
        relationship_id=rel.id,
        status=RelationshipStatus.CONFIRMED.value,
        user_id=current_user.id,
        rationale=update_data.rationale if update_data else None,
    )

    audit_service = AuditService(db)
    await audit_service.log(
        workspace_id=rel.workspace_id,
        user_id=current_user.id,
        action=AuditEventType.RELATIONSHIP_CONFIRMED,
        resource_type="security_relationship",
        resource_id=rel.id,
        old_state={"status": rel.status, "source": rel.source},
        new_state={"status": updated.status, "source": updated.source},
    )

    return _serialize_relationship(updated)


@router.post("/relationships/{relationship_id}/dismiss", response_model=SecurityRelationshipRead)
async def dismiss_relationship(
    relationship_id: UUID,
    update_data: Optional[SecurityRelationshipUpdate] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dismisses an irrelevant or false security relationship.
    """
    repo = AttackPathRepository(db)
    rel = await repo.get_relationship_by_id(relationship_id)
    if not rel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(rel.workspace_id, current_user.id)

    updated = await repo.update_relationship_status(
        relationship_id=rel.id,
        status=RelationshipStatus.DISMISSED.value,
        user_id=current_user.id,
        rationale=update_data.rationale if update_data else None,
    )

    audit_service = AuditService(db)
    await audit_service.log(
        workspace_id=rel.workspace_id,
        user_id=current_user.id,
        action=AuditEventType.RELATIONSHIP_DISMISSED,
        resource_type="security_relationship",
        resource_id=rel.id,
        old_state={"status": rel.status},
        new_state={"status": updated.status},
    )

    return _serialize_relationship(updated)


@router.post("/findings/{finding_id}/correlate", response_model=List[SecurityRelationshipRead])
async def correlate_finding(
    finding_id: UUID,
    include_ai: bool = Query(True),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes deterministic correlation and optional AI correlation for a given finding
    against all other findings on the same scan or asset.
    """
    stmt = (
        select(Finding)
        .options(selectinload(Finding.evidence))
        .where(Finding.id == finding_id)
    )
    res = await db.execute(stmt)
    finding = res.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(finding.workspace_id, current_user.id)

    # Fetch other candidate findings on same asset or scan
    other_stmt = (
        select(Finding)
        .options(selectinload(Finding.evidence))
        .where(
            and_(
                Finding.workspace_id == finding.workspace_id,
                Finding.id != finding.id,
                Finding.asset_id == finding.asset_id,
            )
        )
        .limit(20)
    )
    other_res = await db.execute(other_stmt)
    peers = list(other_res.scalars().all())

    repo = AttackPathRepository(db)
    created_rels: List[SecurityRelationship] = []

    evidence_a = [
        {"file_path": e.file_path, "line_start": e.line_start, "line_end": e.line_end}
        for e in (finding.evidence or [])
    ]

    for peer in peers:
        evidence_b = [
            {"file_path": e.file_path, "line_start": e.line_start, "line_end": e.line_end}
            for e in (peer.evidence or [])
        ]

        # 1. Deterministic Correlation
        det_matches = CorrelationEngine.correlate_pair(
            finding_a=finding,
            finding_b=peer,
            evidence_a=evidence_a,
            evidence_b=evidence_b,
        )

        for match in det_matches:
            # Check existing
            exists = await repo.find_existing_relationship(
                workspace_id=finding.workspace_id,
                source_finding_id=match["source_finding_id"],
                target_finding_id=match["target_finding_id"],
                relationship_type=match["relationship_type"],
            )
            if not exists:
                new_rel = await repo.create_relationship(
                    workspace_id=finding.workspace_id,
                    source_finding_id=match["source_finding_id"],
                    target_finding_id=match["target_finding_id"],
                    relationship_type=match["relationship_type"],
                    confidence=match["confidence"],
                    source=match["source"],
                    rationale=match["rationale"],
                    evidence_reference=match["evidence_reference"],
                )
                created_rels.append(new_rel)

        # 2. AI Correlation (if requested and no deterministic match between pair)
        if include_ai and not det_matches:
            ai_match = await AICorrelationService.analyze_relationship(
                finding_a=finding,
                finding_b=peer,
                evidence_a=evidence_a,
                evidence_b=evidence_b,
            )
            if ai_match:
                exists = await repo.find_existing_relationship(
                    workspace_id=finding.workspace_id,
                    source_finding_id=ai_match["source_finding_id"],
                    target_finding_id=ai_match["target_finding_id"],
                    relationship_type=ai_match["relationship_type"],
                )
                if not exists:
                    new_rel = await repo.create_relationship(
                        workspace_id=finding.workspace_id,
                        source_finding_id=ai_match["source_finding_id"],
                        target_finding_id=ai_match["target_finding_id"],
                        relationship_type=ai_match["relationship_type"],
                        confidence=ai_match["confidence"],
                        source=ai_match["source"],
                        rationale=ai_match["rationale"],
                        evidence_reference=ai_match["evidence_reference"],
                    )
                    created_rels.append(new_rel)

    return [_serialize_relationship(r) for r in created_rels]
