import re
from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel

from app.ai.provider import (
    AIProvider,
    AIRequestConfig,
    AITextResponse,
    AIStructuredResponse,
    AIResponseMetadata,
)
from app.ai.schemas import SecurityAnalysis, EvidenceInterpretation, AIRelationshipSuggestion
from app.schemas.security_team import (
    ReconOutput,
    VulnerabilityAnalystOutput,
    VulnerabilityItemAnalysis,
    AttackPathAnalystOutput,
    RiskAnalystOutput,
    TeamAssessment,
)

T = TypeVar("T", bound=BaseModel)


class FakeAIProvider(AIProvider):
    """
    Deterministic test double provider ONLY for automated testing environments.
    Guarantees deterministic, reproducible, schema-compliant responses without calling external networks.
    NEVER enabled or deployed in production.
    """
    provider_name = "fake_test_provider"

    def __init__(self, override_confidence: float = 0.88, should_fail: bool = False, fail_error_msg: str = "Simulated provider failure"):
        self.override_confidence = override_confidence
        self.should_fail = should_fail
        self.fail_error_msg = fail_error_msg

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AITextResponse:
        if self.should_fail:
            raise RuntimeError(self.fail_error_msg)

        content = "[FakeAIProvider]: Deterministic test evaluation response."
        metadata = AIResponseMetadata(
            provider=self.provider_name,
            model="fake-test-model",
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(content) // 4,
            total_tokens=(len(prompt) + len(content)) // 4,
            estimated_cost_usd=0.0,
            latency_ms=5,
        )
        return AITextResponse(content=content, metadata=metadata)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AIStructuredResponse:
        if self.should_fail:
            raise RuntimeError(self.fail_error_msg)

        # Extract evidence IDs from prompt to generate realistic grounded references
        ev_ids = re.findall(r"Evidence ID:\s*([a-f0-9\-]+)", prompt)
        supporting = []
        for eid in ev_ids[:2]:
            supporting.append({
                "evidence_id": eid,
                "relevance": "Confirmed vulnerable code pattern at specified line location.",
                "quote_or_reference": "AST token match in target file."
            })

        # Build schema-specific deterministic mock data
        if response_schema == SecurityAnalysis:
            mock_data = {
                "summary": "Deterministic test analysis: Potential input validation vulnerability identified in analyzed source.",
                "vulnerability_type": "SQL Injection / Input Validation",
                "severity_assessment": "high",
                "confidence": self.override_confidence,
                "exploitability_assessment": "Easily exploitable if the function parameter is directly reachable via HTTP routing.",
                "impact_assessment": "Unauthorized database reads and potential data modification.",
                "affected_component": "server/handlers.py",
                "attack_preconditions": "Attacker must possess network access to the exposed API endpoint.",
                "evidence_interpretation": {
                    "observed": ["Semgrep detected rule match at line 42", "String concatenation detected in execute() call"],
                    "inferred": ["Query construction permits direct parameter injection if untrusted input is passed"],
                    "uncertain": ["Dynamic reachability from public routers requires runtime request validation"]
                },
                "reasoning": "The AST snippet confirms untrusted parameters are concatenated directly into the SQL string.",
                "recommended_next_steps": "Inspect the caller of this handler to determine if sanitization or parameterization is applied.",
                "uncertainty": "Static analysis only; runtime parameter flow not dynamically traced.",
                "supporting_evidence": supporting,
            }
        elif response_schema == AIRelationshipSuggestion:
            mock_data = {
                "has_relationship": True,
                "relationship_type": "ENABLES",
                "confidence": self.override_confidence,
                "rationale": "Finding A exposes or bypasses a trust boundary that directly enables exploitation of Finding B.",
                "attack_vector_step": "Attacker leverages bypassed auth/input weakness in finding A to reach vulnerable handler in finding B.",
                "evidence_connection": "Both findings share the incoming request processing pipeline.",
            }
        elif response_schema == ReconOutput:
            mock_data = {
                "relevant_components": ["auth_handler", "user_service", "database_gateway"],
                "entry_points": ["/api/v1/auth/login", "/api/v1/users/profile"],
                "security_boundaries": ["JWT Verification Barrier", "Database Isolation Layer"],
                "exposed_areas": ["Public API Route", "Unauthenticated Login Handler"],
                "uncertainty": "Dynamic reverse proxy WAF configurations not modeled in static repo inspection.",
                "observations": ["Repository implements multi-layer authentication routing."],
            }
        elif response_schema == VulnerabilityAnalystOutput:
            finding_ids = re.findall(r'<finding id="([a-f0-9\-]+)">', prompt)
            interpretations = []
            for fid in (finding_ids or ["finding-default-id"])[:5]:
                interpretations.append({
                    "finding_id": fid,
                    "vulnerability_interpretation": "Input validation flaw permitting arbitrary parameter flow.",
                    "preconditions": "Attacker must reach the unauthenticated endpoint with custom payload.",
                    "potential_impact": "Unauthorized extraction of user profile data from backend datastore.",
                    "confidence": self.override_confidence,
                    "missing_evidence": ["Runtime HTTP trace", "ORM sanitization confirmation"],
                    "recommended_investigation": "Inspect upstream middleware parameter sanitizers.",
                })
            mock_data = {
                "findings_analyzed": len(interpretations),
                "interpretations": interpretations,
                "uncertainty": "Static pattern match without runtime taint trace.",
            }
        elif response_schema == AttackPathAnalystOutput:
            mock_data = {
                "candidate_relationships": [
                    {"type": "ENABLES", "rationale": "Bypassed credential barrier enables direct SQL access."}
                ],
                "path_observations": ["Exploit chain demonstrates end-to-end lateral traversal to database."],
                "confidence": self.override_confidence,
                "missing_evidence": ["Network zone firewall rules"],
                "explanation": "Attacker exploits exposed entry point to compromise data store.",
                "uncertainty": "Intermediate network segregation may prevent hop 2.",
            }
        elif response_schema == RiskAnalystOutput:
            mock_data = {
                "deterministic_score_reference": 85.0,
                "risk_band": "CRITICAL",
                "explanation": "Deterministic score reflects compounding critical vulnerability severity and high asset importance.",
                "important_contributing_factors": [
                    "Finding Severity: Critical database injection (+30.0 pts)",
                    "Exploitability: Unauthenticated direct reachability (+20.0 pts)",
                    "Asset Criticality: Production user datastore (+20.0 pts)",
                ],
                "uncertainty": "Internal network firewall policy could lower actual exploitability in practice.",
                "recommended_human_review_priorities": [
                    "Validate authentication boundary on entry point",
                    "Verify parameterized queries on database handler",
                ],
            }
        elif response_schema == TeamAssessment:
            mock_data = {
                "review_status": "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED",
                "executive_summary": "Unified security assessment: Critical exposure chain identified progressing from public API to database.",
                "key_security_concerns": [
                    "Unauthenticated entry point exposes backend database interface",
                    "Compounded risk from multiple co-located findings",
                ],
                "highest_priority_findings": ["Database Query Injection", "Hardcoded Secret"],
                "highest_priority_attack_paths": ["Exploit chain: Auth bypass -> SQL Injection"],
                "risk_interpretation": "Deterministic risk engine calculated CRITICAL (85.0/100). Urgently requires human review.",
                "uncertainties": [
                    "Recon agent: WAF configurations unverified",
                    "Vulnerability analyst: dynamic reachability requires runtime confirmation",
                ],
                "conflicting_assessments": [],
                "recommended_human_actions": [
                    "Immediately rotate exposed credentials",
                    "Deploy parameter validation on vulnerable query endpoints",
                    "Enforce strict authentication middleware on exposed routes",
                ],
                "overall_confidence": self.override_confidence,
                "evidence_references": [s["evidence_id"] for s in supporting] if supporting else ["evidence-ref-1"],
            }
        elif response_schema.__name__ == "AIRemediationProposalOutput":
            target_file_match = re.search(r"Target File:\s*([^\s\n]+)", prompt)
            target_f = target_file_match.group(1) if target_file_match else "app/main.py"
            diff = f"""--- a/{target_f}
+++ b/{target_f}
@@ -10,3 +10,3 @@
-cursor.execute(f"SELECT * FROM users WHERE id = {{user_id}}")
+cursor.execute("SELECT * FROM users WHERE id = :id", {{"id": user_id}})
"""
            mock_data = {
                "proposal_title": f"Parameterized Binding Fix for {target_f}",
                "vulnerability_addressed": "SQL Injection vulnerability via untrusted interpolation",
                "root_cause_explanation": "Direct interpolation of user input allows malicious SQL payload injection.",
                "proposed_solution": "Use parameterized bindings supported by the database query interface.",
                "affected_file_paths": [target_f],
                "unified_diff": diff,
                "expected_security_benefit": "Completely mitigates SQL injection risk on the targeted query.",
                "possible_compatibility_risks": ["Verify parameter dictionary format"],
                "assumptions": ["Query driver supports named parameter bindings"],
                "limitations": ["Applies specifically to this function query"],
                "suggested_tests": ["Test with ' OR '1'='1 input to confirm sanitization"],
            }
        else:
            # Fallback for Stage 4 FindingAnalysisOutput or other schemas
            mock_data = {
                "summary": "Deterministic test analysis of finding.",
                "technical_explanation": "Technical evaluation of vulnerable code pattern.",
                "impact": "Potential compromise of system confidentiality.",
                "confidence": self.override_confidence,
                "classification": "Vulnerability Weakness",
                "uncertainty": "Static analysis limitation.",
                "supporting_evidence": supporting,
            }

        validated = response_schema.model_validate(mock_data)

        metadata = AIResponseMetadata(
            provider=self.provider_name,
            model="fake-test-model",
            prompt_tokens=len(prompt) // 4,
            completion_tokens=200,
            total_tokens=(len(prompt) // 4) + 200,
            estimated_cost_usd=0.0,
            latency_ms=10,
        )
        return AIStructuredResponse(
            parsed=validated,
            raw_json=mock_data,
            metadata=metadata,
        )
