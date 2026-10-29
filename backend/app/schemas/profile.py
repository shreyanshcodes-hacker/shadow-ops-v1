from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class ProfileBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileCreate(ProfileBase):
    firebase_uid: str
    role: str = "user"


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileResponse(ProfileBase):
    id: UUID
    firebase_uid: str
    role: str
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
