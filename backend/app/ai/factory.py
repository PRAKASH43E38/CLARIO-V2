from typing import Optional
from backend.app.core.config import settings
from backend.app.ai.base import BaseAIProvider
from backend.app.ai.mock_provider import MockAIProvider

def get_ai_provider(provider_name: Optional[str] = None) -> BaseAIProvider:
    """Factory to retrieve the configured AI Provider instance."""
    active_provider = provider_name or settings.AI_PROVIDER

    if active_provider == "mock":
        return MockAIProvider()
    elif active_provider == "gemini":
        if not settings.GEMINI_API_KEY:
            # Fall back safely to mock if key is missing in dev
            return MockAIProvider()
        try:
            from backend.app.ai.gemini_provider import GeminiProvider
            return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.AI_MODEL or "gemini-1.5-flash")
        except Exception:
            # Fall back to mock if Gemini fails to initialize
            return MockAIProvider()
    else:
        return MockAIProvider()
