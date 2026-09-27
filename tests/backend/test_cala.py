from backend.app.cala.planner import CalaPlanner
from backend.app.models.curriculum import Concept, Topic
from backend.app.models.learner import LearnerProfile
from backend.app.models.mind_profile import MindProfile
from backend.app.models.session_inputs import SessionInputs


def _planner_inputs(learner_state=""):
    return SessionInputs(
        session_id="ses_test",
        task="Learn a topic",
        goal="Explain the main idea",
        learner_state=learner_state,
        interest="Space",
    )


def _learner_profile(level="unassessed", confidence=0):
    return LearnerProfile(
        user_id="usr_test",
        learning_goal="Legacy goal",
        current_level=level,
        learning_preference="example_first",
        interests="Legacy interest",
        initial_confidence=confidence,
    )


def test_cala_returns_structured_plan_and_safe_beginner_default():
    topic = Topic(
        id="top_test",
        title="Test Curriculum",
        description="A small curriculum",
        sequence_order=1,
    )
    concepts = [
        Concept(
            id="cpt_test",
            topic_id=topic.id,
            title="First Concept",
            description="A real curriculum concept",
            base_difficulty=1,
            sequence_order=1,
        )
    ]
    mind_profile = MindProfile(
        user_id="usr_test",
        preferred_explanation="A worked example",
        learning_motivation="Curiosity",
        support_when_stuck="A hint",
        feedback_preference="Direct",
        challenge_preference="Build up",
    )

    plan_inputs = _planner_inputs()
    profile = _learner_profile()
    result = CalaPlanner.create_plan(
        session_id="ses_test",
        session_inputs=plan_inputs,
        topic=topic,
        concepts=concepts,
        mind_profile=mind_profile,
        learner_profile=profile,
    )
    repeated_result = CalaPlanner.create_plan(
        session_id="ses_test",
        session_inputs=plan_inputs,
        topic=topic,
        concepts=concepts,
        mind_profile=mind_profile,
        learner_profile=profile,
    )

    assert result.session_id == "ses_test"
    assert result.learner_level == "beginner"
    assert "not enough reliable level evidence" in result.learner_level_reason
    assert result.confidence_state.level == "unknown"
    assert result.confidence_state.self_reported_score is None
    assert result.weakness_type == "unknown"
    assert result.recommended_starting_level == "level_1"
    assert "available starting level" in result.recommended_starting_level_reason
    assert result.roadmap[0].is_unlocked is True
    assert result.roadmap[0].topics[0].concepts[0].concept_id == "cpt_test"
    assert [level.is_unlocked for level in result.roadmap] == [True, False, False]
    assert result.initial_agent_routing[0].agent == "Nova"
    assert all(route.status == "planned" for route in result.initial_agent_routing)
    assert "worked example" in result.initial_agent_routing[1].purpose
    assert repeated_result == result


def test_cala_uses_explicit_session_evidence_and_ignores_unassessed_sentinels():
    result = CalaPlanner.create_plan(
        session_id="ses_test",
        session_inputs=_planner_inputs(
            "I have some experience and understand the basics, but I am not confident yet."
        ),
        topic=Topic(id="top_test", title="Test", sequence_order=1),
        concepts=[],
        mind_profile=None,
        learner_profile=_learner_profile(level="unassessed", confidence=0),
    )

    assert result.learner_level == "intermediate"
    assert "some experience" in result.learner_level_reason
    assert result.confidence_state.level == "low"
    assert result.confidence_state.evidence == "learner_state"
    assert result.confidence_state.self_reported_score is None


def test_cala_uses_valid_legacy_self_report_without_treating_zero_as_evidence():
    result = CalaPlanner.create_plan(
        session_id="ses_test",
        session_inputs=_planner_inputs(),
        topic=Topic(id="top_test", title="Test", sequence_order=1),
        concepts=[],
        mind_profile=None,
        learner_profile=_learner_profile(level="advanced", confidence=4),
    )

    assert result.learner_level == "advanced"
    assert "historical baseline" in result.learner_level_reason
    assert result.confidence_state.level == "high"
    assert result.confidence_state.self_reported_score == 4
