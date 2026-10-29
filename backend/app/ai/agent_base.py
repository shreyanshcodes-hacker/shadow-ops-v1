from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar, Optional, List, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentInput(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    scan_id: Optional[UUID] = None
    target_data: Dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    agent_name: str
    status: AgentStatus
    summary: str
    findings_count: int = 0
    data: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)
    evidence_ids: List[UUID] = Field(default_factory=list)


class AgentContext(BaseModel):
    scan_id: UUID
    workspace_id: UUID
    asset_id: UUID
    asset_type: str
    target_identifier: str
    environment: str
    budget_remaining_usd: float = 10.0


class AgentRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_name: str
    status: AgentStatus = AgentStatus.QUEUED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tokens_consumed: int = 0
    cost_usd: float = 0.0
    error_message: Optional[str] = None


InT = TypeVar("InT", bound=AgentInput)
OutT = TypeVar("OutT", bound=AgentOutput)


class Agent(ABC, Generic[InT, OutT]):
    """
    Abstract Security Agent base class:
    Defines common operational lifecycle, typed I/O schemas, and context handling.
    """
    agent_name: str
    description: str

    @abstractmethod
    async def execute(self, input_data: InT, context: AgentContext) -> OutT:
        """Execute agent analysis without autonomous destructive side-effects."""
        pass
