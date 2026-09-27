import os
import tempfile
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.api.routes.research import get_tavily_search_provider
from backend.app.api.routes.orchestration import get_teaching_ai_provider
from backend.app.schemas.ayan import AyanGeneratedThinking
from backend.app.agents.kira.contracts import KiraGeneratedPractical
from backend.app.agents.zayn.quiz import ZaynGeneratedQuiz
from backend.app.core.database import get_db
from backend.app.core.migrations import run_migrations
from backend.app.main import app
from backend.app.models.repositories import (
    CalaPlanRepository,
    CurriculumRepository,
    OrchestrationRepository,
    SessionInputsRepository,
    SessionRepository,
    TeachingResultRepository,
    ThinkingResultRepository,
    PracticalResultRepository,
    ResearchPackageRepository,
    QuizResultRepository,
    ElaraEvaluationRepository,
    AdaptiveDecisionRepository,
    SessionConceptPerformanceRepository,
    UserRepository,
)
from backend.app.models.orchestration import OrchestrationRecord
from backend.app.models.quiz_result import QuizResultRecord
from backend.app.models.session_concept_performance import (
    SessionConceptPerformanceRecord,
)
from backend.app.research.tavily import TavilySearchError
from backend.app.schemas.mira import MiraGeneratedTeaching


@pytest.fixture
def orchestration_client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    run_migrations(path)
    engine = create_engine(f"sqlite:///{path}")
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.pop(get_tavily_search_provider, None)
    app.dependency_overrides.pop(get_teaching_ai_provider, None)
    with TestClient(app) as client:
        yield client, test_session
    app.dependency_overrides.clear()
    test_session.close()
    engine.dispose()
    os.remove(path)


def _create_session(db, email="learner@example.com"):
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


def _create_plan(client, user, session):
    response = client.post(
        f"/api/v1/sessions/{session.id}/cala-plan?user_id={user.id}"
    )
    assert response.status_code == 200
    return response.json()


class MockSearchProvider:
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def search(self, query: str, max_results: int = 5):
        self.calls += 1
        if self.error:
            raise self.error
        return [{
            "title": f"Decision Trees and Information Gain Guide {self.calls}",
            "url": f"https://learn{self.calls}.example.edu/trees",
            "content": (
                "Decision trees use information gain to compare useful data "
                "splits and explain how a model selects a feature."
            ),
        }]


class MockMiraProvider:
    def __init__(self, failure=None, malformed=False):
        self.calls = 0
        self.failure = failure
        self.malformed = malformed
        self.prompt = None

    def generate_structured(
        self, prompt, response_model, system_instruction=None, temperature=0.2
    ):
        self.calls += 1
        self.prompt = prompt
        if self.failure:
            raise self.failure
        if self.malformed:
            return response_model.model_validate({"concept": "missing fields"})
        task = json.loads(prompt.partition("Teaching task:\n")[2])
        sources = task["shared_research_package"]["selected_sources"]
        return MiraGeneratedTeaching(
            concept=task["current_concept"]["title"],
            explanation="Information gain compares how useful different splits are.",
            key_points=["It compares candidate splits.", "Higher gain means a more useful split."],
            examples=["Compare which player statistic best separates outcomes."],
            learner_level=task["current_level"],
            teaching_style="step-by-step",
            source_reference_ids=[sources[0]["source_id"]] if sources else [],
        )

    def generate_text(self, prompt, system_instruction=None, temperature=0.7):
        raise AssertionError("Mira must request structured output.")


class MockAyanProvider:
    def __init__(self, failure=None, malformed=False, forged_source=False):
        self.calls = 0
        self.failure = failure
        self.malformed = malformed
        self.forged_source = forged_source
        self.prompt = None

    def generate_structured(
        self, prompt, response_model, system_instruction=None, temperature=0.2
    ):
        self.calls += 1
        self.prompt = prompt
        if self.failure:
            raise self.failure
        if self.malformed:
            return response_model.model_validate({"concept": "missing fields"})
        task = json.loads(prompt.partition("Critical-thinking task:\n")[2])
        references = task["research_source_references"]
        return AyanGeneratedThinking(
            concept=task["concept"],
            thinking_prompt=(
                f"Why does {task['concept']} help explain your goal? "
                "Describe how you would reason through an example."
            ),
            expected_reasoning_focus=[
                "Explain why the concept supports the learning goal.",
                "Describe the reasoning steps.",
            ],
            difficulty=task["current_level"],
            source_reference_ids=(
                ["unverified-source"]
                if self.forged_source
                else [references[0]["source_id"]] if references else []
            ),
        )

    def generate_text(self, prompt, system_instruction=None, temperature=0.7):
        raise AssertionError("Ayan must request structured output.")


class MockKiraProvider:
    def __init__(self, failure=None, malformed=False, forged_source=False):
        self.calls = 0
        self.failure = failure
        self.malformed = malformed
        self.forged_source = forged_source
        self.prompt = None

    def generate_structured(
        self, prompt, response_model, system_instruction=None, temperature=0.2
    ):
        self.calls += 1
        self.prompt = prompt
        if self.failure:
            raise self.failure
        if self.malformed:
            return response_model.model_validate({"scenario": "incomplete"})
        task = json.loads(prompt.partition("Kira practical task:\n")[2])
        sources = task["research_source_ids"]
        context = task["learner_context"]
        concept = task["concept_name"]
        return KiraGeneratedPractical(
            scenario=f"A real-world decision uses {concept} in {context['interest']}.",
            practical_task=f"Apply {concept} to explain the decision.",
            real_world_context=f"The setting is {context['interest']}.",
            expected_action="Choose relevant evidence and explain how the concept applies.",
            success_criteria=["Connect evidence to the concept."],
            difficulty=context["learner_level"],
            research_source_ids=(
                ["foreign-source"] if self.forged_source else sources[:1]
            ),
        )

    def generate_text(self, prompt, system_instruction=None, temperature=0.7):
        raise AssertionError("Kira must request structured output.")


class MockZaynProvider:
    def __init__(self, failure=None, malformed=False, invalid_question=False):
        self.calls = 0
        self.failure = failure
        self.malformed = malformed
        self.invalid_question = invalid_question
        self.prompt = None

    def generate_structured(
        self, prompt, response_model, system_instruction=None, temperature=0.2
    ):
        self.calls += 1
        self.prompt = prompt
        if self.failure:
            raise self.failure
        if self.malformed:
            return response_model.model_validate({"questions": []})
        task = json.loads(prompt.partition("Zayn quiz task:\n")[2])
        difficulty = task["difficulty"]
        concept_id = (
            "wrong-concept" if self.invalid_question else task["concept_id"]
        )
        questions = []
        for index in range(task["question_count"]):
            correct = f"Apply {task['concept_name']} to this case {index + 1}"
            questions.append({
                "question_id": f"q_{index + 1}",
                "question": f"How should {task['concept_name']} guide decision {index + 1}?",
                "options": [correct, "Ignore the evidence", "Use an unrelated idea"],
                "correct_answer": correct,
                "explanation": "The selected action applies the target concept.",
                "difficulty": difficulty,
                "concept_id": concept_id,
            })
        return ZaynGeneratedQuiz(questions=questions, difficulty=difficulty)

    def generate_text(self, prompt, system_instruction=None, temperature=0.7):
        raise AssertionError("Zayn must request structured output.")


