from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field


class JobStatus(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    job_type: str
    status: str = "queued"
    workspace_id: UUID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_data: Dict[str, Any] = Field(default_factory=dict)


class BaseJob(ABC):
    """
    Abstract contract defining asynchronous job execution boundaries.
    """
    job_type: str

    @abstractmethod
    async def run(self, payload: Dict[str, Any]) -> JobStatus:
        pass


class ScanJobBoundary(BaseJob):
    job_type = "scan_pipeline"

    async def run(self, payload: Dict[str, Any]) -> JobStatus:
        # Prepares async boundary for Phase 6 pipeline
        return JobStatus(
            job_type=self.job_type,
            status="prepared",
            workspace_id=payload["workspace_id"],
        )


class AgentJobBoundary(BaseJob):
    job_type = "agent_execution"

    async def run(self, payload: Dict[str, Any]) -> JobStatus:
        return JobStatus(
            job_type=self.job_type,
            status="prepared",
            workspace_id=payload["workspace_id"],
        )


class VerificationJobBoundary(BaseJob):
    job_type = "verification_run"

    async def run(self, payload: Dict[str, Any]) -> JobStatus:
        return JobStatus(
            job_type=self.job_type,
            status="prepared",
            workspace_id=payload["workspace_id"],
        )


class ReportJobBoundary(BaseJob):
    job_type = "report_compilation"

    async def run(self, payload: Dict[str, Any]) -> JobStatus:
        return JobStatus(
            job_type=self.job_type,
            status="prepared",
            workspace_id=payload["workspace_id"],
        )
