import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True)
    report_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    format: Mapped[str] = mapped_column(String, default="json", nullable=False)
    status: Mapped[str] = mapped_column(String, default="generating", nullable=False)
    storage_object_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    generated_by: Mapped[str] = mapped_column(String, nullable=False)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    data_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, default="report-v1", nullable=False)
    completeness_status: Mapped[str] = mapped_column(String, default="COMPLETE", nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    snapshot_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    scan: Mapped[Optional["Scan"]] = relationship("Scan")

    __table_args__ = (
        CheckConstraint(
            "report_type IN ("
            "'executive_summary', 'technical_vulnerability', "
            "'remediation_progress', 'verification_regression', "
            "'asset_security_posture', 'executive', 'technical', "
            "'scan', 'compliance', 'custom')",
            name="check_report_type",
        ),
        CheckConstraint(
            "format IN ('pdf', 'html', 'json', 'markdown')",
            name="check_report_format",
        ),
        CheckConstraint(
            "status IN ('generating', 'completed', 'ready', 'failed')",
            name="check_report_status",
        ),
    )
