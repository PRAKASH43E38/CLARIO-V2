from pydantic import BaseModel, Field
from typing import List, Optional

class TeachingOutput(BaseModel):
    concept: str = Field(description="Target concept explained")
    explanation: str = Field(description="Clear explanation tailored to learner's level and style")
    step_by_step_breakdown: List[str] = Field(description="Sequential logical steps")
    analogy: Optional[str] = Field(default=None, description="Intuitive analogy to aid retention")
    intuitive_example: str = Field(description="Practical concrete example")
    check_for_understanding_prompt: str = Field(description="Interactive prompt to verify comprehension")
