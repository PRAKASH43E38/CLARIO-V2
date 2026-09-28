from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from backend.app.schemas.research import SharedResearchPackage
from backend.app.schemas.mira import MiraTeachingResponse
from backend.app.schemas.ayan import AyanThinkingResponse
from backend.app.agents.kira.contracts import KiraOutput
from backend.app.agents.zayn.contracts import ZaynDifficulty
from backend.app.agents.elara.contracts import ElaraOutput
from backend.app.schemas.adaptive_decision import (
    AdaptiveDecision,
    SessionConceptPerformance,
)


OrchestrationState = Literal[
    "LEVEL_UNLOCKED",
    "LEVEL_ENTERED",
    "LEVEL_RESEARCH",
    "CALA_READY",
    "RESEARCH_REQUESTED",
    "RESEARCHING",
    "RESEARCH_READY",
    "RESEARCH_FAILED",
    "TEACHING_REQUESTED",
    "TEACHING",
    "TEACHING_READY",
    "TEACHING_FAILED",
    "THINKING_REQUESTED",
    "THINKING",
    "THINKING_READY",
    "THINKING_FAILED",
    "PRACTICAL_REQUESTED",
    "PRACTICAL",
    "PRACTICAL_READY",
    "PRACTICAL_FAILED",
    "QUIZ_REQUESTED",
    "QUIZ_GENERATING",
    "QUIZ_READY",
    "QUIZ_FAILED",
    "QUIZ_SUBMITTED",
    "EVALUATION_REQUESTED",
    "EVALUATING",
    "EVALUATION_READY",
    "EVALUATION_FAILED",
    "DECISION_REQUESTED",
    "DECIDING",
    "DECISION_READY",
    "DECISION_FAILED",
    "DECISION_APPLIED",
    "REMEDIATION_REQUESTED",
    "REMEDIATING",
    "REMEDIATION_FAILED",
    "REMEDIATION_LIMIT_REACHED",
    "RETEST_REQUESTED",
    "RETEST_FAILED",
]
OrchestrationStep = Literal[
    "level_unlocked",
    "level_entered",
    "level_research_started",
    "level_concept_advanced",
    "level_completed",
    "next_level_unlocked",
    "curriculum_completed",
    "cala_plan_loaded",
    "existing_research_package_loaded",
    "nova_task_created",
    "nova_research_dispatched",
    "shared_research_package_received",
    "tavily_not_configured",
    "nova_research_failed",
    "mira_task_created",
    "mira_teaching_dispatched",
    "teaching_response_received",
    "mira_provider_failed",
    "mira_response_invalid",
    "teaching_persistence_failed",
    "ayan_task_created",
    "ayan_thinking_dispatched",
    "thinking_response_received",
    "ayan_provider_failed",
    "ayan_response_invalid",
    "thinking_persistence_failed",
    "kira_task_created",
    "kira_practical_dispatched",
    "practical_activity_received",
    "kira_provider_failed",
    "kira_response_invalid",
    "practical_persistence_failed",
    "zayn_task_created",
    "zayn_quiz_generation_started",
    "quiz_ready",
    "zayn_provider_failed",
    "zayn_response_invalid",
    "quiz_persistence_failed",
    "quiz_submitted",
    "elara_task_created",
    "elara_evaluation_started",
    "evaluation_ready",
    "elara_provider_failed",
    "elara_response_invalid",
    "evaluation_persistence_failed",
    "clario_decision_requested",
    "clario_decision_started",
    "adaptive_decision_persisted",
    "clario_decision_failed",
    "adaptive_decision_applied",
    "remediation_attempt_limit_reached",
    "concept_retest_requested",
    "concept_remediation_requested",
    "concept_remediation_started",
    "mira_remediation_task_created",
    "mira_remediation_dispatched",
    "remediation_teaching_ready",
    "ayan_remediation_task_created",
    "ayan_remediation_dispatched",
    "remediation_thinking_ready",
    "kira_remediation_task_created",
    "kira_remediation_dispatched",
    "remediation_practical_ready",
    "adaptive_quiz_requested",
    "zayn_adaptive_quiz_generation_started",
    "adaptive_quiz_ready",
    "adaptive_provider_failed",
    "adaptive_output_invalid",
    "adaptive_persistence_failed",
    "adaptive_prerequisite_failed",
]


class ClarioOrchestrationContext(BaseModel):
    session_id: str
    cala_plan_id: str
    current_state: OrchestrationState
    current_step: OrchestrationStep
    research_package_id: Optional[str] = None
    research_package: Optional[SharedResearchPackage] = None
    teaching_result_id: Optional[str] = None
    teaching_result: Optional[MiraTeachingResponse] = None
    thinking_result_id: Optional[str] = None
    thinking_result: Optional[AyanThinkingResponse] = None
    practical_result_id: Optional[str] = None
    practical_result: Optional[KiraOutput] = None
    quiz_id: Optional[str] = None
    quiz_difficulty: Optional[ZaynDifficulty] = None
    quiz_status: Optional[
        Literal["GENERATED", "IN_PROGRESS", "SUBMITTED"]
    ] = None
    evaluation_id: Optional[str] = None
    evaluation: Optional[ElaraOutput] = None
    adaptive_decision: Optional[AdaptiveDecision] = None
    concept_performance: Optional[SessionConceptPerformance] = None
    created_at: datetime
    updated_at: datetime
