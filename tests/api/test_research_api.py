import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.api.routes.research import get_tavily_search_provider
from backend.app.core.database import get_db
from backend.app.core.migrations import run_migrations
from backend.app.main import app
from backend.app.models.repositories import (
    CurriculumRepository,
    OrchestrationRepository,
    SessionInputsRepository,
    SessionRepository,
    UserRepository,
)


@pytest.fixture
def research_client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    run_migrations(path)
    engine = create_engine(f"sqlite:///{path}")
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, test_session
    app.dependency_overrides.clear()
    test_session.close()
    engine.dispose()
    os.remove(path)


def _create_session(db, email="researcher@example.com"):
    user = UserRepository.create(db, email, "not-a-real-hash")
    topic = CurriculumRepository.create_topic(
        db, "Decision Trees", "Learn tree-based decision making."
    )
    CurriculumRepository.create_concept(
        db, topic.id, "Information Gain", description="Compare split quality."
    )
    session = SessionRepository.create_session(db, user.id, topic.id)
    SessionInputsRepository.create(
        db,
        session.id,
        task="Understand information gain",
        goal="Explain decision trees",
        learner_state="I know basic probability",
        interest="Sports analytics",
    )
    return user, session


def test_research_post_persists_package_and_is_idempotent(research_client):
    client, db = research_client
    user, session = _create_session(db)

    plan_response = client.post(
        f"/api/v1/sessions/{session.id}/cala-plan?user_id={user.id}"
    )
    assert plan_response.status_code == 200

    class MockSearchProvider:
        calls = 0

        def search(self, query: str, max_results: int = 5):
            self.calls += 1
            return [{
                "title": "Decision Trees and Information Gain Guide",
                "url": f"https://learn{self.calls}.example.edu/trees",
                "content": (
                    "Decision trees use information gain to compare useful data "
                    "splits and explain how a model selects a feature."
                ),
            }]

    provider = MockSearchProvider()
    app.dependency_overrides[get_tavily_search_provider] = lambda: provider

    first = client.post(
        f"/api/v1/sessions/{session.id}/research?user_id={user.id}"
    )
    assert first.status_code == 200
    package = first.json()
    assert package["session_id"] == session.id
    assert package["research_request"]["current_topic"]["topic_id"] == session.topic_id
    assert package["research_request"]["current_topic"]["concepts"][0]["concept_id"] != session.topic_id
    assert len(package["selected_sources"]) == 3
    assert provider.calls == 3

    second = client.post(
        f"/api/v1/sessions/{session.id}/research?user_id={user.id}"
    )
    retrieved = client.get(
        f"/api/v1/sessions/{session.id}/research?user_id={user.id}"
    )
    assert second.status_code == 200
    assert second.json() == package
    assert retrieved.status_code == 200
    assert retrieved.json() == package
    assert provider.calls == 3
    orchestration = OrchestrationRepository.get_by_session_id(db, session.id)
    assert orchestration.current_state == "RESEARCH_READY"
    assert orchestration.research_package_id


def test_research_requires_configuration_only_after_plan_exists(research_client):
    client, db = research_client
    user, session = _create_session(db)
    response_without_plan = client.post(
        f"/api/v1/sessions/{session.id}/research?user_id={user.id}"
    )
    assert response_without_plan.status_code == 409
    client.post(f"/api/v1/sessions/{session.id}/cala-plan?user_id={user.id}")
    app.dependency_overrides[get_tavily_search_provider] = lambda: None

    response = client.post(
        f"/api/v1/sessions/{session.id}/research?user_id={user.id}"
    )

    assert response.status_code == 503
    assert "TAVILY_API_KEY" in response.json()["detail"]


def test_research_routes_enforce_session_ownership(research_client):
    client, db = research_client
    owner, session = _create_session(db)
    other_user = UserRepository.create(
        db, "another@example.com", "not-a-real-hash"
    )
    app.dependency_overrides[get_tavily_search_provider] = lambda: None

    response = client.post(
        f"/api/v1/sessions/{session.id}/research?user_id={other_user.id}"
    )

    assert response.status_code == 404
    assert client.get(
        f"/api/v1/sessions/{session.id}/research?user_id={other_user.id}"
    ).status_code == 404


def test_research_context_and_persistence_are_isolated_per_session(research_client):
    client, db = research_client
    user, first_session = _create_session(db)
    second_session = SessionRepository.create_session(
        db, user.id, first_session.topic_id
    )
    SessionInputsRepository.create(
        db,
        second_session.id,
        task="Apply information gain to choose a sports lineup",
        goal="Compare player statistics",
        learner_state="I have used basic averages",
        interest="Basketball",
    )

    for session in (first_session, second_session):
        response = client.post(
            f"/api/v1/sessions/{session.id}/cala-plan?user_id={user.id}"
        )
        assert response.status_code == 200

    class MockSearchProvider:
        def search(self, query: str, max_results: int = 5):
            return [{
                "title": "Decision Trees and Information Gain Guide",
                "url": "https://learn.example.edu/trees",
                "content": (
                    "Decision trees use information gain to compare useful data "
                    "splits and explain how a model selects a feature."
                ),
            }]

    app.dependency_overrides[get_tavily_search_provider] = lambda: MockSearchProvider()
    packages = []
    for session in (first_session, second_session):
        response = client.post(
            f"/api/v1/sessions/{session.id}/research?user_id={user.id}"
        )
        assert response.status_code == 200
        packages.append(response.json())

    first_request = packages[0]["research_request"]
    second_request = packages[1]["research_request"]
    assert packages[0]["session_id"] == first_session.id
    assert packages[1]["session_id"] == second_session.id
    assert first_request["task"] == "Understand information gain"
    assert second_request["task"] == "Apply information gain to choose a sports lineup"
    assert first_request["interest"] == "Sports analytics"
    assert second_request["interest"] == "Basketball"
    assert client.get(
        f"/api/v1/sessions/{first_session.id}/research?user_id={user.id}"
    ).json() == packages[0]
