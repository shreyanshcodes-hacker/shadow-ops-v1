import hashlib
from typing import Dict, Any, List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class NormalizedFinding(BaseModel):
    fingerprint: str
    rule_id: str
    title: str
    description: str
    severity: str
    confidence: str = "medium"
    cwe_ids: List[str] = Field(default_factory=list)
    cve_ids: List[str] = Field(default_factory=list)
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class FindingNormalizer:
    """
    Transforms raw heterogeneous scanner outputs into normalized ShadowOps finding schemas.
    Computes deterministic SHA-256 deduplication fingerprints.
    """

    @staticmethod
    def compute_fingerprint(asset_id: UUID, rule_id: str, file_path: str, line_start: int) -> str:
        payload = f"{asset_id}:{rule_id}:{file_path}:{line_start}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def normalize_semgrep_match(cls, asset_id: UUID, raw_match: Dict[str, Any]) -> NormalizedFinding:
        rule_id = raw_match.get("check_id", "semgrep.unknown_rule")
        file_path = raw_match.get("path", "unknown")
        start_line = raw_match.get("start", {}).get("line", 0)
        end_line = raw_match.get("end", {}).get("line", start_line)
        extra = raw_match.get("extra", {})

        severity_raw = extra.get("severity", "WARNING").upper()
        severity_map = {
            "ERROR": "critical",
            "WARNING": "medium",
            "INFO": "low",
        }
        severity = severity_map.get(severity_raw, "medium")

        fingerprint = cls.compute_fingerprint(asset_id, rule_id, file_path, start_line)
        message = extra.get("message", "Vulnerability detected by static analysis.")

        return NormalizedFinding(
            fingerprint=fingerprint,
            rule_id=rule_id,
            title=rule_id.split(".")[-1].replace("-", " ").title(),
            description=message,
            severity=severity,
            confidence="high",
            cwe_ids=extra.get("metadata", {}).get("cwe", []),
            cve_ids=[],
            file_path=file_path,
            line_start=start_line,
            line_end=end_line,
            code_snippet=extra.get("lines", ""),
            raw_metadata=extra,
        )
