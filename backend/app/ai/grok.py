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

logger = logging.getLogger("shadowops.ai.grok")

T = TypeVar("T", bound=BaseModel)

GROK_API_URL = "https://api.x.ai/v1/chat/completions"


class GrokProvider(AIProvider):
    provider_name = "grok"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key or settings.GROK_API_KEY
        self.default_model = default_model or settings.GROK_MODEL
        self._http_client = http_client

    @property
    def is_live(self) -> bool:
        """Returns True if a real Grok API key is configured and active."""
        if settings.is_testing:
            return False
        if not self.api_key:
            return False
        if any(self.api_key.startswith(p) for p in ("placeholder", "test", "gsk_", "xai-test", "dummy", "fake")):
            return False
        return True

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AITextResponse:
        cfg = config or AIRequestConfig()
        model = cfg.model_name or self.default_model

        if not self.is_live:
            return self._mock_text_response(prompt, model)

        return await self._call_grok(prompt, None, system_instruction, cfg, model, is_structured=False)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AIStructuredResponse:
        cfg = config or AIRequestConfig()
        model = cfg.model_name or self.default_model

        if not self.is_live:
            return self._mock_structured_response(prompt, response_schema, model)

        return await self._call_grok(prompt, response_schema, system_instruction, cfg, model, is_structured=True)

    async def _call_grok(
        self,
        prompt: str,
        response_schema: Optional[Type[T]],
        system_instruction: Optional[str],
        cfg: AIRequestConfig,
        model: str,
        is_structured: bool = False,
    ) -> Any:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_output_tokens,
        }
        if is_structured:
            body["response_format"] = {"type": "json_object"}

        start_time = time.time()
        client = self._http_client or httpx.AsyncClient(timeout=float(cfg.timeout_seconds))
        should_close = self._http_client is None

        retries = 0
        backoff = 1.0

        try:
            while True:
                try:
                    resp = await client.post(GROK_API_URL, headers=headers, json=body)
                    if resp.status_code == 200:
                        data = resp.json()
                        break
                    elif resp.status_code in (429, 500, 502, 503, 504):
                        retries += 1
                        if retries > cfg.max_retries:
                            resp.raise_for_status()
                        logger.warning(f"Grok API status {resp.status_code}. Backoff {backoff}s...")
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                    else:
                        resp.raise_for_status()
                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    retries += 1
                    if retries > cfg.max_retries:
                        raise RuntimeError(f"Grok network error after {retries} retries: {str(e)}") from e
                    await asyncio.sleep(backoff)
                    backoff *= 2.0

            latency = int((time.time() - start_time) * 1000)
            choice = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
            completion_tokens = usage.get("completion_tokens", len(choice) // 4)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            cost = calculate_cost("grok", prompt_tokens, completion_tokens)

            metadata = AIResponseMetadata(
                provider=self.provider_name,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=cost,
                latency_ms=latency,
            )

            if not is_structured:
                return AITextResponse(content=choice, metadata=metadata)

            parsed_json = json.loads(choice)
            validated = response_schema.model_validate(parsed_json) if response_schema else parsed_json
            return AIStructuredResponse(
                parsed=validated,
                raw_json=parsed_json,
                metadata=metadata,
            )
        finally:
            if should_close:
                await client.aclose()

    def _mock_text_response(self, prompt: str, model: str) -> AITextResponse:
        content = f"[ShadowOps Grok Simulation - {model}]: Adversarial security analysis evaluated."
        metadata = AIResponseMetadata(
            provider=self.provider_name,
            model=model,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(content) // 4,
            total_tokens=(len(prompt) + len(content)) // 4,
            estimated_cost_usd=0.0001,
            latency_ms=60,
        )
        return AITextResponse(content=content, metadata=metadata)

    def _mock_structured_response(self, prompt: str, response_schema: Type[T], model: str) -> AIStructuredResponse:
        import re
        ev_ids = re.findall(r"Evidence ID:\s*([a-f0-9\-]+)", prompt)
        supporting = []
        for eid in ev_ids[:2]:
            supporting.append({
                "evidence_id": eid,
                "relevance": "Confirmed vulnerable code pattern via static rule match.",
                "quote_or_reference": "Identified by scanner rule pattern match."
            })

        mock_data = {
            "summary": "Potential security vulnerability identified from scanner evidence.",
            "technical_explanation": "Adversarial inspection indicates this code path may permit unverified input processing.",
            "impact": "Possibility of compromise depending on deployment boundaries.",
            "confidence": 0.85,
            "classification": "Application Security Weakness",
            "vulnerability_type": "Application Security Weakness",
            "severity_assessment": "high",
            "exploitability_assessment": "Exploitable if untrusted input reaches this handler without prior validation.",
            "impact_assessment": "Possibility of compromise depending on deployment boundaries.",
            "affected_component": "Target source file",
            "attack_preconditions": "Attacker must possess access to the affected route.",
            "evidence_interpretation": {
                "observed": ["Scanner matched static security rule at location", "Static rule pattern match"],
                "inferred": ["Unverified input processing may permit logic subversion"],
                "uncertain": ["Advisory interpretation based strictly on static rule output without dynamic execution"]
            },
            "reasoning": "Adversarial inspection indicates this code path may permit unverified input processing.",
            "recommended_next_steps": "Investigate input source and apply input sanitization or defensive assertions.",
            "uncertainty": "Advisory interpretation based strictly on static rule output.",
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
            estimated_cost_usd=0.0002,
            latency_ms=55,
        )
        return AIStructuredResponse(
            parsed=validated,
            raw_json=mock_data,
            metadata=metadata,
        )
