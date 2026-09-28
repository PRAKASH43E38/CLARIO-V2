from typing import Optional
from backend.app.core.config import settings
from backend.app.ai.base import BaseAIProvider
from backend.app.ai.mock_provider import MockAIProvider


def get_ai_provider(provider_name: Optional[str] = None) -> BaseAIProvider:
    """Factory to retrieve the configured AI Provider instance."""
    active_provider = (provider_name or settings.AI_PROVIDER).strip().lower()
    if active_provider == "mock":
        return MockAIProvider()

    provider_config = {
        "gemini": (
            settings.GEMINI_API_KEY,
            settings.AI_MODEL or "gemini-1.5-flash",
        ),
        "openrouter": (
            settings.OPENROUTER_API_KEY,
            settings.AI_MODEL or "openai/gpt-4.1-mini",
        ),
        "mistral": (
            settings.MISTRAL_API_KEY,
            settings.AI_MODEL or "mistral-small-latest",
        ),
    }
    if active_provider not in provider_config:
        raise ValueError(
            f"Unsupported AI_PROVIDER '{active_provider}'. Choose mock, gemini, "
            "openrouter, or mistral."
        )

    api_key, model = provider_config[active_provider]
    if not api_key or not api_key.strip():
        key_name = {
            "gemini": "GEMINI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "mistral": "MISTRAL_API_KEY",
        }[active_provider]
        raise ValueError(
            f"{key_name} is required when AI_PROVIDER={active_provider}."
        )

    if active_provider == "gemini":
        from backend.app.ai.gemini_provider import GeminiProvider

        return GeminiProvider(api_key=api_key, model=model)

    from backend.app.ai.openai_compatible_provider import (
        MistralProvider,
        OpenRouterProvider,
    )

    if active_provider == "openrouter":
        return OpenRouterProvider(api_key=api_key, model=model)
    return MistralProvider(api_key=api_key, model=model)
