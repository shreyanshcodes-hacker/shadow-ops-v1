import uuid
import logging
from typing import Optional, List, Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ai.provider import get_ai_provider, AIProvider, AIRequestConfig
from app.ai.schemas import FindingAnalysisOutput, SupportingEvidenceItem
from app.ai.safety import build_safe_prompt, validate_supporting_evidence
from app.ai.cost import compute_input_hash, truncate_context
from app.models.finding import Finding, FindingAIAnalysis
from app.models.scan import Scan, AgentRun
from app.repositories.ai_repo import AIRepository
from app.repositories.scan_repo import ScanRepository

logger = logging.getLogger("shadowops.ai.manager")


class AISecurityManager:
    """
    ShadowOps AI Security Manager.
    Orchestrates evidence-grounded security analysis of verified scanner findings.

    CORE INVARIANTS:
    1. AI output is advisory (Level 3 interpretation).
    2. Trusted scanner facts and severities (Level 1/2) are NEVER modified or overwritten by AI.
    3. Non-existent evidence references are rejected/sanitized.
    4. Code and evidence inputs are redacted for sensitive secrets prior to external transmission.
    5. Token usage, estimated cost, and input hashes are tracked persistently in agent_runs.
    """

    def __init__(
        self,
        session: AsyncSession,
        provider: Optional[AIProvider] = None,
        prompt_version: Optional[str] = None,
    ):
        self.session = session
        self.ai_repo = AIRepository(session)
        self.scan_repo = ScanRepository(session)
        self.prompt_version = prompt_version or settings.AI_PROMPT_VERSION
        self.provider = provider or get_ai_provider()

    async def analyze_scan_findings(
        self,
        scan: Scan,
        force: bool = False,
        max_findings: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Analyzes findings for an authorized scan using structured AI analysis.
        """
        findings = await self.scan_repo.list_findings_by_scan(scan.id)
        limit = max_findings or settings.AI_MAX_FINDINGS_PER_RUN
        target_findings = findings[:limit]

        provider_name = self.provider.provider_name
        model_name = settings.GEMINI_MODEL if provider_name == "gemini" else settings.GROK_MODEL

        # Create AgentRun for tracking
        agent_run = await self.ai_repo.create_agent_run(
            scan_id=scan.id,
            workspace_id=scan.workspace_id,
            agent_name="ai_security_manager",
            provider=provider_name,
            model_used=model_name,
            prompt_version=self.prompt_version,
            input_summary={
                "total_findings": len(findings),
                "analyzing_findings": len(target_findings),
                "force": force,
            },
        )

        total_tokens_in = 0
        total_tokens_out = 0
        total_cost = 0.0
        analyzed_count = 0
        skipped_cached_count = 0
        analyses_list: List[FindingAIAnalysis] = []

        cfg = AIRequestConfig(
            model_name=model_name,
            temperature=0.2,
            timeout_seconds=settings.AI_REQUEST_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
            cost_cap_usd=settings.AI_COST_CAP_PER_RUN_USD,
        )

        try:
            for finding in target_findings:
                # Eagerly load or format evidence
                evidence_items = [
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
                valid_evidence_ids: Set[str] = {str(ev["id"]) for ev in evidence_items}

                # Compute deterministic input hash for caching & cost control
                input_hash = compute_input_hash(
                    finding_id=str(finding.id),
                    title=finding.title,
                    source_rule_id=finding.source_rule_id,
                    code_snippet=finding.code_snippet,
                    evidence_items=evidence_items,
                    prompt_version=self.prompt_version,
                )

                # Check if cached analysis already exists
                if not force:
                    existing_analysis = await self.ai_repo.get_analysis_by_finding(finding.id)
                    if existing_analysis and existing_analysis.input_hash == input_hash:
                        skipped_cached_count += 1
                        analyses_list.append(existing_analysis)
                        continue

                # Prepare finding dictionary
                finding_dict = {
                    "id": str(finding.id),
                    "title": finding.title,
                    "source_rule_id": finding.source_rule_id,
                    "description": finding.description,
                    "severity": finding.severity,
                    "cwe_ids": finding.cwe_ids,
                    "location": finding.location,
                    "code_snippet": truncate_context(finding.code_snippet, settings.AI_MAX_INPUT_CHARS),
                }

                # Build security-fenced prompt
                system_instruction, user_prompt = build_safe_prompt(
                    finding_dict=finding_dict,
                    evidence_items=evidence_items,
                    prompt_version=self.prompt_version,
                )

                # Call AI Provider for structured output
                structured_resp = await self.provider.generate_structured(
                    prompt=user_prompt,
                    response_schema=FindingAnalysisOutput,
                    system_instruction=system_instruction,
                    config=cfg,
                )

                parsed_output: FindingAnalysisOutput = structured_resp.parsed
                metadata = structured_resp.metadata

                # Track metrics
                total_tokens_in += metadata.prompt_tokens
                total_tokens_out += metadata.completion_tokens
                total_cost += metadata.estimated_cost_usd

                # Defend against hallucinated evidence IDs
                sanitized_evidence = validate_supporting_evidence(
                    raw_evidence_references=parsed_output.supporting_evidence,
                    valid_evidence_ids=valid_evidence_ids,
                )

                # Invariant Assertion: Scanner severity MUST NOT be overwritten
                original_severity = finding.severity

                # Persist AI Analysis
                saved_analysis = await self.ai_repo.save_finding_analysis(
                    finding_id=finding.id,
                    workspace_id=scan.workspace_id,
                    ai_run_id=agent_run.id,
                    summary=parsed_output.summary,
                    technical_explanation=parsed_output.technical_explanation,
                    impact=parsed_output.impact,
                    confidence=parsed_output.confidence,
                    classification=parsed_output.classification,
                    uncertainty=parsed_output.uncertainty,
                    supporting_evidence=sanitized_evidence,
                    model=metadata.model,
                    provider=metadata.provider,
                    prompt_version=self.prompt_version,
                    input_hash=input_hash,
                )

                # Verify invariant
                assert finding.severity == original_severity, "CRITICAL ERROR: AI mutated scanner severity!"

                analyses_list.append(saved_analysis)
                analyzed_count += 1

            # Update AgentRun to completed
            await self.ai_repo.update_agent_run(
                run_id=agent_run.id,
                status="completed",
                output_summary={
                    "findings_analyzed": analyzed_count,
                    "findings_skipped_cached": skipped_cached_count,
                    "total_analyzed": analyzed_count + skipped_cached_count,
                },
                tokens_input=total_tokens_in,
                tokens_output=total_tokens_out,
                cost_usd=round(total_cost, 6),
            )

            return {
                "scan_id": scan.id,
                "ai_run_id": agent_run.id,
                "status": "completed",
                "findings_analyzed": analyzed_count,
                "findings_skipped_cached": skipped_cached_count,
                "total_findings": len(findings),
                "analyses": analyses_list,
            }

        except Exception as e:
            logger.exception(f"AI Security Manager failed for scan {scan.id}: {str(e)}")
            await self.ai_repo.update_agent_run(
                run_id=agent_run.id,
                status="failed",
                error_code="AI_ANALYSIS_FAILED",
                error_message=str(e),
                tokens_input=total_tokens_in,
                tokens_output=total_tokens_out,
                cost_usd=round(total_cost, 6),
            )
            raise

    async def analyze_single_finding(
        self,
        finding: Finding,
        force: bool = False,
    ) -> FindingAIAnalysis:
        """
        Analyzes a single finding on-demand.
        """
        evidence_items = [
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
        valid_evidence_ids: Set[str] = {str(ev["id"]) for ev in evidence_items}

        input_hash = compute_input_hash(
            finding_id=str(finding.id),
            title=finding.title,
            source_rule_id=finding.source_rule_id,
            code_snippet=finding.code_snippet,
            evidence_items=evidence_items,
            prompt_version=self.prompt_version,
        )

        if not force:
            existing = await self.ai_repo.get_analysis_by_finding(finding.id)
            if existing and existing.input_hash == input_hash:
                return existing

        provider_name = self.provider.provider_name
        model_name = settings.GEMINI_MODEL if provider_name == "gemini" else settings.GROK_MODEL

        finding_dict = {
            "id": str(finding.id),
            "title": finding.title,
            "source_rule_id": finding.source_rule_id,
            "description": finding.description,
            "severity": finding.severity,
            "cwe_ids": finding.cwe_ids,
            "location": finding.location,
            "code_snippet": truncate_context(finding.code_snippet, settings.AI_MAX_INPUT_CHARS),
        }

        system_instruction, user_prompt = build_safe_prompt(
            finding_dict=finding_dict,
            evidence_items=evidence_items,
            prompt_version=self.prompt_version,
        )

        cfg = AIRequestConfig(
            model_name=model_name,
            temperature=0.2,
            timeout_seconds=settings.AI_REQUEST_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
        )

        resp = await self.provider.generate_structured(
            prompt=user_prompt,
            response_schema=FindingAnalysisOutput,
            system_instruction=system_instruction,
            config=cfg,
        )

        parsed: FindingAnalysisOutput = resp.parsed
        sanitized_evidence = validate_supporting_evidence(parsed.supporting_evidence, valid_evidence_ids)

        return await self.ai_repo.save_finding_analysis(
            finding_id=finding.id,
            workspace_id=finding.workspace_id,
            ai_run_id=None,
            summary=parsed.summary,
            technical_explanation=parsed.technical_explanation,
            impact=parsed.impact,
            confidence=parsed.confidence,
            classification=parsed.classification,
            uncertainty=parsed.uncertainty,
            supporting_evidence=sanitized_evidence,
            model=resp.metadata.model,
            provider=resp.metadata.provider,
            prompt_version=self.prompt_version,
            input_hash=input_hash,
        )
