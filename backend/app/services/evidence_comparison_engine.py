import difflib
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.verification import VulnerabilityVerificationStatus


class EvidenceComparisonEngine:
    """
    Independent Evidence Comparison Engine:
    Performs conservative comparison between pre-patch baseline evidence
    and post-patch rescan results.

    Adheres strictly to the core invariant:
    "No sufficient evidence means no verified fix."
    """

    LINE_SHIFT_TOLERANCE = 15

    @classmethod
    def extract_baseline_snapshot(
        cls,
        finding_id: str,
        rule_id: str,
        file_path: str,
        line_start: Optional[int],
        line_end: Optional[int],
        code_snippet: Optional[str],
        evidence_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Creates an immutable baseline snapshot for verification comparison."""
        clean_snippet = (code_snippet or "").strip()
        snippet_hash = hashlib.sha256(clean_snippet.encode("utf-8")).hexdigest() if clean_snippet else ""
        fingerprint = hashlib.sha256(
            f"{rule_id}:{file_path}:{line_start or 0}:{snippet_hash}".encode("utf-8")
        ).hexdigest()

        return {
            "finding_id": finding_id,
            "rule_id": rule_id,
            "file_path": file_path,
            "line_start": line_start or 0,
            "line_end": line_end or 0,
            "code_snippet": clean_snippet,
            "snippet_hash": snippet_hash,
            "fingerprint": fingerprint,
            "evidence_count": len(evidence_items) if evidence_items else 0,
            "evidence_items": evidence_items or [],
        }

    @classmethod
    def compare(
        cls,
        baseline: Dict[str, Any],
        rescan_findings: List[Dict[str, Any]],
        affected_files: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any], int, float, str]:
        """
        Compares baseline finding snapshot against rescan findings.

        Returns:
            category: VulnerabilityVerificationStatus string
            rescan_evidence: matching finding evidence if found
            line_shift: integer shift in lines
            similarity_score: float (0.0 to 1.0)
            explanation: detailed human-readable explanation
        """
        if not baseline or not baseline.get("rule_id"):
            return (
                VulnerabilityVerificationStatus.UNCOMPARABLE.value,
                {},
                0,
                0.0,
                "Baseline evidence is missing or incomplete; verification cannot be determined.",
            )

        target_rule = baseline.get("rule_id")
        target_file = (baseline.get("file_path") or "").replace("\\", "/")
        target_snippet = baseline.get("code_snippet") or ""
        baseline_start = baseline.get("line_start") or 0

        exact_match = None
        moved_match = None
        highest_similarity = 0.0
        calculated_shift = 0

        # 1. Search for matching rule and file
        for rf in rescan_findings:
            r_rule = rf.get("rule_id") or rf.get("source_rule_id") or ""
            r_loc = rf.get("location") or {}
            r_file = (r_loc.get("file_path") or rf.get("file_path") or "").replace("\\", "/")
            r_start = r_loc.get("line_start") or rf.get("line_start") or 0
            r_snippet = (rf.get("code_snippet") or "").strip()

            # Normalize file path endings (e.g. repo/path vs path)
            file_matches = (
                r_file == target_file
                or r_file.endswith("/" + target_file)
                or target_file.endswith("/" + r_file)
            )

            if r_rule == target_rule and file_matches:
                # Calculate snippet similarity
                similarity = difflib.SequenceMatcher(None, target_snippet, r_snippet).ratio() if target_snippet and r_snippet else 1.0
                shift = r_start - baseline_start

                if abs(shift) <= cls.LINE_SHIFT_TOLERANCE and similarity >= 0.8:
                    exact_match = rf
                    highest_similarity = similarity
                    calculated_shift = shift
                    break
                else:
                    moved_match = rf
                    highest_similarity = max(highest_similarity, similarity)
                    calculated_shift = shift

        # 2. Check for newly introduced findings in affected files (regressions)
        new_findings_in_affected = []
        if affected_files:
            norm_affected = [(f or "").replace("\\", "/") for f in affected_files]
            for rf in rescan_findings:
                rf_rule = rf.get("rule_id") or rf.get("source_rule_id") or ""
                rf_loc = rf.get("location") or {}
                rf_file = (rf_loc.get("file_path") or rf.get("file_path") or "").replace("\\", "/")
                is_affected = any(
                    rf_file == af or rf_file.endswith("/" + af) or af.endswith("/" + rf_file)
                    for af in norm_affected
                )
                if is_affected and rf_rule != target_rule:
                    new_findings_in_affected.append(rf)

        # 3. Categorize outcome
        if exact_match:
            return (
                VulnerabilityVerificationStatus.STILL_PRESENT.value,
                exact_match,
                calculated_shift,
                highest_similarity,
                f"Vulnerability '{target_rule}' is STILL PRESENT in '{target_file}' at line {exact_match.get('location', {}).get('line_start', 'unknown')} with similarity {highest_similarity:.2f}.",
            )

        if moved_match:
            return (
                VulnerabilityVerificationStatus.MODIFIED_OR_MOVED.value,
                moved_match,
                calculated_shift,
                highest_similarity,
                f"Vulnerability '{target_rule}' was NOT eliminated; it shifted by {calculated_shift} lines or was modified in '{target_file}'.",
            )

        if new_findings_in_affected:
            first_new = new_findings_in_affected[0]
            new_rule = first_new.get("rule_id") or first_new.get("source_rule_id") or "unknown"
            return (
                VulnerabilityVerificationStatus.POSSIBLE_REGRESSION.value,
                first_new,
                0,
                0.0,
                f"Patch may have introduced regression: new finding '{new_rule}' detected in affected file.",
            )

        # 4. Clean fix verification
        return (
            VulnerabilityVerificationStatus.NO_LONGER_DETECTED.value,
            {},
            0,
            0.0,
            f"Vulnerability '{target_rule}' is NO LONGER DETECTED in '{target_file}'. No related flaws detected.",
        )
