import pytest
from pydantic import BaseModel
from app.ai.gemini import GeminiProvider
from app.ai.grok import GrokProvider
from app.ai.agent_base import AgentStatus, AgentRun


class SampleSecuritySchema(BaseModel):
    vulnerability_detected: bool = True
    confidence: float = 0.95
    cwe: str = "CWE-89"


@pytest.mark.asyncio
async def test_gemini_provider_text_and_structured():
    provider = GeminiProvider()
    assert provider.provider_name == "gemini"

    # Text generation
    text_res = await provider.generate_text("Analyze SQL query")
    assert "Gemini" in text_res.content
    assert text_res.metadata.provider == "gemini"
    assert text_res.metadata.prompt_tokens > 0

    # Structured generation
    struct_res = await provider.generate_structured("Analyze SQL query", SampleSecuritySchema)
    assert struct_res.metadata.provider == "gemini"
    assert hasattr(struct_res.parsed, "vulnerability_detected")


@pytest.mark.asyncio
async def test_grok_provider_text_and_structured():
    provider = GrokProvider()
    assert provider.provider_name == "grok"

    # Text generation
    text_res = await provider.generate_text("Simulate adversary traversal")
    assert "Grok" in text_res.content
    assert text_res.metadata.provider == "grok"

    # Structured generation
    struct_res = await provider.generate_structured("Simulate adversary", SampleSecuritySchema)
    assert struct_res.metadata.provider == "grok"


def test_agent_status_lifecycle():
    run = AgentRun(agent_name="code_security_agent")
    assert run.status == AgentStatus.QUEUED
    run.status = AgentStatus.RUNNING
    assert run.status == AgentStatus.RUNNING
    run.status = AgentStatus.COMPLETED
    assert run.status == AgentStatus.COMPLETED
