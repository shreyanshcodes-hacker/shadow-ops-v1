import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from app.db.base import Base


class SecurityRelationship(Base):
    __tablename__ = "security_relationships"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_finding_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    target_finding_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False, index=True)
    rationale: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evidence_reference: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    confirmed_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    source_finding: Mapped["Finding"] = relationship("Finding", foreign_keys=[source_finding_id], back_populates="outgoing_relationships")
    target_finding: Mapped["Finding"] = relationship("Finding", foreign_keys=[target_finding_id], back_populates="incoming_relationships")

    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('DEPENDS_ON', 'ENABLES', 'EXPOSES', 'LEADS_TO', 'SHARES_COMPONENT', 'SHARES_ENTRY_POINT', 'SHARES_DATA_FLOW', 'AMPLIFIES')",
            name="check_sec_rel_type"
        ),
        CheckConstraint("source IN ('DETERMINISTIC', 'AI_SUGGESTED', 'HUMAN_CONFIRMED')", name="check_sec_rel_source"),
        CheckConstraint("status IN ('active', 'confirmed', 'dismissed')", name="check_sec_rel_status"),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="check_sec_rel_confidence"),
        CheckConstraint("source_finding_id != target_finding_id", name="check_sec_rel_no_self_loop"),
    )
