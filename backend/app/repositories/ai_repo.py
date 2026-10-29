import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.scan import AgentRun
from app.models.finding import FindingAIAnalysis, Finding


class AIRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_agent_run(
        self,
        scan_id: uuid.UUID,
        workspace_id: uuid.UUID,
        agent_name: str,
        provider: str,
        model_used: str,
        prompt_version: str,
        input_hash: Optional[str] = None,
        input_summary: Optional[Dict[str, Any]] = None,
    ) -> AgentRun:
        run = AgentRun(
            id=uuid.uuid4(),
            scan_id=scan_id,
            workspace_id=workspace_id,
            agent_name=agent_name,
            provider=provider,
            model_used=model_used,
            prompt_version=prompt_version,
            input_hash=input_hash,
            status="running",
            input_summary=input_summary or {},
            started_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def update_agent_run(
        self,
        run_id: uuid.UUID,
        status: str,
        output_summary: Optional[Dict[str, Any]] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        cost_usd: Optional[float] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[AgentRun]:
        stmt = (
            update(AgentRun)
            .where(AgentRun.id == run_id)
            .values(
                status=status,
                output_summary=output_summary,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost_usd,
                error_code=error_code,
                error_message=error_message,
                completed_at=datetime.now(timezone.utc),
            )
            .returning(AgentRun)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_agent_run(self, run_id: uuid.UUID) -> Optional[AgentRun]:
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_agent_runs_by_scan(self, scan_id: uuid.UUID) -> List[AgentRun]:
        stmt = select(AgentRun).where(AgentRun.scan_id == scan_id).order_by(AgentRun.created_at.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_analysis_by_finding(self, finding_id: uuid.UUID) -> Optional[FindingAIAnalysis]:
        stmt = (
            select(FindingAIAnalysis)
            .where(FindingAIAnalysis.finding_id == finding_id)
            .order_by(FindingAIAnalysis.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_analyses_by_finding(self, finding_id: uuid.UUID) -> List[FindingAIAnalysis]:
        """Returns all historical AI analyses for a finding, ordered from newest to oldest."""
        stmt = (
            select(FindingAIAnalysis)
            .where(FindingAIAnalysis.finding_id == finding_id)
            .order_by(FindingAIAnalysis.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_analysis_by_id(self, analysis_id: uuid.UUID) -> Optional[FindingAIAnalysis]:
        """Retrieves a specific AI analysis record by its primary key UUID."""
        stmt = select(FindingAIAnalysis).where(FindingAIAnalysis.id == analysis_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_recent_matching_analysis(
        self,
        finding_id: uuid.UUID,
        input_hash: str,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> Optional[FindingAIAnalysis]:
        """Retrieves a matching successful analysis for idempotency/cache reuse."""
        stmt = (
            select(FindingAIAnalysis)
            .where(
                FindingAIAnalysis.finding_id == finding_id,
                FindingAIAnalysis.input_hash == input_hash,
                FindingAIAnalysis.provider == provider,
                FindingAIAnalysis.model == model,
                FindingAIAnalysis.prompt_version == prompt_version,
                FindingAIAnalysis.status == "SUCCEEDED",
            )
            .order_by(FindingAIAnalysis.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_analysis_by_hash(self, input_hash: str, prompt_version: str) -> Optional[FindingAIAnalysis]:
        stmt = (
            select(FindingAIAnalysis)
            .where(
                FindingAIAnalysis.input_hash == input_hash,
                FindingAIAnalysis.prompt_version == prompt_version
            )
            .order_by(FindingAIAnalysis.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_analyses_by_scan(self, scan_id: uuid.UUID) -> List[FindingAIAnalysis]:
        stmt = (
            select(FindingAIAnalysis)
            .join(Finding, Finding.id == FindingAIAnalysis.finding_id)
            .where(Finding.scan_id == scan_id)
            .order_by(FindingAIAnalysis.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def save_finding_analysis(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
        ai_run_id: Optional[uuid.UUID],
        summary: str,
        technical_explanation: str,
        impact: str,
        confidence: float,
        classification: str,
        uncertainty: Optional[str],
        supporting_evidence: List[Dict[str, Any]],
        model: str,
        provider: str,
        prompt_version: str,
        input_hash: Optional[str] = None,
    ) -> FindingAIAnalysis:
        # Check if an analysis already exists for this finding (finding_id is unique)
        existing = await self.get_analysis_by_finding(finding_id)
        if existing:
            existing.ai_run_id = ai_run_id
            existing.summary = summary
            existing.technical_explanation = technical_explanation
            existing.impact = impact
            existing.confidence = confidence
            existing.classification = classification
            existing.uncertainty = uncertainty
            existing.supporting_evidence = supporting_evidence
            existing.model = model
            existing.provider = provider
            existing.prompt_version = prompt_version
            existing.input_hash = input_hash
            existing.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
            return existing

        analysis = FindingAIAnalysis(
            id=uuid.uuid4(),
            finding_id=finding_id,
            ai_run_id=ai_run_id,
            workspace_id=workspace_id,
            summary=summary,
            technical_explanation=technical_explanation,
            impact=impact,
            confidence=confidence,
            classification=classification,
            uncertainty=uncertainty,
            supporting_evidence=supporting_evidence,
            model=model,
            provider=provider,
            prompt_version=prompt_version,
            input_hash=input_hash,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(analysis)
        await self.session.flush()
        return analysis

    async def create_security_analysis(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
        summary: str,
        vulnerability_type: str,
        severity_assessment: str,
        confidence: float,
        exploitability_assessment: str,
        impact_assessment: str,
        affected_component: str,
        attack_preconditions: str,
        evidence_interpretation: Dict[str, Any],
        reasoning: str,
        recommended_next_steps: str,
        uncertainty: str,
        supporting_evidence: List[Dict[str, Any]],
        model: str,
        provider: str,
        prompt_version: str,
        input_hash: str,
        status: str = "SUCCEEDED",
        created_by: Optional[uuid.UUID] = None,
        ai_run_id: Optional[uuid.UUID] = None,
        raw_analysis: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        cost_usd: Optional[float] = None,
    ) -> FindingAIAnalysis:
        """
        Creates a new immutable historical security analysis record.
        Preserves complete versioning across providers, models, and execution times.
        """
        analysis = FindingAIAnalysis(
            id=uuid.uuid4(),
            finding_id=finding_id,
            workspace_id=workspace_id,
            ai_run_id=ai_run_id,
            status=status,
            summary=summary,
            technical_explanation=reasoning,
            impact=impact_assessment,
            confidence=confidence,
            classification=vulnerability_type,
            uncertainty=uncertainty,
            vulnerability_type=vulnerability_type,
            severity_assessment=severity_assessment,
            exploitability_assessment=exploitability_assessment,
            impact_assessment=impact_assessment,
            affected_component=affected_component,
            attack_preconditions=attack_preconditions,
            evidence_interpretation=evidence_interpretation,
            reasoning=reasoning,
            recommended_next_steps=recommended_next_steps,
            raw_analysis=raw_analysis or {},
            supporting_evidence=supporting_evidence,
            model=model,
            provider=provider,
            prompt_version=prompt_version,
            input_hash=input_hash,
            created_by=created_by,
            completed_at=datetime.now(timezone.utc) if status in ("SUCCEEDED", "FAILED") else None,
            error_code=error_code,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost_usd,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(analysis)
        await self.session.flush()
        return analysis
