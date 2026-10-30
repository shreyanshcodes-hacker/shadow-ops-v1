from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class WorkspaceBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=100)


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    settings: Optional[Dict[str, Any]] = None


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    owner_id: UUID
    plan: str
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemberInvite(BaseModel):
    email: str
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    invited_by: Optional[UUID] = None
    invited_at: datetime
    joined_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkspaceDirectoryItem(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    members_count: int
    created_at: Optional[datetime] = None


class EmployeeJoinRequest(BaseModel):
    display_name: Optional[str] = None
    job_title: Optional[str] = None


class CompanyOnboardingRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=100)
    slug: Optional[str] = None
    industry: Optional[str] = None
    team_size: Optional[str] = None
    display_name: Optional[str] = None
    asset_name: Optional[str] = None
    asset_type: Optional[str] = "repository"
    asset_identifier: Optional[str] = None
    asset_environment: Optional[str] = "production"
    asset_criticality: Optional[str] = "high"

