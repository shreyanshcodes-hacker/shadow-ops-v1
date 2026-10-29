from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class AssetType(str, Enum):
    REPOSITORY = "repository"
    API = "api"
    WEB_APP = "application"
    DOMAIN = "infrastructure"
    SERVICE = "service"
    CONTAINER = "container"


class AssetCriticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AssetBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: AssetType = AssetType.REPOSITORY
    subtype: Optional[str] = "github"
    identifier: Optional[str] = Field(default=None, description="Repository URL, hostname, or API endpoint")
    environment: str = Field(default="production", description="Environment: production, staging, development")
    criticality: AssetCriticality = AssetCriticality.MEDIUM
    description: Optional[str] = None
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    criticality: Optional[AssetCriticality] = None
    environment: Optional[str] = None
    description: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class AssetResponse(AssetBase):
    id: UUID
    workspace_id: UUID
    status: str
    last_scanned_at: Optional[datetime] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    authorization_status: Optional[str] = "pending"

    model_config = {"from_attributes": True}
