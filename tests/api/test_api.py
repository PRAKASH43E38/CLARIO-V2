import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.migrations import run_migrations
from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.models.repositories import (
    UserRepository, LearnerProfileRepository, CurriculumRepository,
    SessionRepository, ConceptPerformanceRepository,
)
from backend.app.models.user import User
from backend.app.models.learner import LearnerProfile
from backend.app.models.session import LearningSession

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    run_migrations(path)
    engine = create_engine(f"sqlite:///{path}")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    yield db, path

    db.close()
    engine.dispose()
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def client(temp_db):
    db, _ = temp_db
    
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "clario-api"
    assert data["version"] == "0.1.0"


def test_email_auth_profile_mind_profile_and_learning_inputs(client):
    credentials = {"email": "NewLearner@Example.com", "password": "correct horse battery"}
    registered = client.post("/api/v1/auth/register", json=credentials)
    assert registered.status_code == 201
    auth = registered.json()
    user_id = auth["user_id"]
    assert auth["profile_complete"] is False
    assert auth["mind_profile_complete"] is False

    db = client.app.dependency_overrides[get_db]().__next__()
    user = UserRepository.get_by_id(db, user_id)
    assert user is not None
    assert user.email == "newlearner@example.com"
    assert user.password_hash != credentials["password"]
    assert user.password_hash.startswith("pbkdf2_sha256$")

    logged_in = client.post("/api/v1/auth/login", json=credentials)
    assert logged_in.status_code == 200
    assert logged_in.json()["user_id"] == user_id
    assert client.post("/api/v1/auth/login", json={
        "email": credentials["email"], "password": "wrong password"
    }).status_code == 401

    profile = client.put(f"/api/v1/profile?user_id={user_id}", json={
        "name": "Learner",
        "gender": "prefer_not_to_say",
        "basic_details": "Interested in data",
    })
    assert profile.status_code == 200
    assert profile.json()["authentication_provider"] == "email"

    mind_answers = {
        "learning_motivation": "Curiosity",
        "preferred_explanation": "A worked example",
        "support_when_stuck": "A small hint",
        "feedback_preference": "Direct correction",
        "challenge_preference": "Start gently and build up",
    }
    saved_mind = client.put(f"/api/v1/mind-profile?user_id={user_id}", json=mind_answers)
    assert saved_mind.status_code == 200
    assert saved_mind.json()["preferred_explanation"] == "A worked example"
    assert client.get(f"/api/v1/auth/status?user_id={user_id}").json()["mind_profile_complete"] is True
    changed_mind_answers = {**mind_answers, "preferred_explanation": "A visual analogy"}
    assert client.put(
        f"/api/v1/mind-profile?user_id={user_id}", json=changed_mind_answers
    ).status_code == 409
    assert client.get(f"/api/v1/mind-profile?user_id={user_id}").json()[
        "preferred_explanation"
    ] == "A worked example"

    inputs = {
        "task": "Understand feature scaling",
        "goal": "Choose and apply a scaling method",
        "learner_state": "I know what features are but have not scaled data before",
        "interest": "Sports analytics",
    }
    created = client.post(
        f"/api/v1/learning-session/create?user_id={user_id}",
        json=inputs,
    )
    assert created.status_code == 201
    response_data = created.json()
    assert response_data["inputs"] == inputs

    learner_profile = LearnerProfileRepository.get_by_user_id(db, user_id)
    assert learner_profile is not None
    assert learner_profile.learning_goal == inputs["goal"]
    assert learner_profile.current_level == "unassessed"
    assert learner_profile.learning_preference == "example_first"
    assert learner_profile.interests == inputs["interest"]
    assert learner_profile.initial_confidence == 0
    performance = ConceptPerformanceRepository.get_or_create(
        db, learner_profile.id, "cpt_entropy"
    )
    assert performance.profile_id == learner_profile.id

    state = client.get(f"/api/v1/session/{response_data['session_id']}/state")
    assert state.status_code == 200
    assert state.json()["inputs"] == inputs
    assert state.json()["profile_id"] == learner_profile.id
    assert state.json()["current_concept_id"] == "cpt_entropy"
    assert state.json()["current_step"] == "idle"
    assert state.json()["current_content"] is None
    assert db.query(LearningSession).filter(
        LearningSession.id == response_data["session_id"]
    ).one().activities == []

    mind_before_plan = client.get(
        f"/api/v1/mind-profile?user_id={user_id}"
    ).json()
    plan_response = client.post(
        f"/api/v1/sessions/{response_data['session_id']}/cala-plan?user_id={user_id}"
    )
    assert plan_response.status_code == 200
    plan = plan_response.json()
    assert plan["session_id"] == response_data["session_id"]
    assert plan["task"] == inputs["task"]
    assert plan["learning_goal"] == inputs["goal"]
    assert plan["learner_state"] == inputs["learner_state"]
    assert plan["interest"] == inputs["interest"]
    assert plan["learner_level"] == "beginner"
    assert plan["confidence_state"]["level"] == "unknown"
    assert plan["confidence_state"]["self_reported_score"] is None
    assert plan["weakness_type"] == "unknown"
    assert plan["recommended_starting_level"] == "level_1"
    assert plan["recommended_starting_level_reason"]
    assert plan["roadmap"][0]["is_unlocked"] is True
    assert plan["roadmap"][0]["completion_state"] == "not_started"
    assert [concept["concept_id"] for concept in plan["roadmap"][0]["topics"][0]["concepts"]] == [
        "cpt_entropy",
        "cpt_information_gain",
        "cpt_tree_splits",
    ]
    assert len(plan["roadmap"]) == 1
    assert plan["roadmap"][0]["completion_state"] == "not_started"
    assert all(step["status"] == "planned" for step in plan["initial_agent_routing"])
    assert client.post(
        f"/api/v1/sessions/{response_data['session_id']}/cala-plan?user_id={user_id}"
    ).json() == plan
    assert client.get(
        f"/api/v1/sessions/{response_data['session_id']}/cala-plan?user_id={user_id}"
    ).json() == plan
    assert client.get(
        f"/api/v1/mind-profile?user_id={user_id}"
    ).json() == mind_before_plan

    second_inputs = {
        "task": "Compare decision-tree splits",
        "goal": "Explain information gain",
        "learner_state": "I understand entropy",
        "interest": "Healthcare",
    }
    second = client.post(
        f"/api/v1/learning-session/create?user_id={user_id}",
        json=second_inputs,
    )
    assert second.status_code == 201
    assert second.json()["session_id"] != response_data["session_id"]
    assert LearnerProfileRepository.get_by_user_id(db, user_id).id == learner_profile.id
    assert LearnerProfileRepository.get_by_user_id(db, user_id).learning_goal == inputs["goal"]
    second_plan = client.post(
        f"/api/v1/sessions/{second.json()['session_id']}/cala-plan?user_id={user_id}"
    )
    assert second_plan.status_code == 200
    assert second_plan.json()["session_id"] == second.json()["session_id"]
    assert second_plan.json()["task"] == second_inputs["task"]
    assert second_plan.json()["task"] != plan["task"]
    assert client.get(
        f"/api/v1/sessions/{response_data['session_id']}/cala-plan?user_id={user_id}"
    ).json()["task"] == inputs["task"]

    other_user = client.post("/api/v1/auth/register", json={
        "email": "otherplanowner@example.com",
        "password": "correct horse battery",
    })
    assert other_user.status_code == 201
    assert client.get(
        f"/api/v1/sessions/{response_data['session_id']}/cala-plan"
        f"?user_id={other_user.json()['user_id']}"
    ).status_code == 404
    assert client.get(
        f"/api/v1/session/{response_data['session_id']}/state"
    ).json()["inputs"] == inputs
    assert client.get(
        f"/api/v1/session/{second.json()['session_id']}/state"
    ).json()["inputs"] == second_inputs

    assert client.get(f"/api/v1/dashboard?user_id={user_id}").status_code == 200
    assert client.get(f"/api/v1/roadmap?user_id={user_id}").status_code == 200


