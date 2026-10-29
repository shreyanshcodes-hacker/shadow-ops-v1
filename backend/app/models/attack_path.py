import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from app.db.base import Base, TimestampMixin


class AttackPath(Base, TimestampMixin):
    __tablename__ = "attack_paths"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    entry_point: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    target_asset: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    risk_band: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0, nullable=False)
    node_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    edge_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    factors: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    model_version: Mapped[str] = mapped_column(String, default="risk-v1", nullable=False)

    nodes: Mapped[List["AttackPathNode"]] = relationship("AttackPathNode", back_populates="attack_path", cascade="all, delete-orphan", order_by="AttackPathNode.node_order")
    edges: Mapped[List["AttackPathEdge"]] = relationship("AttackPathEdge", back_populates="attack_path", cascade="all, delete-orphan")
    risk_snapshots: Mapped[List["RiskSnapshot"]] = relationship("RiskSnapshot", back_populates="attack_path", cascade="all, delete-orphan", order_by="desc(RiskSnapshot.calculated_at)")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'mitigated', 'broken', 'draft', 'resolved', 'dismissed')", name="check_attack_path_status"),
        CheckConstraint("risk_band IS NULL OR risk_band IN ('INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="check_attack_path_risk_band"),
    )


class AttackPathNode(Base):
    __tablename__ = "attack_path_nodes"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attack_path_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("attack_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    node_type: Mapped[str] = mapped_column(String, nullable=False)
    node_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    finding_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id"), nullable=True)
    risk_contribution: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    attack_path: Mapped["AttackPath"] = relationship("AttackPath", back_populates="nodes")
    finding: Mapped[Optional["Finding"]] = relationship("Finding")

    __table_args__ = (
        CheckConstraint("node_type IN ('asset', 'vulnerability', 'network_zone', 'trust_boundary', 'data_store', 'attacker')", name="check_ap_node_type"),
    )


class AttackPathEdge(Base):
    __tablename__ = "attack_path_edges"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attack_path_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("attack_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    source_node_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("attack_path_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("attack_path_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    edge_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evidence_refs: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)).with_variant(JSON, "sqlite"), default=list, nullable=False)
    likelihood: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    attack_path: Mapped["AttackPath"] = relationship("AttackPath", back_populates="edges")

    __table_args__ = (
        CheckConstraint("edge_type IN ('exploits', 'accesses', 'trusts', 'contains', 'lateral_movement', 'privilege_escalation')", name="check_ap_edge_type"),
    )


class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    attack_path_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("attack_paths.id", ondelete="CASCADE"), nullable=True, index=True)
    finding_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=True, index=True)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    risk_band: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, default="risk-v1", nullable=False)
    factors: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    calculated_by: Mapped[str] = mapped_column(String, default="deterministic_engine", nullable=False)

    attack_path: Mapped[Optional["AttackPath"]] = relationship("AttackPath", back_populates="risk_snapshots")

    __table_args__ = (
        CheckConstraint("score >= 0.0 AND score <= 100.0", name="check_risk_snapshot_score"),
        CheckConstraint("risk_band IN ('INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="check_risk_snapshot_band"),
    )
