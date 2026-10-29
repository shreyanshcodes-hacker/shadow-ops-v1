import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db.base import Base, TimestampMixin


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    firebase_uid: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default="user", nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships (specifying explicit foreign_keys to resolve ambiguity with invited_by)
    owned_workspaces: Mapped[List["Workspace"]] = relationship("Workspace", back_populates="owner")
    memberships: Mapped[List["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="user",
        primaryjoin="Profile.id == WorkspaceMember.user_id",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="check_profile_role"),
    )