def test_learning_session_requires_profile_and_mind_profile(client):
    created = client.post("/api/v1/auth/register", json={
        "email": "setuprequired@example.com",
        "password": "correct horse battery",
    })
    user_id = created.json()["user_id"]
    body = {
        "task": "Learn",
        "goal": "Understand",
        "learner_state": "New",
        "interest": "Robotics",
    }
    assert client.post(
        f"/api/v1/learning-session/create?user_id={user_id}", json=body
    ).status_code == 400

def test_learning_session_accepts_only_four_inputs(client):
    created = client.post("/api/v1/auth/register", json={
        "email": "strictinputs@example.com",
        "password": "correct horse battery",
    })
    user_id = created.json()["user_id"]
    body = {
        "task": "Learn",
        "goal": "Understand",
        "learner_state": "New",
        "interest": "Robotics",
        "current_level": "beginner",
    }
    assert client.post(
        f"/api/v1/learning-session/create?user_id={user_id}", json=body
    ).status_code == 422


def test_onboarding_submit(client):
    response = client.post("/api/v1/onboarding/submit", json={
        "learning_goal": "Understand Decision Trees",
        "current_level": "beginner",
        "learning_preference": "step_by_step",
        "interests": ["robotics", "finance"],
        "initial_confidence": 3
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "profile_id" in data
    assert data["profile_id"].startswith("prf_")
    assert data["topic_id"] == "top_decision_trees"
    assert data["next_action"] == "start_session"

def test_onboarding_starts_seeded_topic_with_real_session(client):
    onboarding = client.post("/api/v1/onboarding/submit", json={
        "learning_goal": "Learn Decision Trees",
        "current_level": "beginner",
        "learning_preference": "step_by_step",
        "interests": ["robotics"],
        "initial_confidence": 3,
    })
    assert onboarding.status_code == 200
    onboarding_data = onboarding.json()

    started = client.post(
        f"/api/v1/session/start?user_id={onboarding_data['user_id']}",
        json={"topic_id": onboarding_data["topic_id"]},
    )
    assert started.status_code == 200
    session_id = started.json()["session_id"]

    state = client.get(f"/api/v1/session/{session_id}/state")
    assert state.status_code == 200
    state_data = state.json()
    assert state_data["topic_id"] == onboarding_data["topic_id"]
    assert state_data["topic_title"] == "Decision Trees Fundamentals"
    assert state_data["current_concept_id"] == "cpt_entropy"
    assert state_data["current_concept_title"] == "Entropy"
    assert state_data["current_step"] == "teaching"
    assert state_data["current_action"]
    assert state_data["current_content"]["concept"] == "Entropy"


def test_onboarding_status(client):
    response = client.get("/api/v1/onboarding/status?user_id=invalid")
    assert response.status_code == 404


def test_learner_profile(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    
    user = UserRepository.create(db, email="test@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn ML", "intermediate", "example_first", "robotics", 4
    )
    
    response = client.get(f"/api/v1/learner/profile?user_id={user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == profile.id
    assert data["learning_goal"] == "Learn ML"
    assert data["current_level"] == "intermediate"


def test_learner_profile_not_found(client):
    response = client.get("/api/v1/learner/profile?user_id=nonexistent")
    assert response.status_code == 404


def test_session_create(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    
    user = UserRepository.create(db, email="session@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    concept = CurriculumRepository.create_concept(db, topic.id, title="Entropy", base_difficulty=1)
    
    response = client.post(f"/api/v1/session/start?user_id={user.id}", json={"topic_id": topic.id})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "session_id" in data
    assert data["session_id"].startswith("ses_")
    assert data["topic_id"] == topic.id


def test_session_create_no_profile(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    user = UserRepository.create(db, email="noprofile@clario.ai", password_hash="hash")
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    
    response = client.post(f"/api/v1/session/start?user_id={user.id}", json={"topic_id": topic.id})
    assert response.status_code == 400
    assert "onboarding" in response.json()["detail"].lower()

def test_session_start_rejects_topic_without_concepts(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    user = UserRepository.create(db, email="emptytopic@clario.ai", password_hash="hash")
    LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Empty topic")

    response = client.post(
        f"/api/v1/session/start?user_id={user.id}",
        json={"topic_id": topic.id},
    )

    assert response.status_code == 400
    assert "no concepts" in response.json()["detail"].lower()
    assert db.query(LearningSession).count() == 0

def test_session_start_rejects_missing_topic(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    user = UserRepository.create(db, email="missingtopic@clario.ai", password_hash="hash")
    LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )

    response = client.post(
        f"/api/v1/session/start?user_id={user.id}",
        json={"topic_id": "missing_topic"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Topic not found"
    assert db.query(LearningSession).count() == 0


def test_session_state(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    
    user = UserRepository.create(db, email="state@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    concept = CurriculumRepository.create_concept(db, topic.id, title="Entropy", base_difficulty=1)
    session = SessionRepository.create_session(db, user.id, topic.id)
    
    response = client.get(f"/api/v1/session/{session.id}/state")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session.id
    assert data["topic_id"] == topic.id
    assert data["current_step"] == "idle"


def test_thinking_submit(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    
    user = UserRepository.create(db, email="thinking@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    concept = CurriculumRepository.create_concept(db, topic.id, title="Entropy", base_difficulty=1)
    session = SessionRepository.create_session(db, user.id, topic.id)
    
    response = client.post(f"/api/v1/session/start?user_id={user.id}", json={"topic_id": topic.id})
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    
    response = client.post("/api/v1/thinking/submit", json={
        "session_id": session_id,
        "learner_response": "Zero entropy means pure dataset"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "thinking_assessment" in data
    assert "practical_exercise" in data
    assert "next_step" in data


def test_practical_submit(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    
    user = UserRepository.create(db, email="practical@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    concept = CurriculumRepository.create_concept(db, topic.id, title="Entropy", base_difficulty=1)
    session = SessionRepository.create_session(db, user.id, topic.id)
    
    response = client.post(f"/api/v1/session/start?user_id={user.id}", json={"topic_id": topic.id})
    session_id = response.json()["session_id"]
    
    client.post("/api/v1/thinking/submit", json={
        "session_id": session_id,
        "learner_response": "Zero entropy means pure dataset"
    })
    
    response = client.post("/api/v1/practical/submit", json={
        "session_id": session_id,
        "learner_response": "Applied entropy to split data"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "question" in data


def test_quiz_generate(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    
    user = UserRepository.create(db, email="quizgen@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    concept = CurriculumRepository.create_concept(db, topic.id, title="Entropy", base_difficulty=1)
    session = SessionRepository.create_session(db, user.id, topic.id)
    
    response = client.post(f"/api/v1/session/start?user_id={user.id}", json={"topic_id": topic.id})
    session_id = response.json()["session_id"]
    
    client.post("/api/v1/thinking/submit", json={
        "session_id": session_id,
        "learner_response": "Zero entropy means pure dataset"
    })
    client.post("/api/v1/practical/submit", json={
        "session_id": session_id,
        "learner_response": "Applied entropy to split data"
    })
    
    response = client.post(f"/api/v1/quiz/generate?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "question" in data
    assert "question_id" in data["question"]


def test_quiz_submit(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    
    user = UserRepository.create(db, email="quizsub@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    concept = CurriculumRepository.create_concept(db, topic.id, title="Entropy", base_difficulty=1)
    session = SessionRepository.create_session(db, user.id, topic.id)
    
    response = client.post(f"/api/v1/session/start?user_id={user.id}", json={"topic_id": topic.id})
    session_id = response.json()["session_id"]
    
    client.post("/api/v1/thinking/submit", json={
        "session_id": session_id,
        "learner_response": "Zero entropy means pure dataset"
    })
    client.post("/api/v1/practical/submit", json={
        "session_id": session_id,
        "learner_response": "Applied entropy to split data"
    })
    client.post(f"/api/v1/quiz/generate?session_id={session_id}")
    
    response = client.post("/api/v1/quiz/submit", json={
        "session_id": session_id,
        "learner_answer": "A. Pure dataset with only one class"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["evaluated_by"] == "Ellara"
    assert "evaluation" in data
    assert "next_step" in data


def test_dashboard(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    
    user = UserRepository.create(db, email="dashboard@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    concept = CurriculumRepository.create_concept(db, topic.id, title="Entropy", base_difficulty=1)
    
    from backend.app.models.repositories import ConceptPerformanceRepository
    ConceptPerformanceRepository.record_assessment(
        db, profile.id, concept.id, status="mastered", mastery_score=95.0, difficulty_level=2
    )
    
    response = client.get(f"/api/v1/dashboard?user_id={user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "concept_breakdown" in data
    assert "weak_concepts" in data
    assert "recommended_action" in data


def test_roadmap(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    
    user = UserRepository.create(db, email="roadmap@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    c1 = CurriculumRepository.create_concept(db, topic.id, title="Entropy", base_difficulty=1)
    c2 = CurriculumRepository.create_concept(db, topic.id, title="Information Gain", base_difficulty=2)
    
    from backend.app.models.repositories import ConceptPerformanceRepository
    ConceptPerformanceRepository.record_assessment(
        db, profile.id, c1.id, status="mastered", mastery_score=95.0, difficulty_level=2
    )
    
    response = client.get(f"/api/v1/roadmap?user_id={user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["topic_id"] == topic.id
    assert "roadmap" in data
    assert len(data["roadmap"]) == 2
    assert data["roadmap"][0]["concept_title"] == "Entropy"
    assert data["roadmap"][0]["status"] == "mastered"
    assert data["roadmap"][1]["concept_title"] == "Information Gain"
    assert data["roadmap"][1]["is_next"] is True


def test_invalid_request_error_handling(client):
    response = client.post("/api/v1/onboarding/submit", json={})
    assert response.status_code == 422


def test_missing_session_error(client):
    response = client.get("/api/v1/session/invalid/state")
    assert response.status_code == 404


def test_missing_topic_error(client):
    db = client.app.dependency_overrides[get_db]().__next__()
    user = UserRepository.create(db, email="missingt@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 3
    )
    
    response = client.post(f"/api/v1/session/start?user_id={user.id}", json={"topic_id": "nonexistent"})
    assert response.status_code == 404