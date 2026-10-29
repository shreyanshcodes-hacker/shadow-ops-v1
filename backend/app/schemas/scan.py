from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from app.scanning.models import ScanStatus, ScanProfile


class ScanCreateRequest(BaseModel):
    asset_id: UUID
    scan_profile: ScanProfile = ScanProfile.CODE_SECURITY


class ScanEventResponse(BaseModel):
    id: int
    scan_id: UUID
    workspace_id: UUID
    event_type: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ScanSummaryResponse(BaseModel):
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class ScanResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    asset_id: UUID
    scan_type: str
    scan_profile: str
    status: str
    triggered_by: UUID
    triggered_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    progress_percent: int = 0
    error_message: Optional[str] = None
    summary: ScanSummaryResponse = Field(default_factory=ScanSummaryResponse)
    created_at: datetime
    updated_at: datetime


class FindingEvidenceResponse(BaseModel):
    id: UUID
    finding_id: UUID
    evidence_type: str
    title: str
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    created_at: datetime


class FindingResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    scan_id: UUID
    asset_id: UUID
    source: str
    source_rule_id: Optional[str] = None
    title: str
    description: str
    severity: str
    confidence: str
    cwe_ids: List[str] = Field(default_factory=list)
    owasp_categories: List[str] = Field(default_factory=list)
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: Optional[str] = None
    status: str
    created_at: datetime
