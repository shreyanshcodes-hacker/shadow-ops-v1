import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from app.db.base import Base, TimestampMixin


class VerificationJob(Base, TimestampMixin):
    __tablename__ = "verification_jobs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("remediation_proposals.id", ondelete="SET NULL"), nullable=True, index=True)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("remediation_applications.id", ondelete="SET NULL"), nullable=True, index=True)
    rescan_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(String, default="QUEUED", nullable=False, index=True)
    vulnerability_status: Mapped[str] = mapped_column(String, default="UNCOMPARABLE", nullable=False)
    regression_status: Mapped[str] = mapped_column(String, default="SKIPPED", nullable=False)
    scanner_status: Mapped[str] = mapped_column(String, default="COMPLETED", nullable=False)
    test_status: Mapped[str] = mapped_column(String, default="SKIPPED", nullable=False)
    policy_verdict: Mapped[str] = mapped_column(String, default="INCONCLUSIVE", nullable=False, index=True)

    policy_version: Mapped[str] = mapped_column(String, default="verification-policy-v1", nullable=False)
    policy_reasons: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    baseline_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    source_revision: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    target_revision: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    patch_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    asset: Mapped["Asset"] = relationship("Asset")
    finding: Mapped["Finding"] = relationship("Finding")
    proposal: Mapped[Optional["RemediationProposal"]] = relationship("RemediationProposal")
    application: Mapped[Optional["RemediationApplication"]] = relationship("RemediationApplication")
    rescan: Mapped[Optional["Scan"]] = relationship("Scan")

    comparisons: Mapped[List["VerificationComparison"]] = relationship(
        "VerificationComparison", back_populates="job", cascade="all, delete-orphan"
    )
    regression_checks: Mapped[List["VerificationRegressionCheck"]] = relationship(
        "VerificationRegressionCheck", back_populates="job", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["VerificationReview"]] = relationship(
        "VerificationReview", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'BASELINE_CHECK', 'RESCANNING', "
            "'REGRESSION_CHECK', 'COMPARING_EVIDENCE', 'PASSED_PENDING_REVIEW', "
            "'FAILED', 'INCONCLUSIVE', 'BLOCKED', 'CANCELED')",
            name="check_verification_job_status",
        ),
        CheckConstraint(
            "vulnerability_status IN ('STILL_PRESENT', 'NO_LONGER_DETECTED', "
            "'MODIFIED_OR_MOVED', 'POSSIBLE_REGRESSION', 'NEW_FINDING', 'UNCOMPARABLE')",
            name="check_vulnerability_status",
        ),
        CheckConstraint(
            "regression_status IN ('PASS', 'FAIL', 'SKIPPED', 'BLOCKED', 'ERROR')",
            name="check_regression_status",
        ),
        CheckConstraint(
            "scanner_status IN ('COMPLETED', 'FAILED', 'BLOCKED', 'TIMEOUT', 'SCANNER_UNAVAILABLE')",
            name="check_scanner_status",
        ),
        CheckConstraint(
            "test_status IN ('PASS', 'FAIL', 'SKIPPED', 'BLOCKED', 'ERROR')",
            name="check_test_status",
        ),
        CheckConstraint(
            "policy_verdict IN ('VERIFIED_CANDIDATE', 'FAILED', 'INCONCLUSIVE', 'BLOCKED')",
            name="check_policy_verdict",
        ),
    )


class VerificationComparison(Base):
    __tablename__ = "verification_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("verification_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)

    comparison_category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    baseline_evidence: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    rescan_evidence: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    line_shift: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanation: Mapped[str] = mapped_column(String, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    job: Mapped["VerificationJob"] = relationship("VerificationJob", back_populates="comparisons")
    finding: Mapped["Finding"] = relationship("Finding")

    __table_args__ = (
        CheckConstraint(
            "comparison_category IN ('STILL_PRESENT', 'NO_LONGER_DETECTED', "
            "'MODIFIED_OR_MOVED', 'POSSIBLE_REGRESSION', 'NEW_FINDING', 'UNCOMPARABLE')",
            name="check_comparison_category",
        ),
    )


class VerificationRegressionCheck(Base):
    __tablename__ = "verification_regression_checks"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("verification_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    check_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_summary: Mapped[str] = mapped_column(String, default="", nullable=False)
    error_details: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    job: Mapped["VerificationJob"] = relationship("VerificationJob", back_populates="regression_checks")

    __table_args__ = (
        CheckConstraint(
            "status IN ('PASS', 'FAIL', 'SKIPPED', 'BLOCKED', 'ERROR')",
            name="check_regression_check_status",
        ),
    )


class VerificationReview(Base):
    __tablename__ = "verification_reviews"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("verification_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    rationale: Mapped[str] = mapped_column(String, default="", nullable=False)
    finding_status_after: Mapped[str] = mapped_column(String, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    job: Mapped["VerificationJob"] = relationship("VerificationJob", back_populates="reviews")
    reviewer: Mapped["Profile"] = relationship("Profile")
    finding: Mapped["Finding"] = relationship("Finding")

    __table_args__ = (
        CheckConstraint("decision IN ('accepted', 'rejected')", name="check_verif_review_decision"),
    )
