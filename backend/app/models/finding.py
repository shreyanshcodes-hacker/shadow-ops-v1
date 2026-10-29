import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, CheckConstraint, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from app.db.base import Base, TimestampMixin


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_rule_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String, default="medium", nullable=False)
    cwe_ids: Mapped[List[str]] = mapped_column(ARRAY(String).with_variant(JSON, "sqlite"), default=list, nullable=False)
    cve_ids: Mapped[List[str]] = mapped_column(ARRAY(String).with_variant(JSON, "sqlite"), default=list, nullable=False)
    owasp_categories: Mapped[List[str]] = mapped_column(ARRAY(String).with_variant(JSON, "sqlite"), default=list, nullable=False)
    location: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    code_snippet: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    remediation_guidance: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False, index=True)
    triaged_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    triaged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True, index=True)
    risk_factors: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    fixed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    evidence: Mapped[List["FindingEvidence"]] = relationship("FindingEvidence", back_populates="finding", cascade="all, delete-orphan")
    risk_assessment: Mapped[Optional["RiskAssessment"]] = relationship("RiskAssessment", back_populates="finding", uselist=False, cascade="all, delete-orphan")
    ai_analyses: Mapped[List["FindingAIAnalysis"]] = relationship(
        "FindingAIAnalysis",
        back_populates="finding",
        cascade="all, delete-orphan",
        order_by="desc(FindingAIAnalysis.created_at)",
    )
    outgoing_relationships: Mapped[List["SecurityRelationship"]] = relationship(
        "SecurityRelationship",
        primaryjoin="Finding.id==SecurityRelationship.source_finding_id",
        back_populates="source_finding",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[List["SecurityRelationship"]] = relationship(
        "SecurityRelationship",
        primaryjoin="Finding.id==SecurityRelationship.target_finding_id",
        back_populates="target_finding",
        cascade="all, delete-orphan",
    )

    @property
    def latest_ai_analysis(self) -> Optional["FindingAIAnalysis"]:
        return self.ai_analyses[0] if self.ai_analyses else None

    __table_args__ = (
        CheckConstraint("source IN ('semgrep', 'recon', 'dependency', 'ai_analysis', 'manual')", name="check_finding_source"),
        CheckConstraint("severity IN ('critical', 'high', 'medium', 'low', 'info')", name="check_finding_severity"),
        CheckConstraint("confidence IN ('low', 'medium', 'high')", name="check_finding_confidence"),
        CheckConstraint("status IN ('open', 'triaged', 'in_progress', 'fixed', 'false_positive', 'wont_fix', 'risk_accepted')", name="check_finding_status"),
    )


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_object_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    finding: Mapped["Finding"] = relationship("Finding", back_populates="evidence")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), unique=True, nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    base_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    exploitability: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    exposure: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    asset_criticality: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    attack_path_impact: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    final_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, index=True)
    factors: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    formula_version: Mapped[str] = mapped_column(String, nullable=False, default="v1.0")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    calculated_by: Mapped[str] = mapped_column(String, nullable=False, default="risk_engine_v1")

    finding: Mapped["Finding"] = relationship("Finding", back_populates="risk_assessment")


class FindingAIAnalysis(Base, TimestampMixin):
    __tablename__ = "finding_ai_analysis"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    ai_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, default="SUCCEEDED", nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    technical_explanation: Mapped[str] = mapped_column(String, nullable=False)
    impact: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    classification: Mapped[str] = mapped_column(String, nullable=False)
    uncertainty: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    vulnerability_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    severity_assessment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    exploitability_assessment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    impact_assessment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    affected_component: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    attack_preconditions: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evidence_interpretation: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    reasoning: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    recommended_next_steps: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_analysis: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    supporting_evidence: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    input_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tokens_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)

    finding: Mapped["Finding"] = relationship("Finding", back_populates="ai_analyses")

