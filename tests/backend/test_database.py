import pytest
import tempfile
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base
from backend.app.core.migrations import run_migrations
from backend.app.models.user import User
from backend.app.models.learner import LearnerProfile, ConceptPerformance
from backend.app.models.curriculum import Topic, Concept
from backend.app.models.session import LearningSession, Activity, LearnerResponse, Evaluation
from backend.app.models.repositories import (
    UserRepository,
    LearnerProfileRepository,
    CurriculumRepository,
    ConceptPerformanceRepository,
    SessionRepository,
)

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Run migrations
    applied = run_migrations(path)
    assert len(applied) >= 1

    engine = create_engine(f"sqlite:///{path}")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    yield db, path

    db.close()
    engine.dispose()
    if os.path.exists(path):
        os.remove(path)

def test_migration_idempotency(temp_db):
    db, path = temp_db
    # Running migrations again should apply nothing
    second_run = run_migrations(path)
    assert second_run == []

def test_ayan_thinking_results_are_session_and_orchestration_owned(temp_db):
    db, _ = temp_db
    inspector = inspect(db.get_bind())

    assert "thinking_results" in inspector.get_table_names()
    assert {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("thinking_results")
    } == {("session_id", "attempt_number"), ("orchestration_id", "attempt_number")}
    foreign_keys = {
        (
            constraint["constrained_columns"][0],
            constraint["referred_table"],
            constraint["options"].get("ondelete"),
        )
        for constraint in inspector.get_foreign_keys("thinking_results")
    }
    assert foreign_keys == {
        ("session_id", "learning_sessions", "CASCADE"),
        ("orchestration_id", "clario_orchestrations", "CASCADE"),
    }

def test_kira_practical_results_are_session_and_orchestration_owned(temp_db):
    db, _ = temp_db
    inspector = inspect(db.get_bind())

    assert "practical_results" in inspector.get_table_names()
    assert {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("practical_results")
    } == {("session_id", "attempt_number"), ("orchestration_id", "attempt_number")}
    foreign_keys = {
        (
            constraint["constrained_columns"][0],
            constraint["referred_table"],
            constraint["options"].get("ondelete"),
        )
        for constraint in inspector.get_foreign_keys("practical_results")
    }
    assert foreign_keys == {
        ("session_id", "learning_sessions", "CASCADE"),
        ("orchestration_id", "clario_orchestrations", "CASCADE"),
        ("concept_id", "concepts", "CASCADE"),
    }

def test_zayn_quiz_results_store_private_answer_key_and_submission_state(temp_db):
    db, _ = temp_db
    inspector = inspect(db.get_bind())

    assert "quiz_results" in inspector.get_table_names()
    assert {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("quiz_results")
    } == {("session_id", "attempt_number"), ("orchestration_id", "attempt_number")}
    foreign_keys = {
        (
            constraint["constrained_columns"][0],
            constraint["referred_table"],
            constraint["options"].get("ondelete"),
        )
        for constraint in inspector.get_foreign_keys("quiz_results")
    }
    assert foreign_keys == {
        ("session_id", "learning_sessions", "CASCADE"),
        ("orchestration_id", "clario_orchestrations", "CASCADE"),
        ("concept_id", "concepts", "CASCADE"),
    }
    columns = {column["name"] for column in inspector.get_columns("quiz_results")}
    assert {
        "questions_json",
        "answer_key_json",
        "status",
        "submitted_answers_json",
        "correctness_json",
        "submitted_at",
    }.issubset(columns)

