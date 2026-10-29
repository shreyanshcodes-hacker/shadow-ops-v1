from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class AuthorizationStatus(str, Enum):
    AUTHORIZED = "verified"
    PENDING = "pending"
    REVOKED = "rejected"
    EXPIRED = "expired"


class AuthorizationMethod(str, Enum):
    OWNERSHIP = "ownership"
    WRITTEN_PERMISSION = "written_permission"
    BUG_BOUNTY = "bug_bounty"
    INTERNAL = "internal"


class AuthorizationCreate(BaseModel):
    authorization_type: AuthorizationMethod = AuthorizationMethod.OWNERSHIP
    authorization_scope: Optional[str] = "full_scan"
    authorization_reference: Optional[str] = Field(default=None, description="Ticket number, approval doc ref, or OAuth state")
    authorized_by: Optional[str] = Field(default=None, description="Name or role of person authorizing scan")
    evidence_urls: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    expires_at: Optional[datetime] = None


class AuthorizationResponse(BaseModel):
    id: UUID
    asset_id: UUID
    workspace_id: UUID
    authorization_type: str
    authorization_status: str
    authorized_by: Optional[str] = None
    authorization_scope: Optional[str] = "full_scan"
    authorization_reference: Optional[str] = None
    authorized_at: datetime
    expires_at: Optional[datetime] = None
    status: str
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
