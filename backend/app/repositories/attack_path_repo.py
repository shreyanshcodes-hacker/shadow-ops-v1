from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_, desc, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security_relationship import SecurityRelationship
from app.models.attack_path import AttackPath, AttackPathNode, AttackPathEdge, RiskSnapshot
from app.models.finding import Finding


class AttackPathRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_relationship(
        self,
        workspace_id: UUID,
        source_finding_id: UUID,
        target_finding_id: UUID,
        relationship_type: str,
        confidence: float,
        source: str,
        rationale: Optional[str] = None,
        evidence_reference: Optional[Dict[str, Any]] = None,
    ) -> SecurityRelationship:
        rel = SecurityRelationship(
            workspace_id=workspace_id,
            source_finding_id=source_finding_id,
            target_finding_id=target_finding_id,
            relationship_type=relationship_type,
            confidence=confidence,
            source=source,
            status="active",
            rationale=rationale,
            evidence_reference=evidence_reference or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(rel)
        await self.session.commit()
        await self.session.refresh(rel)
        return rel

    async def get_relationship_by_id(self, relationship_id: UUID) -> Optional[SecurityRelationship]:
        stmt = (
            select(SecurityRelationship)
            .options(
                selectinload(SecurityRelationship.source_finding),
                selectinload(SecurityRelationship.target_finding),
            )
            .where(SecurityRelationship.id == relationship_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def find_existing_relationship(
        self,
        workspace_id: UUID,
        source_finding_id: UUID,
        target_finding_id: UUID,
        relationship_type: str,
    ) -> Optional[SecurityRelationship]:
        stmt = select(SecurityRelationship).where(
            and_(
                SecurityRelationship.workspace_id == workspace_id,
                SecurityRelationship.source_finding_id == source_finding_id,
                SecurityRelationship.target_finding_id == target_finding_id,
                SecurityRelationship.relationship_type == relationship_type,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_relationships_by_finding(
        self,
        finding_id: UUID,
        workspace_id: UUID,
    ) -> List[SecurityRelationship]:
        stmt = (
            select(SecurityRelationship)
            .options(
                selectinload(SecurityRelationship.source_finding),
                selectinload(SecurityRelationship.target_finding),
            )
            .where(
                and_(
                    SecurityRelationship.workspace_id == workspace_id,
                    or_(
                        SecurityRelationship.source_finding_id == finding_id,
                        SecurityRelationship.target_finding_id == finding_id,
                    ),
                )
            )
            .order_by(desc(SecurityRelationship.created_at))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_relationships_by_workspace(
        self,
        workspace_id: UUID,
        status: Optional[str] = None,
    ) -> List[SecurityRelationship]:
        conditions = [SecurityRelationship.workspace_id == workspace_id]
        if status:
            conditions.append(SecurityRelationship.status == status)

        stmt = (
            select(SecurityRelationship)
            .options(
                selectinload(SecurityRelationship.source_finding),
                selectinload(SecurityRelationship.target_finding),
            )
            .where(and_(*conditions))
            .order_by(desc(SecurityRelationship.created_at))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_relationship_status(
        self,
        relationship_id: UUID,
        status: str,
        user_id: Optional[UUID] = None,
        rationale: Optional[str] = None,
    ) -> Optional[SecurityRelationship]:
        rel = await self.get_relationship_by_id(relationship_id)
        if not rel:
            return None

        rel.status = status
        rel.updated_at = datetime.now(timezone.utc)
        if status == "confirmed":
            rel.source = "HUMAN_CONFIRMED"
            rel.confirmed_by = user_id
            rel.confirmed_at = datetime.now(timezone.utc)
        if rationale:
            rel.rationale = rationale

        await self.session.commit()
        await self.session.refresh(rel)
        return rel

    async def get_attack_path_by_id(self, path_id: UUID) -> Optional[AttackPath]:
        stmt = (
            select(AttackPath)
            .options(
                selectinload(AttackPath.nodes).selectinload(AttackPathNode.finding),
                selectinload(AttackPath.edges),
                selectinload(AttackPath.risk_snapshots),
            )
            .where(AttackPath.id == path_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_attack_paths_by_workspace(
        self,
        workspace_id: UUID,
        scan_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> List[AttackPath]:
        conditions = [AttackPath.workspace_id == workspace_id]
        if scan_id:
            conditions.append(AttackPath.scan_id == scan_id)
        if status:
            conditions.append(AttackPath.status == status)

        stmt = (
            select(AttackPath)
            .options(
                selectinload(AttackPath.nodes).selectinload(AttackPathNode.finding),
                selectinload(AttackPath.edges),
                selectinload(AttackPath.risk_snapshots),
            )
            .where(and_(*conditions))
            .order_by(desc(AttackPath.risk_score))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def add_risk_snapshot(
        self,
        attack_path_id: UUID,
        workspace_id: UUID,
        score: float,
        risk_band: str,
        model_version: str,
        factors: Dict[str, Any],
        calculated_by: str = "deterministic_engine",
    ) -> RiskSnapshot:
        snapshot = RiskSnapshot(
            workspace_id=workspace_id,
            attack_path_id=attack_path_id,
            score=score,
            risk_band=risk_band,
            model_version=model_version,
            factors=factors,
            calculated_at=datetime.now(timezone.utc),
            calculated_by=calculated_by,
        )
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot
