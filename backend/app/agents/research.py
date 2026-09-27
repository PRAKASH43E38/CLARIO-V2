from typing import Optional
from backend.app.agents.base import BaseAgent
from backend.app.schemas.research import ResearchOutput

class ResearchAgent(BaseAgent):
    """Agent 1: Knowledge acquisition and structure preparation.
    Does NOT teach the learner directly. Does NOT grade or evaluate.
    """

    SYSTEM_INSTRUCTION = (
        "You are the CLARIO Research Agent. Your sole responsibility is gathering, "
        "validating, and structuring foundational educational knowledge for a topic. "
        "Extract key concepts, definitions, base difficulties, and illustrative examples. "
        "Do NOT teach the learner or address them directly. Return structured knowledge."
    )

    def research_topic(self, topic: str, context: Optional[str] = None) -> ResearchOutput:
        prompt = f"Research Topic: {topic}"
        if context:
            prompt += f"\nContext: {context}"
        return self.ai_provider.generate_structured(
            prompt=prompt,
            response_model=ResearchOutput,
            system_instruction=self.SYSTEM_INSTRUCTION,
        )
