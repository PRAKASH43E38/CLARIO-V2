from pydantic import BaseModel, Field
from typing import List, Dict, Literal

class MasterEvaluation(BaseModel):
    strong_concepts: List[str] = Field(default_factory=list, description="List of mastered concepts")
    weak_concepts: List[str] = Field(default_factory=list, description="List of concepts needing remediation")
    misconceptions: List[str] = Field(default_factory=list, description="Detected conceptual misunderstandings")
    concept_status: Dict[str, Literal["mastered", "remediating", "learning"]] = Field(
        description="Mapping of concept name to status"
    )
    remediation_required: bool = Field(description="Whether targeted remediation is needed")
    recommended_action: Literal["advance", "remediate", "continue"] = Field(
        description="Next action recommended to NOVA"
    )
