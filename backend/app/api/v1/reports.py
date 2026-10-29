from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.session import get_db
from app.models.profile import Profile
from app.models.report import Report
from app.schemas.report import (
    DashboardMetricsResponse,
    DashboardTrendsResponse,
    ReportCreateRequest,
    ReportResponse,
    ReportListResponse,
    ReportExportResponse,
    ReportFormat,
)
from app.security.dependencies import get_current_user
from app.services.workspace_service import WorkspaceService
from app.services.dashboard_service import DashboardService
from app.services.report_generator_service import ReportGeneratorService
from app.services.report_export_service import ReportExportService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/reports", tags=["Security Reports & Executive Dashboard"])


@router.get("/dashboard", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches real-time, deterministic dashboard metrics for the workspace.
    Explicitly distinguishes missing data from zero.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    dash_service = DashboardService(db)
    return await dash_service.get_workspace_metrics(workspace_id)


@router.get("/dashboard/trends", response_model=DashboardTrendsResponse)
async def get_dashboard_trends(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    days: int = Query(30, ge=7, le=90, description="Window in days"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches historical 30-day security trends for findings, risk scores, and remediations.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    dash_service = DashboardService(db)
    return await dash_service.get_workspace_trends(workspace_id, days=days)


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_security_report(
    payload: ReportCreateRequest,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates an immutable, point-in-time security report snapshot.
    Supports 5 core report types with deterministic calculations and advisory AI summaries.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    report_gen = ReportGeneratorService(db)
    report = await report_gen.generate_report(
        workspace_id=workspace_id,
        request=payload,
        generated_by=current_user.email or str(current_user.id),
        user_id=current_user.id,
    )
    return report


@router.get("", response_model=ReportListResponse)
async def list_security_reports(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists generated security reports for the authenticated workspace.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    stmt = select(Report).where(Report.workspace_id == workspace_id)
    if report_type:
        stmt = stmt.where(Report.report_type == report_type)

    stmt = stmt.order_by(desc(Report.created_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    reports = list(res.scalars().all())

    # Count
    count_stmt = select(Report).where(Report.workspace_id == workspace_id)
    if report_type:
        count_stmt = count_stmt.where(Report.report_type == report_type)
    c_res = await db.execute(count_stmt)
    total = len(list(c_res.scalars().all()))

    return ReportListResponse(items=reports, total=total)


@router.get("/{id}", response_model=ReportResponse)
async def get_security_report(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a frozen report snapshot by ID. Enforces strict workspace isolation.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    stmt = select(Report).where(Report.id == id, Report.workspace_id == workspace_id)
    res = await db.execute(stmt)
    report = res.scalars().first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return report


@router.post("/{id}/export", response_model=ReportExportResponse)
async def export_security_report(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    export_format: Optional[ReportFormat] = Query(None, alias="format"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Prepares report metadata for export/download.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    stmt = select(Report).where(Report.id == id, Report.workspace_id == workspace_id)
    res = await db.execute(stmt)
    report = res.scalars().first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    target_format = (export_format.value if export_format else report.format).lower()
    cutoff_str = (report.data_cutoff_at or report.created_at).strftime("%Y%m%d_%H%M%S")
    file_name = f"shadowops_{report.report_type}_{str(report.id)[:8]}_{cutoff_str}.{target_format}"
    content_type = "application/pdf" if target_format == "pdf" else "application/json"

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log_action(
        workspace_id=workspace_id,
        actor_id=current_user.id,
        action="report.exported",
        resource_type="report",
        resource_id=str(report.id),
        details={"format": target_format, "file_name": file_name},
    )
    await db.commit()

    return ReportExportResponse(
        report_id=report.id,
        format=target_format,
        file_name=file_name,
        content_type=content_type,
        download_url=f"/api/v1/reports/{report.id}/download?workspace_id={workspace_id}&format={target_format}",
        data_cutoff_at=report.data_cutoff_at,
    )


@router.get("/{id}/download")
async def download_security_report(
    id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    format: str = Query("pdf", description="Export format: pdf or json"),
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Downloads the report directly as a file stream (PDF or JSON).
    Strictly authenticates the user and logs audit evidence.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(workspace_id, current_user.id)

    stmt = select(Report).where(Report.id == id, Report.workspace_id == workspace_id)
    res = await db.execute(stmt)
    report = res.scalars().first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    fmt = format.lower()
    if fmt == "json":
        json_content, file_name, content_type = ReportExportService.export_json(report)
        content_bytes = json_content.encode("utf-8")
    elif fmt == "pdf":
        pdf_bytes, file_name, content_type = ReportExportService.export_pdf(report)
        content_bytes = pdf_bytes
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported format: {format}")

    # Audit download
    audit_service = AuditService(db)
    await audit_service.log_action(
        workspace_id=workspace_id,
        actor_id=current_user.id,
        action="report.downloaded",
        resource_type="report",
        resource_id=str(report.id),
        details={"format": fmt, "file_name": file_name, "byte_size": len(content_bytes)},
    )
    await db.commit()

    return Response(
        content=content_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
