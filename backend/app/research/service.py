from backend.app.agents.nova_research import NovaResearchAgent
from backend.app.research.tavily import TavilySearchProvider
from backend.app.schemas.research import ResearchRequest, SharedResearchPackage


def run_nova_research(
    request: ResearchRequest, search_provider: TavilySearchProvider
) -> SharedResearchPackage:
    """Internal boundary for dispatching scoped research work to Nova."""
    return NovaResearchAgent(search_provider).research(request)
