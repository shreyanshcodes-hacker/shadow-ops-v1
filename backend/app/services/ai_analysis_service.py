import uuid
import logging
from typing import Optional, List, Dict, Any, Set
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.profile import Profile
from app.models.finding import Finding, FindingAIAnalysis
from app.models.asset import Asset
from app.repositories.ai_repo import AIRepository
from app.services.workspace_service import WorkspaceService
from app.services.audit_service import AuditService
from app.schemas.audit import AuditEventType
from app.ai.provider import get_ai_provider, AIProvider, AIRequestConfig
from app.ai.schemas import SecurityAnalysis
from app.ai.context_builder import SecurityAnalysisContextBuilder
from app.ai.prompts import build_security_analyst_prompt, PROMPT_VERSION_V1
from app.ai.safety import validate_supporting_evidence
from app.ai.cost import compute_input_hash

logger = logging.getLogger("shadowops.ai.analyst_service")


class AIAnalysisService:
    """
    Stage 5 AI Security Analyst Lifecycle Service.
    Enforces the complete 12-step analysis workflow with multi-tenant isolation,
    data minimization, prompt injection fencing, and audit logging.
    """

    def __init__(
        self,
        session: AsyncSession,
        provider: Optional[AIProvider] = None,
        prompt_version: str = PROMPT_VERSION_V1,
    ):
        self.session = session
        self.ai_repo = AIRepository(session)
        self.workspace_service = WorkspaceService(session)
        self.audit_service = AuditService(session)
        self.prompt_version = prompt_version
        self.provider = provider or get_ai_provider()

    async def analyze_finding(
        self,
        finding_id: uuid.UUID,
        current_user: Profile,
        force: bool = False,
        provider_override: Optional[str] = None,
    ) -> FindingAIAnalysis:
        # Step 1: User is already verified via FastAPI get_current_user dependency

        # Step 2 & 3: Load Finding with Evidence and Asset, verify workspace access
        stmt = (
            select(Finding)
            .options(
                selectinload(Finding.evidence),
            )
            .where(Finding.id == finding_id)
        )
        res = await self.session.execute(stmt)
        finding = res.scalar_one_or_none()
        if not finding:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

        # Verify workspace membership
        await self.workspace_service.get_workspace(finding.workspace_id, current_user.id)

        # Load Asset for context
        asset_stmt = select(Asset).where(Asset.id == finding.asset_id)
        asset_res = await self.session.execute(asset_stmt)
        asset = asset_res.scalar_one_or_none()

        # Step 4: Resolve Provider & Model
        provider = self.provider
        if provider_override:
            provider = get_ai_provider(provider_override)

        provider_name = provider.provider_name
        if provider_name == "gemini":
            model_name = settings.GEMINI_MODEL
        elif provider_name == "grok":
            model_name = settings.GROK_MODEL
        else:
            model_name = getattr(provider, "default_model", None) or "fake-test-model"

        # Step 5: Format evidence and compute deterministic input hash for idempotency
        evidence_dicts = [
            {
                "id": str(ev.id),
                "evidence_type": ev.evidence_type,
                "title": ev.title,
                "file_path": ev.file_path,
                "line_start": ev.line_start,
                "line_end": ev.line_end,
                "content": ev.content,
            }
            for ev in (finding.evidence or [])
        ]
        valid_evidence_ids: Set[str] = {str(ev["id"]) for ev in evidence_dicts}

        input_hash = compute_input_hash(
            finding_id=str(finding.id),
            title=finding.title,
            source_rule_id=finding.source_rule_id,
            code_snippet=finding.code_snippet,
            evidence_items=evidence_dicts,
            prompt_version=self.prompt_version,
        )

        # Step 6: Idempotency Check (Reuse recent analysis if matches and force == False)
        if not force:
            recent_cached = await self.ai_repo.get_recent_matching_analysis(
                finding_id=finding.id,
                input_hash=input_hash,
                provider=provider_name,
                model=model_name,
                prompt_version=self.prompt_version,
            )
            if recent_cached:
                logger.info(f"Reusing cached AI analysis {recent_cached.id} for finding {finding.id}")
                return recent_cached

        # Audit event: AI Analysis Requested & Started
        await self.audit_service.log(
            workspace_id=finding.workspace_id,
            user_id=current_user.id,
            action=AuditEventType.AI_ANALYSIS_STARTED,
            resource_type="finding",
            resource_id=finding.id,
            new_state={
                "provider": provider_name,
                "model": model_name,
                "prompt_version": self.prompt_version,
                "force": force,
            },
        )

        # Step 7: Build Minimized & Sanitized Context
        finding_dict = {
            "id": str(finding.id),
            "title": finding.title,
            "source": finding.source,
            "source_rule_id": finding.source_rule_id,
            "severity": finding.severity,
            "description": finding.description,
            "cwe_ids": finding.cwe_ids,
            "owasp_categories": finding.owasp_categories,
            "location": finding.location,
            "code_snippet": finding.code_snippet,
        }
        asset_dict = {
            "name": asset.name if asset else "Target Repository",
            "type": asset.type if asset else "repository",
            "environment": "production",
        }

        context = SecurityAnalysisContextBuilder.build(
            finding_dict=finding_dict,
            asset_dict=asset_dict,
            raw_evidence_list=evidence_dicts,
            max_code_chars=settings.AI_MAX_INPUT_CHARS,
        )

        # Step 8: Build Safe Prompt Fences
        system_instruction, user_prompt = build_security_analyst_prompt(
            context=context,
            prompt_version=self.prompt_version,
        )

        cfg = AIRequestConfig(
            model_name=model_name,
            temperature=0.2,
            timeout_seconds=settings.AI_REQUEST_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
        )

        # Step 9 & 10: Invoke Provider with Safe Error Boundary
        try:
            resp = await provider.generate_structured(
                prompt=user_prompt,
                response_schema=SecurityAnalysis,
                system_instruction=system_instruction,
                config=cfg,
            )
        except Exception as e:
            logger.error(f"AI Provider call failed for finding {finding.id}: {str(e)}")
            # Persist failure record
            failed_analysis = await self.ai_repo.create_security_analysis(
                finding_id=finding.id,
                workspace_id=finding.workspace_id,
                status="FAILED",
                summary="AI Security Analyst request failed.",
                vulnerability_type="Analysis Error",
                severity_assessment="unknown",
                confidence=0.0,
                exploitability_assessment="Unavailable",
                impact_assessment="Unavailable",
                affected_component="Unknown",
                attack_preconditions="Unavailable",
                evidence_interpretation={"observed": [], "inferred": [], "uncertain": []},
                reasoning="Provider invocation encountered an error.",
                recommended_next_steps="Retry request or check AI provider credentials.",
                uncertainty="Analysis could not be generated.",
                supporting_evidence=[],
                model=model_name,
                provider=provider_name,
                prompt_version=self.prompt_version,
                input_hash=input_hash,
                created_by=current_user.id,
                error_code="AI_ANALYSIS_PROVIDER_UNAVAILABLE",
            )
            await self.audit_service.log(
                workspace_id=finding.workspace_id,
                user_id=current_user.id,
                action=AuditEventType.AI_ANALYSIS_FAILED,
                resource_type="finding",
                resource_id=finding.id,
                new_state={"analysis_id": str(failed_analysis.id), "error": "AI_ANALYSIS_PROVIDER_UNAVAILABLE"},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI_ANALYSIS_PROVIDER_UNAVAILABLE: The AI provider is temporarily unavailable or credentials are unconfigured.",
            )

        parsed_analysis: SecurityAnalysis = resp.parsed
        metadata = resp.metadata

        # Step 11: Validate Supporting Evidence IDs (Strip Hallucinations)
        sanitized_evidence = validate_supporting_evidence(
            raw_evidence_references=parsed_analysis.supporting_evidence,
            valid_evidence_ids=valid_evidence_ids,
        )

        # Critical Security Invariant Check: Scanner severity MUST NOT be modified
        assert finding.severity == finding_dict["severity"], "CRITICAL: Scanner severity modified by AI operation!"

        # Step 12: Persist Structured Analysis & Log Completion
        saved_analysis = await self.ai_repo.create_security_analysis(
            finding_id=finding.id,
            workspace_id=finding.workspace_id,
            status="SUCCEEDED",
            summary=parsed_analysis.summary,
            vulnerability_type=parsed_analysis.vulnerability_type,
            severity_assessment=parsed_analysis.severity_assessment,
            confidence=parsed_analysis.confidence,
            exploitability_assessment=parsed_analysis.exploitability_assessment,
            impact_assessment=parsed_analysis.impact_assessment,
            affected_component=parsed_analysis.affected_component,
            attack_preconditions=parsed_analysis.attack_preconditions,
            evidence_interpretation=parsed_analysis.evidence_interpretation.model_dump(),
            reasoning=parsed_analysis.reasoning,
            recommended_next_steps=parsed_analysis.recommended_next_steps,
            uncertainty=parsed_analysis.uncertainty,
            supporting_evidence=sanitized_evidence,
            model=metadata.model,
            provider=metadata.provider,
            prompt_version=self.prompt_version,
            input_hash=input_hash,
            created_by=current_user.id,
            raw_analysis=resp.raw_json,
            tokens_input=metadata.prompt_tokens,
            tokens_output=metadata.completion_tokens,
            cost_usd=metadata.estimated_cost_usd,
        )

        await self.audit_service.log(
            workspace_id=finding.workspace_id,
            user_id=current_user.id,
            action=AuditEventType.AI_ANALYSIS_COMPLETED,
            resource_type="finding",
            resource_id=finding.id,
            new_state={
                "analysis_id": str(saved_analysis.id),
                "confidence": float(saved_analysis.confidence),
                "provider": metadata.provider,
                "model": metadata.model,
            },
        )

        return saved_analysis

    async def list_analyses_for_finding(
        self,
        finding_id: uuid.UUID,
        current_user: Profile,
    ) -> List[FindingAIAnalysis]:
        """Lists historical analyses for a finding after verifying workspace access."""
        stmt = select(Finding).where(Finding.id == finding_id)
        res = await self.session.execute(stmt)
        finding = res.scalar_one_or_none()
        if not finding:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

        await self.workspace_service.get_workspace(finding.workspace_id, current_user.id)
        return await self.ai_repo.get_analyses_by_finding(finding_id)

    async def get_analysis_by_id(
        self,
        analysis_id: uuid.UUID,
        current_user: Profile,
    ) -> FindingAIAnalysis:
        """Retrieves a specific analysis record after verifying workspace access."""
        analysis = await self.ai_repo.get_analysis_by_id(analysis_id)
        if not analysis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI analysis not found")

        await self.workspace_service.get_workspace(analysis.workspace_id, current_user.id)
        return analysis
