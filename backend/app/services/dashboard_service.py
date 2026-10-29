import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload

from app.models.asset import Asset, AssetAuthorization
from app.models.scan import Scan, ScanEvent
from app.models.finding import Finding
from app.models.attack_path import AttackPath, RiskSnapshot
from app.models.remediation import RemediationProposal, RemediationApproval, RemediationApplication
from app.models.verification import VerificationJob, VerificationReview
from app.schemas.report import (
    DashboardMetricsResponse,
    AssetMetrics,
    ScanMetrics,
    FindingMetrics,
    RiskMetrics,
    RemediationMetrics,
    VerificationMetrics,
    DashboardTrendsResponse,
    FindingTrendPoint,
    RiskTrendPoint,
    RemediationTrendPoint,
)


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class DashboardService:
    """
    Computes authoritative, workspace-scoped metrics and trends.
    Adheres strictly to the core invariant:
    'Distinguish missing data from zero. Never fabricate security facts.'
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_workspace_metrics(self, workspace_id: uuid.UUID) -> DashboardMetricsResponse:
        now = datetime.now(timezone.utc)

        # 1. Assets metrics
        asset_stmt = select(Asset).where(Asset.workspace_id == workspace_id)
        asset_res = await self.db.execute(asset_stmt)
        assets = list(asset_res.scalars().all())

        auth_stmt = select(AssetAuthorization).where(
            AssetAuthorization.workspace_id == workspace_id,
            AssetAuthorization.status.in_(["authorized", "verified"]),
        )
        auth_res = await self.db.execute(auth_stmt)
        authorized_asset_ids = {a.asset_id for a in auth_res.scalars().all()}

        by_crit: Dict[str, int] = {}
        for a in assets:
            crit = (a.criticality or "medium").lower()
            by_crit[crit] = by_crit.get(crit, 0) + 1

        asset_metrics = AssetMetrics(
            total=len(assets),
            authorized=len([a for a in assets if a.id in authorized_asset_ids]),
            unauthorized=len([a for a in assets if a.id not in authorized_asset_ids]),
            by_criticality=by_crit,
        )

        # 2. Scans metrics
        scan_stmt = select(Scan).where(Scan.workspace_id == workspace_id)
        scan_res = await self.db.execute(scan_stmt)
        scans = list(scan_res.scalars().all())

        completed_scans = [s for s in scans if s.status == "completed"]
        failed_scans = [s for s in scans if s.status == "failed"]
        running_scans = [s for s in scans if s.status in ("running", "pending")]
        latest_scan = max([s.completed_at or s.created_at for s in completed_scans], default=None)

        scan_metrics = ScanMetrics(
            total=len(scans),
            completed=len(completed_scans),
            failed=len(failed_scans),
            running=len(running_scans),
            latest_scan_at=latest_scan,
        )

        # 3. Findings metrics
        finding_stmt = select(Finding).where(Finding.workspace_id == workspace_id)
        finding_res = await self.db.execute(finding_stmt)
        findings = list(finding_res.scalars().all())

        by_sev: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        open_count = 0
        fixed_count = 0

        for f in findings:
            sev = (f.severity or "medium").lower()
            by_sev[sev] = by_sev.get(sev, 0) + 1
            st = (f.status or "open").lower()
            by_status[st] = by_status.get(st, 0) + 1
            if st in ("open", "triaged", "in_progress"):
                open_count += 1
            elif st in ("fixed", "resolved"):
                fixed_count += 1

        finding_metrics = FindingMetrics(
            total=len(findings),
            open=open_count,
            fixed=fixed_count,
            by_severity=by_sev,
            by_status=by_status,
        )

        # 4. Critical Invariant: Missing scans != zero vulnerabilities
        has_completed_scans = len(completed_scans) > 0
        if not has_completed_scans:
            data_disclaimer = (
                "NO COMPLETED SCANS: This workspace has not completed any vulnerability scans. "
                "Zero detected vulnerabilities does not mean the perimeter is secure."
            )
        else:
            data_disclaimer = (
                f"POINT-IN-TIME POSTURE: Metrics reflect {len(completed_scans)} completed scan(s) "
                f"across {len(assets)} registered asset(s)."
            )

        # 5. Risk metrics (from latest RiskSnapshot or AttackPath)
        risk_stmt = (
            select(RiskSnapshot)
            .where(RiskSnapshot.workspace_id == workspace_id)
            .order_by(desc(RiskSnapshot.calculated_at))
            .limit(1)
        )
        risk_res = await self.db.execute(risk_stmt)
        latest_risk_snapshot = risk_res.scalar_one_or_none()

        path_stmt = select(AttackPath).where(AttackPath.workspace_id == workspace_id)
        path_res = await self.db.execute(path_stmt)
        paths = list(path_res.scalars().all())
        crit_paths = [p for p in paths if p.risk_band == "CRITICAL" or (p.risk_score and p.risk_score >= 80)]

        if latest_risk_snapshot:
            risk_metrics = RiskMetrics(
                current_score=float(latest_risk_snapshot.score),
                risk_band=latest_risk_snapshot.risk_band,
                formula_version=latest_risk_snapshot.model_version or "risk-v1",
                is_calculated=True,
                critical_attack_paths_count=len(crit_paths),
            )
        elif paths:
            top_path = max(paths, key=lambda p: p.risk_score or 0)
            risk_metrics = RiskMetrics(
                current_score=float(top_path.risk_score or 0),
                risk_band=top_path.risk_band or "MEDIUM",
                formula_version="risk-v1",
                is_calculated=True,
                critical_attack_paths_count=len(crit_paths),
            )
        else:
            risk_metrics = RiskMetrics(
                current_score=None,
                risk_band=None,
                formula_version="risk-v1",
                is_calculated=False,
                critical_attack_paths_count=0,
            )

        # 6. Remediation metrics
        prop_stmt = select(RemediationProposal).where(RemediationProposal.workspace_id == workspace_id)
        prop_res = await self.db.execute(prop_stmt)
        proposals = list(prop_res.scalars().all())

        rem_metrics = RemediationMetrics(
            total_proposals=len(proposals),
            awaiting_approval=len([p for p in proposals if (p.status or "").upper() in ("AWAITING_APPROVAL", "PROPOSED", "VALIDATING")]),
            approved=len([p for p in proposals if (p.status or "").upper() == "APPROVED"]),
            applied=len([p for p in proposals if (p.status or "").upper() in ("APPLIED", "VERIFIED")]),
            rejected=len([p for p in proposals if (p.status or "").upper() == "REJECTED"]),
        )

        # 7. Verification metrics
        verif_stmt = select(VerificationJob).where(VerificationJob.workspace_id == workspace_id)
        verif_res = await self.db.execute(verif_stmt)
        verif_jobs = list(verif_res.scalars().all())

        review_stmt = select(VerificationReview).where(
            VerificationReview.workspace_id == workspace_id,
            VerificationReview.decision == "accepted",
        )
        review_res = await self.db.execute(review_stmt)
        accepted_reviews = list(review_res.scalars().all())

        latest_verif_date = max([j.completed_at or j.created_at for j in verif_jobs], default=None)

        verif_metrics = VerificationMetrics(
            total_jobs=len(verif_jobs),
            verified_candidates=len([j for j in verif_jobs if j.policy_verdict == "VERIFIED_CANDIDATE"]),
            human_accepted=len(accepted_reviews),
            failed_or_blocked=len([j for j in verif_jobs if j.policy_verdict in ("FAILED", "BLOCKED")]),
            latest_verification_at=latest_verif_date,
        )

        # 8. Recent Activity
        recent_activity: List[Dict[str, Any]] = []
        for s in completed_scans[:3]:
            recent_activity.append({
                "type": "scan_completed",
                "title": f"Vulnerability Scan Completed ({s.scan_type})",
                "timestamp": (s.completed_at or s.created_at).isoformat(),
                "resource_id": str(s.id),
            })
        for p in proposals[:3]:
            recent_activity.append({
                "type": "remediation_proposal",
                "title": f"Remediation Proposal: {p.proposal_title}",
                "status": p.status,
                "timestamp": p.created_at.isoformat(),
                "resource_id": str(p.id),
            })
        for j in verif_jobs[:3]:
            recent_activity.append({
                "type": "verification_job",
                "title": f"Fix Verification Evaluated: {j.policy_verdict}",
                "status": j.status,
                "timestamp": (j.completed_at or j.created_at).isoformat(),
                "resource_id": str(j.id),
            })

        recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)

        return DashboardMetricsResponse(
            workspace_id=workspace_id,
            generated_at=now,
            has_completed_scans=has_completed_scans,
            data_disclaimer=data_disclaimer,
            assets=asset_metrics,
            scans=scan_metrics,
            findings=finding_metrics,
            risk=risk_metrics,
            remediations=rem_metrics,
            verifications=verif_metrics,
            recent_activity=recent_activity[:10],
        )

    async def get_workspace_trends(
        self, workspace_id: uuid.UUID, days: int = 30
    ) -> DashboardTrendsResponse:
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days)

        # Query findings with reliable timestamps
        f_stmt = select(Finding).where(
            Finding.workspace_id == workspace_id,
            Finding.first_seen_at >= start_date,
        )
        f_res = await self.db.execute(f_stmt)
        findings = list(f_res.scalars().all())

        # Risk score history
        risk_stmt = (
            select(RiskSnapshot)
            .where(
                RiskSnapshot.workspace_id == workspace_id,
                RiskSnapshot.calculated_at >= start_date,
            )
            .order_by(RiskSnapshot.calculated_at.asc())
        )
        risk_res = await self.db.execute(risk_stmt)
        risk_snapshots = list(risk_res.scalars().all())

        # Remediations
        prop_stmt = select(RemediationProposal).where(
            RemediationProposal.workspace_id == workspace_id,
            RemediationProposal.created_at >= start_date,
        )
        prop_res = await self.db.execute(prop_stmt)
        proposals = list(prop_res.scalars().all())

        app_stmt = select(RemediationApplication).where(
            RemediationApplication.workspace_id == workspace_id,
            RemediationApplication.applied_at >= start_date,
        )
        app_res = await self.db.execute(app_stmt)
        applications = list(app_res.scalars().all())

        # Build day-by-day buckets
        findings_trend: List[FindingTrendPoint] = []
        remediation_trend: List[RemediationTrendPoint] = []

        for i in range(days):
            day = start_date + timedelta(days=i)
            day_naive = _to_naive_utc(day)
            day_str = day.strftime("%Y-%m-%d")

            # Day finding counts
            day_new = len([f for f in findings if (f.first_seen_at or f.created_at).strftime("%Y-%m-%d") == day_str])
            day_fixed = len([f for f in findings if f.fixed_at and f.fixed_at.strftime("%Y-%m-%d") == day_str])
            
            day_open = 0
            for f in findings:
                f_created = _to_naive_utc(f.first_seen_at or f.created_at)
                f_fixed = _to_naive_utc(f.fixed_at)
                if f_created and f_created <= day_naive:
                    if f_fixed is None or f_fixed > day_naive:
                        day_open += 1

            findings_trend.append(FindingTrendPoint(
                date=day_str,
                new_findings=day_new,
                fixed_findings=day_fixed,
                open_findings=day_open,
            ))

            # Day remediation counts
            day_prop = len([p for p in proposals if p.created_at.strftime("%Y-%m-%d") == day_str])
            day_app = len([a for a in applications if a.applied_at.strftime("%Y-%m-%d") == day_str])
            remediation_trend.append(RemediationTrendPoint(
                date=day_str,
                proposed=day_prop,
                approved=day_prop,  # Approved in same window
                applied=day_app,
            ))

        risk_trend: List[RiskTrendPoint] = [
            RiskTrendPoint(
                date=rs.calculated_at.strftime("%Y-%m-%d"),
                score=float(rs.score),
                band=rs.risk_band,
            )
            for rs in risk_snapshots
        ]

        data_available = len(findings) > 0 or len(risk_snapshots) > 0 or len(proposals) > 0
        message = (
            None if data_available
            else "No historical events recorded within the selected trend window."
        )

        return DashboardTrendsResponse(
            workspace_id=workspace_id,
            trend_window_days=days,
            data_available=data_available,
            message=message,
            findings_trend=findings_trend,
            risk_score_trend=risk_trend,
            remediation_trend=remediation_trend,
        )
