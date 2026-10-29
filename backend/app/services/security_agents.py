"""
Specialized Analytical Security Agents & Agent Registry

Defines the 5 core specialized agents:
1. ReconAgent
2. VulnerabilityAnalystAgent
3. AttackPathAgent
4. RiskAnalystAgent
5. SecurityReviewerAgent

CORE SAFETY INVARIANT:
Agents are analytical workers, NOT autonomous operators.
They cannot execute shell commands, exploit targets, commit code, or alter deterministic risk scores.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional, List
import time
import logging
from pydantic import BaseModel

from app.schemas.security_team import (
    AgentRequest,
    AgentResponse,
    AgentStatus,
    ReconOutput,
    VulnerabilityAnalystOutput,
    AttackPathAnalystOutput,
    RiskAnalystOutput,
    TeamAssessment,
)
from app.services.security_team_context import (
    ReconContextBuilder,
    VulnerabilityContextBuilder,
    AttackPathContextBuilder,
    RiskContextBuilder,
    ReviewerContextBuilder,
)
from app.ai.provider import AIProvider, get_ai_provider, AIRequestConfig

logger = logging.getLogger("shadowops.security_agents")


class BaseSecurityAgent(ABC):
    name: str
    prompt_version: str
    response_schema: Type[BaseModel]

    @abstractmethod
    def build_prompt_and_system(self, context: Dict[str, Any]) -> tuple[str, str]:
        pass

    async def execute(
        self,
        request: AgentRequest,
        provider: Optional[AIProvider] = None,
    ) -> AgentResponse:
        start_time = time.time()
        ai_provider = provider or get_ai_provider()

        try:
            system_instruction, user_prompt = self.build_prompt_and_system(request.context)
        except Exception as e:
            logger.error(f"[{self.name}] Prompt construction failure: {e}")
            return AgentResponse(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                summary=f"Failed to construct prompt: {str(e)}",
                confidence=0.0,
                error_code="PROMPT_BUILD_ERROR",
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
                provider=ai_provider.provider_name,
                prompt_version=self.prompt_version,
            )

        config = AIRequestConfig(
            temperature=0.2,
            timeout_seconds=30,
            max_retries=1,
        )

        try:
            res = await ai_provider.generate_structured(
                prompt=user_prompt,
                response_schema=self.response_schema,
                system_instruction=system_instruction,
                config=config,
            )

            parsed: BaseModel = res.parsed
            raw_dict = res.raw_json or parsed.model_dump()
            duration_ms = int((time.time() - start_time) * 1000)

            # Extract confidence and uncertainty from structured models
            confidence = getattr(parsed, "confidence", getattr(parsed, "overall_confidence", 0.8))
            uncertainty = getattr(parsed, "uncertainty", "")
            if isinstance(getattr(parsed, "uncertainties", None), list):
                uncertainty = "; ".join(getattr(parsed, "uncertainties", []))

            # Extract evidence references
            evidence_refs = []
            if hasattr(parsed, "evidence_references") and isinstance(parsed.evidence_references, list):
                evidence_refs = [str(e) for e in parsed.evidence_references]
            elif hasattr(parsed, "interpretations"):
                for item in getattr(parsed, "interpretations", []):
                    if isinstance(item, dict) and item.get("missing_evidence"):
                        evidence_refs.extend(item.get("missing_evidence"))

            return AgentResponse(
                agent_name=self.name,
                status=AgentStatus.SUCCEEDED,
                summary=f"Completed {self.name} analytical evaluation.",
                structured_output=raw_dict,
                confidence=round(max(0.0, min(1.0, float(confidence))), 2),
                uncertainty=str(uncertainty),
                evidence_references=evidence_refs,
                warnings=[],
                duration_ms=duration_ms,
                provider=res.metadata.provider,
                model=res.metadata.model,
                prompt_version=self.prompt_version,
                tokens_input=res.metadata.prompt_tokens,
                tokens_output=res.metadata.completion_tokens,
                cost_usd=res.metadata.estimated_cost_usd,
            )

        except Exception as e:
            logger.error(f"[{self.name}] Provider execution failed: {e}")
            duration_ms = int((time.time() - start_time) * 1000)
            return AgentResponse(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                summary=f"{self.name} failed during model execution.",
                confidence=0.0,
                error_code="PROVIDER_EXECUTION_FAILURE",
                error_message=str(e),
                duration_ms=duration_ms,
                provider=ai_provider.provider_name,
                prompt_version=self.prompt_version,
            )


# ==============================================================================
# 1. Recon Agent
# ==============================================================================

class ReconAgent(BaseSecurityAgent):
    name = "recon"
    prompt_version = ReconContextBuilder.PROMPT_VERSION
    response_schema = ReconOutput

    def build_prompt_and_system(self, context: Dict[str, Any]) -> tuple[str, str]:
        asset_data = context.get("asset", {})
        scan_data = context.get("scan")
        findings_summary = context.get("findings", [])
        return ReconContextBuilder.build(asset_data, scan_data, findings_summary)


# ==============================================================================
# 2. Vulnerability Analyst Agent
# ==============================================================================

class VulnerabilityAnalystAgent(BaseSecurityAgent):
    name = "vulnerability_analyst"
    prompt_version = VulnerabilityContextBuilder.PROMPT_VERSION
    response_schema = VulnerabilityAnalystOutput

    def build_prompt_and_system(self, context: Dict[str, Any]) -> tuple[str, str]:
        findings = context.get("findings", [])
        evidence = context.get("evidence", {})
        return VulnerabilityContextBuilder.build(findings, evidence)


# ==============================================================================
# 3. Attack Path Agent
# ==============================================================================

class AttackPathAgent(BaseSecurityAgent):
    name = "attack_path"
    prompt_version = AttackPathContextBuilder.PROMPT_VERSION
    response_schema = AttackPathAnalystOutput

    def build_prompt_and_system(self, context: Dict[str, Any]) -> tuple[str, str]:
        findings = context.get("findings", [])
        relationships = context.get("relationships", [])
        attack_paths = context.get("attack_paths", [])
        return AttackPathContextBuilder.build(findings, relationships, attack_paths)


# ==============================================================================
# 4. Risk Analyst Agent
# ==============================================================================

class RiskAnalystAgent(BaseSecurityAgent):
    name = "risk_analyst"
    prompt_version = RiskContextBuilder.PROMPT_VERSION
    response_schema = RiskAnalystOutput

    def build_prompt_and_system(self, context: Dict[str, Any]) -> tuple[str, str]:
        attack_paths = context.get("attack_paths", [])
        risk_factors = context.get("risk_factors", {})
        peak_score = float(context.get("peak_score", 0.0))
        risk_band = str(context.get("risk_band", "INFORMATIONAL"))
        return RiskContextBuilder.build(attack_paths, risk_factors, peak_score, risk_band)


# ==============================================================================
# 5. Security Reviewer Agent
# ==============================================================================

class SecurityReviewerAgent(BaseSecurityAgent):
    name = "security_reviewer"
    prompt_version = ReviewerContextBuilder.PROMPT_VERSION
    response_schema = TeamAssessment

    def build_prompt_and_system(self, context: Dict[str, Any]) -> tuple[str, str]:
        recon_output = context.get("recon_output", {})
        vulnerability_output = context.get("vulnerability_output", {})
        attack_path_output = context.get("attack_path_output", {})
        risk_output = context.get("risk_output", {})
        deterministic_score = float(context.get("deterministic_score", 0.0))
        deterministic_band = str(context.get("deterministic_band", "INFORMATIONAL"))
        findings_count = int(context.get("findings_count", 0))
        paths_count = int(context.get("paths_count", 0))
        return ReviewerContextBuilder.build(
            recon_output=recon_output,
            vulnerability_output=vulnerability_output,
            attack_path_output=attack_path_output,
            risk_output=risk_output,
            deterministic_score=deterministic_score,
            deterministic_band=deterministic_band,
            findings_count=findings_count,
            paths_count=paths_count,
        )


# ==============================================================================
# Centralized Agent Registry
# ==============================================================================

class AgentRegistry:
    """
    Centralized discovery registry for analytical security agents.
    Prevents hardcoded agent branching throughout the application.
    """
    _agents: Dict[str, BaseSecurityAgent] = {
        "recon": ReconAgent(),
        "vulnerability_analyst": VulnerabilityAnalystAgent(),
        "attack_path": AttackPathAgent(),
        "risk_analyst": RiskAnalystAgent(),
        "security_reviewer": SecurityReviewerAgent(),
    }

    @classmethod
    def get(cls, agent_name: str) -> Optional[BaseSecurityAgent]:
        return cls._agents.get(agent_name.lower())

    @classmethod
    def list_agents(cls) -> List[str]:
        return list(cls._agents.keys())

    @classmethod
    def register(cls, agent: BaseSecurityAgent) -> None:
        cls._agents[agent.name.lower()] = agent