def test_elara_evaluations_are_session_orchestration_quiz_owned(temp_db):
    db, path = temp_db
    inspector = inspect(db.get_bind())

    assert "elara_evaluations" in inspector.get_table_names()
    assert {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("elara_evaluations")
    } == {
        ("session_id", "attempt_number"),
        ("orchestration_id", "attempt_number"),
        ("quiz_result_id",),
    }
    foreign_keys = {
        (
            constraint["constrained_columns"][0],
            constraint["referred_table"],
            constraint["options"].get("ondelete"),
        )
        for constraint in inspector.get_foreign_keys("elara_evaluations")
    }
    assert foreign_keys == {
        ("session_id", "learning_sessions", "CASCADE"),
        ("orchestration_id", "clario_orchestrations", "CASCADE"),
        ("concept_id", "concepts", "CASCADE"),
        ("quiz_result_id", "quiz_results", "CASCADE"),
    }
    columns = {column["name"] for column in inspector.get_columns("elara_evaluations")}
    assert {
        "concept_name",
        "quiz_performance_json",
        "concept_strength",
        "concept_weakness",
        "overall_evaluation",
        "confidence",
        "difficulty_signal",
        "evidence_summary",
        "evaluation_json",
        "evaluated_at",
    }.issubset(columns)
    assert run_migrations(path) == []


def test_adaptive_remediation_migration_preserves_attempts_and_foreign_keys(temp_db):
    db, path = temp_db
    inspector = inspect(db.get_bind())

    assert "clario_adaptive_executions" in inspector.get_table_names()
    execution_foreign_keys = {
        constraint["referred_table"]
        for constraint in inspector.get_foreign_keys("clario_adaptive_executions")
    }
    assert execution_foreign_keys == {
        "learning_sessions",
        "clario_orchestrations",
        "concepts",
        "adaptive_decisions",
        "elara_evaluations",
    }
    assert {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints(
            "clario_adaptive_executions"
        )
    } == {("decision_id",), ("session_id", "concept_id", "attempt_number")}
    for table in (
        "teaching_results",
        "thinking_results",
        "practical_results",
        "quiz_results",
        "elara_evaluations",
    ):
        assert "attempt_number" in {
            column["name"] for column in inspector.get_columns(table)
        }
        assert {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table)
        } >= {
            ("session_id", "attempt_number"),
            ("orchestration_id", "attempt_number"),
        }
    assert run_migrations(path) == []
    with db.connection() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []

def test_session_concept_performance_and_adaptive_decision_constraints(temp_db):
    db, path = temp_db
    inspector = inspect(db.get_bind())

    assert "session_concept_performances" in inspector.get_table_names()
    assert "adaptive_decisions" in inspector.get_table_names()
    performance_uniques = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints(
            "session_concept_performances"
        )
    }
    assert ("session_id", "concept_id") in performance_uniques
    performance_fks = {
        constraint["referred_table"]
        for constraint in inspector.get_foreign_keys("session_concept_performances")
    }
    assert performance_fks == {
        "learning_sessions",
        "clario_orchestrations",
        "concepts",
        "elara_evaluations",
    }
    decision_uniques = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("adaptive_decisions")
    }
    assert ("orchestration_id", "evaluation_id") in decision_uniques
    decision_fks = {
        constraint["referred_table"]
        for constraint in inspector.get_foreign_keys("adaptive_decisions")
    }
    assert decision_fks == {
        "learning_sessions",
        "clario_orchestrations",
        "concepts",
        "elara_evaluations",
    }
    assert run_migrations(path) == []

def test_development_curriculum_is_seeded_in_order(temp_db):
    db, _ = temp_db

    topic = CurriculumRepository.get_topic(db, "top_decision_trees")
    assert topic is not None
    assert topic.title == "Decision Trees Fundamentals"

    concepts = CurriculumRepository.list_concepts_by_topic(db, topic.id)
    assert [concept.id for concept in concepts] == [
        "cpt_entropy",
        "cpt_information_gain",
        "cpt_tree_splits",
    ]
    assert all(concept.description for concept in concepts)
    assert [concept.base_difficulty for concept in concepts] == [1, 2, 3]

