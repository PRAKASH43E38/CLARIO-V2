from typing import Optional
from backend.app.ai.base import BaseAIProvider

class BaseAgent:
    """Base class for all CLARIO specialized agents."""

    def __init__(self, ai_provider: BaseAIProvider):
        self.ai_provider = ai_provider
