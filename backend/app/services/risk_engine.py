"""
Deterministic Risk Engine (Model: risk-v1)

CORE PRINCIPLE:
AI MAY SUGGEST RELATIONSHIPS.
DETERMINISTIC CODE DECIDES THE FINAL SCORE.

This engine computes fully reproducible, explainable, and auditable
risk scores strictly bounded between 0.0 and 100.0.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


MODEL_VERSION = "risk-v1"

# Risk Band Definitions
RISK_BANDS = [
    (0.0, 19.99, "INFORMATIONAL"),
    (20.0, 39.99, "LOW"),
    (40.0, 59.99, "MEDIUM"),
    (60.0, 79.99, "HIGH"),
    (80.0, 100.0, "CRITICAL"),
]

# Weights (Sum = 1.00)
WEIGHT_SEVERITY = 0.30
WEIGHT_EXPLOITABILITY = 0.20
WEIGHT_ASSET_CRITICALITY = 0.20
WEIGHT_CONFIDENCE = 0.15
WEIGHT_EXPOSURE = 0.10
WEIGHT_PATH_COMPLEXITY = 0.05

SEVERITY_SCORES = {
    "critical": 100.0,
    "high": 80.0,
    "medium": 50.0,
    "low": 25.0,
    "info": 10.0,
}

CRITICALITY_SCORES = {
    "critical": 100.0,
    "high": 75.0,
    "medium": 50.0,
    "low": 25.0,
}


def score_to_band(score: float) -> str:
    """Map a 0-100 score to its deterministic risk band."""
    clamped = max(0.0, min(100.0, score))
    for low, high, band in RISK_BANDS:
        if low <= clamped <= high:
            return band
    return "CRITICAL" if clamped >= 80.0 else "INFORMATIONAL"


class RiskEngine:
    @staticmethod
    def calculate_attack_path_risk(
        nodes_data: List[Dict[str, Any]],
        edges_data: List[Dict[str, Any]],
        asset_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate the deterministic risk score for an attack path using formula risk-v1.

        Args:
            nodes_data: List of dicts representing nodes (findings, assets, etc.)
            edges_data: List of dicts representing edges/relationships
            asset_metadata: Optional metadata about the target asset (criticality, exposure, etc.)

        Returns:
            Dict containing score, risk_band, model_version, and auditable factor breakdown.
        """
        asset_meta = asset_metadata or {}

        # 1. Finding Severity Factor (30%)
        # Base severity is the highest severity among findings in the path,
        # plus a small path compounding bonus (e.g. multi-step chain).
        severities = [n.get("severity", "info").lower() for n in nodes_data if n.get("severity")]
        if not severities:
            severities = ["low"]

        numeric_sevs = [SEVERITY_SCORES.get(s, 25.0) for s in severities]
        max_sev = max(numeric_sevs)
        # Multi-node path compounding: each additional finding adds up to +3, capped at 15
        chain_compounding = min(15.0, max(0.0, (len(numeric_sevs) - 1) * 3.0))
        finding_severity_score = min(100.0, max_sev + chain_compounding)

        # 2. Exploitability Factor (20%)
        # Look at edge likelihoods, relationship types, and vulnerability types
        edge_likelihoods = [float(e.get("likelihood") or 0.8) for e in edges_data]
        avg_likelihood = (sum(edge_likelihoods) / len(edge_likelihoods)) if edge_likelihoods else 0.75
        # Relationship amplification: ENABLES, EXPOSES, AMPLIFIES increase exploitability
        rel_types = [str(e.get("edge_type", "")).upper() for e in edges_data]
        multiplier = 1.0
        if any(t in ("ENABLES", "EXPOSES", "EXPLOITS") for t in rel_types):
            multiplier += 0.15
        if any(t in ("AMPLIFIES", "PRIVILEGE_ESCALATION") for t in rel_types):
            multiplier += 0.10
        exploitability_score = min(100.0, max(0.0, avg_likelihood * 100.0 * multiplier))

        # 3. Asset Criticality Factor (20%)
        raw_crit = str(asset_meta.get("criticality", "medium")).lower()
        asset_crit_score = CRITICALITY_SCORES.get(raw_crit, 50.0)

        # 4. Confidence Factor (15%)
        # Average confidence of findings and relationships in the path
        node_confidences = []
        for n in nodes_data:
            c = n.get("confidence")
            if isinstance(c, (int, float)):
                node_confidences.append(float(c) * (100.0 if c <= 1.0 else 1.0))
            elif isinstance(c, str):
                conf_map = {"high": 90.0, "medium": 65.0, "low": 40.0}
                node_confidences.append(conf_map.get(c.lower(), 60.0))
            else:
                node_confidences.append(70.0)

        edge_confidences = []
        for e in edges_data:
            c = e.get("confidence")
            if isinstance(c, (int, float)):
                edge_confidences.append(float(c) * (100.0 if c <= 1.0 else 1.0))

        all_conf = node_confidences + edge_confidences
        confidence_score = (sum(all_conf) / len(all_conf)) if all_conf else 75.0
        confidence_score = min(100.0, max(0.0, confidence_score))

        # 5. Exposure Factor (10%)
        # Public asset or external entry point vs internal repository
        is_public = asset_meta.get("is_public", True)
        exposure_type = str(asset_meta.get("exposure_type", "external")).lower()
        if not is_public or exposure_type == "internal":
            exposure_score = 40.0
        elif exposure_type in ("public", "external", "internet_facing"):
            exposure_score = 90.0
        else:
            exposure_score = 70.0

        # 6. Path Complexity Factor (5%)
        # Short paths (1-3 hops) are easier to execute and thus present higher immediate risk
        node_count = len(nodes_data)
        if node_count <= 2:
            path_complexity_score = 95.0
        elif node_count == 3:
            path_complexity_score = 80.0
        elif node_count == 4:
            path_complexity_score = 65.0
        else:
            path_complexity_score = 50.0

        # Weighted Sum
        final_score = (
            (finding_severity_score * WEIGHT_SEVERITY) +
            (exploitability_score * WEIGHT_EXPLOITABILITY) +
            (asset_crit_score * WEIGHT_ASSET_CRITICALITY) +
            (confidence_score * WEIGHT_CONFIDENCE) +
            (exposure_score * WEIGHT_EXPOSURE) +
            (path_complexity_score * WEIGHT_PATH_COMPLEXITY)
        )

        final_score = round(max(0.0, min(100.0, final_score)), 2)
        band = score_to_band(final_score)

        factors = {
            "finding_severity": {
                "score": round(finding_severity_score, 2),
                "weight": WEIGHT_SEVERITY,
                "contribution": round(finding_severity_score * WEIGHT_SEVERITY, 2),
                "details": f"Max node severity: {max_sev:.1f}, chain compounding: +{chain_compounding:.1f}",
            },
            "exploitability": {
                "score": round(exploitability_score, 2),
                "weight": WEIGHT_EXPLOITABILITY,
                "contribution": round(exploitability_score * WEIGHT_EXPLOITABILITY, 2),
                "details": f"Average likelihood: {avg_likelihood:.2f}, relationship multiplier: {multiplier:.2f}",
            },
            "asset_criticality": {
                "score": round(asset_crit_score, 2),
                "weight": WEIGHT_ASSET_CRITICALITY,
                "contribution": round(asset_crit_score * WEIGHT_ASSET_CRITICALITY, 2),
                "details": f"Asset criticality tier: {raw_crit.upper()}",
            },
            "confidence": {
                "score": round(confidence_score, 2),
                "weight": WEIGHT_CONFIDENCE,
                "contribution": round(confidence_score * WEIGHT_CONFIDENCE, 2),
                "details": f"Evaluated across {len(all_conf)} nodes/edges",
            },
            "exposure": {
                "score": round(exposure_score, 2),
                "weight": WEIGHT_EXPOSURE,
                "contribution": round(exposure_score * WEIGHT_EXPOSURE, 2),
                "details": f"Asset exposure: {exposure_type}",
            },
            "path_complexity": {
                "score": round(path_complexity_score, 2),
                "weight": WEIGHT_PATH_COMPLEXITY,
                "contribution": round(path_complexity_score * WEIGHT_PATH_COMPLEXITY, 2),
                "details": f"Path node length: {node_count}",
            },
        }

        return {
            "score": final_score,
            "risk_band": band,
            "model_version": MODEL_VERSION,
            "factors": factors,
            "calculated_at": datetime.utcnow().isoformat(),
            "calculated_by": "deterministic_engine",
        }
