import json
import logging
import asyncio
import time
from typing import Type, TypeVar, Optional, Dict, Any
import httpx
from pydantic import BaseModel

from app.ai.provider import (
    AIProvider,
    AIRequestConfig,
    AITextResponse,
    AIStructuredResponse,
    AIResponseMetadata,
)
from app.ai.cost import calculate_cost
from app.core.config import settings

logger = logging.getLogger("shadowops.ai.gemini")

T = TypeVar("T", bound=BaseModel)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

DEPRECATED_MODELS: Dict[str, str] = {
    "gemini-1.5-flash": "gemini-flash-latest",
    "gemini-1.5-pro": "gemini-flash-latest",
    "gemini-2.0-flash": "gemini-flash-latest",
    "gemini-2.0-flash-lite": "gemini-flash-latest",
    "gemini-2.5-flash": "gemini-flash-latest",
    "gemini-2.5-flash-lite": "gemini-flash-latest",
}


class GeminiProvider(AIProvider):
    provider_name = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        raw_model = default_model or settings.GEMINI_MODEL or "gemini-flash-latest"
        self.default_model = DEPRECATED_MODELS.get(raw_model, raw_model)
        self._http_client = http_client

    @property
    def is_live(self) -> bool:
        """Returns True if a real Gemini API key is configured and active."""
        if settings.is_testing:
            return False
        if not self.api_key:
            return False
        if any(self.api_key.startswith(p) for p in ("placeholder", "test", "dummy", "fake")):
            return False
        return True

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AITextResponse:
        cfg = config or AIRequestConfig()
        raw_model = cfg.model_name or self.default_model
        model = DEPRECATED_MODELS.get(raw_model, raw_model)

        if not self.is_live:
            return self._mock_text_response(prompt, model)

        return await self._call_gemini_text(prompt, system_instruction, cfg, model)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AIStructuredResponse:
        cfg = config or AIRequestConfig()
        raw_model = cfg.model_name or self.default_model
        model = DEPRECATED_MODELS.get(raw_model, raw_model)

        if not self.is_live:
            return self._mock_structured_response(prompt, response_schema, model)

        return await self._call_gemini_structured(prompt, response_schema, system_instruction, cfg, model)

    async def _call_gemini_text(
        self,
        prompt: str,
        system_instruction: Optional[str],
        cfg: AIRequestConfig,
        model: str,
    ) -> AITextResponse:
        url = f"{GEMINI_API_URL.format(model=model)}?key={self.api_key}"
        body: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": cfg.temperature,
                "maxOutputTokens": cfg.max_output_tokens,
            },
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        start_time = time.time()
        data = await self._send_with_retry(url, body, cfg)
        latency = int((time.time() - start_time) * 1000)

        # Extract text candidate
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        content = parts[0].get("text", "") if parts else ""

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", len(prompt) // 4)
        completion_tokens = usage.get("candidatesTokenCount", len(content) // 4)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)
        cost = calculate_cost("gemini", prompt_tokens, completion_tokens)

        metadata = AIResponseMetadata(
            provider=self.provider_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            latency_ms=latency,
        )
        return AITextResponse(content=content, metadata=metadata)

    async def _call_gemini_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str],
        cfg: AIRequestConfig,
        model: str,
    ) -> AIStructuredResponse:
        url = f"{GEMINI_API_URL.format(model=model)}?key={self.api_key}"
        json_schema = response_schema.model_json_schema()

        body: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": cfg.temperature,
                "maxOutputTokens": cfg.max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": json_schema,
            },
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        start_time = time.time()
        data = await self._send_with_retry(url, body, cfg)
        latency = int((time.time() - start_time) * 1000)

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        raw_text = parts[0].get("text", "{}") if parts else "{}"

        # Clean JSON markdown fences if present
        raw_text_clean = raw_text.strip()
        if raw_text_clean.startswith("```json"):
            raw_text_clean = raw_text_clean[7:]
        if raw_text_clean.startswith("```"):
            raw_text_clean = raw_text_clean[3:]
        if raw_text_clean.endswith("```"):
            raw_text_clean = raw_text_clean[:-3]
        raw_text_clean = raw_text_clean.strip()

        parsed_json = json.loads(raw_text_clean)
        validated_obj = response_schema.model_validate(parsed_json)

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", len(prompt) // 4)
        completion_tokens = usage.get("candidatesTokenCount", len(raw_text_clean) // 4)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)
        cost = calculate_cost("gemini", prompt_tokens, completion_tokens)

        metadata = AIResponseMetadata(
            provider=self.provider_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            latency_ms=latency,
        )
        return AIStructuredResponse(
            parsed=validated_obj,
            raw_json=parsed_json,
            metadata=metadata,
        )

    async def _send_with_retry(self, url: str, body: Dict[str, Any], cfg: AIRequestConfig) -> Dict[str, Any]:
        """Sends HTTP request to Gemini with bounded retries and exponential backoff for 429/5xx."""
        client = self._http_client or httpx.AsyncClient(timeout=float(cfg.timeout_seconds))
        should_close = self._http_client is None

        retries = 0
        backoff = 1.0

        try:
            while True:
                try:
                    resp = await client.post(url, json=body)
                    if resp.status_code == 200:
                        return resp.json()
                    elif resp.status_code in (429, 500, 502, 503, 504):
                        retries += 1
                        if retries > cfg.max_retries:
                            resp.raise_for_status()
                        logger.warning(
                            f"Gemini API returned status {resp.status_code}. Backing off {backoff}s (attempt {retries}/{cfg.max_retries})"
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                    else:
                        resp.raise_for_status()
                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    retries += 1
                    if retries > cfg.max_retries:
                        raise RuntimeError(f"Gemini network error after {retries} attempts: {str(e)}") from e
                    logger.warning(f"Gemini connection error: {str(e)}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
        finally:
            if should_close:
                await client.aclose()

    def _mock_text_response(self, prompt: str, model: str) -> AITextResponse:
        p_lower = prompt.lower()
        if "sql" in p_lower or "injection" in p_lower:
            content = (
                "### [Gemini Sentinel] Remediation Guidance: SQL Injection (CWE-89)\n\n"
                "**Root Cause:** Untrusted user input is concatenated directly into SQL statement strings.\n\n"
                "**Recommended Fix:** Replace dynamic string formatting (e.g. `f\"SELECT ... {var}\"`) with parameterized queries / bind parameters.\n\n"
                "```python\n"
                "# Insecure Pattern\n"
                "cursor.execute(f\"SELECT * FROM users WHERE username = '{username}'\")\n\n"
                "# Secure Parameterized Pattern\n"
                "cursor.execute(\"SELECT * FROM users WHERE username = :username\", {\"username\": username})\n"
                "```\n\n"
                "**Next Steps:**\n"
                "1. Audit all ORM or raw SQL execution sites in database repositories.\n"
                "2. Trigger an AI remediation proposal from the finding page to generate a verified diff.\n"
                "3. Run independent fix verification after applying the patch."
            )
        elif "critical" in p_lower or "finding" in p_lower or "vulnerabilit" in p_lower:
            content = (
                "### [Gemini Sentinel] Workspace Security Analysis\n\n"
                "Based on scanner telemetry and perimeter posture:\n\n"
                "- **Prioritization:** Address any injection (CWE-89) or authentication bypass vulnerabilities first, as they provide direct exploit preconditions.\n"
                "- **Deterministic Risk:** High-severity findings connected to external entry points contribute disproportionately to your risk score.\n"
                "- **Action Plan:** Inspect the top findings in the **Findings** tab, review the AI analyst root-cause breakdown, and submit patch proposals for human approval."
            )
        elif "attack" in p_lower or "path" in p_lower or "lateral" in p_lower:
            content = (
                "### [Gemini Sentinel] Attack Path Defense Analysis\n\n"
                "- **Choke Points:** Neutralizing entry-point vulnerabilities breaks multi-hop exploit progressions before attackers can reach private databases.\n"
                "- **Network Boundaries:** Enforce strict segmentation between public-facing API services and internal database/storage tiers.\n"
                "- **Recommendation:** Review the interactive graph in the **Attack Paths** section to inspect candidate edges and verified correlation links."
            )
        else:
            content = (
                f"### [Gemini Sentinel - {model}] Security Advisory\n\n"
                "I have analyzed your request in the context of your authorized workspace perimeter:\n\n"
                f"- **Context:** Your query regarding \"{prompt[:80]}...\" was evaluated against known CWE defensive baselines.\n"
                "- **Key Principles:** Enforce strict input validation, least-privilege RBAC, and defense-in-depth isolation across all components.\n"
                "- **Suggested Action:** Use the **AI Security Team** evaluation to run multi-agent recon, vulnerability analysis, and attack path progression across your assets."
            )

        metadata = AIResponseMetadata(
            provider=self.provider_name,
            model=model,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(content) // 4,
            total_tokens=(len(prompt) + len(content)) // 4,
            estimated_cost_usd=0.00005,
            latency_ms=45,
        )
        return AITextResponse(content=content, metadata=metadata)

    def _mock_structured_response(self, prompt: str, response_schema: Type[T], model: str) -> AIStructuredResponse:
        """Provides deterministic, schema-compliant mock analysis when live API key is not configured."""
        # Extract evidence ID if present in prompt to produce grounded mock references
        import re
        ev_ids = re.findall(r"Evidence ID:\s*([a-f0-9\-]+)", prompt)
        supporting = []
        for eid in ev_ids[:2]:
            supporting.append({
                "evidence_id": eid,
                "relevance": "Confirmed vulnerable code pattern and matched AST pattern at location.",
                "quote_or_reference": "Vulnerable entry point detected in source snippet."
            })

        mock_data = {
            "summary": "Potential security vulnerability detected in scanned source code based on static analysis evidence.",
            "technical_explanation": "The scanned code construct exhibits an insecure pattern where untrusted input or unvalidated parameter handling may compromise runtime control flow or data integrity.",
            "impact": "Exploitation could lead to unauthorized access, data leakage, or unintended logic execution depending on exposure.",
            "confidence": 0.88,
            "classification": "Insecure Implementation / Input Handling",
            "vulnerability_type": "Insecure Implementation / Input Handling",
            "severity_assessment": "high",
            "exploitability_assessment": "Exploitable if untrusted input reaches this handler without prior validation.",
            "impact_assessment": "Exploitation could lead to unauthorized access, data leakage, or unintended logic execution.",
            "affected_component": "Target source file",
            "attack_preconditions": "Attacker must possess network access to route requests to the affected component.",
            "evidence_interpretation": {
                "observed": ["Scanner matched static security rule at location", "Vulnerable AST construct identified"],
                "inferred": ["Unvalidated data flow may permit execution or state compromise"],
                "uncertain": ["Runtime parameter validation could not be dynamically verified without execution"]
            },
            "reasoning": "Static analysis detected that untrusted parameters flow into a sensitive sink without sanitization.",
            "recommended_next_steps": "Review the data flow upstream from this sink and implement parameter validation or binding.",
            "uncertainty": "Static analysis detected the pattern locally; dynamic runtime reachability could not be fully verified without execution.",
            "supporting_evidence": supporting,
            # AI Security Team Schemas Fields
            "executive_summary": "Synthesized security assessment across perimeter components and scanner evidence.",
            "key_security_concerns": ["Input validation vulnerabilities detected", "Potential lateral movement path"],
            "highest_priority_findings": ["Critical finding in target perimeter"],
            "highest_priority_attack_paths": ["Perimeter entry to authentication sink"],
            "risk_interpretation": "Elevated risk due to exposed entry points and unauthenticated code path.",
            "uncertainties": ["Runtime execution parameters not dynamically traced"],
            "conflicting_assessments": [],
            "recommended_human_actions": ["Review and validate proposed remediation diff", "Execute verification rescan"],
            "overall_confidence": 0.88,
            "evidence_references": [eid for eid in ev_ids[:3]],
            "relevant_components": ["API Gateway", "Authentication Controller", "Database Layer"],
            "entry_points": ["/api/v1/auth/login", "/api/v1/users"],
            "security_boundaries": ["DMZ Network Boundary", "Database Private Subnet"],
            "exposed_areas": ["Public HTTP Endpoints"],
            "observations": ["Perimeter contains accessible web services with parameter inputs"],
            "findings_analyzed": 1,
            "interpretations": [],
            "candidate_relationships": [],
            "path_observations": ["Direct path from external input to sensitive database sink"],
            "explanation": "Evaluated static analysis findings against architectural components.",
            "deterministic_score_reference": 78.5,
            "risk_band": "HIGH",
            "important_contributing_factors": ["High severity finding", "Publicly exposed asset"],
            "recommended_human_review_priorities": ["Sanitize user inputs", "Apply parameterized queries"],
        }

        try:
            validated = response_schema.model_validate(mock_data)
        except Exception:
            # Build minimal compliant dictionary for required fields
            data = dict(mock_data)
            for name, field in getattr(response_schema, "model_fields", {}).items():
                if field.is_required() and name not in data:
                    annotation = str(field.annotation)
                    if "str" in annotation:
                        data[name] = f"Simulated {name.replace('_', ' ')}"
                    elif "int" in annotation:
                        data[name] = 0
                    elif "float" in annotation:
                        data[name] = 0.5
                    elif "list" in annotation or "List" in annotation:
                        data[name] = []
                    elif "dict" in annotation or "Dict" in annotation:
                        data[name] = {}
                    elif "bool" in annotation:
                        data[name] = True
                    else:
                        data[name] = f"Simulated {name}"
            validated = response_schema.model_validate(data)

        metadata = AIResponseMetadata(
            provider=self.provider_name,
            model=model,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=180,
            total_tokens=(len(prompt) // 4) + 180,
            estimated_cost_usd=0.0001,
            latency_ms=50,
        )
        return AIStructuredResponse(
            parsed=validated,
            raw_json=mock_data,
            metadata=metadata,
        )
