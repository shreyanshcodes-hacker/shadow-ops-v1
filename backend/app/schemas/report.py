import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ReportType(str, Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    TECHNICAL_VULNERABILITY = "technical_vulnerability"
    REMEDIATION_PROGRESS = "remediation_progress"
    VERIFICATION_REGRESSION = "verification_regression"
    ASSET_SECURITY_POSTURE = "asset_security_posture"


class ReportFormat(str, Enum):
    JSON = "json"
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"


class ReportStatus(str, Enum):
    GENERATING = "generating"
    COMPLETED = "completed"
    READY = "ready"
    FAILED = "failed"


# Dashboard Schemas
class AssetMetrics(BaseModel):
    total: int = 0
    authorized: int = 0
    unauthorized: int = 0
    by_criticality: Dict[str, int] = Field(default_factory=dict)


class ScanMetrics(BaseModel):
    total: int = 0
    completed: int = 0
    failed: int = 0
    running: int = 0
    latest_scan_at: Optional[datetime] = None


class FindingMetrics(BaseModel):
    total: int = 0
    open: int = 0
    fixed: int = 0
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)


class RiskMetrics(BaseModel):
    current_score: Optional[float] = None
    risk_band: Optional[str] = None
    formula_version: str = "risk-v1"
    is_calculated: bool = False
    critical_attack_paths_count: int = 0


class RemediationMetrics(BaseModel):
    total_proposals: int = 0
    awaiting_approval: int = 0
    approved: int = 0
    applied: int = 0
    rejected: int = 0


class VerificationMetrics(BaseModel):
    total_jobs: int = 0
    verified_candidates: int = 0
    human_accepted: int = 0
    failed_or_blocked: int = 0
    latest_verification_at: Optional[datetime] = None


class DashboardMetricsResponse(BaseModel):
    workspace_id: uuid.UUID
    generated_at: datetime
    has_completed_scans: bool
    data_disclaimer: str
    assets: AssetMetrics
    scans: ScanMetrics
    findings: FindingMetrics
    risk: RiskMetrics
    remediations: RemediationMetrics
    verifications: VerificationMetrics
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)


class FindingTrendPoint(BaseModel):
    date: str
    new_findings: int = 0
    fixed_findings: int = 0
    open_findings: int = 0


class RiskTrendPoint(BaseModel):
    date: str
    score: float
    band: str


class RemediationTrendPoint(BaseModel):
    date: str
    proposed: int = 0
    approved: int = 0
    applied: int = 0


class DashboardTrendsResponse(BaseModel):
    workspace_id: uuid.UUID
    trend_window_days: int
    data_available: bool
    message: Optional[str] = None
    findings_trend: List[FindingTrendPoint] = Field(default_factory=list)
    risk_score_trend: List[RiskTrendPoint] = Field(default_factory=list)
    remediation_trend: List[RemediationTrendPoint] = Field(default_factory=list)


# Report Generation Schemas
class ReportCreateRequest(BaseModel):
    report_type: ReportType
    title: Optional[str] = None
    description: Optional[str] = None
    format: ReportFormat = ReportFormat.JSON
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    asset_ids: Optional[List[uuid.UUID]] = None
    severities: Optional[List[str]] = None
    include_ai_summary: bool = True


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    scan_id: Optional[uuid.UUID] = None
    report_type: str
    title: str
    description: Optional[str] = None
    format: str
    status: str
    generated_by: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    data_cutoff_at: datetime
    schema_version: str = "report-v1"
    completeness_status: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    snapshot_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ReportListResponse(BaseModel):
    items: List[ReportResponse]
    total: int


class ReportExportResponse(BaseModel):
    report_id: uuid.UUID
    format: str
    file_name: str
    content_type: str
    download_url: Optional[str] = None
    data_cutoff_at: datetime
