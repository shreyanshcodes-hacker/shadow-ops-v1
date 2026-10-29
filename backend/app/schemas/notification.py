from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class SecurityEventType(str, Enum):
    # Scans
    SCAN_COMPLETED = "scan.completed"
    SCAN_FAILED = "scan.failed"
    
    # Findings
    FINDING_CREATED = "finding.created"
    FINDING_SEVERITY_CHANGED = "finding.severity_changed"
    
    # Risk & Attack Paths
    ATTACK_PATH_DETECTED = "attack_path.detected"
    RISK_CRITICAL_THRESHOLD = "risk.critical_threshold"
    
    # AI Security Team
    SECURITY_TEAM_COMPLETED = "security_team.completed"
    SECURITY_TEAM_FAILED = "security_team.failed"
    
    # Remediation
    REMEDIATION_PROPOSED = "remediation.proposed"
    REMEDIATION_APPROVAL_REQUIRED = "remediation.approval_required"
    REMEDIATION_APPLIED = "remediation.applied"
    REMEDIATION_ROLLED_BACK = "remediation.rolled_back"
    
    # Verification
    VERIFICATION_COMPLETED = "verification.completed"
    VERIFICATION_REGRESSION_DETECTED = "verification.regression_detected"
    VERIFICATION_HUMAN_REVIEW_REQUIRED = "verification.human_review_required"
    
    # Reports
    REPORT_READY = "report.ready"
    REPORT_EXPORT_FAILED = "report.export_failed"


class NotificationCategory(str, Enum):
    SCANS = "scans"
    FINDINGS = "findings"
    REMEDIATION = "remediation"
    VERIFICATION = "verification"
    REPORTS = "reports"
    RISK = "risk"
    GENERAL = "general"


class SecurityEventEnvelope(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    workspace_id: UUID
    actor_id: Optional[UUID] = None
    correlation_id: UUID = Field(default_factory=uuid4)
    resource_type: str
    resource_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None

    @field_validator("payload")
    @classmethod
    def sanitize_payload(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Never allow raw secrets, keys, or credentials in event envelopes."""
        forbidden_keys = {"password", "token", "secret", "api_key", "authorization", "private_key"}
        sanitized = {}
        for k, val in v.items():
            if any(forbidden in k.lower() for forbidden in forbidden_keys):
                sanitized[k] = "[REDACTED]"
            elif isinstance(val, dict):
                sanitized[k] = cls.sanitize_payload(val)
            else:
                sanitized[k] = val
        return sanitized


class EventOutboxResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    event_type: str
    event_version: str
    actor_id: Optional[UUID] = None
    resource_type: str
    resource_id: Optional[UUID] = None
    correlation_id: UUID
    idempotency_key: Optional[str] = None
    payload: Dict[str, Any]
    status: str
    attempts: int
    max_attempts: int
    next_retry_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    event_id: Optional[UUID] = None
    category: str
    type: str
    title: str
    message: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    link_url: Optional[str] = None
    channels: List[str]
    read_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationPreferenceUpdate(BaseModel):
    categories: Optional[Dict[str, bool]] = None
    channels: Optional[Dict[str, bool]] = None
    min_severity: Optional[str] = None


class NotificationPreferenceResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    categories: Dict[str, bool]
    channels: Dict[str, bool]
    min_severity: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationRuleCreate(BaseModel):
    name: str
    event_type: str
    enabled: bool = True
    channels: List[str] = ["in_app"]
    recipient_roles: List[str] = ["OWNER", "ADMIN", "ANALYST"]
    severity_filter: List[str] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    dedup_window_minutes: int = 10
    rate_limit_per_hour: int = 60


class NotificationRuleUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    channels: Optional[List[str]] = None
    recipient_roles: Optional[List[str]] = None
    severity_filter: Optional[List[str]] = None
    dedup_window_minutes: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None


class NotificationRuleResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    event_type: str
    enabled: bool
    channels: List[str]
    recipient_roles: List[str]
    severity_filter: List[str]
    dedup_window_minutes: int
    rate_limit_per_hour: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    workflow_name: str
    trigger_event_id: Optional[UUID] = None
    action_name: str
    status: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    idempotency_key: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkflowRunListResponse(BaseModel):
    items: List[WorkflowRunResponse]
    total: int


class WorkflowRetryRequest(BaseModel):
    run_id: UUID
