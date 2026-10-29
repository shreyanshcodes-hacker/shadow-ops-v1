"""
Security Team Orchestrator

Manages deterministic, multi-agent analytical evaluations across authorized perimeters.
Enforces:
1. Workspace multi-tenancy & authorization check.
2. Controlled sequential execution with dependency tracking.
3. Idempotency to prevent duplicate runaway runs.
4. Bounded retries (MAX_AGENT_RETRIES = 2).
5. Safe partial result handling & cancellation support.
6. Full audit event trail & persistent agent execution history.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone
import logging
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security_team import SecurityTeamRun
from app.models.scan import Scan, AgentRun
from app.models.asset import Asset
from app.models.finding import Finding, FindingEvidence
from app.models.security_relationship import SecurityRelationship
from app.models.attack_path import AttackPath, RiskSnapshot
from app.schemas.security_team import (
    TeamRunStatus,
    AgentStatus,
    AgentRequest,
    AgentResponse,
    TeamAssessment,
)
from app.services.security_agents import AgentRegistry, BaseSecurityAgent
from app.services.audit_service import AuditService
from app.schemas.audit import AuditEventType
from app.ai.provider import get_ai_provider, AIProvider

logger = logging.getLogger("shadowops.security_team.orchestrator")

MAX_AGENT_RETRIES = 2
ORCHESTRATION_VERSION = "security-team-v1"


class SecurityTeamOrchestrator:
    def __init__(self, session: AsyncSession, provider: Optional[AIProvider] = None):
        self.session = session
        self.provider = provider or get_ai_provider()
        self.audit_service = AuditService(session)

    async def create_team_run(
        self,
        workspace_id: UUID,
        asset_id: UUID,
        requested_by: UUID,
        scan_id: Optional[UUID] = None,
        orchestration_version: str = ORCHESTRATION_VERSION,
    ) -> SecurityTeamRun:
        """
        Creates a new team run or returns existing active run (Idempotency Guard).
        """
        # 1. Verify Asset belongs to Workspace
        stmt_asset = select(Asset).where(and_(Asset.id == asset_id, Asset.workspace_id == workspace_id))
        res_asset = await self.session.execute(stmt_asset)
        asset = res_asset.scalar_one_or_none()
        if not asset:
            raise ValueError("Target asset not found or does not belong to specified workspace.")

        # 2. Idempotency Check: check for active runs on identical scope
        stmt_active = select(SecurityTeamRun).where(
            and_(
                SecurityTeamRun.workspace_id == workspace_id,
                SecurityTeamRun.asset_id == asset_id,
                SecurityTeamRun.scan_id == scan_id,
                SecurityTeamRun.orchestration_version == orchestration_version,
                SecurityTeamRun.status.in_([TeamRunStatus.QUEUED.value, TeamRunStatus.RUNNING.value]),
            )
        )
        res_active = await self.session.execute(stmt_active)
        existing = res_active.scalar_one_or_none()
        if existing:
            logger.info(f"Idempotency hit: Returning existing active team run {existing.id}")
            return existing

        # 3. Create new team run record
        team_run = SecurityTeamRun(
            workspace_id=workspace_id,
            asset_id=asset_id,
            scan_id=scan_id,
            status=TeamRunStatus.QUEUED.value,
            requested_by=requested_by,
            orchestration_version=orchestration_version,
            team_summary={},
            confidence=0.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(team_run)
        await self.session.commit()
        await self.session.refresh(team_run)

        # 4. Audit Log
        await self.audit_service.log(
            workspace_id=workspace_id,
            user_id=requested_by,
            action=AuditEventType.SECURITY_TEAM_STARTED,
            resource_type="security_team_run",
            resource_id=team_run.id,
            new_state={"status": team_run.status, "asset_id": str(asset_id)},
        )

        return team_run

    async def execute_team_run(self, team_run_id: UUID) -> SecurityTeamRun:
        """
        Executes the specialized multi-agent pipeline with dependency tracking.
        Pipeline: RECON -> VULNERABILITY_ANALYST -> ATTACK_PATH -> RISK_ANALYST -> SECURITY_REVIEWER
        """
        # Fetch run with agent_runs loaded
        stmt = (
            select(SecurityTeamRun)
            .options(selectinload(SecurityTeamRun.agent_runs))
            .where(SecurityTeamRun.id == team_run_id)
        )
        res = await self.session.execute(stmt)
        team_run = res.scalar_one_or_none()
        if not team_run:
            raise ValueError("Team run not found.")

        if team_run.status in [TeamRunStatus.CANCELED.value, TeamRunStatus.SUCCEEDED.value]:
            return team_run

        team_run.status = TeamRunStatus.RUNNING.value
        team_run.started_at = datetime.now(timezone.utc)
        team_run.updated_at = datetime.now(timezone.utc)
        await self.session.commit()

        # Gather approved context
        asset_stmt = select(Asset).where(Asset.id == team_run.asset_id)
        asset_res = await self.session.execute(asset_stmt)
        asset = asset_res.scalar_one_or_none()

        scan = None
        if team_run.scan_id:
            scan_stmt = select(Scan).where(Scan.id == team_run.scan_id)
            scan_res = await self.session.execute(scan_stmt)
            scan = scan_res.scalar_one_or_none()

        # Findings
        f_conds = [Finding.workspace_id == team_run.workspace_id, Finding.asset_id == team_run.asset_id]
        if team_run.scan_id:
            f_conds.append(Finding.scan_id == team_run.scan_id)
        f_stmt = (
            select(Finding)
            .options(selectinload(Finding.evidence))
            .where(and_(*f_conds))
            .order_by(desc(Finding.created_at))
            .limit(25)
        )
        f_res = await self.session.execute(f_stmt)
        findings = list(f_res.scalars().all())

        # Evidence dictionary
        evidence_by_finding: Dict[str, List[Dict[str, Any]]] = {}
        findings_data = []
        for f in findings:
            fid = str(f.id)
            findings_data.append({
                "id": fid,
                "title": f.title,
                "description": f.description,
                "severity": f.severity,
                "confidence": f.confidence,
                "cwe_ids": f.cwe_ids,
                "owasp_categories": f.owasp_categories,
                "location": f.location,
            })
            evidence_by_finding[fid] = [
                {
                    "id": str(ev.id),
                    "file_path": ev.file_path,
                    "line_start": ev.line_start,
                    "line_end": ev.line_end,
                    "title": ev.title,
                }
                for ev in (f.evidence or [])
            ]

        # Security Relationships
        rel_stmt = (
            select(SecurityRelationship)
            .where(
                and_(
                    SecurityRelationship.workspace_id == team_run.workspace_id,
                    SecurityRelationship.status.in_(["active", "confirmed"]),
                )
            )
            .limit(20)
        )
        rel_res = await self.session.execute(rel_stmt)
        relationships = list(rel_res.scalars().all())
        rel_data = [
            {
                "id": str(r.id),
                "source_finding_id": str(r.source_finding_id),
                "target_finding_id": str(r.target_finding_id),
                "relationship_type": r.relationship_type,
                "source": r.source,
                "confidence": float(r.confidence),
                "rationale": r.rationale,
            }
            for r in relationships
        ]

        # Attack Paths
        p_conds = [AttackPath.workspace_id == team_run.workspace_id]
        if team_run.scan_id:
            p_conds.append(AttackPath.scan_id == team_run.scan_id)
        p_stmt = (
            select(AttackPath)
            .options(selectinload(AttackPath.risk_snapshots))
            .where(and_(*p_conds))
            .order_by(desc(AttackPath.risk_score))
            .limit(10)
        )
        p_res = await self.session.execute(p_stmt)
        attack_paths = list(p_res.scalars().all())
        paths_data = [
            {
                "id": str(p.id),
                "name": p.name,
                "title": p.title,
                "description": p.description,
                "entry_point": p.entry_point,
                "risk_score": float(p.risk_score or 0.0),
                "risk_band": p.risk_band or "INFORMATIONAL",
                "node_count": p.node_count,
                "edge_count": p.edge_count,
            }
            for p in attack_paths
        ]

        peak_score = paths_data[0]["risk_score"] if paths_data else 0.0
        risk_band = paths_data[0]["risk_band"] if paths_data else "INFORMATIONAL"
        risk_factors = attack_paths[0].factors if attack_paths else {}

        agent_results: Dict[str, AgentResponse] = {}

        # Pipeline step runner helper
        async def run_agent_step(agent_name: str, context: Dict[str, Any], task: str) -> Optional[AgentResponse]:
            # Cancellation check
            refreshed_stmt = select(SecurityTeamRun.status).where(SecurityTeamRun.id == team_run_id)
            status_res = await self.session.execute(refreshed_stmt)
            curr_status = status_res.scalar_one_or_none()
            if curr_status == TeamRunStatus.CANCELED.value:
                logger.info(f"Team run {team_run_id} canceled before executing {agent_name}")
                return None

            agent = AgentRegistry.get(agent_name)
            if not agent:
                logger.error(f"Agent {agent_name} not found in registry")
                return None

            agent_run_db = AgentRun(
                team_run_id=team_run.id,
                workspace_id=team_run.workspace_id,
                agent_name=agent.name,
                status=AgentStatus.RUNNING.value,
                provider=self.provider.provider_name,
                prompt_version=agent.prompt_version,
                started_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(agent_run_db)
            await self.session.commit()
            await self.session.refresh(agent_run_db)

            # Audit agent start
            await self.audit_service.log(
                workspace_id=team_run.workspace_id,
                action=AuditEventType.AGENT_STARTED,
                resource_type="agent_run",
                resource_id=agent_run_db.id,
                new_state={"agent_name": agent.name, "team_run_id": str(team_run.id)},
            )

            # Execution with bounded retries
            resp: Optional[AgentResponse] = None
            for attempt in range(1, MAX_AGENT_RETRIES + 1):
                agent_req = AgentRequest(
                    team_run_id=team_run.id,
                    workspace_id=team_run.workspace_id,
                    agent_name=agent.name,
                    context=context,
                    task=task,
                )
                resp = await agent.execute(agent_req, provider=self.provider)
                if resp.status == AgentStatus.SUCCEEDED:
                    break
                logger.warning(f"[{agent.name}] Attempt {attempt} failed: {resp.error_message}")

            # Update AgentRun in DB
            agent_run_db.status = resp.status.value if resp else AgentStatus.FAILED.value
            agent_run_db.output = resp.structured_output if resp else {}
            agent_run_db.confidence = resp.confidence if resp else 0.0
            agent_run_db.completed_at = datetime.now(timezone.utc)
            agent_run_db.error_code = resp.error_code if resp else "EXECUTION_ERROR"
            agent_run_db.error_message = resp.error_message if resp else "Unknown error"
            agent_run_db.model_used = resp.model if resp else "unknown"
            agent_run_db.tokens_input = resp.tokens_input if resp else None
            agent_run_db.tokens_output = resp.tokens_output if resp else None
            agent_run_db.cost_usd = resp.cost_usd if resp else None
            await self.session.commit()

            # Audit agent completion or failure
            audit_action = AuditEventType.AGENT_COMPLETED if resp and resp.status == AgentStatus.SUCCEEDED else AuditEventType.AGENT_FAILED
            await self.audit_service.log(
                workspace_id=team_run.workspace_id,
                action=audit_action,
                resource_type="agent_run",
                resource_id=agent_run_db.id,
                new_state={"agent_name": agent.name, "status": agent_run_db.status},
            )

            return resp

        # -------------------------------------------------------------
        # 1. Recon Agent
        # -------------------------------------------------------------
        recon_ctx = {
            "asset": {
                "name": asset.name if asset else "Target",
                "type": asset.type if asset else "repository",
                "criticality": asset.criticality if asset else "medium",
                "environment": getattr(asset, "environment", "production"),
                "connection_config": asset.connection_config if asset else {},
                "description": getattr(asset, "description", "") if asset else "",
            },
            "scan": {"id": str(scan.id), "scan_type": scan.scan_type} if scan else None,
            "findings": findings_data,
        }
        recon_resp = await run_agent_step("recon", recon_ctx, "Analyze asset architectural perimeter")
        if not recon_resp:
            team_run.status = TeamRunStatus.CANCELED.value
            await self.session.commit()
            return team_run
        agent_results["recon"] = recon_resp

        # -------------------------------------------------------------
        # 2. Vulnerability Analyst Agent
        # -------------------------------------------------------------
        vuln_ctx = {
            "findings": findings_data,
            "evidence": evidence_by_finding,
        }
        vuln_resp = await run_agent_step("vulnerability_analyst", vuln_ctx, "Analyze finding depth and preconditions")
        if not vuln_resp:
            team_run.status = TeamRunStatus.CANCELED.value
            await self.session.commit()
            return team_run
        agent_results["vulnerability_analyst"] = vuln_resp

        # -------------------------------------------------------------
        # 3. Attack Path Agent
        # -------------------------------------------------------------
        path_ctx = {
            "findings": findings_data,
            "relationships": rel_data,
            "attack_paths": paths_data,
        }
        path_resp = await run_agent_step("attack_path", path_ctx, "Analyze lateral movement and transitions")
        if not path_resp:
            team_run.status = TeamRunStatus.CANCELED.value
            await self.session.commit()
            return team_run
        agent_results["attack_path"] = path_resp

        # -------------------------------------------------------------
        # 4. Risk Analyst Agent
        # -------------------------------------------------------------
        risk_ctx = {
            "attack_paths": paths_data,
            "risk_factors": risk_factors,
            "peak_score": peak_score,
            "risk_band": risk_band,
        }
        risk_resp = await run_agent_step("risk_analyst", risk_ctx, "Interpret deterministic risk factors")
        if not risk_resp:
            team_run.status = TeamRunStatus.CANCELED.value
            await self.session.commit()
            return team_run
        agent_results["risk_analyst"] = risk_resp

        # -------------------------------------------------------------
        # 5. Security Reviewer Agent
        # -------------------------------------------------------------
        rev_ctx = {
            "recon_output": agent_results.get("recon", AgentResponse(agent_name="recon", status=AgentStatus.FAILED, summary="")).structured_output,
            "vulnerability_output": agent_results.get("vulnerability_analyst", AgentResponse(agent_name="vuln", status=AgentStatus.FAILED, summary="")).structured_output,
            "attack_path_output": agent_results.get("attack_path", AgentResponse(agent_name="path", status=AgentStatus.FAILED, summary="")).structured_output,
            "risk_output": agent_results.get("risk_analyst", AgentResponse(agent_name="risk", status=AgentStatus.FAILED, summary="")).structured_output,
            "deterministic_score": peak_score,
            "deterministic_band": risk_band,
            "findings_count": len(findings_data),
            "paths_count": len(paths_data),
        }
        rev_resp = await run_agent_step("security_reviewer", rev_ctx, "Synthesize unified security assessment")
        if not rev_resp:
            team_run.status = TeamRunStatus.CANCELED.value
            await self.session.commit()
            return team_run
        agent_results["security_reviewer"] = rev_resp

        # -------------------------------------------------------------
        # Final Team Run Compilation & Status Determination
        # -------------------------------------------------------------
        all_succeeded = all(r.status == AgentStatus.SUCCEEDED for r in agent_results.values())
        reviewer_succeeded = rev_resp.status == AgentStatus.SUCCEEDED

        if all_succeeded:
            team_run.status = TeamRunStatus.SUCCEEDED.value
        elif reviewer_succeeded:
            team_run.status = TeamRunStatus.PARTIAL.value
        else:
            team_run.status = TeamRunStatus.FAILED.value

        team_run.team_summary = rev_resp.structured_output if reviewer_succeeded else {"error": "Security reviewer failed to synthesize assessment"}
        team_run.confidence = rev_resp.confidence if reviewer_succeeded else 0.0
        team_run.completed_at = datetime.now(timezone.utc)
        team_run.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(team_run)

        # Audit Final Team Run Status
        final_audit_action = {
            TeamRunStatus.SUCCEEDED.value: AuditEventType.SECURITY_TEAM_COMPLETED,
            TeamRunStatus.PARTIAL.value: AuditEventType.SECURITY_TEAM_PARTIAL,
            TeamRunStatus.FAILED.value: AuditEventType.SECURITY_TEAM_FAILED,
        }.get(team_run.status, AuditEventType.SECURITY_TEAM_COMPLETED)

        await self.audit_service.log(
            workspace_id=team_run.workspace_id,
            action=final_audit_action,
            resource_type="security_team_run",
            resource_id=team_run.id,
            new_state={"status": team_run.status, "confidence": float(team_run.confidence)},
        )

        return team_run

    async def cancel_team_run(self, team_run_id: UUID, user_id: UUID) -> SecurityTeamRun:
        """
        Safely cancels a running team run and marks remaining work as CANCELED.
        """
        stmt = select(SecurityTeamRun).where(SecurityTeamRun.id == team_run_id)
        res = await self.session.execute(stmt)
        team_run = res.scalar_one_or_none()
        if not team_run:
            raise ValueError("Team run not found.")

        if team_run.status in [TeamRunStatus.SUCCEEDED.value, TeamRunStatus.FAILED.value]:
            return team_run

        team_run.status = TeamRunStatus.CANCELED.value
        team_run.completed_at = datetime.now(timezone.utc)
        team_run.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(team_run)

        await self.audit_service.log(
            workspace_id=team_run.workspace_id,
            user_id=user_id,
            action=AuditEventType.SECURITY_TEAM_CANCELED,
            resource_type="security_team_run",
            resource_id=team_run.id,
            new_state={"status": team_run.status},
        )
        return team_run

    async def mark_human_reviewed(
        self,
        team_run_id: UUID,
        user_id: UUID,
        notes: Optional[str] = None,
    ) -> SecurityTeamRun:
        """
        Captures the explicit human review boundary.
        Agents cannot mark themselves reviewed.
        """
        stmt = select(SecurityTeamRun).where(SecurityTeamRun.id == team_run_id)
        res = await self.session.execute(stmt)
        team_run = res.scalar_one_or_none()
        if not team_run:
            raise ValueError("Team run not found.")

        team_run.reviewed_by = user_id
        team_run.reviewed_at = datetime.now(timezone.utc)
        if notes:
            team_run.review_notes = notes
        team_run.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(team_run)

        await self.audit_service.log(
            workspace_id=team_run.workspace_id,
            user_id=user_id,
            action=AuditEventType.SECURITY_TEAM_REVIEWED,
            resource_type="security_team_run",
            resource_id=team_run.id,
            new_state={"reviewed_by": str(user_id), "reviewed_at": team_run.reviewed_at.isoformat()},
        )
        return team_run
