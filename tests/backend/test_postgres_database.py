import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, delete, inspect, text
from sqlalchemy.orm import Session

from backend.app.core.database import normalize_database_url
from backend.app.core.migrations import run_postgres_migrations
from backend.app.models import (
    AdaptiveDecisionRecord,
    AdaptiveExecutionRecord,
    CalaPlanRecord,
    Concept,
    ConceptPerformance,
    ElaraEvaluationRecord,
    LearnerProfile,
    LearningSession,
    MindProfile,
    OrchestrationRecord,
    PracticalResultRecord,
    QuizResultRecord,
    ResearchPackageRecord,
    SessionConceptPerformanceRecord,
    TeachingResultRecord,
    ThinkingResultRecord,
    Topic,
    User,
)
from backend.app.models.session_inputs import SessionInputs


def test_postgres_urls_use_the_installed_sqlalchemy_driver():
    assert (
        normalize_database_url("postgres://localhost/clario")
        == "postgresql+psycopg2://localhost/clario"
    )
    assert (
        normalize_database_url("postgresql://localhost/clario")
        == "postgresql+psycopg2://localhost/clario"
    )
    assert (
        normalize_database_url("postgresql+psycopg://localhost/clario")
        == "postgresql+psycopg2://localhost/clario"
    )
    assert normalize_database_url("sqlite:///./clario.db") == "sqlite:///./clario.db"
    assert (
        normalize_database_url('DATABASE_URL="postgresql://localhost/clario"')
        == "postgresql+psycopg2://localhost/clario"
    )
    postgres_url = normalize_database_url(
        "postgresql://db.example.neon.tech:5432/clario"
    )
    assert "sslmode" not in postgres_url
    neon_url = normalize_database_url(
        "postgresql://db.example.neon.tech:5432/clario?sslmode=require"
    )
    assert neon_url.startswith("postgresql+psycopg2://")
    assert "sslmode=require" in neon_url
    explicit_ssl = normalize_database_url(
        "postgresql://db.example.neon.tech:5432/clario?sslmode=verify-full"
    )
    assert "sslmode=verify-full" in explicit_ssl


