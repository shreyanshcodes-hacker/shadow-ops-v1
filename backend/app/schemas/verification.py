import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class VerificationJobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    BASELINE_CHECK = "BASELINE_CHECK"
    RESCANNING = "RESCANNING"
    REGRESSION_CHECK = "REGRESSION_CHECK"
    COMPARING_EVIDENCE = "COMPARING_EVIDENCE"
    PASSED_PENDING_REVIEW = "PASSED_PENDING_REVIEW"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    BLOCKED = "BLOCKED"
    CANCELED = "CANCELED"


class VulnerabilityVerificationStatus(str, Enum):
    STILL_PRESENT = "STILL_PRESENT"
    NO_LONGER_DETECTED = "NO_LONGER_DETECTED"
    MODIFIED_OR_MOVED = "MODIFIED_OR_MOVED"
    POSSIBLE_REGRESSION = "POSSIBLE_REGRESSION"
    NEW_FINDING = "NEW_FINDING"
    UNCOMPARABLE = "UNCOMPARABLE"


class RegressionCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class ScannerVerificationStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    TIMEOUT = "TIMEOUT"
    SCANNER_UNAVAILABLE = "SCANNER_UNAVAILABLE"


class VerificationPolicyVerdict(str, Enum):
    VERIFIED_CANDIDATE = "VERIFIED_CANDIDATE"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    BLOCKED = "BLOCKED"


class VerificationReviewDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


# Request Schemas
class VerificationTriggerRequest(BaseModel):
    proposal_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    check_types: Optional[List[str]] = Field(
        default_factory=lambda: ["syntax", "ast_integrity", "rescan", "test_suite"]
    )


class VerificationReviewRequest(BaseModel):
    decision: VerificationReviewDecision
    rationale: str = Field(..., min_length=5, max_length=2000)


# Response Schemas
class VerificationComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    workspace_id: uuid.UUID
    finding_id: uuid.UUID
    comparison_category: str
    rule_id: str
    file_path: str
    baseline_evidence: Dict[str, Any] = Field(default_factory=dict)
    rescan_evidence: Dict[str, Any] = Field(default_factory=dict)
    line_shift: int = 0
    similarity_score: float = 0.0
    explanation: str = ""
    created_at: datetime


class VerificationRegressionCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    workspace_id: uuid.UUID
    check_name: str
    status: str
    duration_ms: int = 0
    output_summary: str = ""
    error_details: Optional[str] = None
    created_at: datetime


class VerificationReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    workspace_id: uuid.UUID
    finding_id: uuid.UUID
    reviewer_id: uuid.UUID
    decision: str
    rationale: str
    finding_status_after: str
    reviewed_at: datetime


class VerificationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    asset_id: uuid.UUID
    finding_id: uuid.UUID
    proposal_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    rescan_id: Optional[uuid.UUID] = None
    status: str
    vulnerability_status: str
    regression_status: str
    scanner_status: str
    test_status: str
    policy_verdict: str
    policy_version: str = "verification-policy-v1"
    policy_reasons: List[str] = Field(default_factory=list)
    baseline_snapshot: Dict[str, Any] = Field(default_factory=dict)
    source_revision: Optional[str] = None
    target_revision: Optional[str] = None
    patch_hash: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    comparisons: Optional[List[VerificationComparisonResponse]] = None
    regression_checks: Optional[List[VerificationRegressionCheckResponse]] = None
    reviews: Optional[List[VerificationReviewResponse]] = None


class VerificationListResponse(BaseModel):
    items: List[VerificationJobResponse]
    total: int
