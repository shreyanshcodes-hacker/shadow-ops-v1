from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.scan import Scan, ScanEvent
from app.models.finding import Finding, FindingEvidence
from app.schemas.scan import ScanSummaryResponse


class ScanRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_scan(
        self,
        workspace_id: UUID,
        asset_id: UUID,
        user_id: UUID,
        scan_type: str = "code",
        scan_profile: str = "CODE_SECURITY",
        target_reference: Optional[str] = None,
    ) -> Scan:
        scan = Scan(
            workspace_id=workspace_id,
            asset_id=asset_id,
            scan_type=scan_type,
            status="queued",
            triggered_by=user_id,
            triggered_at=datetime.now(timezone.utc),
            progress_percent=0,
            scan_config={"profile": scan_profile, "target_reference": target_reference},
            summary={"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        )
        self.session.add(scan)
        await self.session.commit()
        await self.session.refresh(scan)
        return scan

    async def get_scan_by_id(self, scan_id: UUID) -> Optional[Scan]:
        query = select(Scan).where(Scan.id == scan_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_scans_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Scan]:
        query = (
            select(Scan)
            .where(Scan.workspace_id == workspace_id)
            .order_by(desc(Scan.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_scans_by_asset(
        self,
        asset_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Scan]:
        query = (
            select(Scan)
            .where(Scan.asset_id == asset_id)
            .order_by(desc(Scan.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_scan_event(
        self,
        scan_id: UUID,
        workspace_id: UUID,
        event_type: str,
        message: str,
        data: Optional[dict] = None,
        phase: str = "execution",
    ) -> ScanEvent:
        event = ScanEvent(
            scan_id=scan_id,
            workspace_id=workspace_id,
            phase=phase,
            event_type=event_type,
            message=message,
            data=data or {},
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def list_scan_events(self, scan_id: UUID) -> List[ScanEvent]:
        query = select(ScanEvent).where(ScanEvent.scan_id == scan_id).order_by(ScanEvent.created_at.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_scan_status(
        self,
        scan: Scan,
        new_status: str,
        progress_percent: Optional[int] = None,
        error_message: Optional[str] = None,
        summary: Optional[dict] = None,
    ) -> Scan:
        now = datetime.now(timezone.utc)
        scan.status = new_status
        if progress_percent is not None:
            scan.progress_percent = progress_percent
        if error_message is not None:
            scan.error_message = error_message
        if summary is not None:
            scan.summary = summary

        if new_status == "running" and not scan.started_at:
            scan.started_at = now
        elif new_status in ["completed", "failed", "cancelled"]:
            scan.completed_at = now
            if scan.started_at:
                started = scan.started_at if scan.started_at.tzinfo else scan.started_at.replace(tzinfo=timezone.utc)
                scan.duration_ms = int((now - started).total_seconds() * 1000)

        await self.session.commit()
        await self.session.refresh(scan)
        return scan

    async def save_findings_and_evidence(
        self,
        scan: Scan,
        findings_data: List[dict],
    ) -> Tuple[List[Finding], ScanSummaryResponse]:
        summary = ScanSummaryResponse(
            total_findings=len(findings_data),
            critical=sum(1 for f in findings_data if f["severity"] == "critical"),
            high=sum(1 for f in findings_data if f["severity"] == "high"),
            medium=sum(1 for f in findings_data if f["severity"] == "medium"),
            low=sum(1 for f in findings_data if f["severity"] == "low"),
            info=sum(1 for f in findings_data if f["severity"] == "info"),
        )

        persisted_findings: List[Finding] = []
        for item in findings_data:
            finding = Finding(
                workspace_id=scan.workspace_id,
                scan_id=scan.id,
                asset_id=scan.asset_id,
                source="semgrep",
                source_rule_id=item["rule_id"],
                title=item["title"],
                description=item["message"],
                severity=item["severity"],
                confidence="high",
                cwe_ids=item.get("cwe_ids", []),
                owasp_categories=item.get("owasp_categories", []),
                code_snippet=item.get("code_snippet"),
                status="open",
                first_seen_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
            )
            self.session.add(finding)
            await self.session.flush()

            # Create corresponding FindingEvidence
            evidence = FindingEvidence(
                finding_id=finding.id,
                workspace_id=scan.workspace_id,
                evidence_type="STATIC_ANALYSIS",
                title=f"Semgrep Match: {item['rule_id']}",
                description=item["message"],
                file_path=item["file_path"],
                line_start=item["line_start"],
                line_end=item["line_end"],
                content={"snippet": item.get("code_snippet"), "metadata": item.get("raw_metadata")},
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(evidence)
            persisted_findings.append(finding)

        scan.summary = summary.model_dump()
        await self.session.commit()
        return persisted_findings, summary

    async def list_findings_by_scan(self, scan_id: UUID) -> List[Finding]:
        query = (
            select(Finding)
            .options(selectinload(Finding.evidence))
            .where(Finding.scan_id == scan_id)
            .order_by(Finding.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_findings_by_workspace(self, workspace_id: UUID, skip: int = 0, limit: int = 100) -> List[Finding]:
        query = (
            select(Finding)
            .where(Finding.workspace_id == workspace_id)
            .order_by(Finding.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
