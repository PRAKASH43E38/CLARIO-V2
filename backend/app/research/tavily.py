import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilyConfigurationError(RuntimeError):
    pass


class TavilySearchError(RuntimeError):
    pass


class TavilySearchProvider:
    """Replaceable backend-only Tavily search adapter."""

    def __init__(self, api_key: str | None, timeout_seconds: float = 15.0):
        if not api_key or not api_key.strip():
            raise TavilyConfigurationError("TAVILY_API_KEY is not configured.")
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("Tavily search query must not be empty.")
        if not 1 <= max_results <= 20:
            raise ValueError("Tavily max_results must be between 1 and 20.")
        payload = json.dumps(
            {
                "api_key": self._api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": False,
            }
        ).encode("utf-8")
        request = Request(
            TAVILY_SEARCH_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise TavilySearchError("Tavily search request failed.") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TavilySearchError("Tavily returned an invalid response.") from exc

        if not isinstance(decoded, dict):
            raise TavilySearchError("Tavily returned an invalid response.")
        results = decoded.get("results")
        if not isinstance(results, list):
            raise TavilySearchError("Tavily response did not contain a results list.")
        return [
            self._normalize_result(result)
            for result in results[:max_results]
            if isinstance(result, dict)
        ]

    @staticmethod
    def _normalize_result(result: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for field in ("title", "url"):
            value = result.get(field)
            if isinstance(value, str):
                normalized[field] = value

        content = result.get("content")
        if not isinstance(content, str) or not content.strip():
            content = result.get("snippet")
        if isinstance(content, str):
            normalized["content"] = content

        published_date = result.get("published_date", result.get("publishedDate"))
        if isinstance(published_date, str):
            normalized["published_date"] = published_date

        source_type = result.get("source_type", result.get("type"))
        if isinstance(source_type, str):
            normalized["source_type"] = source_type
        return normalized
