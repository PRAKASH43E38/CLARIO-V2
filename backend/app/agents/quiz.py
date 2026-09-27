from typing import Optional, List
from backend.app.agents.base import BaseAgent
from backend.app.schemas.quiz import QuizQuestion, QuizGrading

class QuizAgent(BaseAgent):
    """Agent 5: Formal measurement of learning (Quiz Friend UX).
    Generates calibrated assessments and produces structured scores and mistake diagnoses.
    """

    GENERATE_INSTRUCTION = (
        "You are the CLARIO Quiz Agent (represented as Quiz Friend). "
        "Generate a calibrated question (MCQ, short answer, or scenario) to test concept mastery. "
        "Ensure the question matches the requested difficulty. "
        "If this is a retest, generate a completely distinct question and do not repeat previous question IDs."
    )

    GRADE_INSTRUCTION = (
        "You are grading a quiz response. Evaluate correctness, score from 0-100, "
        "isolate specific mistakes, and provide constructive recommendations."
    )

    def generate_question(
        self,
        concept: str,
        difficulty_level: int = 1,
        format_type: str = "mcq",
        attempt_number: int = 1,
        exclude_question_ids: Optional[List[str]] = None,
    ) -> QuizQuestion:
        prompt = (
            f"Concept: {concept}\n"
            f"Difficulty Level: {difficulty_level}\n"
            f"Format: {format_type}\n"
            f"Attempt Number: {attempt_number}"
        )
        if exclude_question_ids:
            prompt += f"\nExclude Question IDs: {', '.join(exclude_question_ids)}"

        return self.ai_provider.generate_structured(
            prompt=prompt,
            response_model=QuizQuestion,
            system_instruction=self.GENERATE_INSTRUCTION,
        )

    def grade_answer(
        self,
        question: str,
        correct_answer: str,
        learner_answer: str,
        difficulty_level: int = 1,
    ) -> QuizGrading:
        prompt = (
            f"Question: {question}\n"
            f"Authoritative Answer: {correct_answer}\n"
            f"Learner Answer: {learner_answer}\n"
            f"Difficulty Level: {difficulty_level}"
        )
        return self.ai_provider.generate_structured(
            prompt=prompt,
            response_model=QuizGrading,
            system_instruction=self.GRADE_INSTRUCTION,
        )
