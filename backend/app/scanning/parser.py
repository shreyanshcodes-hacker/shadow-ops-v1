import re
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class NormalizedScanFinding(BaseModel):
    rule_id: str
    severity: str  # critical, high, medium, low, info
    title: str
    message: str
    file_path: str
    line_start: int
    line_end: int
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    code_snippet: Optional[str] = None
    cwe_ids: List[str] = Field(default_factory=list)
    owasp_categories: List[str] = Field(default_factory=list)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


def redact_sensitive_strings(text: str) -> str:
    """Redacts potential secrets/tokens from messages and code snippets."""
    if not text:
        return text
    # Redact AWS Keys
    text = re.sub(r'AKIA[0-9A-Z]{16}', 'AKIA[REDACTED_AWS_KEY]', text)
    # Redact common secret key assignments
    text = re.sub(r'(api_key|secret|password|token)\s*=\s*["\']([^"\']+)["\']', r'\1="[REDACTED]"', text, flags=re.IGNORECASE)
    return text


class SemgrepParser:
    """Parses structured Semgrep JSON output into normalized finding objects."""

    SEVERITY_MAPPING = {
        "ERROR": "critical",
        "WARNING": "medium",
        "INFO": "low",
        "EXPERIMENT": "info",
    }

    @classmethod
    def parse_results(cls, semgrep_json: Dict[str, Any]) -> List[NormalizedScanFinding]:
        results = semgrep_json.get("results", [])
        findings: List[NormalizedScanFinding] = []

        for item in results:
            check_id = item.get("check_id", "semgrep.detected_issue")
            path = item.get("path", "unknown")
            start = item.get("start", {})
            end = item.get("end", {})
            extra = item.get("extra", {})

            raw_severity = extra.get("severity", "WARNING").upper()
            mapped_sev = cls.SEVERITY_MAPPING.get(raw_severity, "medium")

            message = redact_sensitive_strings(extra.get("message", "Static security finding."))
            snippet = redact_sensitive_strings(extra.get("lines", ""))

            # Extract CWE / OWASP metadata
            meta = extra.get("metadata", {})
            cwe = meta.get("cwe", [])
            if isinstance(cwe, str):
                cwe = [cwe]

            owasp = meta.get("owasp", [])
            if isinstance(owasp, str):
                owasp = [owasp]

            title = check_id.split(".")[-1].replace("-", " ").replace("_", " ").title()

            findings.append(
                NormalizedScanFinding(
                    rule_id=check_id,
                    severity=mapped_sev,
                    title=title,
                    message=message,
                    file_path=path,
                    line_start=start.get("line", 1),
                    line_end=end.get("line", 1),
                    column_start=start.get("col"),
                    column_end=end.get("col"),
                    code_snippet=snippet,
                    cwe_ids=cwe,
                    owasp_categories=owasp,
                    raw_metadata=extra,
                )
            )

        return findings
