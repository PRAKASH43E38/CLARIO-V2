from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class CriticalThinkingQuestion(BaseModel):
    question: str = Field(description="Probing reasoning question (Why, How, What-if)")
    probing_type: Literal["why", "how", "what_if", "assumption_change"] = Field(
        description="Type of reasoning probe"
    )
    expected_reasoning_points: List[str] = Field(
        description="Key points that demonstrate valid understanding"
    )

class CriticalThinkingAssessment(BaseModel):
    reasoning_assessment: str = Field(description="Evaluation of the learner's explanation")
    conceptual_understanding: Literal["high", "moderate", "low"] = Field(
        description="Assessed level of understanding"
    )
    misconception: Optional[str] = Field(default=None, description="Identified flaw or gap, if any")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
