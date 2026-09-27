from typing import Optional
from backend.app.agents.base import BaseAgent
from backend.app.schemas.teaching import TeachingOutput

class TeachingAgent(BaseAgent):
    """Agent 2: Adaptive explanation of concepts (Teaching Friend UX).
    Explains concepts clearly tailored to learner level and preferred style.
    Does NOT assess or grade final responses.
    """

    SYSTEM_INSTRUCTION = (
        "You are the CLARIO Teaching Agent (represented to the learner as Teaching Friend). "
        "Your role is to explain concepts clearly, intuitively, and adaptively based on "
        "the learner's level and preferred style. Use analogies and step-by-step breakdowns. "
        "If this is a remediation round, provide an alternative explanation addressing previous gaps. "
        "Do NOT grade or evaluate the learner."
    )

    def explain_concept(
        self,
        concept: str,
        topic_context: str,
        learner_level: str = "intermediate",
        learning_preference: str = "step_by_step",
        is_remediation: bool = False,
        remediation_notes: Optional[str] = None,
    ) -> TeachingOutput:
        prompt = (
            f"Concept: {concept}\n"
            f"Topic Context: {topic_context}\n"
            f"Learner Level: {learner_level}\n"
            f"Learning Preference: {learning_preference}\n"
            f"Is Remediation: {is_remediation}"
        )
        if remediation_notes:
            prompt += f"\nRemediation Focus: {remediation_notes}"

        return self.ai_provider.generate_structured(
            prompt=prompt,
            response_model=TeachingOutput,
            system_instruction=self.SYSTEM_INSTRUCTION,
        )
