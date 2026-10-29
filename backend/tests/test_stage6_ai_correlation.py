import pytest
from uuid import uuid4

from app.models.finding import Finding
from app.services.ai_correlation import AICorrelationService
from app.ai.safety import redact_secrets


@pytest.mark.asyncio
async def test_ai_relationship_correlation_structured_suggestion():
    """Verify that AI correlation service produces structured, bounded relationship suggestions."""
    ws_id = uuid4()
    asset_id = uuid4()
    scan_id = uuid4()

    f1 = Finding(
        id=uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan_id,
        source="semgrep",
        title="Unprotected JWT secret verification",
        description="Missing signature check on user token",
        severity="high",
        confidence="high",
    )
    f2 = Finding(
        id=uuid4(),
        workspace_id=ws_id,
        asset_id=asset_id,
        scan_id=scan_id,
        source="semgrep",
        title="Privileged administrative role modification",
        description="User can escalate their role in request body",
        severity="critical",
        confidence="high",
    )

    result = await AICorrelationService.analyze_relationship(
        finding_a=f1,
        finding_b=f2,
        provider_name="fake",
    )

    assert result is not None
    assert result["source_finding_id"] == f1.id
    assert result["target_finding_id"] == f2.id
    assert result["source"] == "AI_SUGGESTED"
    assert result["relationship_type"] in [
        "DEPENDS_ON",
        "ENABLES",
        "EXPOSES",
        "LEADS_TO",
        "SHARES_COMPONENT",
        "SHARES_ENTRY_POINT",
        "SHARES_DATA_FLOW",
        "AMPLIFIES",
    ]
    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["rationale"]) > 0


@pytest.mark.asyncio
async def test_ai_correlation_secret_redaction():
    """Verify that sensitive secrets are purged from finding text before prompt construction."""
    raw_title = "Secret leak: AKIAIOSFODNN7EXAMPLE discovered in api"
    redacted = redact_secrets(raw_title)
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED_AWS_KEY_ID]" in redacted
