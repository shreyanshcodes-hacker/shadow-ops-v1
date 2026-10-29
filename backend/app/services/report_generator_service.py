import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload

from app.models.report import Report
from app.models.asset import Asset, AssetAuthorization
from app.models.scan import Scan
from app.models.finding import Finding, FindingEvidence
from app.models.attack_path import AttackPath, RiskSnapshot
from app.models.remediation import RemediationProposal, RemediationApproval, RemediationApplication
from app.models.verification import VerificationJob, VerificationReview
from app.schemas.report import ReportCreateRequest, ReportType, ReportFormat
from app.services.audit_service import AuditService
from app.schemas.audit import AuditEventType
from app.ai.provider import get_ai_provider, AIRequestConfig
from app.core.logging import logger


SECRET_PATTERNS = [
    re.compile(r'(?:api[_-]?key|apikey|secret|token|password|passwd|auth[_-]?token)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.\/+=]{8,})["\']?', re.IGNORECASE),
    re.compile(r'Bearer\s+([a-zA-Z0-9_\-\.\/+=]{10,})', re.IGNORECASE),
    re.compile(r'-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----'),
    re.compile(r'(postgres(?:ql)?|mysql|mongodb|redis):\/\/[^:\s]+:([^@\s]+)@', re.IGNORECASE),
    re.compile(r'(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{82})'),
    re.compile(r'(AKIA[0-9A-Z]{16})'),
]


def redact_sensitive_data(text: Optional[str]) -> Optional[str]:
    """
    Sanitizes code snippets, logs, and evidence text by redacting sensitive secrets.
    """
    if not text:
        return text
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted


class ReportGeneratorService:
    """
    Authoritative Report Generation Service for Stage 10.
    Builds frozen, immutable, evidence-grounded security reports.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_service = AuditService(db)

    async def generate_report(
        self,
        workspace_id: uuid.UUID,
        request: ReportCreateRequest,
        generated_by: str,
        user_id: Optional[uuid.UUID] = None,
    ) -> Report:
        cutoff_at = datetime.now(timezone.utc)
        title = request.title or f"{request.report_type.value.replace('_', ' ').title()} - {cutoff_at.strftime('%Y-%m-%d')}"
        description = request.description or f"Automated {request.report_type.value} report generated on {cutoff_at.strftime('%Y-%m-%d %H:%M:%S UTC')}."

        # Initialize report record
        report = Report(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            report_type=request.report_type.value,
            title=title,
            description=description,
            format=request.format.value,
            status="generating",
            generated_by=generated_by,
            period_start=request.period_start,
            period_end=request.period_end,
            data_cutoff_at=cutoff_at,
            schema_version="report-v1",
            completeness_status="COMPLETE",
            parameters={
                "report_type": request.report_type.value,
                "asset_ids": [str(a) for a in (request.asset_ids or [])],
                "severities": request.severities or [],
                "period_start": request.period_start.isoformat() if request.period_start else None,
                "period_end": request.period_end.isoformat() if request.period_end else None,
                "include_ai_summary": request.include_ai_summary,
            },
            snapshot_data={},
            metadata_={},
        )
        self.db.add(report)
        await self.db.flush()

        try:
            # Dispatch generation by report type
            if request.report_type == ReportType.EXECUTIVE_SUMMARY:
                snapshot, completeness = await self._build_executive_summary(workspace_id, request, cutoff_at)
            elif request.report_type == ReportType.TECHNICAL_VULNERABILITY:
                snapshot, completeness = await self._build_technical_vulnerabilities(workspace_id, request, cutoff_at)
            elif request.report_type == ReportType.REMEDIATION_PROGRESS:
                snapshot, completeness = await self._build_remediation_progress(workspace_id, request, cutoff_at)
            elif request.report_type == ReportType.VERIFICATION_REGRESSION:
                snapshot, completeness = await self._build_verification_regression(workspace_id, request, cutoff_at)
            elif request.report_type == ReportType.ASSET_SECURITY_POSTURE:
                snapshot, completeness = await self._build_asset_security_posture(workspace_id, request, cutoff_at)
            else:
                snapshot, completeness = await self._build_executive_summary(workspace_id, request, cutoff_at)

            report.snapshot_data = snapshot
            report.completeness_status = completeness
            report.status = "completed"
            report.completed_at = datetime.now(timezone.utc)

            # Audit event
            await self.audit_service.log_action(
                workspace_id=workspace_id,
                actor_id=user_id,
                action="report.generated",
                resource_type="report",
                resource_id=str(report.id),
                details={
                    "report_type": report.report_type,
                    "format": report.format,
                    "title": report.title,
                    "completeness_status": report.completeness_status,
                },
            )

            await self.db.commit()
            await self.db.refresh(report)
            return report

        except Exception as e:
            await self.db.rollback()
            logger.exception("Failed to generate report %s: %s", report.id, str(e))
            # Mark failed
            report.status = "failed"
            report.error_message = str(e)
            self.db.add(report)
            await self.db.commit()
            raise

    # --------------------------------------------------------------------------
    # 1. Executive Summary
    # --------------------------------------------------------------------------
    async def _build_executive_summary(
        self,
        workspace_id: uuid.UUID,
        request: ReportCreateRequest,
        cutoff_at: datetime,
    ) -> tuple[Dict[str, Any], str]:
        # Assets & Authorizations
        assets_res = await self.db.execute(select(Asset).where(Asset.workspace_id == workspace_id))
        assets = list(assets_res.scalars().all())

        auth_res = await self.db.execute(
            select(AssetAuthorization).where(
                AssetAuthorization.workspace_id == workspace_id,
                AssetAuthorization.status.in_(["authorized", "verified"]),
            )
        )
        auth_asset_ids = {a.asset_id for a in auth_res.scalars().all()}

        # Scans
        scan_res = await self.db.execute(select(Scan).where(Scan.workspace_id == workspace_id))
        all_scans = list(scan_res.scalars().all())
        completed_scans = [s for s in all_scans if s.status == "completed"]
        has_completed_scans = len(completed_scans) > 0

        # Findings
        f_stmt = select(Finding).where(Finding.workspace_id == workspace_id)
        if request.asset_ids:
            f_stmt = f_stmt.where(Finding.asset_id.in_(request.asset_ids))
        if request.severities:
            f_stmt = f_stmt.where(Finding.severity.in_(request.severities))
        findings_res = await self.db.execute(f_stmt)
        findings = list(findings_res.scalars().all())

        open_findings = [f for f in findings if f.status in ("open", "triaged", "in_progress")]
        fixed_findings = [f for f in findings if f.status in ("fixed", "resolved")]

        sev_counts: Dict[str, int] = {}
        for f in open_findings:
            s = (f.severity or "medium").lower()
            sev_counts[s] = sev_counts.get(s, 0) + 1

        # Risk Snapshot
        risk_res = await self.db.execute(
            select(RiskSnapshot)
            .where(RiskSnapshot.workspace_id == workspace_id)
            .order_by(desc(RiskSnapshot.calculated_at))
            .limit(1)
        )
        latest_risk = risk_res.scalars().first()

        # Attack Paths
        ap_res = await self.db.execute(
            select(AttackPath).where(
                AttackPath.workspace_id == workspace_id,
                AttackPath.status == "active",
            )
        )
        attack_paths = list(ap_res.scalars().all())
        crit_paths = [
            ap for ap in attack_paths
            if (ap.risk_band or "").upper() in ("CRITICAL", "HIGH") or ap.is_critical
        ]

        # Remediations & Verifications
        rem_res = await self.db.execute(
            select(RemediationProposal).where(RemediationProposal.workspace_id == workspace_id)
        )
        remediations = list(rem_res.scalars().all())
        applied_remediations = [r for r in remediations if r.status in ("applied", "verified")]

        ver_res = await self.db.execute(
            select(VerificationJob).where(VerificationJob.workspace_id == workspace_id)
        )
        verifications = list(ver_res.scalars().all())
        verified_candidates = [v for v in verifications if v.status in ("PASSED_PENDING_REVIEW", "COMPLETED")]

        # Top critical findings
        critical_findings_sorted = sorted(
            [f for f in open_findings if f.severity in ("critical", "high")],
            key=lambda x: (x.severity == "critical", x.created_at),
            reverse=True,
        )[:10]

        top_findings_data = [
            {
                "finding_id": str(f.id),
                "title": f.title,
                "severity": f.severity,
                "rule_id": f.source_rule_id or "unknown-rule",
                "asset_id": str(f.asset_id),
                "file_path": f.location.get("file_path", "N/A") if isinstance(f.location, dict) else "N/A",
                "line_start": f.location.get("line_start") if isinstance(f.location, dict) else None,
                "cwe_id": f.cwe_ids[0] if (f.cwe_ids and isinstance(f.cwe_ids, list) and len(f.cwe_ids) > 0) else "N/A",
                "status": f.status,
            }
            for f in critical_findings_sorted
        ]

        # Missing data disclaimer
        disclaimer = "Data reflects verified scans."
        completeness = "COMPLETE"
        if not has_completed_scans:
            disclaimer = "CAUTION: No completed scans exist in this workspace. Zero reported findings does not imply zero risk."
            completeness = "PARTIAL"

        # AI Advisory Summary
        ai_narrative = await self._generate_ai_executive_summary(
            workspace_id=workspace_id,
            total_assets=len(assets),
            authorized_assets=len(auth_asset_ids),
            completed_scans=len(completed_scans),
            open_findings=len(open_findings),
            sev_counts=sev_counts,
            risk_score=float(latest_risk.score) if latest_risk and latest_risk.score is not None else None,
            risk_band=latest_risk.risk_band if latest_risk else None,
            crit_paths_count=len(crit_paths),
            remediations_applied=len(applied_remediations),
            verified_count=len(verified_candidates),
            include_ai=request.include_ai_summary,
            cutoff_at=cutoff_at,
        )

        snapshot: Dict[str, Any] = {
            "report_type": ReportType.EXECUTIVE_SUMMARY.value,
            "generated_at": cutoff_at.isoformat(),
            "scope": {
                "total_assets": len(assets),
                "authorized_assets": len(auth_asset_ids),
                "unauthorized_assets": len(assets) - len(auth_asset_ids),
                "has_completed_scans": has_completed_scans,
                "completed_scans_count": len(completed_scans),
            },
            "disclaimer": disclaimer,
            "executive_narrative": ai_narrative,
            "metrics": {
                "risk_score": float(latest_risk.score) if latest_risk and latest_risk.score is not None else None,
                "risk_band": latest_risk.risk_band if latest_risk else ("NOT_CALCULATED" if not has_completed_scans else "LOW"),
                "formula_version": latest_risk.model_version if latest_risk else "risk-v1",
                "open_findings_count": len(open_findings),
                "fixed_findings_count": len(fixed_findings),
                "by_severity": sev_counts,
                "critical_attack_paths_count": len(crit_paths),
                "active_attack_paths_count": len(attack_paths),
                "remediations_proposed": len(remediations),
                "remediations_applied": len(applied_remediations),
                "verifications_completed": len(verified_candidates),
            },
            "top_critical_findings": top_findings_data,
            "attack_paths_summary": [
                {
                    "path_id": str(ap.id),
                    "title": ap.title or ap.name or f"Path to {ap.target_asset or 'Asset'}",
                    "risk_tier": ap.risk_band or ("CRITICAL" if ap.is_critical else "MEDIUM"),
                    "target_node": ap.target_asset or "Internal Asset",
                    "step_count": ap.node_count,
                    "status": ap.status,
                }
                for ap in crit_paths[:5]
            ],
            "limitations": [
                "AI summary is strictly advisory; all scores are calculated deterministically.",
                "Un-scanned or unauthorized assets are not evaluated for vulnerabilities.",
            ],
        }

        return snapshot, completeness

    # --------------------------------------------------------------------------
    # 2. Technical Vulnerabilities Report
    # --------------------------------------------------------------------------
    async def _build_technical_vulnerabilities(
        self,
        workspace_id: uuid.UUID,
        request: ReportCreateRequest,
        cutoff_at: datetime,
    ) -> tuple[Dict[str, Any], str]:
        # Fetch Assets
        asset_stmt = select(Asset).where(Asset.workspace_id == workspace_id)
        if request.asset_ids:
            asset_stmt = asset_stmt.where(Asset.id.in_(request.asset_ids))
        asset_res = await self.db.execute(asset_stmt)
        assets_by_id = {a.id: a for a in asset_res.scalars().all()}

        # Fetch Findings with Evidence
        f_stmt = (
            select(Finding)
            .options(selectinload(Finding.evidence))
            .where(Finding.workspace_id == workspace_id)
        )
        if request.asset_ids:
            f_stmt = f_stmt.where(Finding.asset_id.in_(request.asset_ids))
        if request.severities:
            f_stmt = f_stmt.where(Finding.severity.in_(request.severities))
        if request.period_start:
            f_stmt = f_stmt.where(Finding.created_at >= request.period_start)
        if request.period_end:
            f_stmt = f_stmt.where(Finding.created_at <= request.period_end)

        f_res = await self.db.execute(f_stmt)
        findings = list(f_res.scalars().all())

        # Fetch Remediations for correlation
        rem_stmt = select(RemediationProposal).where(RemediationProposal.workspace_id == workspace_id)
        rem_res = await self.db.execute(rem_stmt)
        rems_by_finding: Dict[uuid.UUID, RemediationProposal] = {
            r.finding_id: r for r in rem_res.scalars().all()
        }

        # Build detailed findings data with redacted code snippets
        findings_list = []
        rule_distribution: Dict[str, int] = {}
        severity_distribution: Dict[str, int] = {}

        for f in findings:
            sev = (f.severity or "medium").lower()
            severity_distribution[sev] = severity_distribution.get(sev, 0) + 1
            rule_id = f.source_rule_id or "unknown-rule"
            rule_distribution[rule_id] = rule_distribution.get(rule_id, 0) + 1

            asset = assets_by_id.get(f.asset_id)
            rem = rems_by_finding.get(f.id)

            ev_list = []
            if f.evidence:
                for ev in f.evidence:
                    raw_content = ""
                    if isinstance(ev.content, dict):
                        raw_content = ev.content.get("snippet") or ev.content.get("text") or str(ev.content)
                    elif ev.content:
                        raw_content = str(ev.content)

                    ev_list.append({
                        "evidence_id": str(ev.id),
                        "evidence_type": ev.evidence_type,
                        "title": ev.title,
                        "file_path": ev.file_path,
                        "line_start": ev.line_start,
                        "line_end": ev.line_end,
                        "snippet_redacted": redact_sensitive_data(raw_content),
                    })

            file_path = f.location.get("file_path", "N/A") if isinstance(f.location, dict) else "N/A"
            line_start = f.location.get("line_start") if isinstance(f.location, dict) else None
            line_end = f.location.get("line_end") if isinstance(f.location, dict) else None
            cwe_id = f.cwe_ids[0] if (f.cwe_ids and isinstance(f.cwe_ids, list) and len(f.cwe_ids) > 0) else "N/A"
            owasp_category = f.owasp_categories[0] if (f.owasp_categories and isinstance(f.owasp_categories, list) and len(f.owasp_categories) > 0) else "N/A"

            findings_list.append({
                "finding_id": str(f.id),
                "title": f.title,
                "description": f.description,
                "rule_id": rule_id,
                "severity": f.severity,
                "confidence": f.confidence,
                "status": f.status,
                "file_path": file_path,
                "line_start": line_start,
                "line_end": line_end,
                "cwe_id": cwe_id,
                "owasp_category": owasp_category,
                "asset_id": str(f.asset_id),
                "asset_name": asset.name if asset else "Unknown Asset",
                "evidence_count": len(ev_list),
                "evidence_items": ev_list,
                "remediation": {
                    "proposal_id": str(rem.id) if rem else None,
                    "status": rem.status if rem else None,
                    "title": rem.proposal_title if rem else None,
                } if rem else None,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            })

        snapshot: Dict[str, Any] = {
            "report_type": ReportType.TECHNICAL_VULNERABILITY.value,
            "generated_at": cutoff_at.isoformat(),
            "total_findings": len(findings_list),
            "severity_distribution": severity_distribution,
            "top_rules": sorted(rule_distribution.items(), key=lambda x: x[1], reverse=True)[:10],
            "findings": findings_list,
            "redaction_applied": True,
            "scope": {
                "filtered_assets_count": len(assets_by_id),
                "severities_filter": request.severities or ["all"],
            },
        }
        return snapshot, "COMPLETE"

    # --------------------------------------------------------------------------
    # 3. Remediation Progress Report
    # --------------------------------------------------------------------------
    async def _build_remediation_progress(
        self,
        workspace_id: uuid.UUID,
        request: ReportCreateRequest,
        cutoff_at: datetime,
    ) -> tuple[Dict[str, Any], str]:
        rem_stmt = select(RemediationProposal).where(RemediationProposal.workspace_id == workspace_id)
        if request.asset_ids:
            rem_stmt = rem_stmt.where(RemediationProposal.asset_id.in_(request.asset_ids))
        rem_res = await self.db.execute(rem_stmt)
        proposals = list(rem_res.scalars().all())

        # Approvals & Applications
        app_res = await self.db.execute(
            select(RemediationApplication).where(RemediationApplication.workspace_id == workspace_id)
        )
        applications_by_proposal: Dict[uuid.UUID, RemediationApplication] = {
            a.proposal_id: a for a in app_res.scalars().all()
        }

        # Verifications
        ver_res = await self.db.execute(
            select(VerificationJob).where(VerificationJob.workspace_id == workspace_id)
        )
        ver_by_finding: Dict[uuid.UUID, VerificationJob] = {
            v.finding_id: v for v in ver_res.scalars().all() if v.finding_id
        }

        # Status counts
        status_counts: Dict[str, int] = {}
        for p in proposals:
            st = (p.status or "draft").lower()
            status_counts[st] = status_counts.get(st, 0) + 1

        proposals_data = []
        for p in proposals:
            app = applications_by_proposal.get(p.id)
            ver = ver_by_finding.get(p.finding_id)

            proposals_data.append({
                "proposal_id": str(p.id),
                "finding_id": str(p.finding_id),
                "asset_id": str(p.asset_id),
                "title": p.proposal_title,
                "problem_summary": p.problem_summary,
                "status": p.status,
                "affected_files": p.affected_files,
                "patch_reference": p.patch_reference,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "approved_by": str(p.approved_by) if p.approved_by else None,
                "approved_at": p.approved_at.isoformat() if p.approved_at else None,
                "applied_by": str(p.applied_by) if p.applied_by else None,
                "applied_at": p.applied_at.isoformat() if p.applied_at else None,
                "application": {
                    "applied_revision": getattr(app, "target_revision", None),
                    "rollback_available": getattr(app, "checkpoint_id", None) is not None or getattr(app, "rollback_patch", None) is not None,
                    "applied_at": app.applied_at.isoformat() if getattr(app, "applied_at", None) else None,
                } if app else None,
                "verification": {
                    "job_id": str(ver.id),
                    "status": ver.status,
                    "policy_verdict": ver.policy_verdict,
                } if ver else None,
            })

        snapshot: Dict[str, Any] = {
            "report_type": ReportType.REMEDIATION_PROGRESS.value,
            "generated_at": cutoff_at.isoformat(),
            "total_proposals": len(proposals),
            "status_distribution": status_counts,
            "applied_count": status_counts.get("applied", 0) + status_counts.get("verified", 0),
            "pending_approval_count": status_counts.get("proposed", 0) + status_counts.get("validating", 0),
            "proposals": proposals_data,
        }
        return snapshot, "COMPLETE"

    # --------------------------------------------------------------------------
    # 4. Verification & Regression Report (Stage 9 focus)
    # --------------------------------------------------------------------------
    async def _build_verification_regression(
        self,
        workspace_id: uuid.UUID,
        request: ReportCreateRequest,
        cutoff_at: datetime,
    ) -> tuple[Dict[str, Any], str]:
        # Verification jobs
        v_stmt = select(VerificationJob).where(VerificationJob.workspace_id == workspace_id)
        if request.asset_ids:
            v_stmt = v_stmt.where(VerificationJob.asset_id.in_(request.asset_ids))
        v_res = await self.db.execute(v_stmt)
        jobs = list(v_res.scalars().all())

        # Reviews
        rev_res = await self.db.execute(
            select(VerificationReview).where(VerificationReview.workspace_id == workspace_id)
        )
        reviews_by_job: Dict[uuid.UUID, VerificationReview] = {
            r.job_id: r for r in rev_res.scalars().all()
        }

        # Invariant counts
        status_counts: Dict[str, int] = {}
        comparison_outcomes: Dict[str, int] = {}
        regression_failures = 0
        human_signoffs = 0

        jobs_data = []
        for j in jobs:
            st = (j.status or "QUEUED").upper()
            status_counts[st] = status_counts.get(st, 0) + 1

            if j.vulnerability_status:
                outcome = j.vulnerability_status.upper()
                comparison_outcomes[outcome] = comparison_outcomes.get(outcome, 0) + 1

            if (j.regression_status or "").upper() == "FAIL":
                regression_failures += 1

            rev = reviews_by_job.get(j.id)
            if rev:
                human_signoffs += 1

            jobs_data.append({
                "job_id": str(j.id),
                "asset_id": str(j.asset_id),
                "finding_id": str(j.finding_id) if j.finding_id else None,
                "proposal_id": str(j.proposal_id) if j.proposal_id else None,
                "status": j.status,
                "vulnerability_status": j.vulnerability_status,
                "regression_status": j.regression_status,
                "policy_verdict": j.policy_verdict,
                "policy_reasons": j.policy_reasons,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "human_review": {
                    "review_id": str(rev.id),
                    "decision": rev.decision,
                    "reviewer_id": str(rev.reviewer_id),
                    "rationale": rev.rationale,
                    "reviewed_at": rev.reviewed_at.isoformat() if rev.reviewed_at else None,
                } if rev else None,
            })

        snapshot: Dict[str, Any] = {
            "report_type": ReportType.VERIFICATION_REGRESSION.value,
            "generated_at": cutoff_at.isoformat(),
            "total_verification_jobs": len(jobs),
            "status_distribution": status_counts,
            "comparison_outcomes": comparison_outcomes,
            "regression_failures_count": regression_failures,
            "human_signoffs_count": human_signoffs,
            "verification_invariant": "No sufficient evidence means no verified fix.",
            "jobs": jobs_data,
        }
        return snapshot, "COMPLETE"

    # --------------------------------------------------------------------------
    # 5. Asset Security Posture Report
    # --------------------------------------------------------------------------
    async def _build_asset_security_posture(
        self,
        workspace_id: uuid.UUID,
        request: ReportCreateRequest,
        cutoff_at: datetime,
    ) -> tuple[Dict[str, Any], str]:
        a_stmt = select(Asset).where(Asset.workspace_id == workspace_id)
        if request.asset_ids:
            a_stmt = a_stmt.where(Asset.id.in_(request.asset_ids))
        a_res = await self.db.execute(a_stmt)
        assets = list(a_res.scalars().all())

        # Authorizations
        auth_res = await self.db.execute(
            select(AssetAuthorization).where(AssetAuthorization.workspace_id == workspace_id)
        )
        auths_by_asset: Dict[uuid.UUID, AssetAuthorization] = {
            a.asset_id: a for a in auth_res.scalars().all()
        }

        # Scans
        scans_res = await self.db.execute(
            select(Scan).where(Scan.workspace_id == workspace_id).order_by(desc(Scan.created_at))
        )
        scans_by_asset: Dict[uuid.UUID, List[Scan]] = {}
        for s in scans_res.scalars().all():
            scans_by_asset.setdefault(s.asset_id, []).append(s)

        # Findings
        find_res = await self.db.execute(
            select(Finding).where(Finding.workspace_id == workspace_id)
        )
        findings_by_asset: Dict[uuid.UUID, List[Finding]] = {}
        for f in find_res.scalars().all():
            findings_by_asset.setdefault(f.asset_id, []).append(f)

        assets_data = []
        for a in assets:
            auth = auths_by_asset.get(a.id)
            scans = scans_by_asset.get(a.id, [])
            latest_scan = scans[0] if scans else None
            findings = findings_by_asset.get(a.id, [])
            open_findings = [f for f in findings if f.status in ("open", "triaged", "in_progress")]

            sev_breakdown: Dict[str, int] = {}
            for f in open_findings:
                s = (f.severity or "medium").lower()
                sev_breakdown[s] = sev_breakdown.get(s, 0) + 1

            target_val = a.connection_config.get("target") if isinstance(a.connection_config, dict) else "N/A"
            env_val = a.connection_config.get("environment", "production") if isinstance(a.connection_config, dict) else "production"

            assets_data.append({
                "asset_id": str(a.id),
                "name": a.name,
                "asset_type": a.type,
                "criticality": a.criticality or "medium",
                "environment": env_val,
                "target": target_val,
                "is_active": a.status == "active",
                "authorization": {
                    "status": auth.status if auth else "unauthorized",
                    "authorized_at": auth.authorized_at.isoformat() if auth and auth.authorized_at else None,
                    "expires_at": auth.expires_at.isoformat() if auth and auth.expires_at else None,
                },
                "scans": {
                    "total_runs": len(scans),
                    "latest_scan_status": latest_scan.status if latest_scan else "never_scanned",
                    "latest_scan_at": latest_scan.created_at.isoformat() if latest_scan else None,
                },
                "open_findings_count": len(open_findings),
                "severity_breakdown": sev_breakdown,
            })

        snapshot: Dict[str, Any] = {
            "report_type": ReportType.ASSET_SECURITY_POSTURE.value,
            "generated_at": cutoff_at.isoformat(),
            "total_assets": len(assets),
            "assets": assets_data,
        }
        return snapshot, "COMPLETE"

    # --------------------------------------------------------------------------
    # AI Executive Narrative Generator (Advisory Only)
    # --------------------------------------------------------------------------
    async def _generate_ai_executive_summary(
        self,
        workspace_id: uuid.UUID,
        total_assets: int,
        authorized_assets: int,
        completed_scans: int,
        open_findings: int,
        sev_counts: Dict[str, int],
        risk_score: Optional[float],
        risk_band: Optional[str],
        crit_paths_count: int,
        remediations_applied: int,
        verified_count: int,
        include_ai: bool,
        cutoff_at: datetime,
    ) -> Dict[str, Any]:
        """
        Generates an advisory executive narrative.
        If AI is unavailable or disabled, gracefully falls back to deterministic summary.
        """
        deterministic_narrative = (
            f"As of {cutoff_at.strftime('%Y-%m-%d %H:%M UTC')}, the workspace manages {total_assets} assets "
            f"({authorized_assets} authorized) with {completed_scans} completed scans. "
            f"There are {open_findings} open findings ({sev_counts.get('critical', 0)} critical, "
            f"{sev_counts.get('high', 0)} high). The deterministic risk score stands at "
            f"{f'{risk_score:.1f}' if risk_score is not None else 'N/A'} ({risk_band or 'UNSCANNED'}), "
            f"with {crit_paths_count} critical attack paths active. "
            f"Remediation velocity shows {remediations_applied} patches applied and {verified_count} fixes independently verified."
        )

        if not include_ai:
            return {
                "narrative": deterministic_narrative,
                "is_ai_generated": False,
                "disclaimer": "Deterministic system generated summary.",
                "generated_at": cutoff_at.isoformat(),
            }

        try:
            ai_provider = get_ai_provider()
            prompt = (
                f"You are an executive cybersecurity advisor reviewing verified deterministic scan facts for a startup.\n"
                f"Data Context:\n"
                f"- Assets: {total_assets} total ({authorized_assets} authorized)\n"
                f"- Completed Scans: {completed_scans}\n"
                f"- Open Findings: {open_findings} (Critical: {sev_counts.get('critical', 0)}, High: {sev_counts.get('high', 0)}, Medium: {sev_counts.get('medium', 0)}, Low: {sev_counts.get('low', 0)})\n"
                f"- Deterministic Risk Score: {risk_score} ({risk_band})\n"
                f"- Critical Attack Paths: {crit_paths_count}\n"
                f"- Patches Applied: {remediations_applied}, Verified: {verified_count}\n\n"
                f"Instructions:\n"
                f"Write a concise 2-paragraph executive security posture summary for startup founders and engineering leads.\n"
                f"Explain the primary risk drivers and recommended next steps.\n"
                f"DO NOT invent findings, DO NOT change the risk score, and DO NOT claim compliance certifications."
            )
            config = AIRequestConfig(timeout_seconds=10, max_output_tokens=500)
            ai_res = await ai_provider.generate_text(
                prompt=prompt,
                system_instruction="You are ShadowOps Executive Advisor. Summarize only facts provided. Never fabricate numbers.",
                config=config,
            )
            narrative = ai_res.content.strip() if ai_res and ai_res.content else deterministic_narrative
            return {
                "narrative": narrative,
                "is_ai_generated": True,
                "disclaimer": "Advisory only. Deterministic findings and verification records take precedence.",
                "generated_at": cutoff_at.isoformat(),
            }
        except Exception as e:
            logger.warning("AI executive summary generation skipped or failed (%s). Using fallback.", str(e))
            return {
                "narrative": deterministic_narrative,
                "is_ai_generated": False,
                "disclaimer": "Deterministic system generated summary (AI service unavailable).",
                "generated_at": cutoff_at.isoformat(),
            }
