import pytest
from uuid import uuid4
from app.scanners.semgrep import SemgrepRunner, SemgrepConfig
from app.scanners.normalizer import FindingNormalizer


def test_semgrep_runner_command_builder():
    config = SemgrepConfig(rulesets=["p/owasp-top-ten", "p/secrets"])
    runner = SemgrepRunner(config)
    cmd = runner.build_command("/tmp/target-repo")

    assert cmd[0] == "semgrep"
    assert "--config" in cmd
    assert "p/owasp-top-ten" in cmd
    assert "/tmp/target-repo" in cmd


def test_finding_normalizer_fingerprint_and_schema():
    asset_id = uuid4()
    mock_semgrep_match = {
        "check_id": "python.django.security.injection.sql",
        "path": "app/views.py",
        "start": {"line": 42},
        "end": {"line": 45},
        "extra": {
            "severity": "ERROR",
            "message": "Potential SQL injection vulnerability",
            "lines": "cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')",
            "metadata": {"cwe": ["CWE-89"]},
        },
    }

    finding = FindingNormalizer.normalize_semgrep_match(asset_id, mock_semgrep_match)

    assert finding.rule_id == "python.django.security.injection.sql"
    assert finding.severity == "critical"
    assert finding.line_start == 42
    assert "CWE-89" in finding.cwe_ids
    assert len(finding.fingerprint) == 64  # SHA-256 hash length

    # Deduplication test: identical match on same asset produces identical fingerprint
    finding_duplicate = FindingNormalizer.normalize_semgrep_match(asset_id, mock_semgrep_match)
    assert finding.fingerprint == finding_duplicate.fingerprint
