import pytest
from pydantic import BaseModel
from backend.app.ai.base import BaseAIProvider
from backend.app.ai.mock_provider import MockAIProvider
from backend.app.ai.factory import get_ai_provider
from backend.app.schemas.research import ResearchOutput

class SampleModel(BaseModel):
    name: str
    score: int

def test_mock_provider_structured():
    provider = MockAIProvider()
    provider.set_response_for_model("SampleModel", {"name": "Test", "score": 99})

    result = provider.generate_structured("test prompt", SampleModel)
    assert isinstance(result, SampleModel)
    assert result.name == "Test"
    assert result.score == 99
    assert len(provider.call_history) == 1

def test_mock_provider_defaults():
    provider = MockAIProvider()
    result = provider.generate_structured("research ML", ResearchOutput)
    assert isinstance(result, ResearchOutput)
    assert result.topic == "Decision Trees"
    assert len(result.key_concepts) >= 1

def test_mock_provider_text():
    provider = MockAIProvider()
    txt = provider.generate_text("Explain entropy")
    assert "Mock text response" in txt

def test_ai_provider_factory():
    provider = get_ai_provider("mock")
    assert isinstance(provider, BaseAIProvider)
    assert isinstance(provider, MockAIProvider)
