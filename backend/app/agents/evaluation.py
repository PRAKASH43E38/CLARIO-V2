from typing import Optional, List
from backend.app.agents.base import BaseAgent
from backend.app.schemas.thinking import CriticalThinkingAssessment
from backend.app.schemas.quiz import QuizGrading
from backend.app.schemas.evaluation import MasterEvaluation

class EvaluationAgent(BaseAgent):
    """Agent 6: Master diagnostic engine (Ellara).
    Aggregates multi-source evidence: Teaching interaction, Critical Thinking answers,
    Practical exercises, and Quizzes to determine conceptual mastery and remediation needs.
    Feeds structured results back to NOVA.
    """

    SYSTEM_INSTRUCTION = (
        "You are Ellara, the CLARIO Evaluation Agent. Your purpose is diagnostic analysis. "
        "Synthesize all available evidence from teaching, critical thinking, practical application, "
        "and quiz results. Determine which concepts are mastered, which require remediation, "
        "and identify fundamental misconceptions. Return machine-readable structured evaluation."
    )

    def evaluate_mastery(
        self,
        topic: str,
        concept: str,
        thinking_eval: Optional[CriticalThinkingAssessment] = None,
        practical_summary: Optional[str] = None,
        quiz_grading: Optional[QuizGrading] = None,
    ) -> MasterEvaluation:
        evidence = [f"Topic: {topic}", f"Evaluated Concept: {concept}"]
        if thinking_eval:
            evidence.append(
                f"Thinking Reasoning: {thinking_eval.reasoning_assessment}, "
                f"Understanding: {thinking_eval.conceptual_understanding}, "
                f"Misconception: {thinking_eval.misconception}"
            )
        if practical_summary:
            evidence.append(f"Practical Summary: {practical_summary}")
        if quiz_grading:
            evidence.append(
                f"Quiz Score: {quiz_grading.score}, "
                f"Mistakes: {', '.join(quiz_grading.mistakes) if quiz_grading.mistakes else 'None'}"
            )

        prompt = "\n".join(evidence)
        return self.ai_provider.generate_structured(
            prompt=prompt,
            response_model=MasterEvaluation,
            system_instruction=self.SYSTEM_INSTRUCTION,
        )
