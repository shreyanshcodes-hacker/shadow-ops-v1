import pytest
from app.services.risk_engine import RiskEngine, score_to_band, MODEL_VERSION


def test_risk_score_deterministic_reproducibility():
    """Verify that identical inputs yield mathematically identical risk scores every single execution."""
    nodes = [
        {"severity": "critical", "confidence": "high"},
        {"severity": "high", "confidence": 0.85},
    ]
    edges = [
        {"edge_type": "ENABLES", "likelihood": 0.9, "confidence": 0.9},
    ]
    asset_meta = {"criticality": "high", "is_public": True, "exposure_type": "external"}

    first_run = RiskEngine.calculate_attack_path_risk(nodes, edges, asset_meta)
    for _ in range(50):
        subsequent_run = RiskEngine.calculate_attack_path_risk(nodes, edges, asset_meta)
        assert subsequent_run["score"] == first_run["score"]
        assert subsequent_run["risk_band"] == first_run["risk_band"]
        assert subsequent_run["model_version"] == MODEL_VERSION
        assert subsequent_run["factors"] == first_run["factors"]


def test_risk_score_bounds_and_band_mapping():
    """Test score clamping and edge-case boundary mapping across all risk bands."""
    assert score_to_band(-10.0) == "INFORMATIONAL"
    assert score_to_band(0.0) == "INFORMATIONAL"
    assert score_to_band(19.9) == "INFORMATIONAL"
    assert score_to_band(20.0) == "LOW"
    assert score_to_band(39.9) == "LOW"
    assert score_to_band(40.0) == "MEDIUM"
    assert score_to_band(59.9) == "MEDIUM"
    assert score_to_band(60.0) == "HIGH"
    assert score_to_band(79.9) == "HIGH"
    assert score_to_band(80.0) == "CRITICAL"
    assert score_to_band(100.0) == "CRITICAL"
    assert score_to_band(150.0) == "CRITICAL"


def test_risk_engine_factor_weights():
    """Verify that all factor weights strictly sum to 1.00 and each factor contributes predictably."""
    from app.services.risk_engine import (
        WEIGHT_SEVERITY,
        WEIGHT_EXPLOITABILITY,
        WEIGHT_ASSET_CRITICALITY,
        WEIGHT_CONFIDENCE,
        WEIGHT_EXPOSURE,
        WEIGHT_PATH_COMPLEXITY,
    )

    total_weight = (
        WEIGHT_SEVERITY
        + WEIGHT_EXPLOITABILITY
        + WEIGHT_ASSET_CRITICALITY
        + WEIGHT_CONFIDENCE
        + WEIGHT_EXPOSURE
        + WEIGHT_PATH_COMPLEXITY
    )
    assert abs(total_weight - 1.00) < 1e-6

    # Test minimal inputs
    nodes = [{"severity": "info", "confidence": "low"}]
    edges = [{"edge_type": "accesses", "likelihood": 0.2}]
    asset_meta = {"criticality": "low", "is_public": False, "exposure_type": "internal"}

    res = RiskEngine.calculate_attack_path_risk(nodes, edges, asset_meta)
    assert 0.0 <= res["score"] <= 100.0
    assert res["risk_band"] in ["INFORMATIONAL", "LOW"]

    # Test maximal inputs
    max_nodes = [
        {"severity": "critical", "confidence": "high"},
        {"severity": "critical", "confidence": "high"},
        {"severity": "critical", "confidence": "high"},
    ]
    max_edges = [
        {"edge_type": "ENABLES", "likelihood": 1.0, "confidence": 1.0},
        {"edge_type": "EXPOSES", "likelihood": 1.0, "confidence": 1.0},
    ]
    max_asset = {"criticality": "critical", "is_public": True, "exposure_type": "external"}

    max_res = RiskEngine.calculate_attack_path_risk(max_nodes, max_edges, max_asset)
    assert max_res["score"] >= 80.0
    assert max_res["risk_band"] == "CRITICAL"
    assert max_res["calculated_by"] == "deterministic_engine"


def test_ai_cannot_override_risk_score():
    """Verify the core safety invariant: AI cannot inject or alter numerical risk score."""
    # Even if an AI agent tries to include 'risk_score': 10.0 or 99.0 in metadata,
    # the RiskEngine calculates purely from deterministic factors.
    tainted_meta = {
        "criticality": "high",
        "is_public": True,
        "exposure_type": "external",
        "ai_suggested_score": 5.0,  # adversarial attempt to downgrade
    }
    nodes = [{"severity": "critical", "confidence": "high"}]
    edges = [{"edge_type": "EXPLOITS", "likelihood": 0.9}]

    res = RiskEngine.calculate_attack_path_risk(nodes, edges, tainted_meta)
    # The score should reflect high severity (80+), completely ignoring the 5.0
    assert res["score"] > 60.0
    assert "ai_suggested_score" not in res["factors"]
