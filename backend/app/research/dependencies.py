from backend.app.core.config import settings
from backend.app.research.tavily import TavilySearchProvider


def get_tavily_search_provider() -> TavilySearchProvider | None:
    if not settings.TAVILY_API_KEY or not settings.TAVILY_API_KEY.strip():
        return None
    return TavilySearchProvider(settings.TAVILY_API_KEY)
