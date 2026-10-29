from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import Scan, ScanEvent
from app.models.finding import Finding
from app.models.profile import Profile
from app.repositories.scan_repo import ScanRepository
from app.repositories.asset_repo import AssetRepository
from app.services.audit_service import AuditService
from app.schemas.audit import AuditEventType
from app.services.authorization_service import AuthorizationService
from app.scanning.models import ScanStatus, ScanProfile, ScanEventType, validate_transition
from app.scanning.exceptions import (
    ScanAuthorizationException,
    StateTransitionException,
    TargetValidationException,
    SemgrepExecutionException,
)
from app.scanning.policies import ScanPathPolicy
from app.scanning.runner import ScanJobRunner
from app.scanning.semgrep import ScannerAdapter, SemgrepAdapter


class ScanService:
    """
    Core orchestrator for controlled vulnerability scans.
    Enforces NO AUTHORIZATION -> NO SCAN before triggering analysis.
    """

    def __init__(
        self,
        session: AsyncSession,
        scanner_adapter: Optional[ScannerAdapter] = None,
    ):
        self.session = session
        self.scan_repo = ScanRepository(session)
        self.asset_repo = AssetRepository(session)
        self.auth_service = AuthorizationService(session)
        self.audit_service = AuditService(session)
        self.runner = ScanJobRunner(adapter=scanner_adapter or SemgrepAdapter())

    async def create_and_enqueue_scan(
        self,
        asset_id: UUID,
        workspace_id: UUID,
        current_user: Profile,
        scan_profile: ScanProfile = ScanProfile.CODE_SECURITY,
    ) -> Scan:
        """
        Validates authorization, creates scan record, and queues execution.
        CRITICAL SECURITY INVARIANT: Must strictly reject unauthorized assets.
        """
        # 1. Verify Asset exists and belongs to workspace
        asset = await self.asset_repo.get_by_id(asset_id)
        if not asset or asset.workspace_id != workspace_id:
            await self.audit_service.log(
                workspace_id=workspace_id,
                action=AuditEventType.SCAN_BLOCKED,
                user_id=current_user.id,
                resource_type="scan",
                resource_id=asset_id,
                new_state={"reason": "Asset not found or workspace mismatch"},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found in the specified workspace",
            )

        # 2. STRICT SECURITY GATE: Enforce NO AUTHORIZATION -> NO SCAN
        try:
            await self.auth_service.verify_scan_authorization(asset_id, workspace_id)
        except HTTPException as exc:
            raise exc

        # 3. Create Scan Record in QUEUED state
        scan = await self.scan_repo.create_scan(
            workspace_id=workspace_id,
            asset_id=asset_id,
            user_id=current_user.id,
            scan_type="code",
            scan_profile=scan_profile.value,
            target_reference=asset.connection_config.get("identifier"),
        )

        # 4. Emit Events & Audit
        await self.scan_repo.add_scan_event(
            scan_id=scan.id,
            workspace_id=workspace_id,
            event_type=ScanEventType.SCAN_CREATED.value,
            message="Scan initialized in security command queue.",
        )
        await self.scan_repo.add_scan_event(
            scan_id=scan.id,
            workspace_id=workspace_id,
            event_type=ScanEventType.AUTHORIZATION_CONFIRMED.value,
            message="Server verified active legal authorization proof. Pre-flight check passed.",
        )
        await self.scan_repo.add_scan_event(
            scan_id=scan.id,
            workspace_id=workspace_id,
            event_type=ScanEventType.SCAN_QUEUED.value,
            message=f"Scan enqueued with profile {scan_profile.value}.",
        )

        await self.audit_service.log(
            workspace_id=workspace_id,
            action=AuditEventType.SCAN_CREATED,
            user_id=current_user.id,
            resource_type="scan",
            resource_id=scan.id,
            new_state={"asset_id": str(asset_id), "profile": scan_profile.value},
        )

        return scan

    async def execute_controlled_scan(self, scan_id: UUID) -> Scan:
        """
        Executes the analysis lifecycle for a queued scan.
        Runs Semgrep against the controlled fixture target.
        """
        scan = await self.scan_repo.get_scan_by_id(scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

        # Validate transition from QUEUED -> RUNNING
        if not validate_transition(ScanStatus(scan.status), ScanStatus.RUNNING):
            raise StateTransitionException(f"Cannot transition scan from {scan.status} to running.")

        await self.scan_repo.update_scan_status(scan, "running", progress_percent=10)
        await self.scan_repo.add_scan_event(
            scan_id=scan.id,
            workspace_id=scan.workspace_id,
            event_type=ScanEventType.SCAN_STARTED.value,
            message="Scan worker initiated sandbox execution.",
        )

        # Resolve controlled target fixture
        backend_root = Path(__file__).resolve().parent.parent
        target_dir = backend_root / "scanning" / "fixtures" / "vulnerable_repo"

        try:
            validated_path = ScanPathPolicy.sanitize_and_validate_target(
                str(target_dir),
                base_dir=backend_root,
            )

            await self.scan_repo.add_scan_event(
                scan_id=scan.id,
                workspace_id=scan.workspace_id,
                event_type=ScanEventType.ANALYSIS_STARTED.value,
                message="Target filesystem validation complete. Static analysis engine starting.",
            )
            await self.scan_repo.add_scan_event(
                scan_id=scan.id,
                workspace_id=scan.workspace_id,
                event_type=ScanEventType.SEMGREP_STARTED.value,
                message="Semgrep ruleset execution engaged against target repository.",
            )
            await self.scan_repo.update_scan_status(scan, "running", progress_percent=40)

            # Execute Semgrep via runner
            findings = await self.runner.execute_scan(validated_path, timeout_seconds=60)

            await self.scan_repo.add_scan_event(
                scan_id=scan.id,
                workspace_id=scan.workspace_id,
                event_type=ScanEventType.SEMGREP_COMPLETED.value,
                message="Semgrep rule evaluation finished successfully.",
            )
            await self.scan_repo.add_scan_event(
                scan_id=scan.id,
                workspace_id=scan.workspace_id,
                event_type=ScanEventType.RESULTS_PARSED.value,
                message=f"Parsed {len(findings)} normalized static code vulnerabilities.",
            )
            await self.scan_repo.update_scan_status(scan, "running", progress_percent=75)

            # Persist Findings and Evidence
            findings_dicts = [f.model_dump() for f in findings]
            persisted, summary = await self.scan_repo.save_findings_and_evidence(scan, findings_dicts)

            await self.scan_repo.add_scan_event(
                scan_id=scan.id,
                workspace_id=scan.workspace_id,
                event_type=ScanEventType.EVIDENCE_STORED.value,
                message="Evidence artifacts, code snippets, and provenance links stored in PostgreSQL.",
            )

            # Mark scan COMPLETED
            await self.scan_repo.update_scan_status(
                scan,
                "completed",
                progress_percent=100,
                summary=summary.model_dump(),
            )
            await self.scan_repo.add_scan_event(
                scan_id=scan.id,
                workspace_id=scan.workspace_id,
                event_type=ScanEventType.SCAN_COMPLETED.value,
                message=f"Scan completed. Total findings: {summary.total_findings} (Critical: {summary.critical}, High: {summary.high}).",
            )
            await self.audit_service.log(
                workspace_id=scan.workspace_id,
                action=AuditEventType.SCAN_COMPLETED,
                user_id=scan.triggered_by,
                resource_type="scan",
                resource_id=scan.id,
                new_state=summary.model_dump(),
            )
            return scan

        except Exception as e:
            err_msg = str(e)
            await self.scan_repo.update_scan_status(
                scan,
                "failed",
                error_message=err_msg,
            )
            await self.scan_repo.add_scan_event(
                scan_id=scan.id,
                workspace_id=scan.workspace_id,
                event_type=ScanEventType.SCAN_FAILED.value,
                message=f"Analysis pipeline aborted: {err_msg}",
            )
            await self.audit_service.log(
                workspace_id=scan.workspace_id,
                action=AuditEventType.SCAN_FAILED,
                user_id=scan.triggered_by,
                resource_type="scan",
                resource_id=scan.id,
                new_state={"error": err_msg},
            )
            return scan

    async def cancel_scan(self, scan_id: UUID, current_user: Profile) -> Scan:
        """Cancels an active or queued scan."""
        scan = await self.scan_repo.get_scan_by_id(scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

        if not validate_transition(ScanStatus(scan.status), ScanStatus.CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel scan in '{scan.status}' state.",
            )

        # Terminate active scanner subprocess if running
        await self.runner.cancel()

        await self.scan_repo.update_scan_status(scan, "cancelled", error_message="Cancelled by operator.")
        await self.scan_repo.add_scan_event(
            scan_id=scan.id,
            workspace_id=scan.workspace_id,
            event_type=ScanEventType.SCAN_CANCELLED.value,
            message=f"Scan execution cancelled by operator {current_user.email}.",
        )
        await self.audit_service.log(
            workspace_id=scan.workspace_id,
            action=AuditEventType.SCAN_CANCELLED,
            user_id=current_user.id,
            resource_type="scan",
            resource_id=scan.id,
            new_state={"cancelled_by": current_user.email},
        )
        return scan
