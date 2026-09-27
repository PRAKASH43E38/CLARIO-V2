from typing import Optional
from backend.app.agents.base import BaseAgent
from backend.app.schemas.thinking import CriticalThinkingQuestion, CriticalThinkingAssessment

class CriticalThinkingAgent(BaseAgent):
    """Agent 3: Tests and develops reasoning (Thinking Friend UX).
    Probes understanding with Why, How, What-if questions and evaluates reasoning quality.
    """

    PROMPT_INSTRUCTION = (
        "You are the CLARIO Critical Thinking Agent (represented as Thinking Friend). "
        "Your job is to generate Socratic probing questions (Why, How, What-if) to test "
        "whether the learner genuinely grasps underlying principles rather than memorizing definitions."
    )

    EVAL_INSTRUCTION = (
        "You are evaluating learner reasoning. Analyze the explanation to detect misconceptions, "
        "assess depth of conceptual understanding, and assign a confidence score."
    )

    def generate_question(self, concept: str, concept_explanation: str) -> CriticalThinkingQuestion:
        prompt = (
            f"Concept: {concept}\n"
            f"Concept Explanation: {concept_explanation}\n"
            f"Generate a probing reasoning question."
        )
        return self.ai_provider.generate_structured(
            prompt=prompt,
            response_model=CriticalThinkingQuestion,
            system_instruction=self.PROMPT_INSTRUCTION,
        )

    def evaluate_reasoning(
        self,
        concept: str,
        question: str,
        learner_response: str,
    ) -> CriticalThinkingAssessment:
        prompt = (
            f"Concept: {concept}\n"
            f"Probing Question: {question}\n"
            f"Learner Response: {learner_response}\n"
            f"Assess the reasoning quality and identify any misconceptions."
        )
        return self.ai_provider.generate_structured(
            prompt=prompt,
            response_model=CriticalThinkingAssessment,
            system_instruction=self.EVAL_INSTRUCTION,
        )
