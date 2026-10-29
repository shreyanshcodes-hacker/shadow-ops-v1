from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.profile import Profile
from app.models.finding import Finding
from app.schemas.scan import FindingResponse
from app.security.dependencies import get_current_user
from app.services.workspace_service import WorkspaceService

router = APIRouter(tags=["Findings"])


@router.get("/findings/{finding_id}", response_model=FindingResponse)
async def get_finding_by_id(
    finding_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the authoritative scanner facts for a specific finding.
    Enforces multi-tenant workspace isolation.
    """
    stmt = (
        select(Finding)
        .options(selectinload(Finding.evidence))
        .where(Finding.id == finding_id)
    )
    res = await db.execute(stmt)
    finding = res.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(finding.workspace_id, current_user.id)

    file_path = None
    line_start = None
    line_end = None
    if finding.location:
        file_path = finding.location.get("file")
        line_start = finding.location.get("start_line")
        line_end = finding.location.get("end_line")

    return FindingResponse(
        id=finding.id,
        workspace_id=finding.workspace_id,
        scan_id=finding.scan_id,
        asset_id=finding.asset_id,
        source=finding.source,
        source_rule_id=finding.source_rule_id,
        title=finding.title,
        description=finding.description,
        severity=finding.severity,
        confidence=finding.confidence,
        cwe_ids=finding.cwe_ids or [],
        owasp_categories=finding.owasp_categories or [],
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        code_snippet=finding.code_snippet,
        status=finding.status,
        created_at=finding.created_at,
    )
