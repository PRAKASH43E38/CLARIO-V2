import pytest
from backend.app.ai.mock_provider import MockAIProvider
from backend.app.agents.research import ResearchAgent
from backend.app.agents.teaching import TeachingAgent
from backend.app.agents.thinking import CriticalThinkingAgent
from backend.app.agents.practical import PracticalAgent
from backend.app.agents.quiz import QuizAgent
from backend.app.agents.evaluation import EvaluationAgent
from backend.app.schemas import (
    ResearchOutput,
    TeachingOutput,
    CriticalThinkingQuestion,
    CriticalThinkingAssessment,
    PracticalExercise,
    QuizQuestion,
    QuizGrading,
    MasterEvaluation,
)

@pytest.fixture
def provider():
    return MockAIProvider()

def test_research_agent(provider):
    agent = ResearchAgent(provider)
    res = agent.research_topic("Decision Trees")
    assert isinstance(res, ResearchOutput)
    assert res.topic == "Decision Trees"
    assert len(res.key_concepts) > 0
    assert res.key_concepts[0].title == "Entropy"

def test_teaching_agent(provider):
    agent = TeachingAgent(provider)
    res = agent.explain_concept("Entropy", "Decision Trees", learner_level="beginner")
    assert isinstance(res, TeachingOutput)
    assert res.concept == "Entropy"
    assert len(res.step_by_step_breakdown) > 0
    assert res.analogy is not None

def test_critical_thinking_agent(provider):
    agent = CriticalThinkingAgent(provider)
    q = agent.generate_question("Entropy", "Entropy measures impurity.")
    assert isinstance(q, CriticalThinkingQuestion)
    assert q.probing_type in ["why", "how", "what_if", "assumption_change"]

    assessment = agent.evaluate_reasoning("Entropy", q.question, "Purity is maximized when entropy is zero.")
    assert isinstance(assessment, CriticalThinkingAssessment)
    assert assessment.conceptual_understanding in ["high", "moderate", "low"]
    assert assessment.confidence >= 0.0

def test_practical_agent(provider):
    agent = PracticalAgent(provider)
    ex = agent.generate_exercise("Entropy", "Decision Trees", learner_interests="finance")
    assert isinstance(ex, PracticalExercise)
    assert ex.practical_type in ["case_study", "coding_exercise", "decision_problem", "mini_project"]
    assert len(ex.task_prompt) > 0

def test_quiz_agent(provider):
    agent = QuizAgent(provider)
    q = agent.generate_question("Entropy", difficulty_level=1)
    assert isinstance(q, QuizQuestion)
    assert q.correct_answer != ""

    grading = agent.grade_answer(q.question_text, q.correct_answer, q.correct_answer, difficulty_level=1)
    assert isinstance(grading, QuizGrading)
    assert grading.score == 100.0

def test_evaluation_agent_ellara(provider):
    agent = EvaluationAgent(provider)
    grading = QuizGrading(score=95.0, concept_performance=95.0, mistakes=[], difficulty=1, recommendation="Good")
    eval_res = agent.evaluate_mastery("Decision Trees", "Entropy", quiz_grading=grading)
    assert isinstance(eval_res, MasterEvaluation)
    assert "Entropy" in eval_res.strong_concepts
    assert eval_res.remediation_required is False
    assert eval_res.recommended_action == "advance"