@pytest.fixture(scope="module")
def postgres_database():
    database_url = os.getenv("CLARIO_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set CLARIO_TEST_DATABASE_URL to a disposable PostgreSQL database.")

    engine = create_engine(normalize_database_url(database_url), pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.fail("CLARIO_TEST_DATABASE_URL must use PostgreSQL.")

    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            connection.commit()
            run_postgres_migrations(connection)
        yield engine
    finally:
        engine.dispose()


def test_postgres_schema_constraints_and_clario_persistence(postgres_database):
    engine = postgres_database
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "users",
        "learner_profiles",
        "mind_profiles",
        "topics",
        "concepts",
        "learning_sessions",
        "session_inputs",
        "cala_plans",
        "research_packages",
        "clario_orchestrations",
        "quiz_results",
        "elara_evaluations",
        "session_concept_performances",
        "adaptive_decisions",
        "clario_adaptive_executions",
    }.issubset(tables)
    assert "ix_clario_adaptive_executions_session_created" in {
        index["name"] for index in inspector.get_indexes("clario_adaptive_executions")
    }
    assert "ix_research_packages_session_level_attempt" in {
        index["name"] for index in inspector.get_indexes("research_packages")
    }
    assert {
        (foreign_key["constrained_columns"][0], foreign_key["referred_table"])
        for foreign_key in inspector.get_foreign_keys("clario_adaptive_executions")
    } == {
        ("session_id", "learning_sessions"),
        ("orchestration_id", "clario_orchestrations"),
        ("concept_id", "concepts"),
        ("decision_id", "adaptive_decisions"),
        ("source_evaluation_id", "elara_evaluations"),
    }

    with engine.connect() as connection:
        transaction = connection.begin()
        db = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            user = User(
                id="pg_test_user",
                email="pg-test@example.invalid",
                password_hash="not-a-real-login",
            )
            topic = Topic(id="pg_test_topic", title="Test topic")
            concept = Concept(
                id="pg_test_concept",
                topic_id=topic.id,
                title="Test concept",
            )
            profile = LearnerProfile(
                id="pg_test_profile",
                user_id=user.id,
                learning_goal="Test goal",
                current_level="beginner",
                learning_preference="visual",
                interests="testing",
                initial_confidence=1,
            )
            session = LearningSession(
                id="pg_test_session",
                user_id=user.id,
                topic_id=topic.id,
            )
            db.add_all([user, topic, concept, profile, session])
            db.flush()

            mind_profile = MindProfile(
                id="pg_test_mind_profile",
                user_id=user.id,
                learning_motivation="curiosity",
                preferred_explanation="worked_example",
                support_when_stuck="different_explanation",
                feedback_preference="direct_correction",
                challenge_preference="steady_pace",
            )
            concept_performance = ConceptPerformance(
                id="pg_test_learner_concept_performance",
                profile_id=profile.id,
                concept_id=concept.id,
                status="learning",
                difficulty_level=1,
                mastery_score=0.25,
                attempt_count=1,
            )
            session_inputs = SessionInputs(
                id="pg_test_inputs",
                session_id=session.id,
                task="Test task",
                goal="Test goal",
                learner_state="beginner",
                interest="testing",
            )
            cala_plan = CalaPlanRecord(
                id="pg_test_cala",
                session_id=session.id,
                plan_json='{"roadmap":[]}',
            )
            research_package = ResearchPackageRecord(
                id="pg_test_research",
                session_id=session.id,
                attempt_number=1,
                package_json='{"sources":[]}',
            )
            db.add_all([session_inputs, cala_plan, research_package])
            db.flush()

            orchestration = OrchestrationRecord(
                id="pg_test_orchestration",
                session_id=session.id,
                cala_plan_id=cala_plan.id,
                current_state="DECISION_READY",
                current_step="test",
                research_package_id=research_package.id,
            )
            teaching = TeachingResultRecord(
                id="pg_test_teaching",
                session_id=session.id,
                orchestration_id=orchestration.id,
                concept=concept.title,
                response_json="{}",
                learner_level="beginner",
                attempt_number=1,
            )
            thinking = ThinkingResultRecord(
                id="pg_test_thinking",
                session_id=session.id,
                orchestration_id=orchestration.id,
                concept=concept.title,
                response_json="{}",
                attempt_number=1,
            )
            practical = PracticalResultRecord(
                id="pg_test_practical",
                session_id=session.id,
                orchestration_id=orchestration.id,
                concept_id=concept.id,
                scenario="Test scenario",
                practical_task="Apply the concept",
                real_world_context="Integration test",
                expected_action="Complete the task",
                success_criteria="Task completed",
                difficulty="EASY",
                research_source_ids="[]",
                attempt_number=1,
            )
            quiz = QuizResultRecord(
                id="pg_test_quiz",
                session_id=session.id,
                orchestration_id=orchestration.id,
                concept_id=concept.id,
                difficulty="MEDIUM",
                time_limit_seconds=60,
                questions_json="[]",
                answer_key_json="{}",
                status="SUBMITTED",
                attempt_number=1,
            )
            db.add_all(
                [
                    mind_profile,
                    concept_performance,
                    orchestration,
                    teaching,
                    thinking,
                    practical,
                    quiz,
                ]
            )
            db.flush()

            evaluation = ElaraEvaluationRecord(
                id="pg_test_evaluation",
                session_id=session.id,
                orchestration_id=orchestration.id,
                concept_id=concept.id,
                quiz_result_id=quiz.id,
                concept_name=concept.title,
                quiz_performance_json='{"accuracy":100}',
                concept_strength="strong",
                concept_weakness="none",
                overall_evaluation="Sufficient evidence",
                confidence=0.9,
                difficulty_signal="maintain",
                evidence_summary="Integration test",
                evaluation_json="{}",
                attempt_number=1,
                evaluated_at=datetime.now(timezone.utc),
            )
            db.add(evaluation)
            db.flush()

            performance = SessionConceptPerformanceRecord(
                id="pg_test_performance",
                session_id=session.id,
                orchestration_id=orchestration.id,
                concept_id=concept.id,
                concept_name=concept.title,
                current_difficulty="MEDIUM",
                mastery_status="mastered",
                strength="strong",
                weakness="none",
                evaluation_confidence=0.9,
                quiz_accuracy=100,
                attempt_count=1,
                remediation_count=0,
                last_evaluation_id=evaluation.id,
            )
            decision = AdaptiveDecisionRecord(
                id="pg_test_decision",
                session_id=session.id,
                orchestration_id=orchestration.id,
                concept_id=concept.id,
                evaluation_id=evaluation.id,
                decision="CONTINUE",
                mastery_status="mastered",
                current_difficulty="MEDIUM",
                next_difficulty="MEDIUM",
                reason="Integration test",
                remediation_required=0,
                decision_json="{}",
            )
            db.add_all([performance, decision])
            db.flush()

            execution = AdaptiveExecutionRecord(
                id="pg_test_execution",
                session_id=session.id,
                orchestration_id=orchestration.id,
                concept_id=concept.id,
                decision_id=decision.id,
                source_evaluation_id=evaluation.id,
                attempt_number=1,
                decision_type="RETEACH",
                status="COMPLETED",
                remediation_context_json="{}",
            )
            db.add(execution)
            db.commit()

            persisted_decision = db.get(AdaptiveDecisionRecord, decision.id)
            persisted_execution = db.get(AdaptiveExecutionRecord, execution.id)
            persisted_performance = db.get(
                SessionConceptPerformanceRecord, performance.id
            )
            assert persisted_decision is not None
            assert persisted_execution is not None
            assert persisted_performance is not None
            assert persisted_performance.mastery_status == "mastered"
            assert db.get(MindProfile, mind_profile.id) is not None
            assert db.get(ConceptPerformance, concept_performance.id) is not None
            assert db.get(TeachingResultRecord, teaching.id) is not None
            assert db.get(ThinkingResultRecord, thinking.id) is not None
            assert db.get(PracticalResultRecord, practical.id) is not None
            second_user = User(
                id="pg_test_user_2",
                email="pg-test-2@example.invalid",
                password_hash="not-a-real-login",
            )
            second_session = LearningSession(
                id="pg_test_session_2",
                user_id=second_user.id,
                topic_id=topic.id,
            )
            db.add_all([second_user, second_session])
            db.commit()
            assert (
                db.query(SessionConceptPerformanceRecord)
                .filter_by(session_id=second_session.id)
                .all()
                == []
            )

            user.name = "Updated integration learner"
            db.commit()
            assert db.get(User, user.id).name == "Updated integration learner"
            db.execute(delete(User).where(User.id == user.id))
            db.commit()
            assert db.get(User, "pg_test_user") is None
        finally:
            db.close()
            transaction.rollback()
