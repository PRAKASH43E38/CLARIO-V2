from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class PracticalExercise(BaseModel):
    scenario_title: str = Field(description="Title of the real-world scenario")
    practical_type: Literal["case_study", "coding_exercise", "decision_problem", "mini_project"] = Field(
        description="Format of the practical application"
    )
    scenario_description: str = Field(description="Context and narrative of the scenario")
    task_prompt: str = Field(description="Specific actionable task for the learner")
    hints: List[str] = Field(default_factory=list, description="Guidance hints if stuck")
