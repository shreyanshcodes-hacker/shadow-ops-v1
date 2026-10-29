import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class RelationshipType(str, Enum):
    DEPENDS_ON = "DEPENDS_ON"
    ENABLES = "ENABLES"
    EXPOSES = "EXPOSES"
    LEADS_TO = "LEADS_TO"
    SHARES_COMPONENT = "SHARES_COMPONENT"
    SHARES_ENTRY_POINT = "SHARES_ENTRY_POINT"
    SHARES_DATA_FLOW = "SHARES_DATA_FLOW"
    AMPLIFIES = "AMPLIFIES"


class RelationshipSource(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    AI_SUGGESTED = "AI_SUGGESTED"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"


class RelationshipStatus(str, Enum):
    ACTIVE = "active"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"


class RiskBand(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AttackPathStatus(str, Enum):
    ACTIVE = "active"
    MITIGATED = "mitigated"
    BROKEN = "broken"
    DRAFT = "draft"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# --- Security Relationship Schemas ---

class SecurityRelationshipBase(BaseModel):
    source_finding_id: uuid.UUID
    target_finding_id: uuid.UUID
    relationship_type: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source: RelationshipSource = RelationshipSource.DETERMINISTIC
    rationale: Optional[str] = None
    evidence_reference: Dict[str, Any] = Field(default_factory=dict)


class SecurityRelationshipCreate(SecurityRelationshipBase):
    pass


class SecurityRelationshipUpdate(BaseModel):
    status: Optional[RelationshipStatus] = None
    rationale: Optional[str] = None


class SecurityRelationshipRead(SecurityRelationshipBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    status: RelationshipStatus
    confirmed_by: Optional[uuid.UUID] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    source_finding_title: Optional[str] = None
    target_finding_title: Optional[str] = None


# --- Risk Snapshot & Factor Schemas ---

class RiskFactorBreakdown(BaseModel):
    finding_severity: float = Field(description="Normalized severity score (0-100), weight 30%")
    exploitability: float = Field(description="Exploitability score (0-100), weight 20%")
    asset_criticality: float = Field(description="Asset importance (0-100), weight 20%")
    confidence: float = Field(description="Finding/Relationship confidence (0-100), weight 15%")
    exposure: float = Field(description="Entry point / internet exposure (0-100), weight 10%")
    path_complexity: float = Field(description="Attack path length & chain factor (0-100), weight 5%")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed explanatory breakdown of each factor")


class RiskSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    attack_path_id: Optional[uuid.UUID] = None
    finding_id: Optional[uuid.UUID] = None
    score: float
    risk_band: RiskBand
    model_version: str
    factors: Dict[str, Any]
    calculated_at: datetime
    calculated_by: str


# --- Attack Path Node & Edge Schemas ---

class AttackPathNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attack_path_id: uuid.UUID
    workspace_id: uuid.UUID
    node_type: str
    node_order: int
    label: str
    description: Optional[str] = None
    asset_id: Optional[uuid.UUID] = None
    finding_id: Optional[uuid.UUID] = None
    risk_contribution: float
    metadata_: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    finding_title: Optional[str] = None
    finding_severity: Optional[str] = None


class AttackPathEdgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attack_path_id: uuid.UUID
    workspace_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    edge_type: str
    description: Optional[str] = None
    evidence_refs: List[uuid.UUID] = Field(default_factory=list)
    likelihood: Optional[float] = None
    created_at: datetime


# --- Attack Path Schemas ---

class AttackPathRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    scan_id: Optional[uuid.UUID] = None
    name: str
    title: Optional[str] = None
    description: Optional[str] = None
    entry_point: Optional[str] = None
    target_asset: Optional[str] = None
    risk_score: Optional[float] = None
    risk_band: Optional[RiskBand] = None
    confidence: float = 1.0
    node_count: int = 0
    edge_count: int = 0
    is_critical: bool = False
    status: str = "active"
    factors: Dict[str, Any] = Field(default_factory=dict)
    model_version: str = "risk-v1"
    created_at: datetime
    updated_at: datetime


class AttackPathDetailRead(AttackPathRead):
    nodes: List[AttackPathNodeRead] = Field(default_factory=list)
    edges: List[AttackPathEdgeRead] = Field(default_factory=list)
    risk_snapshots: List[RiskSnapshotRead] = Field(default_factory=list)


class AttackPathRecalculateResponse(BaseModel):
    attack_path_id: uuid.UUID
    previous_score: Optional[float] = None
    new_score: float
    risk_band: RiskBand
    model_version: str
    factors: Dict[str, Any]
    snapshot_id: uuid.UUID
