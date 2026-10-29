import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from app.db.base import Base, TimestampMixin


class RemediationProposal(Base, TimestampMixin):
    __tablename__ = "remediation_proposals"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True)
    finding_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    source_scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True)
    
    proposed_by: Mapped[str] = mapped_column(String, default="ai_security_team", nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    proposal_title: Mapped[str] = mapped_column(String, nullable=False)
    problem_summary: Mapped[str] = mapped_column(String, default="", nullable=False)
    proposed_solution: Mapped[str] = mapped_column(String, default="", nullable=False)
    rationale: Mapped[str] = mapped_column(String, default="", nullable=False)
    
    # Backward compatibility with earlier schemas
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="", nullable=False)
    fix_type: Mapped[str] = mapped_column(String, default="code_change", nullable=False)
    
    affected_files: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    patch_reference: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    unified_diff: Mapped[str] = mapped_column(String, default="", nullable=False)
    patch_hash: Mapped[str] = mapped_column(String, default="", nullable=False, index=True)
    
    risk_assessment: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    suggested_tests: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    target_base_revision: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    validation_results: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Status lifecycle
    status: Mapped[str] = mapped_column(String, default="PROPOSED", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Approvals & Application audit
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    finding: Mapped["Finding"] = relationship("Finding")
    asset: Mapped[Optional["Asset"]] = relationship("Asset")
    scan: Mapped[Optional["Scan"]] = relationship("Scan")
    creator: Mapped[Optional["Profile"]] = relationship("Profile", foreign_keys=[created_by])
    approver: Mapped[Optional["Profile"]] = relationship("Profile", foreign_keys=[approved_by])
    applier: Mapped[Optional["Profile"]] = relationship("Profile", foreign_keys=[applied_by])

    validations: Mapped[List["RemediationValidation"]] = relationship("RemediationValidation", back_populates="proposal", cascade="all, delete-orphan")
    approvals: Mapped[List["RemediationApproval"]] = relationship("RemediationApproval", back_populates="proposal", cascade="all, delete-orphan")
    checkpoints: Mapped[List["RemediationCheckpoint"]] = relationship("RemediationCheckpoint", back_populates="proposal", cascade="all, delete-orphan")
    applications: Mapped[List["RemediationApplication"]] = relationship("RemediationApplication", back_populates="proposal", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'GENERATING', 'PROPOSED', 'VALIDATING', 'VALIDATION_FAILED', "
            "'AWAITING_APPROVAL', 'APPROVED', 'APPLYING', 'APPLIED', 'REJECTED', 'EXPIRED', "
            "'ROLLED_BACK', 'FAILED', 'proposed', 'approved', 'rejected', 'applied', 'superseded')",
            name="check_proposal_status"
        ),
    )


class RemediationValidation(Base):
    __tablename__ = "remediation_validations"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("remediation_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    check_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_summary: Mapped[str] = mapped_column(String, default="", nullable=False)
    error_details: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    proposal: Mapped["RemediationProposal"] = relationship("RemediationProposal", back_populates="validations")

    __table_args__ = (
        CheckConstraint("status IN ('PASS', 'FAIL', 'BLOCKED', 'SKIPPED')", name="check_val_status"),
    )


class RemediationApproval(Base):
    __tablename__ = "remediation_approvals"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("remediation_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    approved_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    patch_hash: Mapped[str] = mapped_column(String, default="", nullable=False)
    proposal_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    justification: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    conditions: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    validation_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    proposal: Mapped["RemediationProposal"] = relationship("RemediationProposal", back_populates="approvals")
    approver: Mapped["Profile"] = relationship("Profile", foreign_keys=[approved_by])

    __table_args__ = (
        CheckConstraint("decision IN ('approved', 'rejected')", name="check_approval_decision"),
    )


class RemediationCheckpoint(Base):
    __tablename__ = "remediation_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("remediation_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    checkpoint_type: Mapped[str] = mapped_column(String, default="file_snapshot", nullable=False)
    base_revision: Mapped[str] = mapped_column(String, default="HEAD", nullable=False)
    snapshot_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    proposal: Mapped["RemediationProposal"] = relationship("RemediationProposal", back_populates="checkpoints")


class RemediationApplication(Base):
    __tablename__ = "remediation_applications"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("remediation_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    applied_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False)
    checkpoint_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("remediation_checkpoints.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="APPLIED", nullable=False, index=True)
    patch_hash: Mapped[str] = mapped_column(String, nullable=False)
    applied_diff: Mapped[str] = mapped_column(String, nullable=False)
    changed_files: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    target_revision: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    verification_status: Mapped[str] = mapped_column(String, default="VERIFICATION_PENDING", nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    rolled_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    proposal: Mapped["RemediationProposal"] = relationship("RemediationProposal", back_populates="applications")
    checkpoint: Mapped[Optional["RemediationCheckpoint"]] = relationship("RemediationCheckpoint")
    applier: Mapped["Profile"] = relationship("Profile", foreign_keys=[applied_by])

    __table_args__ = (
        CheckConstraint("status IN ('APPLYING', 'APPLIED', 'FAILED', 'ROLLED_BACK')", name="check_app_status"),
        CheckConstraint("verification_status IN ('VERIFICATION_PENDING', 'VERIFYING', 'VERIFIED', 'FAILED')", name="check_app_verif_status"),
    )


class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("remediation_proposals.id", ondelete="SET NULL"), nullable=True, index=True)
    scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)
    verification_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    evidence_refs: Mapped[List[uuid.UUID]] = mapped_column(JSONB, default=list, nullable=False)
    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("verification_type IN ('reproduction_test', 'semgrep_rescan', 'dependency_check', 'config_audit', 'regression_test')", name="check_verif_type"),
        CheckConstraint("status IN ('pending', 'running', 'passed', 'failed', 'inconclusive')", name="check_verif_status"),
    )