def test_user_and_profile_crud(temp_db):
    db, _ = temp_db

    # Create User
    user = UserRepository.create(db, email="learner@clario.ai", password_hash="secret_hash")
    assert user.id.startswith("usr_")
    assert user.email == "learner@clario.ai"

    # Query User
    queried = UserRepository.get_by_email(db, "learner@clario.ai")
    assert queried is not None
    assert queried.id == user.id

    # Create Profile
    profile = LearnerProfileRepository.create(
        db,
        user_id=user.id,
        learning_goal="Understand Decision Trees",
        current_level="intermediate",
        learning_preference="example_first",
        interests="robotics",
        initial_confidence=3,
    )
    assert profile.id.startswith("prf_")
    assert profile.user_id == user.id

    # Query Profile
    queried_profile = LearnerProfileRepository.get_by_user_id(db, user.id)
    assert queried_profile is not None
    assert queried_profile.learning_goal == "Understand Decision Trees"

    # Update Profile
    updated = LearnerProfileRepository.update(db, profile, initial_confidence=4)
    assert updated.initial_confidence == 4

def test_curriculum_and_concept_performance(temp_db):
    db, _ = temp_db

    # Create Curriculum
    topic = CurriculumRepository.create_topic(db, title="Decision Trees", sequence_order=1)
    assert topic.id.startswith("top_")

    c1 = CurriculumRepository.create_concept(db, topic_id=topic.id, title="Entropy", base_difficulty=1)
    c2 = CurriculumRepository.create_concept(db, topic_id=topic.id, title="Information Gain", base_difficulty=2)
    assert c1.id.startswith("cpt_")
    assert c2.id.startswith("cpt_")

    # Create User and Profile
    user = UserRepository.create(db, email="student@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "ai", 2
    )

    # Initial Concept Performance
    cp = ConceptPerformanceRepository.get_or_create(db, profile.id, c1.id)
    assert cp.status == "learning"
    assert cp.mastery_score == 0.0

    # Record assessment: Mastered Entropy
    cp_mastered = ConceptPerformanceRepository.record_assessment(
        db, profile.id, c1.id, status="mastered", mastery_score=92.5, difficulty_level=2
    )
    assert cp_mastered.status == "mastered"
    assert cp_mastered.mastery_score == 92.5
    assert cp_mastered.attempt_count == 1

    # Record assessment: Weak Information Gain -> Remediating
    cp_weak = ConceptPerformanceRepository.record_assessment(
        db, profile.id, c2.id, status="remediating", mastery_score=40.0, difficulty_level=1
    )
    assert cp_weak.status == "remediating"
    assert cp_weak.mastery_score == 40.0

    # Verify concept-level tracking (Entropy mastered, Information Gain remediating)
    all_perfs = ConceptPerformanceRepository.list_by_profile(db, profile.id)
    perf_map = {p.concept_id: p.status for p in all_perfs}
    assert perf_map[c1.id] == "mastered"
    assert perf_map[c2.id] == "remediating"

def test_session_activity_and_evaluation_flow(temp_db):
    db, _ = temp_db

    user = UserRepository.create(db, email="eval@clario.ai", password_hash="hash")
    topic = CurriculumRepository.create_topic(db, title="Neural Networks")
    concept = CurriculumRepository.create_concept(db, topic.id, title="Backpropagation")

    # Start Session
    session = SessionRepository.create_session(db, user.id, topic.id)
    assert session.id.startswith("ses_")
    assert session.status == "active"

    # Create Activity (Thinking Friend)
    activity = SessionRepository.create_activity(
        db,
        session_id=session.id,
        companion_type="thinking",
        content_payload='{"question": "Why does the gradient vanish?"}',
        concept_id=concept.id,
    )
    assert activity.id.startswith("act_")
    assert activity.companion_type == "thinking"

    # Record Learner Response
    response = SessionRepository.record_response(
        db, activity.id, "Because repeated multiplication of small derivatives approaches zero."
    )
    assert response.id.startswith("rsp_")
    assert "small derivatives" in response.response_text

    # Record Evaluation from Ellara
    evaluation = SessionRepository.record_evaluation(
        db,
        response_id=response.id,
        evaluator_name="Ellara",
        score=95.0,
        feedback_payload='{"reasoning": "accurate understanding of chain rule"}',
        remediation_required=False,
    )
    assert evaluation.id.startswith("evl_")
    assert evaluation.evaluator_name == "Ellara"
    assert evaluation.remediation_required == 0
