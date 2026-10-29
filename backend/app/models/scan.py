import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, BigInteger, DateTime, ForeignKey, CheckConstraint, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from app.db.base import Base, TimestampMixin


class Scan(Base, TimestampMixin):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="queued", nullable=False, index=True)
    triggered_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    phases_completed: Mapped[List[str]] = mapped_column(ARRAY(String).with_variant(JSON, "sqlite"), default=list, nullable=False)
    current_phase: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scan_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    summary: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (
        CheckConstraint("scan_type IN ('full', 'recon', 'code', 'dependency', 'targeted')", name="check_scan_type"),
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'partial')", name="check_scan_status"),
    )


class ScanEvent(Base):
    __tablename__ = "scan_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=True, index=True)
    team_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("security_team_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    provider: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    input_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, default="QUEUED", nullable=False)
    input_reference: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    input_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    output_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    tokens_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    team_run: Mapped[Optional["SecurityTeamRun"]] = relationship("SecurityTeamRun", back_populates="agent_runs")

    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'BLOCKED', 'pending', 'running', 'completed', 'failed', 'timeout')",
            name="check_agent_status",
        ),
    )