class MockElaraProvider:
    def __init__(
        self,
        failure=None,
        malformed=False,
        invalid=False,
        mismatched_metrics=False,
        strength="moderate",
        weakness="conceptual",
        confidence=0.6,
        signal="maintain",
    ):
        self.calls = 0
        self.failure = failure
        self.malformed = malformed
        self.invalid = invalid
        self.mismatched_metrics = mismatched_metrics
        self.strength = strength
        self.weakness = weakness
        self.confidence = confidence
        self.signal = signal
        self.prompt = None

    def generate_structured(
        self, prompt, response_model, system_instruction=None, temperature=0.2
    ):
        self.calls += 1
        self.prompt = prompt
        if self.failure:
            raise self.failure
        if self.malformed:
            return {"concept_strength": "moderate"}
        task = json.loads(prompt.partition("Elara evaluation task:\n")[2])
        performance = task["quiz_result_reference"]["performance"]
        if self.mismatched_metrics:
            performance = {**performance, "accuracy": 100}
        return {
            "concept_strength": self.strength if not self.invalid else "mastered",
            "concept_weakness": self.weakness,
            "quiz_performance": performance,
            "thinking_evidence": "unavailable",
            "practical_evidence": "unavailable",
            "overall_evaluation": (
                "Quiz evidence shows partial understanding; learner responses "
                "for thinking and practice are unavailable."
            ),
            "confidence": self.confidence,
            "difficulty_signal": self.signal,
            "evidence_summary": (
                f"Quiz accuracy is {performance['accuracy']}%. "
                "No Ayan or Kira learner response was collected."
            ),
        }

    def generate_text(self, prompt, system_instruction=None, temperature=0.7):
        raise AssertionError("Elara must request structured output.")


def _prepare_research_ready(client, user, session):
    _create_plan(client, user, session)
    initialized = client.post(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    )
    assert initialized.status_code == 200
    app.dependency_overrides[get_tavily_search_provider] = lambda: MockSearchProvider()
    ready = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/research?user_id={user.id}"
    )
    assert ready.status_code == 200
    return ready.json()


def _prepare_teaching_ready(client, user, session):
    ready = _prepare_research_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockMiraProvider()
    taught = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/teach?user_id={user.id}"
    )
    assert taught.status_code == 200
    assert taught.json()["current_state"] == "TEACHING_READY"
    return ready, taught.json()


def _prepare_thinking_ready(client, user, session):
    research, teaching = _prepare_teaching_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = MockAyanProvider
    thinking = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/think?user_id={user.id}"
    )
    assert thinking.status_code == 200
    assert thinking.json()["current_state"] == "THINKING_READY"
    return research, teaching, thinking.json()


def _prepare_practical_ready(client, user, session):
    research, teaching, thinking = _prepare_thinking_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = MockKiraProvider
    practical = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/practical?user_id={user.id}"
    )
    assert practical.status_code == 200
    assert practical.json()["current_state"] == "PRACTICAL_READY"
    return research, teaching, thinking, practical.json()


def _prepare_quiz_submitted(
    client, db, user, session, correct_count=3, difficulty="EASY"
):
    _prepare_practical_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockZaynProvider()
    path = f"/api/v1/sessions/{session.id}"
    presentation = client.post(
        f"{path}/orchestration/quiz?user_id={user.id}"
    ).json()
    answer_key = json.loads(
        QuizResultRepository.get_by_session_id(db, session.id).answer_key_json
    )
    answers = {}
    for index, question in enumerate(presentation["questions"]):
        if difficulty != "EASY":
            question["difficulty"] = difficulty
        answers[question["question_id"]] = (
            answer_key[question["question_id"]]["correct_answer"]
            if index < correct_count
            else question["options"][1]
        )
    quiz = QuizResultRepository.get_by_session_id(db, session.id)
    quiz.difficulty = difficulty
    quiz.time_limit_seconds = {"EASY": 30, "MEDIUM": 60, "HARD": 90}[difficulty]
    quiz.questions_json = json.dumps(presentation["questions"])
    db.commit()
    submitted = client.post(
        f"{path}/quiz/submit?user_id={user.id}",
        json={"quiz_id": presentation["quiz_id"], "answers": answers},
    )
    assert submitted.status_code == 200
    return presentation, answers


def _prepare_evaluation_ready(
    client, db, user, session, provider=None, correct_count=3, difficulty="EASY"
):
    _prepare_quiz_submitted(
        client,
        db,
        user,
        session,
        correct_count=correct_count,
        difficulty=difficulty,
    )
    selected_provider = provider or MockElaraProvider()
    app.dependency_overrides[get_teaching_ai_provider] = lambda: selected_provider
    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/evaluate?user_id={user.id}"
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_initialize_requires_plan_and_returns_cala_ready_context(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)

    missing_plan = client.post(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    )
    assert missing_plan.status_code == 409
    _create_plan(client, user, session)

    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    )

    assert response.status_code == 200
    state = response.json()
    assert state["session_id"] == session.id
    assert state["cala_plan_id"] == CalaPlanRepository.get_by_session_id(
        db, session.id
    ).id
    assert state["current_state"] == "CALA_READY"
    assert state["current_step"] == "cala_plan_loaded"
    assert state["research_package_id"] is None


def test_initialize_is_idempotent_and_isolated_by_session(orchestration_client):
    client, db = orchestration_client
    user, first_session = _create_session(db)
    second_user, second_session = _create_session(db, "other@example.com")
    _create_plan(client, user, first_session)
    _create_plan(client, second_user, second_session)

    first = client.post(
        f"/api/v1/sessions/{first_session.id}/orchestration?user_id={user.id}"
    ).json()
    repeated = client.post(
        f"/api/v1/sessions/{first_session.id}/orchestration?user_id={user.id}"
    ).json()
    second = client.post(
        f"/api/v1/sessions/{second_session.id}/orchestration?user_id={second_user.id}"
    ).json()

    assert first == repeated
    assert first["session_id"] != second["session_id"]
    assert OrchestrationRepository.get_by_session_id(db, first_session.id).id
    assert OrchestrationRepository.get_by_session_id(db, second_session.id).id
    assert client.get(
        f"/api/v1/sessions/{first_session.id}/orchestration?user_id={second_user.id}"
    ).status_code == 404


def test_invalid_session_is_not_initialized(orchestration_client):
    client, db = orchestration_client
    user, _session = _create_session(db)

    response = client.post(
        f"/api/v1/sessions/ses_missing/orchestration?user_id={user.id}"
    )

    assert response.status_code == 404
    assert OrchestrationRepository.get_by_session_id(db, "ses_missing") is None


def test_orchestrator_dispatches_nova_and_persists_research_ready_context(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _create_plan(client, user, session)
    initialized = client.post(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    )
    provider = MockSearchProvider()
    app.dependency_overrides[get_tavily_search_provider] = lambda: provider

    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/research?user_id={user.id}"
    )

    assert response.status_code == 200
    state = response.json()
    assert initialized.json()["current_state"] == "CALA_READY"
    assert state["current_state"] == "RESEARCH_READY"
    assert state["current_step"] == "shared_research_package_received"
    assert state["cala_plan_id"] == CalaPlanRepository.get_by_session_id(
        db, session.id
    ).id
    assert state["research_package_id"]
    assert state["research_package"]["session_id"] == session.id
    assert state["research_package"]["research_request"]["task"] == (
        "Understand information gain"
    )
    assert state["research_package"]["research_request"]["current_topic"][
        "topic_id"
    ] == session.topic_id
    assert state["research_package"]["research_request"]["current_topic"][
        "concepts"
    ][0]["concept_id"] != session.topic_id
    assert provider.calls == 3


