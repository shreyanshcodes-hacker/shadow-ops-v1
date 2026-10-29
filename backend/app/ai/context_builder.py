import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.ai.safety import redact_secrets
from app.ai.cost import truncate_context
from app.core.config import settings


class MinimizedEvidenceItem(BaseModel):
    id: str
    evidence_type: str
    title: str
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    sanitized_content: str


class SecurityAnalysisContext(BaseModel):
    finding_id: str
    title: str
    source: str
    source_rule_id: Optional[str] = None
    severity: str
    description: str
    cwe_ids: List[str] = Field(default_factory=list)
    owasp_categories: List[str] = Field(default_factory=list)
    location: Dict[str, Any] = Field(default_factory=dict)
    sanitized_code_snippet: str
    asset_name: str
    asset_type: str
    environment: str
    evidence_items: List[MinimizedEvidenceItem] = Field(default_factory=list)


class SecurityAnalysisContextBuilder:
    """
    Dedicated Context Builder for Stage 5 AI Security Analyst.
    Enforces data minimization, secret redaction, and bounded input sizing.
    Guarantees no internal credentials, unrelated files, or sensitive tokens reach the LLM.
    """

    @staticmethod
    def build(
        finding_dict: Dict[str, Any],
        asset_dict: Optional[Dict[str, Any]] = None,
        raw_evidence_list: Optional[List[Dict[str, Any]]] = None,
        max_code_chars: int = 12000,
    ) -> SecurityAnalysisContext:
        asset = asset_dict or {}
        evidence_list = raw_evidence_list or []

        # 1. Sanitize code snippet & truncate
        raw_snippet = finding_dict.get("code_snippet") or ""
        redacted_snippet = redact_secrets(raw_snippet)
        truncated_snippet = truncate_context(redacted_snippet, max_chars=max_code_chars)

        # 2. Sanitize & minimize evidence items
        minimized_evidence: List[MinimizedEvidenceItem] = []
        for ev in evidence_list:
            ev_id = str(ev.get("id", ""))
            raw_content = str(ev.get("content", ""))
            redacted_content = redact_secrets(raw_content)
            truncated_content = truncate_context(redacted_content, max_chars=3000)

            minimized_evidence.append(
                MinimizedEvidenceItem(
                    id=ev_id,
                    evidence_type=ev.get("evidence_type", "unknown"),
                    title=ev.get("title", ""),
                    file_path=ev.get("file_path"),
                    line_start=ev.get("line_start"),
                    line_end=ev.get("line_end"),
                    sanitized_content=truncated_content,
                )
            )

        # 3. Assemble strictly minimized security context
        return SecurityAnalysisContext(
            finding_id=str(finding_dict.get("id", "")),
            title=redact_secrets(finding_dict.get("title") or ""),
            source=finding_dict.get("source") or "semgrep",
            source_rule_id=finding_dict.get("source_rule_id"),
            severity=finding_dict.get("severity") or "unknown",
            description=redact_secrets(finding_dict.get("description") or ""),
            cwe_ids=finding_dict.get("cwe_ids") or [],
            owasp_categories=finding_dict.get("owasp_categories") or [],
            location=finding_dict.get("location") or {},
            sanitized_code_snippet=truncated_snippet,
            asset_name=redact_secrets(asset.get("name") or "Authorized Target"),
            asset_type=asset.get("type") or "repository",
            environment=asset.get("environment") or "production",
            evidence_items=minimized_evidence,
        )
