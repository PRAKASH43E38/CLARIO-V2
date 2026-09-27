import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.migrations import run_migrations
from backend.app.models.repositories import (
    UserRepository,
    LearnerProfileRepository,
    CurriculumRepository,
    SessionRepository,
    ConceptPerformanceRepository,
)
from backend.app.ai.mock_provider import MockAIProvider
from backend.app.orchestrator import (
    NovaOrchestrator,
    ActiveSessionContext,
    LearningStep,
    AdaptiveAction,
    AdaptivePolicy,
)
from backend.app.schemas.quiz import QuizGrading
from backend.app.schemas.evaluation import MasterEvaluation

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
def setup_curriculum(temp_db):
    db, path = temp_db
    user = UserRepository.create(db, email="adaptive@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Master ML", "intermediate", "step_by_step", "robotics", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    c1 = CurriculumRepository.create_concept(db, topic.id, title="Entropy", base_difficulty=1)
    c2 = CurriculumRepository.create_concept(db, topic.id, title="Information Gain", base_difficulty=2)
    session = SessionRepository.create_session(db, user.id, topic.id)
    return {
        "db": db,
        "user": user,
        "profile": profile,
        "topic": topic,
        "c1": c1,
        "c2": c2,
        "session": session,
    }

def test_1_strong_concept_progression(setup_curriculum):
    \"\"\"1. Strong concept -> progression\"\"\"
    db = setup_curriculum["db"]
    mock_ai = MockAIProvider()
    nova = NovaOrchestrator(ai_provider=mock_ai)

    ctx = ActiveSessionContext(
        session_id=setup_curriculum["session"].id,
        user_id=setup_curriculum["user"].id,
        profile_id=setup_curriculum["profile"].id,
        topic_id=setup_curriculum["topic"].id,
        topic_title=setup_curriculum["topic"].title,
        current_concept_id=setup_curriculum["c1"].id,
        current_concept_title="Entropy",
        difficulty_level=1,
    )

    ctx = nova.start_learning_flow(ctx, db=db)
    ctx = nova.proceed_to_thinking(ctx, db=db)
    ctx = nova.submit_thinking_response(ctx, "Zero entropy is pure.", db=db)
    ctx = nova.proceed_to_quiz(ctx, db=db)
    ctx = nova.submit_quiz_response(ctx, "A. Pure dataset with only one class", db=db)

    assert ctx.latest_decision is not None
    assert ctx.latest_decision.action == AdaptiveAction.ADVANCE
    assert ctx.latest_decision.new_status == "mastered"
    assert ctx.is_remediating is False

def test_2_weak_concept_remediation(setup_curriculum):
    \"\"\"2. Weak concept -> remediation\"\"\"
    db = setup_curriculum["db"]
    mock_ai = MockAIProvider()

    # Configure weak quiz result (40%) and Ellara remediation recommendation
    mock_ai.set_response_for_model("QuizGrading", {
        "score": 40.0,
        "concept_performance": 40.0,
        "mistakes": ["Confused entropy with information gain"],
        "difficulty": 2,
        "recommendation": "Needs remediation",
    })
    mock_ai.set_response_for_model("MasterEvaluation", {
        "strong_concepts": [],
        "weak_concepts": ["Entropy"],
        "misconceptions": ["Assumed high entropy means high purity"],
        "concept_status": {"Entropy": "remediating"},
        "remediation_required": True,
        "recommended_action": "remediate",
    })

    nova = NovaOrchestrator(ai_provider=mock_ai)

    ctx = ActiveSessionContext(
        session_id=setup_curriculum["session"].id,
        user_id=setup_curriculum["user"].id,
        profile_id=setup_curriculum["profile"].id,
        topic_id=setup_curriculum["topic"].id,
        topic_title=setup_curriculum["topic"].title,
        current_concept_id=setup_curriculum["c1"].id,
        current_concept_title="Entropy",
        difficulty_level=2,
    )

    ctx = nova.start_learning_flow(ctx, db=db)
    ctx = nova.proceed_to_thinking(ctx, db=db)
    ctx = nova.submit_thinking_response(ctx, "Inaccurate reasoning", db=db)
    ctx = nova.proceed_to_quiz(ctx, db=db)
    ctx = nova.submit_quiz_response(ctx, "Wrong answer", db=db)

    assert ctx.latest_decision is not None
    assert ctx.latest_decision.action == AdaptiveAction.REMEDIATE
    assert ctx.latest_decision.new_status == "remediating"
    assert ctx.is_remediating is True
    assert "remediation" in ctx.remediation_notes.lower()

def test_3_single_weak_concept_isolated_remediation(setup_curriculum):
    \"\"\"3. Single weak concept -> only that concept remediated (strong concept retained).\"\"\"
    db = setup_curriculum["db"]
    profile_id = setup_curriculum["profile"].id
    c1 = setup_curriculum["c1"]
    c2 = setup_curriculum["c2"]

    # Pre-populate c1 (Entropy) as mastered
    ConceptPerformanceRepository.record_assessment(
        db, profile_id, c1.id, status="mastered", mastery_score=95.0, difficulty_level=2
    )

    mock_ai = MockAIProvider()
    mock_ai.set_response_for_model("QuizGrading", {
        "score": 45.0,
        "concept_performance": 45.0,
        "mistakes": ["Incorrect log subtraction"],
        "difficulty": 2,
        "recommendation": "Remediate Information Gain",
    })
    mock_ai.set_response_for_model("MasterEvaluation", {
        "strong_concepts": ["Entropy"],
        "weak_concepts": ["Information Gain"],
        "misconceptions": ["Subtracted entropies in reverse order"],
        "concept_status": {"Entropy": "mastered", "Information Gain": "remediating"},
        "remediation_required": True,
        "recommended_action": "remediate",
    })

    nova = NovaOrchestrator(ai_provider=mock_ai)

    ctx = ActiveSessionContext(
        session_id=setup_curriculum["session"].id,
        user_id=setup_curriculum["user"].id,
        profile_id=profile_id,
        topic_id=setup_curriculum["topic"].id,
        topic_title=setup_curriculum["topic"].title,
        current_concept_id=c2.id,
        current_concept_title="Information Gain",
        difficulty_level=2,
    )

    ctx = nova.start_learning_flow(ctx, db=db)
    ctx = nova.proceed_to_quiz(ctx, db=db)
    ctx = nova.submit_quiz_response(ctx, "Wrong answer", db=db)

    # Verify only Information Gain is remediating
    assert ctx.latest_decision.target_concept_title == "Information Gain"
    assert ctx.latest_decision.action == AdaptiveAction.REMEDIATE

    # Verify Entropy remains mastered in database
    perf_entropy = ConceptPerformanceRepository.get_by_profile_and_concept(db, profile_id, c1.id)
    assert perf_entropy.status == "mastered"
    assert perf_entropy.mastery_score == 95.0

    # Verify Information Gain is remediating
    perf_gain = ConceptPerformanceRepository.get_by_profile_and_concept(db, profile_id, c2.id)
    assert perf_gain.status == "remediating"
    assert perf_gain.mastery_score == 45.0

def test_4_difficulty_decreases_on_weakness():
    \"\"\"4. Difficulty decreases for weak performance.\"\"\"
    evaluation = MasterEvaluation(
        strong_concepts=[],
        weak_concepts=["Entropy"],
        misconceptions=["Calculation error"],
        concept_status={"Entropy": "remediating"},
        remediation_required=True,
        recommended_action="remediate",
    )
    decision = AdaptivePolicy.evaluate(
        concept_title="Entropy",
        current_status="learning",
        current_difficulty=3,
        attempt_count=1,
        evaluation=evaluation,
        quiz_score=50.0,
    )
    assert decision.new_difficulty == 2
    assert decision.action == AdaptiveAction.REMEDIATE

    # Verify boundary floored at 1
    decision_min = AdaptivePolicy.evaluate(
        concept_title="Entropy",
        current_status="learning",
        current_difficulty=1,
        attempt_count=1,
        evaluation=evaluation,
        quiz_score=40.0,
    )
    assert decision_min.new_difficulty == 1

def test_5_difficulty_increases_on_high_mastery():
    \"\"\"5. Difficulty increases/advances after demonstrated mastery.\"\"\"
    evaluation = MasterEvaluation(
        strong_concepts=["Entropy"],
        weak_concepts=[],
        misconceptions=[],
        concept_status={"Entropy": "mastered"},
        remediation_required=False,
        recommended_action="advance",
    )
    # Score 90% >= HIGH_MASTERY_THRESHOLD (85) -> difficulty +1
    decision = AdaptivePolicy.evaluate(
        concept_title="Entropy",
        current_status="learning",
        current_difficulty=2,
        attempt_count=1,
        evaluation=evaluation,
        quiz_score=90.0,
    )
    assert decision.new_difficulty == 3
    assert decision.action == AdaptiveAction.ADVANCE
    assert decision.new_status == "mastered"

    # Verify capped at MAX_DIFFICULTY = 5
    decision_max = AdaptivePolicy.evaluate(
        concept_title="Entropy",
        current_status="learning",
        current_difficulty=5,
        attempt_count=1,
        evaluation=evaluation,
        quiz_score=100.0,
    )
    assert decision_max.new_difficulty == 5

def test_6_retest_uses_new_question_instance(setup_curriculum):
    \"\"\"6. Retest uses a new question/task.\"\"\"
    db = setup_curriculum["db"]
    mock_ai = MockAIProvider()
    nova = NovaOrchestrator(ai_provider=mock_ai)

    ctx = ActiveSessionContext(
        session_id=setup_curriculum["session"].id,
        user_id=setup_curriculum["user"].id,
        profile_id=setup_curriculum["profile"].id,
        topic_id=setup_curriculum["topic"].id,
        topic_title=setup_curriculum["topic"].title,
        current_concept_id=setup_curriculum["c1"].id,
        current_concept_title="Entropy",
    )

    # First attempt
    ctx = nova.proceed_to_quiz(ctx, db=db)
    q1_id = ctx.quiz_question.question_id
    assert q1_id == "q_001"

    # Trigger second attempt
    ctx.attempt_count = 2
    ctx = nova.proceed_to_quiz(ctx, db=db)
    q2_id = ctx.quiz_question.question_id

    # Retest question must be distinct
    assert q2_id != q1_id
    assert q2_id == "q_002"
    assert "q_001" in ctx.asked_question_ids
    assert "q_002" in ctx.asked_question_ids

def test_7_repeated_weakness_remains_in_remediation():
    \"\"\"7. Repeated weakness remains in remediation.\"\"\"
    evaluation = MasterEvaluation(
        strong_concepts=[],
        weak_concepts=["Entropy"],
        misconceptions=["Persisting misconception"],
        concept_status={"Entropy": "remediating"},
        remediation_required=True,
        recommended_action="remediate",
    )
    decision = AdaptivePolicy.evaluate(
        concept_title="Entropy",
        current_status="remediating",
        current_difficulty=1,
        attempt_count=2,
        evaluation=evaluation,
        quiz_score=55.0,
    )
    assert decision.action == AdaptiveAction.REMEDIATE
    assert decision.new_status == "remediating"
    assert decision.attempt_number == 3

def test_8_successful_remediation_exits_remediation():
    \"\"\"8. Successful remediation exits remediation.\"\"\"
    evaluation = MasterEvaluation(
        strong_concepts=["Entropy"],
        weak_concepts=[],
        misconceptions=[],
        concept_status={"Entropy": "mastered"},
        remediation_required=False,
        recommended_action="advance",
    )
    decision = AdaptivePolicy.evaluate(
        concept_title="Entropy",
        current_status="remediating",
        current_difficulty=1,
        attempt_count=2,
        evaluation=evaluation,
        quiz_score=88.0,
    )
    assert decision.action == AdaptiveAction.ADVANCE
    assert decision.new_status == "mastered"
    assert decision.remediation_notes is None

def test_9_learner_state_persists_correctly(setup_curriculum):
    \"\"\"9. Learner state persists correctly in database.\"\"\"
    db = setup_curriculum["db"]
    profile_id = setup_curriculum["profile"].id
    c1 = setup_curriculum["c1"]

    mock_ai = MockAIProvider()
    nova = NovaOrchestrator(ai_provider=mock_ai)

    ctx = ActiveSessionContext(
        session_id=setup_curriculum["session"].id,
        user_id=setup_curriculum["user"].id,
        profile_id=profile_id,
        topic_id=setup_curriculum["topic"].id,
        topic_title=setup_curriculum["topic"].title,
        current_concept_id=c1.id,
        current_concept_title="Entropy",
    )

    ctx = nova.proceed_to_quiz(ctx, db=db)
    ctx = nova.submit_quiz_response(ctx, "A. Pure dataset with only one class", db=db)

    # Verify database persistence
    perf = ConceptPerformanceRepository.get_by_profile_and_concept(db, profile_id, c1.id)
    assert perf is not None
    assert perf.status == "mastered"
    assert perf.mastery_score == 100.0
    assert perf.attempt_count == 1

def test_10_nova_next_action_decision_from_ellara(setup_curriculum):
    \"\"\"10. NOVA makes the correct next-action decision from Ellara output.\"\"\"
    db = setup_curriculum["db"]
    profile_id = setup_curriculum["profile"].id
    c1 = setup_curriculum["c1"]
    c2 = setup_curriculum["c2"]

    mock_ai = MockAIProvider()
    nova = NovaOrchestrator(ai_provider=mock_ai)

    ctx = ActiveSessionContext(
        session_id=setup_curriculum["session"].id,
        user_id=setup_curriculum["user"].id,
        profile_id=profile_id,
        topic_id=setup_curriculum["topic"].id,
        topic_title=setup_curriculum["topic"].title,
        current_concept_id=c1.id,
        current_concept_title="Entropy",
    )

    # When Entropy is mastered, NOVA should advance ctx to the next unmastered concept (Information Gain)
    ctx = nova.proceed_to_quiz(ctx, db=db)
    ctx = nova.submit_quiz_response(ctx, "A. Pure dataset with only one class", db=db)

    assert ctx.latest_decision.action == AdaptiveAction.ADVANCE
    assert ctx.current_concept_id == c2.id
    assert ctx.current_concept_title == "Information Gain"
    assert ctx.difficulty_level == 2
"""

# Write test file
test_path = BASE / "tests/orchestrator/test_adaptive_engine.py"
test_path.write_text(test_files["tests/orchestrator/test_adaptive_engine.py"], encoding="utf-8")
print("Saved tests/orchestrator/test_adaptive_engine.py")
