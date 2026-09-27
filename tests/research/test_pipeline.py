import json
from unittest.mock import patch

import pytest

from backend.app.agents.nova_research import NovaResearchAgent
from backend.app.research.tavily import (
    TavilyConfigurationError,
    TavilySearchProvider,
)
from backend.app.research.validation import validate_and_rank_sources
from backend.app.schemas.research import (
    ResearchConcept,
    ResearchRequest,
    ResearchTopicContext,
)


@pytest.fixture
def research_request():
    return ResearchRequest(
        session_id="ses_test",
        learning_goal="Explain decision trees",
        task="Understand information gain",
        learner_state="I know basic probability",
        interest="Sports analytics",
        learner_level="beginner",
        recommended_starting_level="level_1",
        current_topic=ResearchTopicContext(
            topic_id="topic_trees",
            title="Decision Trees",
            concepts=[
                ResearchConcept(
                    concept_id="information_gain",
                    title="Information Gain",
                    description="Measure the value of a split.",
                )
            ],
        ),
        research_objective="Find reliable decision tree learning materials.",
    )


def _candidate(index: int, domain: str | None = None) -> dict[str, str]:
    return {
        "title": f"Decision Trees and Information Gain Guide {index}",
        "url": f"https://{domain or f'learning{index}.edu'}/decision-trees?utm_source=search",
        "content": (
            "Decision trees use information gain to compare useful data splits "
            "and explain how a model selects a feature."
        ),
    }


def test_validation_canonicalizes_deduplicates_and_limits_sources(research_request):
    candidates = [_candidate(index) for index in range(12)]
    candidates += [_candidate(0), {
        **_candidate(12),
        "url": "https://www.facebook.com/decision-trees",
    }]
    candidates[1]["url"] = (
        "https://www.learning1.edu/decision-trees?utm_source=other"
    )

    sources, duplicates, rejected = validate_and_rank_sources(
        research_request, candidates
    )

    assert len(sources) == 10
    assert len({source.url for source in sources}) == 10
    assert duplicates == 1
    assert rejected == 3
    assert all(source.validation_status == "validated" for source in sources)
    assert all("utm_" not in source.url for source in sources)


def test_validation_caps_sources_per_domain_and_rejects_noise(research_request):
    candidates = [
        _candidate(1, "learn.example.edu"),
        _candidate(2, "learn.example.edu"),
        _candidate(3, "learn.example.edu"),
        _candidate(4, "other.example.org"),
        {
            **_candidate(5),
            "url": "https://facebook.com/decision-trees",
        },
    ]
    candidates[0]["url"] = "https://learn.example.edu/decision-trees/1"
    candidates[1]["url"] = "https://learn.example.edu/decision-trees/2"
    candidates[2]["url"] = "https://learn.example.edu/decision-trees/3"

    sources, duplicates, rejected = validate_and_rank_sources(
        research_request, candidates
    )

    assert len(sources) == 3
    assert sum(source.domain == "learn.example.edu" for source in sources) == 2
    assert duplicates == 0
    assert rejected == 2


def test_nova_builds_bounded_queries_and_packages_only_validated_sources(
    research_request,
):
    class MockSearchProvider:
        def __init__(self):
            self.queries = []

        def search(self, query: str, max_results: int = 5):
            self.queries.append((query, max_results))
            return [_candidate(len(self.queries))]

    provider = MockSearchProvider()
    package = NovaResearchAgent(provider).research(research_request)

    assert len(provider.queries) <= 3
    assert all(max_results == 5 for _, max_results in provider.queries)
    assert len(package.queries) == len(provider.queries)
    assert len(package.selected_sources) == len(provider.queries)
    assert package.validation_information.status == "partial"
    assert "Source excerpts" in package.research_summary
    assert "basic probability" in " ".join(query for query, _ in provider.queries)


def test_nova_returns_explicit_empty_validation_result(research_request):
    class EmptySearchProvider:
        def search(self, query: str, max_results: int = 5):
            return []

    package = NovaResearchAgent(EmptySearchProvider()).research(research_request)

    assert package.selected_sources == []
    assert package.validation_information.status == "no_sources"
    assert "No learning facts were inferred" in package.research_summary


def test_tavily_requires_key_only_when_provider_is_used():
    with pytest.raises(TavilyConfigurationError):
        TavilySearchProvider(None)


def test_tavily_normalizes_search_results_without_live_network():
    class MockResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "results": [
                        {
                            "title": "Decision tree",
                            "url": "https://example.com",
                            "snippet": "Decision tree resource description",
                            "publishedDate": "2026-01-01",
                            "score": 0.99,
                        },
                        {"title": 23},
                        "not a result",
                    ]
                }
            ).encode("utf-8")

    with patch("backend.app.research.tavily.urlopen", return_value=MockResponse()):
        results = TavilySearchProvider("test-key").search("decision trees")

    assert results == [
        {
            "title": "Decision tree",
            "url": "https://example.com",
            "content": "Decision tree resource description",
            "published_date": "2026-01-01",
        },
        {},
    ]


def test_duplicate_url_with_invalid_result_does_not_hide_valid_result(research_request):
    invalid = _candidate(1)
    invalid["content"] = ""
    valid = _candidate(2)
    valid["url"] = invalid["url"]

    sources, duplicates, rejected = validate_and_rank_sources(
        research_request, [invalid, valid]
    )

    assert len(sources) == 1
    assert duplicates == 0
    assert rejected == 1
