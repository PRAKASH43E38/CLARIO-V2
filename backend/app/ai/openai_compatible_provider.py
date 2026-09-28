import json
from typing import Any, Optional, Type, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError

from backend.app.ai.base import BaseAIProvider

T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleProvider(BaseAIProvider):
    API_URL = ""
    PROVIDER_NAME = "AI"
    EXTRA_HEADERS: dict[str, str] = {}

    def __init__(self, api_key: str, model: str):
        if not api_key.strip():
            raise ValueError(f"{self.PROVIDER_NAME} API key is required.")
        self.api_key = api_key
        self.model = model

    def _generate(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str],
        temperature: float,
        json_mode: bool,
    ) -> str:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        request = Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                **self.EXTRA_HEADERS,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(
                f"{self.PROVIDER_NAME} request failed with HTTP {exc.code}."
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(
                f"{self.PROVIDER_NAME} request could not reach the provider."
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"{self.PROVIDER_NAME} returned an invalid response."
            ) from exc

        try:
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"{self.PROVIDER_NAME} response did not contain a completion."
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"{self.PROVIDER_NAME} returned empty content.")
        return content.strip()

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        schema = json.dumps(response_model.model_json_schema(), ensure_ascii=True)
        structured_prompt = (
            f"{prompt}\n\nReturn only a JSON object conforming to this schema:\n{schema}"
        )
        response = self._generate(
            structured_prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            json_mode=True,
        )
        try:
            return response_model.model_validate(json.loads(response))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(
                f"{self.PROVIDER_NAME} returned malformed structured content."
            ) from exc

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        return self._generate(
            prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            json_mode=False,
        )


class OpenRouterProvider(OpenAICompatibleProvider):
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    PROVIDER_NAME = "OpenRouter"
    EXTRA_HEADERS = {"X-Title": "CLARIO"}


class MistralProvider(OpenAICompatibleProvider):
    API_URL = "https://api.mistral.ai/v1/chat/completions"
    PROVIDER_NAME = "Mistral"
