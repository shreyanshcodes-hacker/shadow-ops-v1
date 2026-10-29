import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from app.db.base import Base, TimestampMixin


class SecurityTeamRun(Base, TimestampMixin):
    __tablename__ = "security_team_runs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, default="QUEUED", nullable=False, index=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False)
    orchestration_version: Mapped[str] = mapped_column(String, default="security-team-v1", nullable=False)
    team_summary: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    agent_runs: Mapped[List["AgentRun"]] = relationship("AgentRun", back_populates="team_run", cascade="all, delete-orphan", order_by="AgentRun.created_at")
    asset: Mapped["Asset"] = relationship("Asset")
    scan: Mapped[Optional["Scan"]] = relationship("Scan")
    requester: Mapped["Profile"] = relationship("Profile", foreign_keys=[requested_by])
    reviewer: Mapped[Optional["Profile"]] = relationship("Profile", foreign_keys=[reviewed_by])

    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'PARTIAL', 'SUCCEEDED', 'FAILED', 'CANCELED')",
            name="check_security_team_run_status",
        ),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="check_security_team_run_confidence"),
    )