def test_research_trigger_is_idempotent_and_get_reloads_persisted_context(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _create_plan(client, user, session)
    client.post(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    )
    provider = MockSearchProvider()
    app.dependency_overrides[get_tavily_search_provider] = lambda: provider
    path = f"/api/v1/sessions/{session.id}/orchestration"

    first = client.post(f"{path}/research?user_id={user.id}")
    second = client.post(f"{path}/research?user_id={user.id}")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert provider.calls == 3
    record = OrchestrationRepository.get_by_session_id(db, session.id)
    assert record.current_state == "RESEARCH_READY"
    assert record.research_package_id == first.json()["research_package_id"]

    engine = db.get_bind()
    db.close()
    reloaded_db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    def override_reloaded_db():
        yield reloaded_db

    app.dependency_overrides[get_db] = override_reloaded_db
    loaded = client.get(f"{path}?user_id={user.id}")
    reloaded_db.close()

    assert loaded.status_code == 200
    assert loaded.json() == first.json()


def test_research_configuration_failure_is_persisted_and_retryable(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _create_plan(client, user, session)
    client.post(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    )
    app.dependency_overrides[get_tavily_search_provider] = lambda: None
    path = f"/api/v1/sessions/{session.id}/orchestration"

    failed = client.post(f"{path}/research?user_id={user.id}")
    state = client.get(f"{path}?user_id={user.id}")

    assert failed.status_code == 503
    assert "TAVILY_API_KEY" in failed.json()["detail"]
    assert state.json()["current_state"] == "RESEARCH_FAILED"
    assert state.json()["current_step"] == "tavily_not_configured"
    assert state.json()["research_package_id"] is None


def test_provider_failure_sets_deterministic_failure_state(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    _create_plan(client, user, session)
    client.post(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    )
    app.dependency_overrides[get_tavily_search_provider] = lambda: MockSearchProvider(
        TavilySearchError("provider offline")
    )
    path = f"/api/v1/sessions/{session.id}/orchestration"

    response = client.post(f"{path}/research?user_id={user.id}")

    assert response.status_code == 502
    state = client.get(path + f"?user_id={user.id}").json()
    assert state["current_state"] == "RESEARCH_FAILED"
    assert state["current_step"] == "nova_research_failed"


def test_mira_requires_research_package(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    missing_plan = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/teach?user_id={user.id}"
    )
    assert missing_plan.status_code == 409
    _create_plan(client, user, session)
    client.post(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    )
    app.dependency_overrides[get_teaching_ai_provider] = MockMiraProvider

    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/teach?user_id={user.id}"
    )

    assert response.status_code == 409
    assert "research package" in response.json()["detail"]


def test_mira_rejects_package_without_validated_sources(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    _create_plan(client, user, session)
    client.post(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    )

    class EmptySearchProvider:
        def search(self, query: str, max_results: int = 5):
            return []

    app.dependency_overrides[get_tavily_search_provider] = EmptySearchProvider
    researched = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/research?user_id={user.id}"
    )
    assert researched.status_code == 200
    assert researched.json()["research_package"]["selected_sources"] == []
    provider = MockMiraProvider()
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider

    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/teach?user_id={user.id}"
    )

    assert response.status_code == 409
    assert "validated research source" in response.json()["detail"]
    assert provider.calls == 0
    assert client.get(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    ).json()["current_state"] == "RESEARCH_READY"


def test_mira_handoff_persists_structured_response_and_is_idempotent(
    orchestration_client, monkeypatch,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    research_ready = _prepare_research_ready(client, user, session)
    provider = MockMiraProvider()
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider
    path = f"/api/v1/sessions/{session.id}"
    transitions = []
    original_update_state = OrchestrationRepository.update_state

    def track_state(db_session, record, current_state, current_step, **kwargs):
        transitions.append(current_state)
        return original_update_state(
            db_session, record, current_state, current_step, **kwargs
        )

    monkeypatch.setattr(OrchestrationRepository, "update_state", track_state)

    response = client.post(
        f"{path}/orchestration/teach?user_id={user.id}"
    )
    repeated = client.post(
        f"{path}/orchestration/teach?user_id={user.id}"
    )

    assert response.status_code == 200
    state = response.json()
    assert state["current_state"] == "TEACHING_READY"
    assert state["current_step"] == "teaching_response_received"
    assert state["research_package_id"] == research_ready["research_package_id"]
    assert state["teaching_result_id"]
    assert state["teaching_result"]["concept"] == "Information Gain"
    assert state["teaching_result"]["learner_level"] == "beginner"
    assert state["teaching_result"]["key_points"]
    assert state["teaching_result"]["examples"]
    assert state["teaching_result"]["source_references"][0]["source_id"] == (
        research_ready["research_package"]["selected_sources"][0]["source_id"]
    )
    assert repeated.json() == state
    assert transitions == ["TEACHING_REQUESTED", "TEACHING", "TEACHING_READY"]
    assert provider.calls == 1
    assert TeachingResultRepository.get_by_session_id(db, session.id).orchestration_id == (
        OrchestrationRepository.get_by_session_id(db, session.id).id
    )

    retrieved = client.get(f"{path}/teaching?user_id={user.id}")
    assert retrieved.status_code == 200
    assert retrieved.json() == state["teaching_result"]
    assert client.get(
        f"{path}/orchestration?user_id={user.id}"
    ).json()["current_state"] == "TEACHING_READY"
    assert json.loads(provider.prompt.partition("Teaching task:\n")[2])[
        "shared_research_package"
    ]["session_id"] == session.id


@pytest.mark.parametrize(
    ("provider", "expected_step", "expected_detail"),
    [
        (MockMiraProvider(failure=RuntimeError("provider unavailable")), "mira_provider_failed", "provider"),
        (MockMiraProvider(malformed=True), "mira_response_invalid", "malformed"),
    ],
)
def test_mira_failures_are_controlled_and_persisted(
    orchestration_client, provider, expected_step, expected_detail
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_research_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider
    path = f"/api/v1/sessions/{session.id}"

    response = client.post(f"{path}/orchestration/teach?user_id={user.id}")

    assert response.status_code == 502
    assert expected_detail in response.json()["detail"].lower()
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "TEACHING_FAILED"
    assert state["current_step"] == expected_step
    assert state["research_package_id"]
    assert state["teaching_result_id"] is None
    assert TeachingResultRepository.get_by_session_id(db, session.id) is None


def test_teaching_endpoints_enforce_ownership_and_invalid_sessions(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    other_user, _ = _create_session(db, "other@example.com")

    assert client.post(
        f"/api/v1/sessions/ses_missing/orchestration/teach?user_id={user.id}"
    ).status_code == 404
    assert client.get(
        f"/api/v1/sessions/{session.id}/teaching?user_id={other_user.id}"
    ).status_code == 404
    assert client.post(
        f"/api/v1/sessions/{session.id}/orchestration/teach?user_id={other_user.id}"
    ).status_code == 404


def test_teaching_result_is_session_isolated(orchestration_client):
    client, db = orchestration_client
    user, first_session = _create_session(db)
    second_session = SessionRepository.create_session(db, user.id, first_session.topic_id)
    SessionInputsRepository.create(
        db,
        second_session.id,
        task="Learn another task",
        goal="A different goal",
        learner_state="Different learner state",
        interest="Basketball",
    )
    _prepare_research_ready(client, user, first_session)
    second_ready = _prepare_research_ready(client, user, second_session)
    assert second_ready["session_id"] == second_session.id
    provider = MockMiraProvider()
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider

    first_result = client.post(
        f"/api/v1/sessions/{first_session.id}/orchestration/teach?user_id={user.id}"
    )
    second_result = client.post(
        f"/api/v1/sessions/{second_session.id}/orchestration/teach?user_id={user.id}"
    )

    assert first_result.json()["teaching_result"]["session_id"] == first_session.id
    assert second_result.json()["teaching_result"]["session_id"] == second_session.id
    assert TeachingResultRepository.get_by_session_id(db, first_session.id).id != (
        TeachingResultRepository.get_by_session_id(db, second_session.id).id
    )


def test_teaching_result_survives_database_session_reload(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_research_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockMiraProvider()
    path = f"/api/v1/sessions/{session.id}"
    taught = client.post(f"{path}/orchestration/teach?user_id={user.id}")
    assert taught.status_code == 200
    user_id = user.id
    session_id = session.id
    engine = db.get_bind()
    db.close()
    reloaded_db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    def override_reloaded_db():
        yield reloaded_db

    app.dependency_overrides[get_db] = override_reloaded_db
    path = f"/api/v1/sessions/{session_id}"
    loaded = client.get(f"{path}/teaching?user_id={user_id}")
    state = client.get(f"{path}/orchestration?user_id={user_id}")
    reloaded_db.close()

    assert loaded.status_code == 200
    assert loaded.json() == taught.json()["teaching_result"]
    assert state.json()["current_state"] == "TEACHING_READY"
    assert state.json()["teaching_result_id"] == taught.json()["teaching_result_id"]


def test_teaching_persistence_failure_sets_failure_state(
    orchestration_client, monkeypatch
):
    from sqlalchemy.exc import SQLAlchemyError

    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_research_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockMiraProvider()

    def fail_persistence(*args, **kwargs):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(
        TeachingResultRepository,
        "create_if_missing",
        fail_persistence,
    )
    path = f"/api/v1/sessions/{session.id}"

    response = client.post(f"{path}/orchestration/teach?user_id={user.id}")

    assert response.status_code == 500
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "TEACHING_FAILED"
    assert state["current_step"] == "teaching_persistence_failed"
    assert state["research_package_id"]
    assert state["teaching_result_id"] is None


def test_ayan_requires_mira_teaching_and_research_context(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    app.dependency_overrides[get_teaching_ai_provider] = MockAyanProvider

    without_plan = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/think?user_id={user.id}"
    )
    assert without_plan.status_code == 409
    _prepare_research_ready(client, user, session)
    without_mira = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/think?user_id={user.id}"
    )
    assert without_mira.status_code == 409
    assert "Mira teaching" in without_mira.json()["detail"]


def test_ayan_generates_persists_and_reuses_thinking_response(
    orchestration_client, monkeypatch
):
    client, db = orchestration_client
    user, session = _create_session(db)
    research, teaching = _prepare_teaching_ready(client, user, session)
    provider = MockAyanProvider()
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider
    transitions = []
    original_update_state = OrchestrationRepository.update_state

    def track_state(db_session, record, current_state, current_step, **kwargs):
        transitions.append(current_state)
        return original_update_state(
            db_session, record, current_state, current_step, **kwargs
        )

    monkeypatch.setattr(OrchestrationRepository, "update_state", track_state)
    path = f"/api/v1/sessions/{session.id}"
    first = client.post(f"{path}/orchestration/think?user_id={user.id}")
    second = client.post(f"{path}/orchestration/think?user_id={user.id}")

    assert first.status_code == second.status_code == 200
    state = first.json()
    result = state["thinking_result"]
    assert state["current_state"] == "THINKING_READY"
    assert state["current_step"] == "thinking_response_received"
    assert state["research_package_id"] == research["research_package_id"]
    assert state["teaching_result_id"] == teaching["teaching_result_id"]
    assert state["thinking_result_id"]
    assert result["session_id"] == session.id
    assert result["concept"] == teaching["teaching_result"]["concept"]
    assert result["thinking_prompt"]
    assert result["expected_reasoning_focus"]
    assert result["difficulty"] == teaching["teaching_result"]["learner_level"]
    assert result["source_references"][0]["source_id"] == (
        teaching["teaching_result"]["source_references"][0]["source_id"]
    )
    assert second.json() == state
    assert transitions == ["THINKING_REQUESTED", "THINKING", "THINKING_READY"]
    assert provider.calls == 1

    task_json = json.loads(provider.prompt.partition("Critical-thinking task:\n")[2])
    assert task_json["mira_teaching_result"]["concept"] == result["concept"]
    assert task_json["research_source_references"][0]["source_id"] == (
        result["source_references"][0]["source_id"]
    )
    retrieved = client.get(f"{path}/thinking?user_id={user.id}")
    assert retrieved.status_code == 200
    assert retrieved.json() == result


@pytest.mark.parametrize(
    ("provider", "failure_step", "detail"),
    [
        (
            MockAyanProvider(failure=RuntimeError("provider unavailable")),
            "ayan_provider_failed",
            "provider",
        ),
        (
            MockAyanProvider(malformed=True),
            "ayan_response_invalid",
            "malformed",
        ),
        (
            MockAyanProvider(forged_source=True),
            "ayan_response_invalid",
            "outside the supplied research context",
        ),
    ],
)
def test_ayan_provider_and_output_failures_persist_thinking_failed(
    orchestration_client, provider, failure_step, detail
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_teaching_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider
    path = f"/api/v1/sessions/{session.id}"

    response = client.post(f"{path}/orchestration/think?user_id={user.id}")

    assert response.status_code == 502
    assert detail in response.json()["detail"].lower()
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "THINKING_FAILED"
    assert state["current_step"] == failure_step
    assert state["research_package_id"]
    assert state["teaching_result_id"]
    assert state["thinking_result_id"] is None


def test_ayan_session_ownership_and_invalid_session(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    other, _ = _create_session(db, "other@example.com")

    assert client.post(
        f"/api/v1/sessions/ses_missing/orchestration/think?user_id={user.id}"
    ).status_code == 404
    assert client.post(
        f"/api/v1/sessions/{session.id}/orchestration/think?user_id={other.id}"
    ).status_code == 404
    assert client.get(
        f"/api/v1/sessions/{session.id}/thinking?user_id={other.id}"
    ).status_code == 404


def test_ayan_persistence_is_isolated_by_session(orchestration_client):
    client, db = orchestration_client
    user, first_session = _create_session(db)
    second_session = SessionRepository.create_session(
        db, user.id, first_session.topic_id
    )
    SessionInputsRepository.create(
        db,
        second_session.id,
        task="A separate task",
        goal="A separate goal",
        learner_state="Separate learner evidence",
        interest="Basketball",
    )
    _prepare_teaching_ready(client, user, first_session)
    _prepare_teaching_ready(client, user, second_session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockAyanProvider()

    first = client.post(
        f"/api/v1/sessions/{first_session.id}/orchestration/think?user_id={user.id}"
    )
    second = client.post(
        f"/api/v1/sessions/{second_session.id}/orchestration/think?user_id={user.id}"
    )

    assert first.json()["thinking_result"]["session_id"] == first_session.id
    assert second.json()["thinking_result"]["session_id"] == second_session.id
    assert first.json()["thinking_result_id"] != second.json()["thinking_result_id"]


def test_ayan_persistence_survives_database_reload(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_teaching_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockAyanProvider()
    user_id, session_id = user.id, session.id
    path = f"/api/v1/sessions/{session_id}"
    created = client.post(f"{path}/orchestration/think?user_id={user_id}")
    engine = db.get_bind()
    db.close()
    reloaded = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    def override_reloaded_db():
        yield reloaded

    app.dependency_overrides[get_db] = override_reloaded_db
    result = client.get(f"{path}/thinking?user_id={user_id}")
    state = client.get(f"{path}/orchestration?user_id={user_id}")
    reloaded.close()

    assert result.status_code == 200
    assert result.json() == created.json()["thinking_result"]
    assert state.json()["current_state"] == "THINKING_READY"
    assert state.json()["thinking_result_id"] == created.json()["thinking_result_id"]


def test_ayan_persistence_failure_sets_thinking_failed(
    orchestration_client, monkeypatch
):
    from sqlalchemy.exc import SQLAlchemyError

    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_teaching_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockAyanProvider()

    def fail_persistence(*args, **kwargs):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(ThinkingResultRepository, "create_if_missing", fail_persistence)
    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/think?user_id={user.id}"
    )

    assert response.status_code == 500
    state = client.get(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    ).json()
    assert state["current_state"] == "THINKING_FAILED"
    assert state["current_step"] == "thinking_persistence_failed"


def test_kira_requires_orchestration_ayan_result_and_research_package(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    base = f"/api/v1/sessions/{session.id}"

    missing_orchestration = client.post(
        f"{base}/orchestration/practical?user_id={user.id}"
    )
    assert missing_orchestration.status_code == 409

    _prepare_teaching_ready(client, user, session)
    missing_ayan = client.post(
        f"{base}/orchestration/practical?user_id={user.id}"
    )
    assert missing_ayan.status_code == 409
    assert "Ayan" in missing_ayan.json()["detail"]

    _prepare_thinking_ready(client, user, session)
    package = ResearchPackageRepository.get_by_session_id(db, session.id)
    db.delete(package)
    db.commit()
    missing_package = client.post(
        f"{base}/orchestration/practical?user_id={user.id}"
    )
    assert missing_package.status_code == 409


def test_kira_valid_execution_transitions_persists_and_reuses_result(
    orchestration_client, monkeypatch
):
    client, db = orchestration_client
    user, session = _create_session(db)
    research, teaching, thinking = _prepare_thinking_ready(client, user, session)
    provider = MockKiraProvider()
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider
    transitions = []
    original_update_state = OrchestrationRepository.update_state

    def track_state(db_session, record, current_state, current_step, **kwargs):
        transitions.append(current_state)
        return original_update_state(
            db_session, record, current_state, current_step, **kwargs
        )

    monkeypatch.setattr(OrchestrationRepository, "update_state", track_state)
    path = f"/api/v1/sessions/{session.id}"
    first = client.post(f"{path}/orchestration/practical?user_id={user.id}")
    second = client.post(f"{path}/orchestration/practical?user_id={user.id}")

    assert first.status_code == second.status_code == 200
    state = first.json()
    result = state["practical_result"]
    assert state["current_state"] == "PRACTICAL_READY"
    assert state["current_step"] == "practical_activity_received"
    assert state["thinking_result_id"] == thinking["thinking_result_id"]
    assert state["practical_result_id"]
    assert state["research_package_id"] == research["research_package_id"]
    assert state["teaching_result_id"] == teaching["teaching_result_id"]
    assert result["agent"] == "Kira"
    assert result["session_id"] == session.id
    assert result["orchestration_id"] == (
        db.query(OrchestrationRecord)
        .filter_by(session_id=session.id)
        .first()
        .id
    )
    assert result["concept_id"]
    assert result["scenario"]
    assert result["practical_task"]
    assert result["real_world_context"]
    assert result["expected_action"]
    assert result["success_criteria"]
    assert result["difficulty"] == teaching["teaching_result"]["learner_level"]
    assert result["research_source_ids"][0] in {
        source["source_id"] for source in research["research_package"]["selected_sources"]
    }
    assert second.json() == state
    assert transitions == ["PRACTICAL_REQUESTED", "PRACTICAL", "PRACTICAL_READY"]
    assert provider.calls == 1
    fetched = client.get(f"{path}/practical?user_id={user.id}")
    assert fetched.status_code == 200
    assert fetched.json() == result


@pytest.mark.parametrize(
    ("provider", "failure_step", "detail"),
    [
        (
            MockKiraProvider(failure=RuntimeError("provider unavailable")),
            "kira_provider_failed",
            "provider",
        ),
        (
            MockKiraProvider(malformed=True),
            "kira_response_invalid",
            "malformed",
        ),
        (
            MockKiraProvider(forged_source=True),
            "kira_response_invalid",
            "outside the session research package",
        ),
    ],
)
def test_kira_provider_and_output_failures_persist_practical_failed(
    orchestration_client, provider, failure_step, detail
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_thinking_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider
    path = f"/api/v1/sessions/{session.id}"

    response = client.post(f"{path}/orchestration/practical?user_id={user.id}")

    assert response.status_code == 502
    assert detail in response.json()["detail"].lower()
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "PRACTICAL_FAILED"
    assert state["current_step"] == failure_step
    assert state["thinking_result_id"]
    assert state["practical_result_id"] is None


def test_kira_rejects_cross_session_research_package_and_non_owner(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    other, other_session = _create_session(db, "other-kira@example.com")
    _prepare_thinking_ready(client, user, session)
    package_record = ResearchPackageRepository.get_by_session_id(db, session.id)
    package = json.loads(package_record.package_json)
    package["session_id"] = other_session.id
    package_record.package_json = json.dumps(package)
    db.commit()
    path = f"/api/v1/sessions/{session.id}"

    cross_session = client.post(
        f"{path}/orchestration/practical?user_id={user.id}"
    )
    not_owner = client.post(
        f"{path}/orchestration/practical?user_id={other.id}"
    )
    invalid_session = client.get(
        f"/api/v1/sessions/ses_missing/practical?user_id={user.id}"
    )

    assert cross_session.status_code == 409
    assert "session" in cross_session.json()["detail"].lower()
    assert not_owner.status_code == 404
    assert invalid_session.status_code == 404


def test_kira_persistence_failure_sets_practical_failed(
    orchestration_client, monkeypatch
):
    from sqlalchemy.exc import SQLAlchemyError

    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_thinking_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockKiraProvider()

    def fail_persistence(*args, **kwargs):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(
        PracticalResultRepository, "create_if_missing", fail_persistence
    )
    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/practical?user_id={user.id}"
    )

    assert response.status_code == 500
    state = client.get(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    ).json()
    assert state["current_state"] == "PRACTICAL_FAILED"
    assert state["current_step"] == "practical_persistence_failed"


def test_kira_returns_not_found_for_missing_result_and_unowned_get(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    other, _ = _create_session(db, "kira-reader@example.com")

    assert client.get(
        f"/api/v1/sessions/{session.id}/practical?user_id={user.id}"
    ).status_code == 404
    assert client.get(
        f"/api/v1/sessions/{session.id}/practical?user_id={other.id}"
    ).status_code == 404


def test_zayn_requires_session_orchestration_and_kira_result(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    path = f"/api/v1/sessions/{session.id}"
    missing_orchestration = client.post(
        f"{path}/orchestration/quiz?user_id={user.id}"
    )
    assert missing_orchestration.status_code == 409

    _prepare_thinking_ready(client, user, session)
    missing_kira = client.post(f"{path}/orchestration/quiz?user_id={user.id}")
    assert missing_kira.status_code == 409
    assert "Kira" in missing_kira.json()["detail"]


def test_zayn_generates_idempotent_safe_presentation_and_get_result(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    research, teaching, thinking, practical = _prepare_practical_ready(
        client, user, session
    )
    provider = MockZaynProvider()
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider
    path = f"/api/v1/sessions/{session.id}"

    generated = client.post(
        f"{path}/orchestration/quiz?user_id={user.id}"
    )
    repeated = client.post(f"{path}/orchestration/quiz?user_id={user.id}")

    assert generated.status_code == repeated.status_code == 200
    presentation = generated.json()
    assert presentation["session_id"] == session.id
    assert presentation["orchestration_id"] == (
        db.query(OrchestrationRecord).filter_by(session_id=session.id).first().id
    )
    assert presentation["concept_id"] == practical["practical_result"]["concept_id"]
    assert presentation["difficulty"] == "EASY"
    assert presentation["time_limit_seconds"] == 30
    assert presentation["status"] == "IN_PROGRESS"
    assert len(presentation["questions"]) == 5
    assert provider.calls == 1
    assert repeated.json() == presentation
    assert all(
        "correct_answer" not in question and "explanation" not in question
        for question in presentation["questions"]
    )
    assert "correct_answer" not in generated.text
    assert "answer_key" not in generated.text
    stored = QuizResultRepository.get_by_session_id(db, session.id)
    assert stored.status == "IN_PROGRESS"
    assert "correct_answer" not in stored.questions_json
    assert "correct_answer" in stored.answer_key_json
    assert "explanation" in stored.answer_key_json
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "QUIZ_READY"
    assert state["quiz_id"] == presentation["quiz_id"]
    assert state["quiz_status"] == "IN_PROGRESS"
    fetched = client.get(f"{path}/quiz?user_id={user.id}")
    assert fetched.status_code == 200
    assert fetched.json() == presentation
    assert "correct_answer" not in fetched.text
    assert research["research_package_id"]
    assert teaching["teaching_result_id"]
    assert thinking["thinking_result_id"]


@pytest.mark.parametrize(
    ("provider", "step", "message"),
    [
        (
            MockZaynProvider(failure=RuntimeError("provider unavailable")),
            "zayn_provider_failed",
            "provider",
        ),
        (
            MockZaynProvider(malformed=True),
            "zayn_response_invalid",
            "malformed",
        ),
        (
            MockZaynProvider(invalid_question=True),
            "zayn_response_invalid",
            "different concept",
        ),
    ],
)
def test_zayn_failures_persist_quiz_failed(
    orchestration_client, provider, step, message
):
    client, _ = orchestration_client
    user, session = _create_session(orchestration_client[1])
    _prepare_practical_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider
    path = f"/api/v1/sessions/{session.id}"

    response = client.post(f"{path}/orchestration/quiz?user_id={user.id}")

    assert response.status_code == 502
    assert message in response.json()["detail"].lower()
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "QUIZ_FAILED"
    assert state["current_step"] == step
    assert state["quiz_id"] is None


def test_zayn_submit_valid_answers_hides_results_and_is_idempotent(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_practical_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockZaynProvider()
    path = f"/api/v1/sessions/{session.id}"
    presentation = client.post(
        f"{path}/orchestration/quiz?user_id={user.id}"
    ).json()
    answer_key = json.loads(
        QuizResultRepository.get_by_session_id(db, session.id).answer_key_json
    )
    answers = {
        question["question_id"]: answer_key[question["question_id"]]["correct_answer"]
        for question in presentation["questions"]
    }
    payload = {"quiz_id": presentation["quiz_id"], "answers": answers}

    submitted = client.post(f"{path}/quiz/submit?user_id={user.id}", json=payload)
    repeated = client.post(f"{path}/quiz/submit?user_id={user.id}", json=payload)

    assert submitted.status_code == repeated.status_code == 200
    assert submitted.json()["status"] == "SUBMITTED"
    assert submitted.json()["quiz_id"] == presentation["quiz_id"]
    assert "correct_answer" not in submitted.text
    assert "correctness" not in submitted.text
    assert "score" not in submitted.text
    assert repeated.json()["status"] == "SUBMITTED"
    persisted = QuizResultRepository.get_by_session_id(db, session.id)
    assert persisted.status == "SUBMITTED"
    assert json.loads(persisted.correctness_json) == {
        question_id: True for question_id in answers
    }
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "QUIZ_SUBMITTED"
    assert state["quiz_status"] == "SUBMITTED"

    different_answers = dict(answers)
    first_question = presentation["questions"][0]
    different_answers[first_question["question_id"]] = first_question["options"][1]
    conflict = client.post(
        f"{path}/quiz/submit?user_id={user.id}",
        json={"quiz_id": presentation["quiz_id"], "answers": different_answers},
    )
    assert conflict.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"quiz_id": "unknown", "answers": {}},
        {"quiz_id": "quiz_id", "answers": {"forged-question": "answer"}},
        {"quiz_id": "quiz_id", "answers": {"q_1": "not-an-option"}},
    ],
)
def test_zayn_submission_rejects_invalid_quiz_question_and_answer(
    orchestration_client, payload
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_practical_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockZaynProvider()
    path = f"/api/v1/sessions/{session.id}"
    presentation = client.post(
        f"{path}/orchestration/quiz?user_id={user.id}"
    ).json()
    if payload["quiz_id"] == "quiz_id":
        payload["quiz_id"] = presentation["quiz_id"]

    response = client.post(
        f"{path}/quiz/submit?user_id={user.id}", json=payload
    )
    assert response.status_code in {404, 422}


def test_zayn_rejects_non_owner_and_cross_session_submission(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    other, _ = _create_session(db, "zayn-other@example.com")
    _prepare_practical_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockZaynProvider()
    path = f"/api/v1/sessions/{session.id}"
    presentation = client.post(
        f"{path}/orchestration/quiz?user_id={user.id}"
    ).json()
    answers = {
        question["question_id"]: question["options"][0]
        for question in presentation["questions"]
    }

    not_owner = client.get(f"{path}/quiz?user_id={other.id}")
    cross_session = client.post(
        f"/api/v1/sessions/{other.id}/quiz/submit?user_id={other.id}",
        json={"quiz_id": presentation["quiz_id"], "answers": answers},
    )
    missing_session = client.get(
        "/api/v1/sessions/ses_missing/quiz?user_id=" + user.id
    )

    assert not_owner.status_code == 404
    assert cross_session.status_code == 404
    assert missing_session.status_code == 404


def test_zayn_persistence_failure_records_quiz_failed(orchestration_client, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_practical_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockZaynProvider()

    def fail_persistence(*args, **kwargs):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(QuizResultRepository, "create_if_missing", fail_persistence)
    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/quiz?user_id={user.id}"
    )

    assert response.status_code == 500
    state = client.get(
        f"/api/v1/sessions/{session.id}/orchestration?user_id={user.id}"
    ).json()
    assert state["current_state"] == "QUIZ_FAILED"
    assert state["current_step"] == "quiz_persistence_failed"


def test_elara_evaluates_submitted_quiz_idempotently_and_returns_safe_result(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_quiz_submitted(client, db, user, session)
    provider = MockElaraProvider()
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider
    path = f"/api/v1/sessions/{session.id}"

    evaluated = client.post(f"{path}/orchestration/evaluate?user_id={user.id}")
    repeated = client.post(f"{path}/orchestration/evaluate?user_id={user.id}")

    assert evaluated.status_code == repeated.status_code == 200
    output = evaluated.json()
    assert output["agent"] == "Elara"
    assert output["session_id"] == session.id
    assert output["concept_name"] == "Information Gain"
    assert output["quiz_performance"] == {
        "quiz_result_id": QuizResultRepository.get_by_session_id(db, session.id).id,
        "difficulty": "EASY",
        "total_questions": 5,
        "answered_questions": 5,
        "unanswered_questions": 0,
        "correct_answers": 3,
        "incorrect_answers": 2,
        "accuracy": 60.0,
    }
    assert output["thinking_evidence"] == "unavailable"
    assert output["practical_evidence"] == "unavailable"
    assert provider.calls == 1
    assert "answer_key" not in provider.prompt
    assert '"correct_answer":' not in provider.prompt
    assert "explanation" not in evaluated.text
    assert '"correct_answer":' not in evaluated.text
    assert "remediation" not in evaluated.text.lower()
    stored = ElaraEvaluationRepository.get_by_session_id(db, session.id)
    assert stored is not None
    assert stored.quiz_result_id == QuizResultRepository.get_by_session_id(
        db, session.id
    ).id
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "EVALUATION_READY"
    assert state["evaluation_id"] == stored.id
    assert state["evaluation"] == output
    assert client.get(f"{path}/evaluation?user_id={user.id}").json() == output


def test_elara_calculates_accuracy_and_unanswered_questions_from_submission(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_quiz_submitted(client, db, user, session)
    quiz = QuizResultRepository.get_by_session_id(db, session.id)
    answers = json.loads(quiz.submitted_answers_json)
    correctness = json.loads(quiz.correctness_json)
    unanswered_id = next(iter(answers))
    answers.pop(unanswered_id)
    correctness.pop(unanswered_id)
    quiz.submitted_answers_json = json.dumps(answers)
    quiz.correctness_json = json.dumps(correctness)
    db.commit()
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockElaraProvider()

    result = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/evaluate?user_id={user.id}"
    )

    assert result.status_code == 200
    assert result.json()["quiz_performance"] == {
        "quiz_result_id": quiz.id,
        "difficulty": "EASY",
        "total_questions": 5,
        "answered_questions": 4,
        "unanswered_questions": 1,
        "correct_answers": 2,
        "incorrect_answers": 2,
        "accuracy": 50.0,
    }


def test_elara_rejects_missing_or_unowned_session_and_orchestration(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    other, _ = _create_session(db, "elara-other@example.com")

    assert client.post(
        f"/api/v1/sessions/ses_missing/orchestration/evaluate?user_id={user.id}"
    ).status_code == 404
    assert client.post(
        f"/api/v1/sessions/{session.id}/orchestration/evaluate?user_id={other.id}"
    ).status_code == 404
    assert client.post(
        f"/api/v1/sessions/{session.id}/orchestration/evaluate?user_id={user.id}"
    ).status_code == 409


def test_elara_requires_submitted_quiz(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_practical_ready(client, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockZaynProvider()
    path = f"/api/v1/sessions/{session.id}"
    assert client.post(f"{path}/orchestration/quiz?user_id={user.id}").status_code == 200
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockElaraProvider()

    response = client.post(f"{path}/orchestration/evaluate?user_id={user.id}")

    assert response.status_code == 409
    assert "submitted" in response.json()["detail"].lower()
    assert client.get(f"{path}/orchestration?user_id={user.id}").json()[
        "current_state"
    ] == "QUIZ_READY"


@pytest.mark.parametrize(
    "missing_result",
    ["teaching", "thinking", "practical", "quiz"],
)
def test_elara_requires_same_session_worker_evidence(
    orchestration_client, missing_result
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_quiz_submitted(client, db, user, session)
    repository_by_name = {
        "teaching": TeachingResultRepository,
        "thinking": ThinkingResultRepository,
        "practical": PracticalResultRepository,
        "quiz": QuizResultRepository,
    }
    result = repository_by_name[missing_result].get_by_session_id(db, session.id)
    db.delete(result)
    db.commit()

    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/evaluate?user_id={user.id}"
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    ("provider", "expected_step"),
    [
        (MockElaraProvider(failure=RuntimeError("provider unavailable")), "elara_provider_failed"),
        (MockElaraProvider(malformed=True), "elara_response_invalid"),
        (MockElaraProvider(invalid=True), "elara_response_invalid"),
        (MockElaraProvider(mismatched_metrics=True), "elara_response_invalid"),
    ],
)
def test_elara_provider_and_invalid_output_failures_are_persisted(
    orchestration_client, provider, expected_step
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_quiz_submitted(client, db, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: provider
    path = f"/api/v1/sessions/{session.id}"

    response = client.post(f"{path}/orchestration/evaluate?user_id={user.id}")

    assert response.status_code == 502
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "EVALUATION_FAILED"
    assert state["current_step"] == expected_step
    assert ElaraEvaluationRepository.get_by_session_id(db, session.id) is None


def test_elara_persistence_failure_sets_evaluation_failed(
    orchestration_client, monkeypatch
):
    from sqlalchemy.exc import SQLAlchemyError

    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_quiz_submitted(client, db, user, session)
    app.dependency_overrides[get_teaching_ai_provider] = lambda: MockElaraProvider()

    def fail_persistence(*args, **kwargs):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(ElaraEvaluationRepository, "create_if_missing", fail_persistence)
    path = f"/api/v1/sessions/{session.id}"
    response = client.post(f"{path}/orchestration/evaluate?user_id={user.id}")

    assert response.status_code == 500
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "EVALUATION_FAILED"
    assert state["current_step"] == "evaluation_persistence_failed"


def test_elara_get_is_session_owned_and_returns_not_found_without_result(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    other, _ = _create_session(db, "elara-reader@example.com")
    path = f"/api/v1/sessions/{session.id}/evaluation"

    assert client.get(f"{path}?user_id={user.id}").status_code == 404
    assert client.get(f"{path}?user_id={other.id}").status_code == 404


def test_elara_rejects_cross_session_worker_evidence(orchestration_client):
    client, db = orchestration_client
    user, session = _create_session(db)
    _, other_session = _create_session(db, "elara-cross-session@example.com")
    _prepare_quiz_submitted(client, db, user, session)
    thinking = ThinkingResultRepository.get_by_session_id(db, session.id)
    thinking.session_id = other_session.id
    db.commit()

    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/evaluate?user_id={user.id}"
    )

    assert response.status_code == 409


def test_clario_decision_is_concept_scoped_idempotent_and_persisted(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    topic_id = session.topic_id
    sibling = CurriculumRepository.create_concept(
        db, topic_id, "Tree Splits", description="Choose a split."
    )
    _prepare_evaluation_ready(
        client,
        db,
        user,
        session,
        MockElaraProvider(
            strength="strong", weakness="none", confidence=0.9, signal="maintain"
        ),
        correct_count=5,
    )
    evaluation = ElaraEvaluationRepository.get_by_session_id(db, session.id)
    sibling_performance = SessionConceptPerformanceRecord(
        session_id=session.id,
        orchestration_id=OrchestrationRepository.get_by_session_id(db, session.id).id,
        concept_id=sibling.id,
        concept_name=sibling.title,
        current_difficulty="HARD",
        mastery_status="remediating",
        strength="weak",
        weakness="practical",
        evaluation_confidence=0.8,
        quiz_accuracy=20,
        attempt_count=4,
        remediation_count=2,
        last_evaluation_id=evaluation.id,
    )
    db.add(sibling_performance)
    db.commit()
    path = f"/api/v1/sessions/{session.id}"

    first = client.post(f"{path}/orchestration/decide?user_id={user.id}")
    repeated = client.post(f"{path}/orchestration/decide?user_id={user.id}")

    assert first.status_code == repeated.status_code == 200
    decision = first.json()
    assert decision["decision"] == "CONTINUE"
    assert decision["mastery_status"] == "mastered"
    assert decision["current_difficulty"] == "EASY"
    assert decision["next_difficulty"] == "EASY"
    assert decision["evaluation_reference"] == evaluation.id
    assert repeated.json() == decision
    assert AdaptiveDecisionRepository.get_by_session_id(db, session.id)
    concept_records = SessionConceptPerformanceRepository.list_by_session_id(
        db, session.id
    )
    current = next(row for row in concept_records if row.concept_id != sibling.id)
    untouched = next(row for row in concept_records if row.concept_id == sibling.id)
    assert current.mastery_status == "mastered"
    assert current.attempt_count == 1
    assert current.remediation_count == 0
    assert current.last_evaluation_id == evaluation.id
    assert untouched.mastery_status == "remediating"
    assert untouched.current_difficulty == "HARD"
    assert untouched.attempt_count == 4
    assert len(concept_records) == 2
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "DECISION_READY"
    assert state["adaptive_decision"] == decision
    assert state["concept_performance"]["concept_id"] == current.concept_id
    assert client.get(f"{path}/decision?user_id={user.id}").json() == decision
    listed = client.get(f"{path}/concept-performance?user_id={user.id}")
    assert listed.status_code == 200
    assert len(listed.json()) == 2


def test_clario_decision_reteach_reduces_only_weak_concept_difficulty(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_evaluation_ready(
        client,
        db,
        user,
        session,
        MockElaraProvider(
            strength="weak", weakness="conceptual", confidence=0.9, signal="decrease"
        ),
        difficulty="MEDIUM",
    )

    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/decide?user_id={user.id}"
    )

    assert response.status_code == 200
    decision = response.json()
    assert decision["decision"] == "REDUCE_DIFFICULTY"
    assert decision["mastery_status"] == "remediating"
    assert decision["remediation_required"] is True
    assert decision["current_difficulty"] == "MEDIUM"
    assert decision["next_difficulty"] == "EASY"
    performance = SessionConceptPerformanceRepository.get_by_session_and_concept(
        db, session.id, decision["concept_id"]
    )
    assert performance.current_difficulty == "EASY"
    assert performance.remediation_count == 1
    assert performance.attempt_count == 1


def test_clario_decision_retest_does_not_mark_insufficient_evidence_mastered(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_evaluation_ready(
        client,
        db,
        user,
        session,
        MockElaraProvider(
            strength="insufficient_evidence",
            weakness="insufficient_evidence",
            confidence=0.2,
            signal="insufficient_evidence",
        ),
        correct_count=0,
    )

    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/decide?user_id={user.id}"
    )

    assert response.status_code == 200
    decision = response.json()
    assert decision["decision"] == "RETEST"
    assert decision["mastery_status"] == "learning"
    assert decision["next_difficulty"] == "EASY"
    performance = SessionConceptPerformanceRepository.get_by_session_and_concept(
        db, session.id, decision["concept_id"]
    )
    assert performance.mastery_status == "learning"
    assert performance.remediation_count == 0


def test_clario_decision_increases_difficulty_for_mastered_concept_only(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    sibling = CurriculumRepository.create_concept(
        db, session.topic_id, "Tree Splits", description="Choose a split."
    )
    _prepare_evaluation_ready(
        client,
        db,
        user,
        session,
        MockElaraProvider(
            strength="strong", weakness="none", confidence=0.95, signal="increase"
        ),
        correct_count=5,
        difficulty="MEDIUM",
    )
    evaluation = ElaraEvaluationRepository.get_by_session_id(db, session.id)
    sibling_performance = SessionConceptPerformanceRecord(
        session_id=session.id,
        orchestration_id=OrchestrationRepository.get_by_session_id(db, session.id).id,
        concept_id=sibling.id,
        concept_name=sibling.title,
        current_difficulty="HARD",
        mastery_status="learning",
        strength="moderate",
        weakness="none",
        evaluation_confidence=0.5,
        quiz_accuracy=50,
        attempt_count=1,
        remediation_count=0,
        last_evaluation_id=evaluation.id,
    )
    db.add(sibling_performance)
    db.commit()

    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/decide?user_id={user.id}"
    )

    assert response.status_code == 200
    decision = response.json()
    assert decision["decision"] == "INCREASE_DIFFICULTY"
    assert decision["mastery_status"] == "mastered"
    assert decision["current_difficulty"] == "MEDIUM"
    assert decision["next_difficulty"] == "HARD"
    untouched = SessionConceptPerformanceRepository.get_by_session_and_concept(
        db, session.id, sibling.id
    )
    assert untouched.current_difficulty == "HARD"
    assert untouched.mastery_status == "learning"


def test_clario_decision_completes_only_fully_mastered_mapped_level(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_evaluation_ready(
        client,
        db,
        user,
        session,
        MockElaraProvider(
            strength="strong", weakness="none", confidence=0.9, signal="maintain"
        ),
        correct_count=5,
    )

    response = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/decide?user_id={user.id}"
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "COMPLETE_LEVEL"
    stored_plan = CalaPlanRepository.get_by_session_id(db, session.id)
    plan = json.loads(stored_plan.plan_json)
    assert plan["roadmap"][0]["completion_state"] == "completed"
    assert plan["roadmap"][1]["is_unlocked"] is False
    assert all(
        concept["concept_id"] == response.json()["concept_id"]
        for topic in plan["roadmap"][0]["topics"]
        for concept in topic["concepts"]
    )


def test_clario_decision_rejects_missing_state_owner_and_orchestration(
    orchestration_client,
):
    client, db = orchestration_client
    user, session = _create_session(db)
    other, _ = _create_session(db, "decision-owner@example.com")
    assert client.post(
        f"/api/v1/sessions/ses_missing/orchestration/decide?user_id={user.id}"
    ).status_code == 404
    assert client.post(
        f"/api/v1/sessions/{session.id}/orchestration/decide?user_id={other.id}"
    ).status_code == 404
    assert client.post(
        f"/api/v1/sessions/{session.id}/orchestration/decide?user_id={user.id}"
    ).status_code == 409

    _prepare_evaluation_ready(client, db, user, session)
    orchestration = OrchestrationRepository.get_by_session_id(db, session.id)
    orchestration.current_state = "EVALUATION_FAILED"
    db.commit()
    rejected = client.post(
        f"/api/v1/sessions/{session.id}/orchestration/decide?user_id={user.id}"
    )
    assert rejected.status_code == 409
    assert AdaptiveDecisionRepository.get_by_session_id(db, session.id) is None


def test_clario_decision_persistence_failure_sets_decision_failed(
    orchestration_client, monkeypatch
):
    from sqlalchemy.exc import SQLAlchemyError

    client, db = orchestration_client
    user, session = _create_session(db)
    _prepare_evaluation_ready(client, db, user, session)

    def fail_persistence(*args, **kwargs):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(
        AdaptiveDecisionRepository, "create_if_missing", fail_persistence
    )
    path = f"/api/v1/sessions/{session.id}"
    response = client.post(f"{path}/orchestration/decide?user_id={user.id}")
    assert response.status_code == 500
    state = client.get(f"{path}/orchestration?user_id={user.id}").json()
    assert state["current_state"] == "DECISION_FAILED"
    assert state["current_step"] == "clario_decision_failed"
    assert SessionConceptPerformanceRepository.list_by_session_id(
        db, session.id
    ) == []
