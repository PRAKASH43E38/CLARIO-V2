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
from backend.app.orchestrator.nova import NovaOrchestrator
from backend.app.orchestrator.state import ActiveSessionContext, LearningStep

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

def test_nova_sequential_learning_flow(temp_db):
    db, _ = temp_db

    # Setup database entities
    user = UserRepository.create(db, email="nova_test@clario.ai", password_hash="hash")
    profile = LearnerProfileRepository.create(
        db, user.id, "Learn Trees", "beginner", "step_by_step", "robotics", 3
    )
    topic = CurriculumRepository.create_topic(db, title="Decision Trees")
    concept = CurriculumRepository.create_concept(db, topic.id, title="Entropy", base_difficulty=1)
    session = SessionRepository.create_session(db, user.id, topic.id)

    # Initialize NOVA with Mock AI
    mock_ai = MockAIProvider()
    nova = NovaOrchestrator(ai_provider=mock_ai)

    ctx = ActiveSessionContext(
        session_id=session.id,
        user_id=user.id,
        profile_id=profile.id,
        topic_id=topic.id,
        topic_title="Decision Trees",
        current_concept_id=concept.id,
        current_concept_title="Entropy",
    )

    # Step 1 & 2: Start learning flow (Research -> Teaching)
    ctx = nova.start_learning_flow(ctx, db=db)
    assert ctx.current_step == LearningStep.TEACHING
    assert ctx.research_data is not None
    assert ctx.teaching_data is not None
    assert ctx.teaching_data.concept == "Entropy"

    # Step 3: Transition to Critical Thinking
    ctx = nova.proceed_to_thinking(ctx, db=db)
    assert ctx.current_step == LearningStep.THINKING
    assert ctx.thinking_question is not None

    # Step 4: Submit Thinking Response -> Routes to Practical
    ctx = nova.submit_thinking_response(ctx, "Zero entropy means complete certainty.", db=db)
    assert ctx.current_step == LearningStep.PRACTICAL
    assert ctx.thinking_assessment is not None
    assert ctx.thinking_assessment.conceptual_understanding == "high"
    assert ctx.practical_exercise is not None

    # Step 5: Transition to Quiz
    ctx = nova.proceed_to_quiz(ctx, db=db)
    assert ctx.current_step == LearningStep.QUIZ
    assert ctx.quiz_question is not None

    # Step 6: Submit Quiz Answer -> Evaluated by Ellara
    ctx = nova.submit_quiz_response(ctx, "A. Pure dataset with only one class", db=db)
    assert ctx.current_step == LearningStep.EVALUATION
    assert ctx.quiz_grading is not None
    assert ctx.evaluation_result is not None
    assert ctx.evaluation_result.remediation_required is False
    assert ctx.evaluation_result.recommended_action == "advance"

    # Verify ConceptPerformance is persisted in DB as mastered
    perf = ConceptPerformanceRepository.get_or_create(db, profile.id, concept.id)
    assert perf.status == "mastered"
    assert perf.mastery_score == 100.0
