from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class RemediationStatus(str, Enum):
    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    PROPOSED = "PROPOSED"
    VALIDATING = "VALIDATING"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class ApplicationStatus(str, Enum):
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class VerificationStatus(str, Enum):
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


# Strict structured output schema from AI Remediation Engine
class AIRemediationProposalOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    proposal_title: str = Field(..., min_length=5, max_length=200)
    vulnerability_addressed: str = Field(..., min_length=3)
    root_cause_explanation: str = Field(..., min_length=10)
    proposed_solution: str = Field(..., min_length=10)
    affected_file_paths: List[str] = Field(..., min_length=1)
    unified_diff: str = Field(..., min_length=10)
    expected_security_benefit: str = Field(..., min_length=5)
    possible_compatibility_risks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    suggested_tests: List[str] = Field(default_factory=list)


# API Schemas
class RemediationProposalCreateRequest(BaseModel):
    custom_guidance: Optional[str] = Field(None, max_length=1000)
    model_preference: Optional[str] = None


class RemediationValidationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    proposal_id: UUID
    check_name: str
    status: ValidationStatus
    duration_ms: int
    output_summary: str
    error_details: Optional[str] = None
    executed_at: datetime


class RemediationApprovalRequest(BaseModel):
    patch_hash: str = Field(..., description="SHA-256 hash of the canonical unified diff reviewed by the human")
    justification: Optional[str] = Field(None, max_length=2000)


class RemediationApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    proposal_id: UUID
    approved_by: UUID
    decision: str
    patch_hash: str
    proposal_version: int
    justification: Optional[str] = None
    validation_snapshot: Dict[str, Any]
    approved_at: datetime


class RemediationRejectRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=2000)


class RemediationApplyRequest(BaseModel):
    patch_hash: str = Field(..., description="SHA-256 hash of the patch to apply (must match approved hash)")
    target_revision: Optional[str] = None


class RemediationRollbackRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=2000)


class RemediationApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    proposal_id: UUID
    workspace_id: UUID
    applied_by: UUID
    checkpoint_id: Optional[UUID] = None
    status: ApplicationStatus
    patch_hash: str
    applied_diff: str
    changed_files: List[str]
    target_revision: Optional[str] = None
    verification_status: VerificationStatus
    applied_at: datetime
    rolled_back_at: Optional[datetime] = None
    error_message: Optional[str] = None


class RemediationProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    asset_id: Optional[UUID] = None
    finding_id: UUID
    source_scan_id: Optional[UUID] = None
    proposed_by: str
    created_by: Optional[UUID] = None
    model_used: Optional[str] = None

    proposal_title: str
    problem_summary: str
    proposed_solution: str
    rationale: str

    affected_files: List[str]
    unified_diff: str
    patch_hash: str

    risk_assessment: Dict[str, Any]
    suggested_tests: List[str]
    target_base_revision: Optional[str] = None
    validation_results: Dict[str, Any]

    status: RemediationStatus
    version: int
    failure_reason: Optional[str] = None

    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    applied_by: Optional[UUID] = None
    applied_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    validations: List[RemediationValidationResponse] = Field(default_factory=list)
    approvals: List[RemediationApprovalResponse] = Field(default_factory=list)
    applications: List[RemediationApplicationResponse] = Field(default_factory=list)


class RemediationListResponse(BaseModel):
    items: List[RemediationProposalResponse]
    total: int
