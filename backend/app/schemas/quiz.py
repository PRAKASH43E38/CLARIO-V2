from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class QuizQuestion(BaseModel):
    question_id: str = Field(description="Unique question identifier")
    format: Literal["mcq", "short_answer", "scenario", "coding"] = Field(default="mcq")
    question_text: str = Field(description="Question body")
    options: Optional[List[str]] = Field(default=None, description="Options if format is MCQ")
    correct_answer: str = Field(description="Authoritative correct answer")
    difficulty: int = Field(ge=1, le=5, description="Difficulty rating 1-5")

class QuizGrading(BaseModel):
    score: float = Field(ge=0.0, le=100.0, description="Score between 0 and 100")
    concept_performance: float = Field(ge=0.0, le=100.0, description="Specific concept score")
    mistakes: List[str] = Field(default_factory=list, description="Identified specific errors")
    difficulty: int = Field(description="Tested difficulty level")
    recommendation: str = Field(description="Immediate assessment observation")
