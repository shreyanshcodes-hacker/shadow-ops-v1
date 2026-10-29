"""
Deterministic Correlation Engine

Discovers direct, auditable security relationships between findings
based on static code proximity, shared components, CWE/OWASP categories,
and security dependency heuristics.

All relationships created here are tagged with source='DETERMINISTIC'.
"""

import uuid
from typing import List, Dict, Any, Optional
from app.models.finding import Finding
from app.schemas.attack_path import RelationshipType, RelationshipSource


class CorrelationEngine:
    @staticmethod
    def correlate_pair(
        finding_a: Finding,
        finding_b: Finding,
        evidence_a: Optional[List[Dict[str, Any]]] = None,
        evidence_b: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate two findings for deterministic security relationships.
        Returns a list of relationship specifications (if any).
        """
        if finding_a.id == finding_b.id:
            return []
        if finding_a.workspace_id != finding_b.workspace_id:
            return []

        relationships: List[Dict[str, Any]] = []

        # Extract file paths and line ranges from evidence
        files_a = set()
        lines_a = []
        if evidence_a:
            for ev in evidence_a:
                fp = ev.get("file_path")
                if fp:
                    files_a.add(fp)
                ls = ev.get("line_start")
                if ls is not None:
                    lines_a.append(ls)

        files_b = set()
        lines_b = []
        if evidence_b:
            for ev in evidence_b:
                fp = ev.get("file_path")
                if fp:
                    files_b.add(fp)
                ls = ev.get("line_start")
                if ls is not None:
                    lines_b.append(ls)

        shared_files = files_a.intersection(files_b)

        # Rule 1: SHARES_COMPONENT (Same file path on same asset)
        if shared_files:
            file_sample = next(iter(shared_files))
            relationships.append({
                "source_finding_id": finding_a.id,
                "target_finding_id": finding_b.id,
                "relationship_type": RelationshipType.SHARES_COMPONENT.value,
                "confidence": 0.95,
                "source": RelationshipSource.DETERMINISTIC.value,
                "rationale": f"Both findings reside within the same source file: {file_sample}",
                "evidence_reference": {
                    "shared_file": file_sample,
                    "rule": "shared_file_path",
                },
            })

            # Rule 2: AMPLIFIES (Line proximity within <= 30 lines)
            min_dist = float("inf")
            for la in lines_a:
                for lb in lines_b:
                    dist = abs(la - lb)
                    if dist < min_dist:
                        min_dist = dist

            if min_dist <= 30:
                relationships.append({
                    "source_finding_id": finding_a.id,
                    "target_finding_id": finding_b.id,
                    "relationship_type": RelationshipType.AMPLIFIES.value,
                    "confidence": 0.90,
                    "source": RelationshipSource.DETERMINISTIC.value,
                    "rationale": f"Findings are closely co-located in the same code block ({min_dist} lines apart)",
                    "evidence_reference": {
                        "shared_file": file_sample,
                        "line_distance": min_dist,
                        "rule": "code_line_proximity",
                    },
                })

        # Rule 3: SHARES_ENTRY_POINT (Shared CWE or OWASP category on same asset)
        if finding_a.asset_id == finding_b.asset_id:
            shared_cwe = set(finding_a.cwe_ids or []).intersection(set(finding_b.cwe_ids or []))
            shared_owasp = set(finding_a.owasp_categories or []).intersection(set(finding_b.owasp_categories or []))

            if shared_cwe or shared_owasp:
                cat_desc = ", ".join(list(shared_cwe) + list(shared_owasp))
                relationships.append({
                    "source_finding_id": finding_a.id,
                    "target_finding_id": finding_b.id,
                    "relationship_type": RelationshipType.SHARES_ENTRY_POINT.value,
                    "confidence": 0.85,
                    "source": RelationshipSource.DETERMINISTIC.value,
                    "rationale": f"Findings share security classification: {cat_desc}",
                    "evidence_reference": {
                        "shared_cwe": list(shared_cwe),
                        "shared_owasp": list(shared_owasp),
                        "rule": "shared_classification",
                    },
                })

            # Rule 4: EXPOSES (Secret/Credential disclosure + Injection/API vuln)
            a_is_secret = any(
                term in (finding_a.title + " " + finding_a.description).lower()
                for term in ["secret", "token", "password", "credential", "api_key", "cwe-798"]
            )
            b_is_sink = any(
                term in (finding_b.title + " " + finding_b.description).lower()
                for term in ["injection", "sql", "command", "rce", "exec", "database", "ssrf"]
            )
            if a_is_secret and b_is_sink:
                relationships.append({
                    "source_finding_id": finding_a.id,
                    "target_finding_id": finding_b.id,
                    "relationship_type": RelationshipType.EXPOSES.value,
                    "confidence": 0.90,
                    "source": RelationshipSource.DETERMINISTIC.value,
                    "rationale": f"Credential exposure in '{finding_a.title}' exposes internal backend services vulnerable in '{finding_b.title}'",
                    "evidence_reference": {
                        "source_title": finding_a.title,
                        "target_title": finding_b.title,
                        "rule": "credential_exposes_sink",
                    },
                })

            # Rule 5: ENABLES (Auth bypass/access control precedes vulnerability)
            a_is_auth = any(
                term in (finding_a.title + " " + finding_a.description).lower()
                for term in ["auth", "permission", "cors", "jwt", "access control", "bypass", "unauthenticated", "cwe-287", "cwe-306"]
            )
            if a_is_auth and (b_is_sink or finding_b.severity in ("critical", "high")):
                relationships.append({
                    "source_finding_id": finding_a.id,
                    "target_finding_id": finding_b.id,
                    "relationship_type": RelationshipType.ENABLES.value,
                    "confidence": 0.88,
                    "source": RelationshipSource.DETERMINISTIC.value,
                    "rationale": f"Access control weakness '{finding_a.title}' enables direct unauthenticated access to '{finding_b.title}'",
                    "evidence_reference": {
                        "source_title": finding_a.title,
                        "target_title": finding_b.title,
                        "rule": "auth_bypass_enables_exploit",
                    },
                })

        return relationships
