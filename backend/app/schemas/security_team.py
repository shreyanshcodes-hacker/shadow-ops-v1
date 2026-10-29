import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class TeamRunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PARTIAL = "PARTIAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class AgentStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


# ==============================================================================
# Typed Agent Contract
# ==============================================================================

class AgentRequest(BaseModel):
    run_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    team_run_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    workspace_id: uuid.UUID
    agent_name: str
    scope: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    task: str = "Execute specialized analytical assessment."
    constraints: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    agent_name: str
    status: AgentStatus
    summary: str
    structured_output: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    uncertainty: str = ""
    evidence_references: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    duration_ms: Optional[int] = None
    provider: str = "unknown"
    model: str = "unknown"
    prompt_version: str = "v1"
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# ==============================================================================
# Agent-Specific Structured Output Schemas
# ==============================================================================

class ReconOutput(BaseModel):
    relevant_components: List[str] = Field(default_factory=list)
    entry_points: List[str] = Field(default_factory=list)
    security_boundaries: List[str] = Field(default_factory=list)
    exposed_areas: List[str] = Field(default_factory=list)
    uncertainty: str = ""
    observations: List[str] = Field(default_factory=list)


class VulnerabilityItemAnalysis(BaseModel):
    finding_id: str
    vulnerability_interpretation: str
    preconditions: str
    potential_impact: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    missing_evidence: List[str] = Field(default_factory=list)
    recommended_investigation: str


class VulnerabilityAnalystOutput(BaseModel):
    findings_analyzed: int = 0
    interpretations: List[VulnerabilityItemAnalysis] = Field(default_factory=list)
    uncertainty: str = ""


class AttackPathAnalystOutput(BaseModel):
    candidate_relationships: List[Dict[str, Any]] = Field(default_factory=list)
    path_observations: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    missing_evidence: List[str] = Field(default_factory=list)
    explanation: str = ""
    uncertainty: str = ""


class RiskAnalystOutput(BaseModel):
    deterministic_score_reference: float = 0.0
    risk_band: str = "INFORMATIONAL"
    explanation: str = ""
    important_contributing_factors: List[str] = Field(default_factory=list)
    uncertainty: str = ""
    recommended_human_review_priorities: List[str] = Field(default_factory=list)


class TeamAssessment(BaseModel):
    review_status: str = "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED"
    executive_summary: str
    key_security_concerns: List[str] = Field(default_factory=list)
    highest_priority_findings: List[str] = Field(default_factory=list)
    highest_priority_attack_paths: List[str] = Field(default_factory=list)
    risk_interpretation: str = ""
    uncertainties: List[str] = Field(default_factory=list)
    conflicting_assessments: List[str] = Field(default_factory=list)
    recommended_human_actions: List[str] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    evidence_references: List[str] = Field(default_factory=list)


# ==============================================================================
# API Request & Response Schemas
# ==============================================================================

class CreateTeamRunRequest(BaseModel):
    workspace_id: uuid.UUID
    asset_id: uuid.UUID
    scan_id: Optional[uuid.UUID] = None
    orchestration_version: str = "security-team-v1"


class HumanReviewRequest(BaseModel):
    notes: Optional[str] = None


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_run_id: Optional[uuid.UUID] = None
    agent_name: str
    status: str
    provider: Optional[str] = None
    model_used: Optional[str] = None
    prompt_version: Optional[str] = None
    confidence: float = 0.0
    attempt: int = 1
    input_reference: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class SecurityTeamRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    asset_id: uuid.UUID
    scan_id: Optional[uuid.UUID] = None
    status: TeamRunStatus
    requested_by: uuid.UUID
    orchestration_version: str
    team_summary: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SecurityTeamRunDetailRead(SecurityTeamRunRead):
    agent_runs: List[AgentRunRead] = Field(default_factory=list)
    assessment: Optional[TeamAssessment] = None
