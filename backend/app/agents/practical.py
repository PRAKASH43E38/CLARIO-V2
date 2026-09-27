from typing import Optional
from backend.app.agents.base import BaseAgent
from backend.app.schemas.practical import PracticalExercise

class PracticalAgent(BaseAgent):
    """Agent 4: Validates ability to apply knowledge (Practical Friend UX).
    Generates real-world scenarios, case studies, coding exercises, or decision problems.
    """

    SYSTEM_INSTRUCTION = (
        "You are the CLARIO Practical Agent (represented as Practical Friend). "
        "Your role is to move knowledge from theory into practical real-world application. "
        "Create authentic case studies, decision problems, or mini-projects tailored to "
        "the concept and learner interests."
    )

    def generate_exercise(
        self,
        concept: str,
        topic_context: str,
        learner_interests: Optional[str] = None,
        difficulty_level: int = 1,
    ) -> PracticalExercise:
        prompt = (
            f"Concept: {concept}\n"
            f"Topic Context: {topic_context}\n"
            f"Difficulty Level: {difficulty_level}"
        )
        if learner_interests:
            prompt += f"\nLearner Interests (use for scenario context): {learner_interests}"

        return self.ai_provider.generate_structured(
            prompt=prompt,
            response_model=PracticalExercise,
            system_instruction=self.SYSTEM_INSTRUCTION,
        )
