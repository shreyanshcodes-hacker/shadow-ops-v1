import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import HTTPException
from app.services.authorization_service import AuthorizationService
from app.repositories.authorization_repo import AuthorizationRepository
from app.schemas.authorization import AuthorizationCreate, AuthorizationStatus
from app.models.asset import Asset


@pytest.mark.asyncio
async def test_no_authorization_no_scan_boundary(db_session):
    auth_service = AuthorizationService(db_session)
    auth_repo = AuthorizationRepository(db_session)

    workspace_id = uuid4()
    asset_id = uuid4()

    # 1. Test: Missing authorization -> Must raise 403
    with pytest.raises(HTTPException) as exc_missing:
        await auth_service.verify_scan_authorization(asset_id, workspace_id)
    assert exc_missing.value.status_code == 403
    assert "NO AUTHORIZATION -> NO SCAN" in exc_missing.value.detail

    # 2. Test: Pending authorization -> Must raise 403
    await auth_repo.create_or_update(
        asset_id=asset_id,
        workspace_id=workspace_id,
        auth_in=AuthorizationCreate(authorization_type="ownership"),
        status=AuthorizationStatus.PENDING,
    )
    with pytest.raises(HTTPException) as exc_pending:
        await auth_service.verify_scan_authorization(asset_id, workspace_id)
    assert exc_pending.value.status_code == 403
    assert "pending" in exc_pending.value.detail

    # 3. Test: Revoked authorization -> Must raise 403
    await auth_repo.update_status(asset_id, AuthorizationStatus.REVOKED)
    with pytest.raises(HTTPException) as exc_revoked:
        await auth_service.verify_scan_authorization(asset_id, workspace_id)
    assert exc_revoked.value.status_code == 403
    assert "revoked" in exc_revoked.value.detail

    # 4. Test: Expired authorization -> Must raise 403
    expired_auth = AuthorizationCreate(
        authorization_type="ownership",
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    await auth_repo.create_or_update(
        asset_id=asset_id,
        workspace_id=workspace_id,
        auth_in=expired_auth,
        status=AuthorizationStatus.AUTHORIZED,
    )
    with pytest.raises(HTTPException) as exc_expired:
        await auth_service.verify_scan_authorization(asset_id, workspace_id)
    assert exc_expired.value.status_code == 403
    assert "expired" in exc_expired.value.detail

    # 5. Test: Active, verified, unexpired authorization -> Must succeed
    valid_auth = AuthorizationCreate(
        authorization_type="ownership",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    await auth_repo.create_or_update(
        asset_id=asset_id,
        workspace_id=workspace_id,
        auth_in=valid_auth,
        status=AuthorizationStatus.AUTHORIZED,
    )
    is_valid = await auth_service.verify_scan_authorization(asset_id, workspace_id)
    assert is_valid is True
