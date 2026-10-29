from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class AIRequestConfig(BaseModel):
    model_name: Optional[str] = None
    temperature: float = 0.2
    max_output_tokens: int = 4096
    timeout_seconds: int = 60
    max_retries: int = 3
    cost_cap_usd: float = 2.0


class AIResponseMetadata(BaseModel):
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: int = 0


class AITextResponse(BaseModel):
    content: str
    metadata: AIResponseMetadata


class AIStructuredResponse(BaseModel):
    parsed: Any
    raw_json: Dict[str, Any]
    metadata: AIResponseMetadata


class AIProvider(ABC):
    """
    Abstract AI Provider Interface:
    Decouples business logic from external LLM providers (Gemini / Grok).
    Supports structured schema generation, token tracking, timeouts, and cost controls.
    """
    provider_name: str

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AITextResponse:
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AIStructuredResponse:
        pass


def get_ai_provider(provider_name: Optional[str] = None) -> AIProvider:
    """
    Factory function to retrieve the configured AI provider instance.
    """
    from app.core.config import settings
    from app.ai.gemini import GeminiProvider
    from app.ai.grok import GrokProvider

    chosen = (provider_name or settings.AI_PROVIDER).lower()
    if chosen in ("fake", "fake_test_provider", "test_double") or settings.ENVIRONMENT == "test":
        from app.ai.fake import FakeAIProvider
        return FakeAIProvider()
    if chosen == "grok":
        return GrokProvider()
    return GeminiProvider()
