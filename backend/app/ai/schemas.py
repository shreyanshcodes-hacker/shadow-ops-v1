import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SupportingEvidenceItem(BaseModel):
    evidence_id: str = Field(description="UUID of the trusted finding evidence item referenced")
    relevance: str = Field(description="Explanation of why this evidence supports the finding")
    quote_or_reference: Optional[str] = Field(default=None, description="Exact relevant excerpt or line number reference")


class EvidenceInterpretation(BaseModel):
    observed: List[str] = Field(
        default_factory=list,
        description="Directly observed facts from scanner rule match, file path, line numbers, and AST snippet"
    )
    inferred: List[str] = Field(
        default_factory=list,
        description="Logical deductions regarding how this code pattern could be triggered or manipulated"
    )
    uncertain: List[str] = Field(
        default_factory=list,
        description="Uncertainties, missing context, or assumptions that require human or dynamic verification"
    )


class SecurityAnalysis(BaseModel):
    summary: str = Field(description="Executive summary of the detected security weakness")
    vulnerability_type: str = Field(description="Normalized vulnerability type (e.g., SQL Injection, Hardcoded Secret, Insecure Deserialization)")
    severity_assessment: str = Field(description="Advisory severity assessment (critical, high, medium, low, info)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0 reflecting certainty in the assessment")
    exploitability_assessment: str = Field(description="Technical evaluation of ease of exploitability and accessibility")
    impact_assessment: str = Field(description="Assessment of potential impact on data confidentiality, integrity, availability, or business systems")
    affected_component: str = Field(description="Identified affected file, module, endpoint, or logical component")
    attack_preconditions: str = Field(description="Preconditions required for an attacker to exploit this issue")
    evidence_interpretation: EvidenceInterpretation = Field(description="Structured breakdown into observed, inferred, and uncertain aspects")
    reasoning: str = Field(description="Step-by-step analytical reasoning connecting scanner evidence to the security conclusion")
    recommended_next_steps: str = Field(description="Actionable guidance for a human security reviewer to investigate and verify")
    uncertainty: str = Field(description="Summary of primary uncertainties or limits of this static analysis")
    supporting_evidence: List[SupportingEvidenceItem] = Field(
        default_factory=list,
        description="Verified references to provided scanner evidence IDs"
    )


# Stage 4 Compatibility Model
class FindingAnalysisOutput(BaseModel):
    summary: str = Field(description="Concise executive summary of the vulnerability")
    technical_explanation: str = Field(description="In-depth technical explanation of the vulnerability mechanism and root cause")
    impact: str = Field(description="Potential impact on data confidentiality, integrity, availability, or business operations")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0 reflecting certainty in the finding")
    classification: str = Field(description="Security category classification (e.g., OWASP category, CWE family, or weakness type)")
    uncertainty: Optional[str] = Field(default=None, description="Known uncertainties, assumptions, or missing context")
    supporting_evidence: List[SupportingEvidenceItem] = Field(
        default_factory=list,
        description="List of verified evidence items directly supporting this analysis"
    )


# API Schemas
class FindingAIAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    ai_run_id: Optional[uuid.UUID] = None
    workspace_id: uuid.UUID
    status: str = "SUCCEEDED"
    summary: str
    technical_explanation: str
    impact: str
    confidence: float
    classification: str
    uncertainty: Optional[str] = None
    vulnerability_type: Optional[str] = None
    severity_assessment: Optional[str] = None
    exploitability_assessment: Optional[str] = None
    impact_assessment: Optional[str] = None
    affected_component: Optional[str] = None
    attack_preconditions: Optional[str] = None
    evidence_interpretation: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    recommended_next_steps: Optional[str] = None
    raw_analysis: Optional[Dict[str, Any]] = None
    supporting_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    model: str
    provider: str
    prompt_version: str
    input_hash: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class AIRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scan_id: uuid.UUID
    workspace_id: uuid.UUID
    agent_name: str
    provider: Optional[str] = None
    model_used: Optional[str] = None
    prompt_version: Optional[str] = None
    status: str
    input_summary: Optional[Dict[str, Any]] = None
    output_summary: Optional[Dict[str, Any]] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class TriggerScanAnalysisRequest(BaseModel):
    force: bool = False
    max_findings: Optional[int] = Field(default=None, ge=1, le=50)


class TriggerFindingAnalysisRequest(BaseModel):
    force: bool = False
    provider: Optional[str] = None


class ScanAnalysisSummaryResponse(BaseModel):
    scan_id: uuid.UUID
    ai_run_id: uuid.UUID
    status: str
    findings_analyzed: int
    findings_skipped_cached: int
    total_findings: int
    analyses: List[FindingAIAnalysisRead]


class AIRelationshipSuggestion(BaseModel):
    has_relationship: bool = Field(description="Whether a plausible security relationship exists between the two findings")
    relationship_type: Optional[str] = Field(
        default=None,
        description="One of: DEPENDS_ON, ENABLES, EXPOSES, LEADS_TO, SHARES_COMPONENT, SHARES_ENTRY_POINT, SHARES_DATA_FLOW, AMPLIFIES"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.5, description="Confidence score between 0.0 and 1.0")
    rationale: str = Field(description="Clear technical explanation justifying the relationship or explaining why none exists")
    attack_vector_step: Optional[str] = Field(default=None, description="How an attacker transitions from source finding to target finding")
    evidence_connection: Optional[str] = Field(default=None, description="Explanation of how the findings' code, endpoints, or data flows connect")


class SecurityChatMessage(BaseModel):
    role: str = "user"  # "user" | "assistant" | "system"
    content: str


class SecurityChatRequest(BaseModel):
    workspace_id: uuid.UUID
    message: str = Field(min_length=1, max_length=4000)
    history: List[SecurityChatMessage] = Field(default_factory=list)
    asset_id: Optional[uuid.UUID] = None
    finding_id: Optional[uuid.UUID] = None


class SecurityChatResponse(BaseModel):
    reply: str
    provider: str = "gemini"
    grounded_context: Dict[str, Any] = Field(default_factory=dict)
    suggested_actions: List[str] = Field(default_factory=list)

