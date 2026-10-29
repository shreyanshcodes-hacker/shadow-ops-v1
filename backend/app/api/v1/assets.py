from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.profile import Profile
from app.schemas.asset import AssetCreate, AssetResponse
from app.schemas.authorization import AuthorizationCreate, AuthorizationResponse, AuthorizationStatus
from app.schemas.workspace import WorkspaceRole
from app.security.dependencies import get_current_user, RequireWorkspaceMember
from app.services.asset_service import AssetService
from app.services.authorization_service import AuthorizationService
from app.services.workspace_service import WorkspaceService

router = APIRouter(tags=["Assets & Authorization"])


def serialize_asset(asset) -> AssetResponse:
    auth_status = asset.authorization.status if asset.authorization else "pending"
    identifier = asset.connection_config.get("identifier") if asset.connection_config else None
    return AssetResponse(
        id=asset.id,
        workspace_id=asset.workspace_id,
        name=asset.name,
        type=asset.type,
        subtype=asset.subtype,
        identifier=identifier,
        environment=asset.connection_config.get("environment", "production"),
        criticality=asset.criticality,
        description=asset.connection_config.get("description"),
        connection_config=asset.connection_config or {},
        tags=asset.tags or [],
        status=asset.status,
        last_scanned_at=asset.last_scanned_at,
        created_by=asset.created_by,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        authorization_status=auth_status,
    )


@router.get("/workspaces/{workspace_id}/assets", response_model=List[AssetResponse])
async def list_workspace_assets(
    workspace_id: UUID,
    current_user: Profile = Depends(get_current_user),
    _membership=Depends(RequireWorkspaceMember()),
    db: AsyncSession = Depends(get_db),
):
    """List assets within an authorized workspace."""
    service = AssetService(db)
    assets = await service.list_assets(workspace_id)
    return [serialize_asset(a) for a in assets]


@router.post("/workspaces/{workspace_id}/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace_asset(
    workspace_id: UUID,
    asset_in: AssetCreate,
    current_user: Profile = Depends(get_current_user),
    _membership=Depends(RequireWorkspaceMember([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])),
    db: AsyncSession = Depends(get_db),
):
    """Add a new target asset to the workspace with initial pending authorization."""
    service = AssetService(db)
    asset = await service.create_asset(asset_in, workspace_id=workspace_id, user_id=current_user.id)
    return serialize_asset(asset)


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve asset details. Validates caller workspace membership."""
    service = AssetService(db)
    asset = await service.get_asset(asset_id)
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(asset.workspace_id, current_user.id)
    return serialize_asset(asset)


@router.post("/assets/{asset_id}/authorization", response_model=AuthorizationResponse)
async def record_asset_authorization(
    asset_id: UUID,
    auth_in: AuthorizationCreate,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Record or verify authorization for an asset.
    MANDATORY SECURITY REQUIREMENT: Only verified authorized assets may be scanned.
    """
    asset_service = AssetService(db)
    asset = await asset_service.get_asset(asset_id)

    # Validate caller has owner or admin role
    ws_service = WorkspaceService(db)
    caller_membership = await ws_service.workspace_repo.get_membership(asset.workspace_id, current_user.id)
    if not caller_membership or caller_membership.role not in [WorkspaceRole.OWNER.value, WorkspaceRole.ADMIN.value]:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners or admins can verify asset authorization",
        )

    auth_service = AuthorizationService(db)
    record = await auth_service.record_authorization(
        asset_id=asset.id,
        workspace_id=asset.workspace_id,
        auth_in=auth_in,
        user_id=current_user.id,
        status_val=AuthorizationStatus.AUTHORIZED,
    )

    return AuthorizationResponse(
        id=record.id,
        asset_id=record.asset_id,
        workspace_id=record.workspace_id,
        authorization_type=record.authorization_type,
        authorization_status=record.status,
        authorized_by=record.authorized_by,
        authorization_scope=auth_in.authorization_scope or "full_scan",
        authorization_reference=auth_in.authorization_reference,
        authorized_at=record.authorized_at,
        expires_at=record.expires_at,
        status=record.status,
        verified_by=record.verified_by,
        verified_at=record.verified_at,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
