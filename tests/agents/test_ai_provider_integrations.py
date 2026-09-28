import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest
from pydantic import BaseModel

from backend.app.ai.factory import get_ai_provider
from backend.app.ai.openai_compatible_provider import (
    MistralProvider,
    OpenRouterProvider,
)
from backend.app.core.config import settings


class SampleResponse(BaseModel):
    answer: str


@pytest.mark.parametrize(
    ("provider_class", "expected_url"),
    [
        (
            OpenRouterProvider,
            "https://openrouter.ai/api/v1/chat/completions",
        ),
        (MistralProvider, "https://api.mistral.ai/v1/chat/completions"),
    ],
)
def test_openai_compatible_provider_generates_validated_structured_output(
    provider_class, expected_url
):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(
        {"choices": [{"message": {"content": '{"answer": "ready"}'}}]}
    ).encode()
    provider = provider_class(api_key="test-key", model="test-model")

    with patch(
        "backend.app.ai.openai_compatible_provider.urlopen",
        return_value=response,
    ) as urlopen:
        result = provider.generate_structured(
            "Answer the question.",
            SampleResponse,
            system_instruction="Be concise.",
        )

    assert result == SampleResponse(answer="ready")
    request = urlopen.call_args.args[0]
    assert request.full_url == expected_url
    assert request.get_header("Authorization") == "Bearer test-key"
    payload = json.loads(request.data)
    assert payload["model"] == "test-model"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["messages"][0] == {
        "role": "system",
        "content": "Be concise.",
    }
    assert "answer" in payload["messages"][1]["content"]


def test_openai_compatible_provider_generates_text():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(
        {"choices": [{"message": {"content": "  Provider response  "}}]}
    ).encode()
    provider = MistralProvider(api_key="test-key", model="test-model")

    with patch(
        "backend.app.ai.openai_compatible_provider.urlopen",
        return_value=response,
    ):
        result = provider.generate_text("Say hello.")

    assert result == "Provider response"


def test_openai_compatible_provider_reports_http_failure():
    provider = OpenRouterProvider(api_key="test-key", model="test-model")

    with patch(
        "backend.app.ai.openai_compatible_provider.urlopen",
        side_effect=HTTPError(provider.API_URL, 401, "Unauthorized", {}, None),
    ):
        with pytest.raises(RuntimeError, match="HTTP 401"):
            provider.generate_text("Hello.")


def test_openai_compatible_provider_rejects_malformed_structured_content():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(
        {"choices": [{"message": {"content": '{"answer": 4}'}}]}
    ).encode()
    provider = MistralProvider(api_key="test-key", model="test-model")

    with patch(
        "backend.app.ai.openai_compatible_provider.urlopen",
        return_value=response,
    ):
        with pytest.raises(ValueError, match="malformed structured content"):
            provider.generate_structured("Answer.", SampleResponse)


@pytest.mark.parametrize(
    ("provider_name", "key_name", "provider_class"),
    [
        ("gemini", "GEMINI_API_KEY", "GeminiProvider"),
        ("openrouter", "OPENROUTER_API_KEY", OpenRouterProvider),
        ("mistral", "MISTRAL_API_KEY", MistralProvider),
    ],
)
def test_provider_factory_selects_configured_provider(
    monkeypatch, provider_name, key_name, provider_class
):
    monkeypatch.setattr(settings, "AI_PROVIDER", provider_name)
    monkeypatch.setattr(settings, key_name, "test-key")
    monkeypatch.setattr(settings, "AI_MODEL", None)

    provider = get_ai_provider()

    if provider_name == "gemini":
        assert provider.__class__.__name__ == provider_class
    else:
        assert isinstance(provider, provider_class)


@pytest.mark.parametrize(
    ("provider_name", "key_name"),
    [
        ("gemini", "GEMINI_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
        ("mistral", "MISTRAL_API_KEY"),
    ],
)
def test_provider_factory_reports_missing_selected_provider_key(
    monkeypatch, provider_name, key_name
):
    monkeypatch.setattr(settings, "AI_PROVIDER", provider_name)
    monkeypatch.setattr(settings, key_name, None)

    with pytest.raises(ValueError, match=key_name):
        get_ai_provider()


def test_provider_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "unknown")

    with pytest.raises(ValueError, match="Unsupported AI_PROVIDER"):
        get_ai_provider()
