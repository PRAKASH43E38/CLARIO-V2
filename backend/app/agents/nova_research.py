from datetime import datetime, timezone

from backend.app.research.tavily import TavilySearchProvider
from backend.app.research.validation import validate_and_rank_sources
from backend.app.schemas.research import (
    ResearchQueryResult,
    ResearchRequest,
    SharedResearchPackage,
    ResearchValidationInfo,
)


class NovaResearchAgent:
    """Nova's bounded responsibility is web research and source preparation."""

    MAX_QUERIES = 3
    RESULTS_PER_QUERY = 5

    def __init__(self, search_provider: TavilySearchProvider):
        self.search_provider = search_provider

    @staticmethod
    def build_queries(request: ResearchRequest) -> list[str]:
        topic = request.current_topic.title
        concept = (
            request.current_topic.concepts[0].title
            if request.current_topic.concepts
            else topic
        )
        candidates = [
            f"{request.learning_goal} {topic} {concept} foundational explanation",
            (
                f"{request.task} {concept} {request.learner_state} "
                f"{request.learner_level} "
                "step-by-step learning resource"
            ),
            f"{concept} {request.interest} practical application examples",
        ]
        queries: list[str] = []
        for query in candidates:
            normalized = " ".join(query.split())
            if normalized and normalized not in queries:
                queries.append(normalized[:240])
        return queries[: NovaResearchAgent.MAX_QUERIES]

    def research(self, request: ResearchRequest) -> SharedResearchPackage:
        queries = self.build_queries(request)
        candidates = []
        query_results = []
        for query in queries:
            results = self.search_provider.search(
                query=query, max_results=self.RESULTS_PER_QUERY
            )
            candidates.extend(results)
            query_results.append(
                ResearchQueryResult(query=query, result_count=len(results))
            )

        selected_sources, duplicate_count, rejected_count = validate_and_rank_sources(
            request, candidates
        )
        accepted_count = len(selected_sources)
        validation_status = (
            "complete"
            if accepted_count == 10
            else "partial"
            if accepted_count
            else "no_sources"
        )
        research_summary = self._build_summary(request, selected_sources)
        return SharedResearchPackage(
            session_id=request.session_id,
            research_request=request,
            research_summary=research_summary,
            key_concepts=request.current_topic.concepts,
            selected_sources=selected_sources,
            research_timestamp=datetime.now(timezone.utc),
            queries=query_results,
            validation_information=ResearchValidationInfo(
                status=validation_status,
                candidates_received=len(candidates),
                sources_validated=accepted_count,
                sources_rejected=rejected_count,
                duplicate_sources_removed=duplicate_count,
                maximum_sources_per_domain=2,
            ),
        )

    @staticmethod
    def _build_summary(request: ResearchRequest, sources) -> str:
        if not sources:
            return (
                "No sources passed relevance and content validation for this "
                "research request. No learning facts were inferred."
            )
        excerpts = " ".join(
            f"{source.title}: {source.snippet}" for source in sources[:3]
        )
        return (
            f"Retrieved {len(sources)} validated learning sources for "
            f"{request.learning_goal}. "
            f"Source excerpts: {excerpts}"
        )
