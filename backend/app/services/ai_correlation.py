"""
AI Relationship Correlation Service

Invokes the configured AI Provider to analyze pairs of security findings
and infer contextual attack transitions, data flows, and compounding relationships.

IMPORTANT SAFETY CONSTRAINTS:
- AI may suggest relationships, but tagged strictly as source='AI_SUGGESTED'.
- Untrusted inputs are fenced and sanitized.
- Returned relationship types are checked against an explicit allowlist.
- Deterministic backend logic retains authoritative control.
"""

from typing import Optional, Dict, Any, List
from app.models.finding import Finding
from app.ai.provider import get_ai_provider, AIRequestConfig
from app.ai.schemas import AIRelationshipSuggestion
from app.ai.safety import redact_secrets
from app.schemas.attack_path import RelationshipType, RelationshipSource

ALLOWED_RELATIONSHIPS = {r.value for r in RelationshipType}

SYSTEM_INSTRUCTION = """You are a senior cybersecurity attack-path analyst for ShadowOps.
Your task is to analyze two security findings from the same workspace and determine if there is a plausible, causal, or compounding attack relationship between them.

Allowed relationship types:
- DEPENDS_ON: Target finding requires source finding to exist or be reachable first.
- ENABLES: Source finding directly facilitates or bypasses barriers to exploit target finding.
- EXPOSES: Source finding leaks secrets/credentials or access vectors reaching target finding.
- LEADS_TO: Exploiting source finding naturally advances attacker to target finding.
- SHARES_COMPONENT: Both findings reside in or affect the same software component/service.
- SHARES_ENTRY_POINT: Both findings share common attack surface or entry gateway.
- SHARES_DATA_FLOW: Data tainted or controlled in source finding flows into target finding.
- AMPLIFIES: Combined presence of both findings significantly increases overall risk.

Output must strictly adhere to the structured schema.
If no plausible security connection exists, set has_relationship=false and explain why in rationale."""


class AICorrelationService:
    @staticmethod
    async def analyze_relationship(
        finding_a: Finding,
        finding_b: Finding,
        evidence_a: Optional[List[Dict[str, Any]]] = None,
        evidence_b: Optional[List[Dict[str, Any]]] = None,
        provider_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate two findings using LLM structured reasoning.
        Returns a validated relationship dictionary or None.
        """
        if finding_a.id == finding_b.id:
            return None
        if finding_a.workspace_id != finding_b.workspace_id:
            return None

        # Redact any sensitive content in titles or descriptions
        title_a = redact_secrets(finding_a.title)
        desc_a = redact_secrets(finding_a.description)
        title_b = redact_secrets(finding_b.title)
        desc_b = redact_secrets(finding_b.description)

        # Build structurally fenced prompt
        prompt = f"""
<security_analysis_context>
Analyze the following two security findings for contextual relationships.

<finding_a>
Finding ID: {finding_a.id}
Title: {title_a}
Severity: {finding_a.severity}
CWEs: {finding_a.cwe_ids}
OWASP: {finding_a.owasp_categories}
Description: {desc_a[:500]}
Evidence Summary: {str(evidence_a)[:400] if evidence_a else "None"}
</finding_a>

<finding_b>
Finding ID: {finding_b.id}
Title: {title_b}
Severity: {finding_b.severity}
CWEs: {finding_b.cwe_ids}
OWASP: {finding_b.owasp_categories}
Description: {desc_b[:500]}
Evidence Summary: {str(evidence_b)[:400] if evidence_b else "None"}
</finding_b>

Determine if finding A and finding B exhibit any of the allowed security relationships.
</security_analysis_context>
"""

        provider = get_ai_provider(provider_name)
        config = AIRequestConfig(temperature=0.2, timeout_seconds=30)

        response = await provider.generate_structured(
            prompt=prompt,
            response_schema=AIRelationshipSuggestion,
            system_instruction=SYSTEM_INSTRUCTION,
            config=config,
        )

        parsed: AIRelationshipSuggestion = response.parsed
        if not parsed.has_relationship:
            return None

        # Validate relationship type against allowlist
        rel_type = (parsed.relationship_type or "").upper().strip()
        if rel_type not in ALLOWED_RELATIONSHIPS:
            return None

        # Enforce bounded confidence
        conf = max(0.0, min(1.0, float(parsed.confidence)))
        if conf < 0.4:
            return None

        return {
            "source_finding_id": finding_a.id,
            "target_finding_id": finding_b.id,
            "relationship_type": rel_type,
            "confidence": round(conf, 2),
            "source": RelationshipSource.AI_SUGGESTED.value,
            "rationale": parsed.rationale,
            "evidence_reference": {
                "attack_vector_step": parsed.attack_vector_step,
                "evidence_connection": parsed.evidence_connection,
                "ai_model": response.metadata.model,
                "ai_provider": response.metadata.provider,
            },
        }
