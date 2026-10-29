import asyncio
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.profile import Profile
from app.schemas.scan import (
    ScanCreateRequest,
    ScanResponse,
    ScanEventResponse,
    FindingResponse,
    ScanSummaryResponse,
)
from app.schemas.workspace import WorkspaceRole
from app.security.dependencies import get_current_user, RequireWorkspaceMember
from app.services.scan_service import ScanService
from app.services.workspace_service import WorkspaceService
from app.repositories.scan_repo import ScanRepository
from app.repositories.asset_repo import AssetRepository

router = APIRouter(tags=["Security Scans"])


def serialize_scan(scan) -> ScanResponse:
    summary_data = scan.summary or {}
    summary = ScanSummaryResponse(
        total_findings=summary_data.get("total_findings", 0),
        critical=summary_data.get("critical", 0),
        high=summary_data.get("high", 0),
        medium=summary_data.get("medium", 0),
        low=summary_data.get("low", 0),
        info=summary_data.get("info", 0),
    )
    profile = scan.scan_config.get("profile", "CODE_SECURITY") if scan.scan_config else "CODE_SECURITY"

    return ScanResponse(
        id=scan.id,
        workspace_id=scan.workspace_id,
        asset_id=scan.asset_id,
        scan_type=scan.scan_type,
        scan_profile=profile,
        status=scan.status,
        triggered_by=scan.triggered_by,
        triggered_at=scan.triggered_at,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        duration_ms=scan.duration_ms,
        progress_percent=scan.progress_percent,
        error_message=scan.error_message,
        summary=summary,
        created_at=scan.created_at,
        updated_at=scan.updated_at,
    )


@router.post("/scans", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    request: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiates a controlled vulnerability scan for an asset.
    MANDATORY INVARIANT: Rejects immediately with 403 if asset lacks valid authorization.
    """
    asset_repo = AssetRepository(db)
    asset = await asset_repo.get_by_id(request.asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    # Validate caller is member of asset's workspace with scan privileges
    ws_service = WorkspaceService(db)
    caller_membership = await ws_service.workspace_repo.get_membership(asset.workspace_id, current_user.id)
    if not caller_membership or caller_membership.role not in [
        WorkspaceRole.OWNER.value,
        WorkspaceRole.ADMIN.value,
        WorkspaceRole.MEMBER.value,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to initiate scans in this workspace",
        )

    scan_service = ScanService(db)
    scan = await scan_service.create_and_enqueue_scan(
        asset_id=request.asset_id,
        workspace_id=asset.workspace_id,
        current_user=current_user,
        scan_profile=request.scan_profile,
    )

    # Immediately execute the controlled scan pipeline
    await scan_service.execute_controlled_scan(scan.id)
    return serialize_scan(scan)


@router.get("/scans", response_model=List[ScanResponse])
async def list_workspace_scans(
    workspace_id: UUID,
    skip: int = 0,
    limit: int = 50,
    current_user: Profile = Depends(get_current_user),
    _membership=Depends(RequireWorkspaceMember()),
    db: AsyncSession = Depends(get_db),
):
    """Lists scans belonging strictly to the authenticated workspace."""
    repo = ScanRepository(db)
    scans = await repo.list_scans_by_workspace(workspace_id, skip=skip, limit=limit)
    return [serialize_scan(s) for s in scans]


@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves scan details. Validates caller workspace membership."""
    repo = ScanRepository(db)
    scan = await repo.get_scan_by_id(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(scan.workspace_id, current_user.id)
    return serialize_scan(scan)


@router.get("/scans/{scan_id}/events", response_model=List[ScanEventResponse])
async def get_scan_events(
    scan_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves chronological lifecycle events for a scan."""
    repo = ScanRepository(db)
    scan = await repo.get_scan_by_id(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(scan.workspace_id, current_user.id)

    events = await repo.list_scan_events(scan_id)
    return [
        ScanEventResponse(
            id=e.id,
            scan_id=e.scan_id,
            workspace_id=e.workspace_id,
            event_type=e.event_type,
            message=e.message,
            data=e.data,
            created_at=e.created_at,
        )
        for e in events
    ]


@router.post("/scans/{scan_id}/cancel", response_model=ScanResponse)
async def cancel_scan(
    scan_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancels a queued or active scan."""
    repo = ScanRepository(db)
    scan = await repo.get_scan_by_id(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(scan.workspace_id, current_user.id)

    service = ScanService(db)
    cancelled = await service.cancel_scan(scan_id, current_user)
    return serialize_scan(cancelled)


@router.get("/assets/{asset_id}/scans", response_model=List[ScanResponse])
async def list_asset_scans(
    asset_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists scans for a specific asset within caller's workspace."""
    asset_repo = AssetRepository(db)
    asset = await asset_repo.get_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(asset.workspace_id, current_user.id)

    scan_repo = ScanRepository(db)
    scans = await scan_repo.list_scans_by_asset(asset_id)
    return [serialize_scan(s) for s in scans]


@router.get("/scans/{scan_id}/findings", response_model=List[FindingResponse])
async def list_scan_findings(
    scan_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves real static analysis findings for a completed scan."""
    scan_repo = ScanRepository(db)
    scan = await scan_repo.get_scan_by_id(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(scan.workspace_id, current_user.id)

    findings = await scan_repo.list_findings_by_scan(scan_id)
    return [
        FindingResponse(
            id=f.id,
            workspace_id=f.workspace_id,
            scan_id=f.scan_id,
            asset_id=f.asset_id,
            source=f.source,
            source_rule_id=f.source_rule_id,
            title=f.title,
            description=f.description,
            severity=f.severity,
            confidence=f.confidence,
            cwe_ids=f.cwe_ids or [],
            owasp_categories=f.owasp_categories or [],
            file_path=f.evidence[0].file_path if f.evidence else None,
            line_start=f.evidence[0].line_start if f.evidence else None,
            line_end=f.evidence[0].line_end if f.evidence else None,
            code_snippet=f.code_snippet,
            status=f.status,
            created_at=f.created_at,
        )
        for f in findings
    ]
