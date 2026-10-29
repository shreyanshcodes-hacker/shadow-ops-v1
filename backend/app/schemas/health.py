from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Application status")
    environment: str = Field(description="Active environment")
    version: str = Field(default="1.0.0", description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp")


class DatabaseHealthResponse(BaseModel):
    status: str = Field(description="Database connectivity status: connected or degraded")
    database_connected: bool
    latency_ms: Optional[float] = None
    pool_info: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReadinessResponse(BaseModel):
    status: str = Field(description="Readiness status: ready or degraded")
    environment: str
    database: Dict[str, Any]
    scanner: Dict[str, Any]
    outbox_backlog: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
