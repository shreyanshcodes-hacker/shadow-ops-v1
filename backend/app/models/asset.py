import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, DateTime, ForeignKey, CheckConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from app.db.base import Base, TimestampMixin


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subtype: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    connection_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    credentials_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    criticality: Mapped[str] = mapped_column(String, default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False, index=True)
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String).with_variant(JSON, "sqlite"), default=list, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="assets")
    authorization: Mapped[Optional["AssetAuthorization"]] = relationship("AssetAuthorization", back_populates="asset", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("type IN ('repository', 'api', 'infrastructure', 'application', 'container')", name="check_asset_type"),
        CheckConstraint("criticality IN ('low', 'medium', 'high', 'critical')", name="check_asset_criticality"),
        CheckConstraint("status IN ('active', 'archived', 'error')", name="check_asset_status"),
    )


class AssetAuthorization(Base, TimestampMixin):
    __tablename__ = "asset_authorizations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    authorization_type: Mapped[str] = mapped_column(String, nullable=False)
    evidence_files: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)).with_variant(JSON, "sqlite"), default=list, nullable=False)
    evidence_urls: Mapped[List[str]] = mapped_column(ARRAY(String).with_variant(JSON, "sqlite"), default=list, nullable=False)
    authorized_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False, index=True)
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="authorization")

    __table_args__ = (
        CheckConstraint("authorization_type IN ('ownership', 'written_permission', 'bug_bounty', 'internal')", name="check_auth_type"),
        CheckConstraint("status IN ('pending', 'verified', 'rejected', 'expired')", name="check_auth_status"),
    )
