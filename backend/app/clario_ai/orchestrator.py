import asyncio
import json
import os
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.agents.mira_teaching import (
    MiraProviderError,
    MiraResponseError,
    MiraTeachingAgent,
)
from backend.app.agents.zayn import (
    ZaynDifficulty,
    ZaynOutput,
    ZaynPresentation,
    ZaynQuizAgent,
    ZaynSubmissionRequest,
    ZaynSubmissionResponse,
    ZaynTask,
)
from backend.app.agents.zayn.contracts import (
    ZAYN_TIME_LIMITS,
    ZaynAnswerKeyEntry,
    ZaynLearnerContext,
    ZaynPracticalReference,
    ZaynThinkingReference,
    ZaynTeachingReference,
)
from backend.app.agents.zayn.quiz import ZaynProviderError, ZaynResponseError
from backend.app.agents.elara import (
    ElaraEvaluationAgent,
    ElaraOutput,
    ElaraProviderError,
    ElaraResponseError,
    ElaraTask,
)
from backend.app.agents.elara.contracts import (
    ElaraLearnerContext,
    ElaraPracticalReference,
    ElaraQuizPerformance,
    ElaraQuizReference,
    ElaraTeachingReference,
    ElaraThinkingReference,
)
from backend.app.clario_ai.decision_engine import decide_concept_outcome
from backend.app.agents.ayan_thinking import (
    AyanCriticalThinkingAgent,
    AyanProviderError,
    AyanResponseError,
)
from backend.app.agents.kira import (
    KiraOutput,
    KiraPracticalAgent,
    KiraProviderError,
    KiraResponseError,
    KiraTask,
)
from backend.app.ai.base import BaseAIProvider
from backend.app.cala import CalaPlanner
from backend.app.cala.schemas import (
    CalaResult,
    GeneratedRemainingCurriculum,
    LevelProgressionEvent,
    LevelProgressionResult,
    RoadmapConcept,
    RoadmapLevel,
    RoadmapTopic,
)
from backend.app.models.orchestration import OrchestrationRecord
from backend.app.models.adaptive_execution import AdaptiveExecutionRecord
from backend.app.models.session_concept_performance import (
    SessionConceptPerformanceRecord,
)
from backend.app.models.practical_result import PracticalResultRecord
from backend.app.models.repositories import (
    CalaPlanRepository,
    LearnerProfileRepository,
    OrchestrationRepository,
    ResearchPackageRepository,
    SessionRepository,
    TeachingResultRepository,
    ThinkingResultRepository,
    PracticalResultRepository,
    QuizResultRepository,
    ElaraEvaluationRepository,
    SessionConceptPerformanceRepository,
    AdaptiveDecisionRepository,
    AdaptiveExecutionRepository,
    CurriculumRepository,
)
from backend.app.research.request_builder import research_request_from_cala
from backend.app.research.service import run_nova_research
from backend.app.research.tavily import (
    TavilyConfigurationError,
    TavilySearchError,
    TavilySearchProvider,
)
from backend.app.schemas.orchestration import ClarioOrchestrationContext
from backend.app.schemas.adaptive_decision import (
    AdaptiveDecision,
    SessionConceptPerformance,
)
from backend.app.schemas.adaptive_execution import (
    AdaptiveExecutionResult,
    RemediationContext,
)
from backend.app.schemas.mira import (
    MiraRemediationMetadata,
    MiraTeachingResponse,
    MiraTeachingTask,
)
from backend.app.schemas.ayan import (
    AyanCriticalThinkingTask,
    AyanThinkingResponse,
)
from backend.app.agents.kira.contracts import (
    KiraLearnerContext,
    KiraResearchSource,
    KiraTeachingReference,
    KiraThinkingReference,
)
from backend.app.schemas.mira import MiraSourceReference
from backend.app.schemas.research import ResearchConcept, SharedResearchPackage


class CalaPlanRequiredError(ValueError):
    pass


class ResearchConfigurationMissingError(RuntimeError):
    pass


class ResearchDispatchError(RuntimeError):
    pass


class ResearchPackageRequiredError(ValueError):
    pass


class TeachingInProgressError(RuntimeError):
    pass


class TeachingProviderFailure(RuntimeError):
    pass


class TeachingOutputInvalid(RuntimeError):
    pass


class TeachingPersistenceFailure(RuntimeError):
    pass


class ThinkingPrerequisiteError(ValueError):
    pass


class ThinkingInProgressError(RuntimeError):
    pass


class ThinkingProviderFailure(RuntimeError):
    pass


class ThinkingOutputInvalid(RuntimeError):
    pass


class ThinkingPersistenceFailure(RuntimeError):
    pass


class PracticalPrerequisiteError(ValueError):
    pass


class PracticalInProgressError(RuntimeError):
    pass


class PracticalProviderFailure(RuntimeError):
    pass


class PracticalOutputInvalid(RuntimeError):
    pass


class PracticalPersistenceFailure(RuntimeError):
    pass


class QuizPrerequisiteError(ValueError):
    pass


class QuizInProgressError(RuntimeError):
    pass


class QuizProviderFailure(RuntimeError):
    pass


class QuizOutputInvalid(RuntimeError):
    pass


class QuizPersistenceFailure(RuntimeError):
    pass


class InvalidQuizSubmissionError(ValueError):
    pass


class QuizSubmissionConflict(RuntimeError):
    pass


class EvaluationPrerequisiteError(ValueError):
    pass


class EvaluationInProgressError(RuntimeError):
    pass


class EvaluationProviderFailure(RuntimeError):
    pass


class EvaluationOutputInvalid(RuntimeError):
    pass


class EvaluationPersistenceFailure(RuntimeError):
    pass


class DecisionPrerequisiteError(ValueError):
    pass


class DecisionPersistenceFailure(RuntimeError):
    pass


class LevelProgressionPrerequisiteError(ValueError):
    pass


class LevelCurriculumProviderFailure(RuntimeError):
    pass


class LevelCurriculumOutputInvalid(RuntimeError):
    pass


class AdaptiveExecutionPrerequisiteError(ValueError):
    pass


class AdaptiveExecutionProviderFailure(RuntimeError):
    pass


class AdaptiveExecutionOutputInvalid(RuntimeError):
    pass


class AdaptiveExecutionPersistenceFailure(RuntimeError):
    pass


class AdaptiveExecutionConfigurationError(RuntimeError):
    pass


DEFAULT_MAX_REMEDIATION_ATTEMPTS = 3


class ClarioAIOrchestrator:
    """Owns session workflow transitions and dispatches bounded worker tasks."""

    @staticmethod
    def _active_level(plan: CalaResult) -> Optional[RoadmapLevel]:
        level_id = plan.current_level_id or plan.recommended_starting_level
        return next((item for item in plan.roadmap if item.level_id == level_id), None)

    @staticmethod
    def _level_concepts(level: RoadmapLevel) -> list[RoadmapConcept]:
        return [
            concept
            for topic in sorted(level.topics, key=lambda item: item.order)
            for concept in sorted(topic.concepts, key=lambda item: item.order)
        ]

    @staticmethod
    def _active_concept(plan: CalaResult) -> Optional[RoadmapConcept]:
        level = ClarioAIOrchestrator._active_level(plan)
        if level is None:
            return None
        concepts = ClarioAIOrchestrator._level_concepts(level)
        return next(
            (
                concept
                for concept in concepts
                if concept.concept_id == plan.active_concept_id
            ),
            concepts[0] if concepts else None,
        )

    @staticmethod
    def _active_attempt(plan: CalaResult) -> int:
        return plan.active_attempt_number

    @staticmethod
    def initialize_from_cala(
        db: Session, session_id: str
    ) -> ClarioOrchestrationContext:
        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        if not plan_record:
            raise CalaPlanRequiredError("Create the CALA plan before orchestration.")

        plan = CalaResult.model_validate_json(plan_record.plan_json)
        current_level = ClarioAIOrchestrator._active_level(plan)
        if current_level is None:
            raise CalaPlanRequiredError("The active CALA level is unavailable.")
        if current_level.level_state == "LEVEL_UNLOCKED":
            current_level.level_state = "LEVEL_ENTERED"
            plan.progression_history.append(
                LevelProgressionEvent(
                    action="LEVEL_ENTERED",
                    level_id=current_level.level_id,
                    concept_id=plan.active_concept_id,
                    reason="The learner entered the unlocked starting level.",
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            plan_record.plan_json = plan.model_dump_json()
            db.add(plan_record)
            db.commit()

        existing_package = (
            ResearchPackageRepository.get_by_session_id(db, session_id)
        )
        if existing_package and (
            existing_package.level_id != current_level.level_id
            or existing_package.attempt_number != plan.active_attempt_number
        ):
            existing_package = None
        initial_state = "LEVEL_ENTERED"
        initial_step = "level_entered"
        package_id: Optional[str] = None
        package: Optional[SharedResearchPackage] = None
        if existing_package:
            initial_state = "RESEARCH_READY"
            initial_step = "existing_research_package_loaded"
            package_id = existing_package.id
            package = SharedResearchPackage.model_validate_json(
                existing_package.package_json
            )

        record = OrchestrationRepository.create_if_missing(
            db,
            session_id=session_id,
            cala_plan_id=plan_record.id,
            current_state=initial_state,
            current_step=initial_step,
            research_package_id=package_id,
        )
        if record.research_package_id:
            package_record = ResearchPackageRepository.get_by_id(
                db, record.research_package_id
            )
            package = (
                SharedResearchPackage.model_validate_json(package_record.package_json)
                if package_record
                else None
            )
        teaching_record = TeachingResultRepository.get_by_session_id(db, session_id)
        teaching = (
            MiraTeachingResponse.model_validate_json(teaching_record.response_json)
            if teaching_record
            else None
        )
        thinking_record = ThinkingResultRepository.get_by_session_id(db, session_id)
        thinking = (
            AyanThinkingResponse.model_validate_json(thinking_record.response_json)
            if thinking_record
            else None
        )
        practical_record = PracticalResultRepository.get_by_session_id(db, session_id)
        practical = (
            ClarioAIOrchestrator._practical_output(practical_record)
            if practical_record
            else None
        )
        quiz_record = QuizResultRepository.get_by_session_id(db, session_id)
        evaluation_record = ElaraEvaluationRepository.get_by_session_id(db, session_id)
        decision_record = AdaptiveDecisionRepository.get_by_session_id(db, session_id)
        performance_record = (
            SessionConceptPerformanceRepository.get_by_session_and_concept(
                db, session_id, decision_record.concept_id
            )
            if decision_record
            else None
        )
        return ClarioAIOrchestrator._context(
            record,
            package,
            teaching,
            teaching_record.id if teaching_record else None,
            thinking,
            thinking_record.id if thinking_record else None,
            practical,
            practical_record.id if practical_record else None,
            quiz_record.id if quiz_record else None,
            quiz_record.difficulty if quiz_record else None,
            quiz_record.status if quiz_record else None,
            evaluation_record.id if evaluation_record else None,
            (
                ElaraOutput.model_validate_json(evaluation_record.evaluation_json)
                if evaluation_record
                else None
            ),
            (
                AdaptiveDecision.model_validate_json(decision_record.decision_json)
                if decision_record
                else None
            ),
            (
                ClarioAIOrchestrator._concept_performance_output(performance_record)
                if performance_record
                else None
            ),
        )

    @staticmethod
    def get_state(
        db: Session, session_id: str
    ) -> Optional[ClarioOrchestrationContext]:
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        if not record:
            return None
        package_record = (
            ResearchPackageRepository.get_by_id(db, record.research_package_id)
            if record.research_package_id
            else None
        )
        package = (
            SharedResearchPackage.model_validate_json(package_record.package_json)
            if package_record
            else None
        )
        teaching_record = TeachingResultRepository.get_by_session_id(db, session_id)
        teaching = (
            MiraTeachingResponse.model_validate_json(teaching_record.response_json)
            if teaching_record
            else None
        )
        thinking_record = ThinkingResultRepository.get_by_session_id(db, session_id)
        thinking = (
            AyanThinkingResponse.model_validate_json(thinking_record.response_json)
            if thinking_record
            else None
        )
        practical_record = PracticalResultRepository.get_by_session_id(db, session_id)
        practical = (
            ClarioAIOrchestrator._practical_output(practical_record)
            if practical_record
            else None
        )
        quiz_record = QuizResultRepository.get_by_session_id(db, session_id)
        evaluation_record = ElaraEvaluationRepository.get_by_session_id(db, session_id)
        decision_record = AdaptiveDecisionRepository.get_by_session_id(db, session_id)
        performance_record = (
            SessionConceptPerformanceRepository.get_by_session_and_concept(
                db, session_id, decision_record.concept_id
            )
            if decision_record
            else None
        )
        return ClarioAIOrchestrator._context(
            record,
            package,
            teaching,
            teaching_record.id if teaching_record else None,
            thinking,
            thinking_record.id if thinking_record else None,
            practical,
            practical_record.id if practical_record else None,
            quiz_record.id if quiz_record else None,
            quiz_record.difficulty if quiz_record else None,
            quiz_record.status if quiz_record else None,
            evaluation_record.id if evaluation_record else None,
            (
                ElaraOutput.model_validate_json(evaluation_record.evaluation_json)
                if evaluation_record
                else None
            ),
            (
                AdaptiveDecision.model_validate_json(decision_record.decision_json)
                if decision_record
                else None
            ),
            (
                ClarioAIOrchestrator._concept_performance_output(performance_record)
                if performance_record
                else None
            ),
        )

    @staticmethod
    async def request_research(
        db: Session,
        session_id: str,
        search_provider: TavilySearchProvider | None,
    ) -> ClarioOrchestrationContext:
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        if not record:
            raise CalaPlanRequiredError(
                "Initialize CLARIO-AI orchestration before requesting research."
            )
        if record.research_package_id:
            return ClarioAIOrchestrator.get_state(db, session_id)

        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        if not plan_record or plan_record.id != record.cala_plan_id:
            raise CalaPlanRequiredError("The session's persisted CALA plan is unavailable.")
        plan = CalaResult.model_validate_json(plan_record.plan_json)
        if plan.session_id != session_id:
            raise CalaPlanRequiredError("CALA plan/session mismatch.")
        try:
            research_request = research_request_from_cala(plan)
        except ValueError as exc:
            raise CalaPlanRequiredError(str(exc)) from exc

        current_level = ClarioAIOrchestrator._active_level(plan)
        if current_level is None:
            raise CalaPlanRequiredError("The active CALA level is unavailable.")
        current_level.level_state = "LEVEL_RESEARCH"
        plan_record.plan_json = plan.model_dump_json()
        db.add(plan_record)
        db.commit()
        OrchestrationRepository.update_state(
            db, record, "RESEARCH_REQUESTED", "nova_task_created"
        )
        if search_provider is None:
            OrchestrationRepository.update_state(
                db, record, "RESEARCH_FAILED", "tavily_not_configured"
            )
            raise ResearchConfigurationMissingError(
                "Web research is not configured. Set TAVILY_API_KEY on the backend."
            )

        OrchestrationRepository.update_state(
            db, record, "RESEARCHING", "nova_research_dispatched"
        )
        try:
            package = await asyncio.to_thread(
                run_nova_research, research_request, search_provider
            )
        except TavilyConfigurationError as exc:
            OrchestrationRepository.update_state(
                db, record, "RESEARCH_FAILED", "tavily_not_configured"
            )
            raise ResearchConfigurationMissingError(
                "Web research is not configured. Set TAVILY_API_KEY on the backend."
            ) from exc
        except TavilySearchError as exc:
            OrchestrationRepository.update_state(
                db, record, "RESEARCH_FAILED", "nova_research_failed"
            )
            raise ResearchDispatchError(
                "The web research provider could not complete the search."
            ) from exc

        package_record = ResearchPackageRepository.create(
            db,
            session_id,
            package.model_dump_json(),
            level_id=current_level.level_id,
            attempt_number=ClarioAIOrchestrator._active_attempt(plan),
        )
        saved_package = SharedResearchPackage.model_validate_json(
            package_record.package_json
        )
        OrchestrationRepository.update_state(
            db,
            record,
            "RESEARCH_READY",
            "shared_research_package_received",
            research_package_id=package_record.id,
        )
        return ClarioAIOrchestrator._context(record, saved_package)

    @staticmethod
    async def request_teaching(
        db: Session,
        session_id: str,
        ai_provider: BaseAIProvider,
    ) -> ClarioOrchestrationContext:
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        if not record:
            raise CalaPlanRequiredError(
                "Initialize CLARIO-AI orchestration before requesting teaching."
            )
        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        if not plan_record or plan_record.id != record.cala_plan_id:
            raise ResearchPackageRequiredError(
                "The session's CALA plan is unavailable."
            )
        plan = CalaResult.model_validate_json(plan_record.plan_json)
        active_concept = ClarioAIOrchestrator._active_concept(plan)
        existing_result = TeachingResultRepository.get_by_session_and_attempt(
            db, session_id, ClarioAIOrchestrator._active_attempt(plan)
        )
        if existing_result:
            if (
                active_concept is None
                or existing_result.concept.casefold()
                != active_concept.title.casefold()
            ):
                raise ResearchPackageRequiredError(
                    "The persisted Mira result belongs to a different active concept."
                )
            MiraTeachingResponse.model_validate_json(existing_result.response_json)
            if record.current_state != "TEACHING_READY":
                OrchestrationRepository.update_state(
                    db,
                    record,
                    "TEACHING_READY",
                    "teaching_response_received",
                )
            return ClarioAIOrchestrator.get_state(db, session_id)
        if record.current_state == "TEACHING":
            raise TeachingInProgressError("Mira teaching is already in progress.")
        if record.current_state not in {"RESEARCH_READY", "TEACHING_FAILED"}:
            raise ResearchPackageRequiredError(
                "A completed research package is required before Mira can teach."
            )
        if not record.research_package_id:
            raise ResearchPackageRequiredError(
                "A completed research package is required before Mira can teach."
            )

        package_record = (
            ResearchPackageRepository.get_by_id(db, record.research_package_id)
            if record.research_package_id
            else None
        )
        if (
            not plan_record
            or plan_record.id != record.cala_plan_id
            or not package_record
            or package_record.id != record.research_package_id
        ):
            raise ResearchPackageRequiredError(
                "The session's CALA plan or research package is unavailable."
            )
        package = SharedResearchPackage.model_validate_json(
            package_record.package_json
        )
        if plan.session_id != session_id or package.session_id != session_id:
            raise ResearchPackageRequiredError(
                "CALA plan or research package session mismatch."
            )
        if not package.selected_sources:
            raise ResearchPackageRequiredError(
                "Mira requires at least one validated research source."
            )
        concept = ClarioAIOrchestrator._current_concept(plan, package)
        learner_profile = LearnerProfileRepository.get_by_user_id(
            db, SessionRepository.get_session(db, session_id).user_id
        )
        task = MiraTeachingTask(
            session_id=session_id,
            task=plan.task,
            learning_goal=plan.learning_goal,
            learner_state=plan.learner_state,
            interest=plan.interest,
            current_concept=concept,
            shared_research_package=package,
            current_level=plan.learner_level,
            learning_preference=(
                learner_profile.learning_preference if learner_profile else None
            ),
            teaching_instruction=(
                "Explain the current concept using the supplied validated research "
                "package and learner context. Do not assess or make progression decisions."
            ),
        )
        OrchestrationRepository.update_state(
            db, record, "TEACHING_REQUESTED", "mira_task_created"
        )
        OrchestrationRepository.update_state(
            db, record, "TEACHING", "mira_teaching_dispatched"
        )
        try:
            response = await asyncio.to_thread(MiraTeachingAgent(ai_provider).teach, task)
        except MiraProviderError as exc:
            OrchestrationRepository.update_state(
                db, record, "TEACHING_FAILED", "mira_provider_failed"
            )
            raise TeachingProviderFailure(str(exc)) from exc
        except MiraResponseError as exc:
            OrchestrationRepository.update_state(
                db, record, "TEACHING_FAILED", "mira_response_invalid"
            )
            raise TeachingOutputInvalid(str(exc)) from exc

        try:
            result_record = TeachingResultRepository.create_if_missing(
                db,
                session_id=session_id,
                orchestration_id=record.id,
                concept=response.concept,
                response_json=response.model_dump_json(),
                learner_level=response.learner_level,
                attempt_number=ClarioAIOrchestrator._active_attempt(plan),
            )
        except SQLAlchemyError as exc:
            db.rollback()
            OrchestrationRepository.update_state(
                db, record, "TEACHING_FAILED", "teaching_persistence_failed"
            )
            raise TeachingPersistenceFailure(
                "Mira's teaching result could not be persisted."
            ) from exc

        persisted_response = MiraTeachingResponse.model_validate_json(
            result_record.response_json
        )
        OrchestrationRepository.update_state(
            db,
            record,
            "TEACHING_READY",
            "teaching_response_received",
        )
        return ClarioAIOrchestrator._context(
            record, package, persisted_response, result_record.id
        )

    @staticmethod
    def get_teaching_result(
        db: Session, session_id: str
    ) -> Optional[MiraTeachingResponse]:
        result = TeachingResultRepository.get_by_session_id(db, session_id)
        if not result:
            return None
        return MiraTeachingResponse.model_validate_json(result.response_json)

    @staticmethod
    async def request_thinking(
        db: Session,
        session_id: str,
        ai_provider: BaseAIProvider,
    ) -> ClarioOrchestrationContext:
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        if not record:
            raise CalaPlanRequiredError(
                "Initialize CLARIO-AI orchestration before requesting thinking."
            )
        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        if not plan_record or plan_record.id != record.cala_plan_id:
            raise ThinkingPrerequisiteError("The session's CALA plan is unavailable.")
        plan = CalaResult.model_validate_json(plan_record.plan_json)
        active_concept = ClarioAIOrchestrator._active_concept(plan)
        attempt_number = ClarioAIOrchestrator._active_attempt(plan)
        existing_result = ThinkingResultRepository.get_by_session_and_attempt(
            db, session_id, attempt_number
        )
        if existing_result:
            if (
                active_concept is None
                or existing_result.concept.casefold()
                != active_concept.title.casefold()
            ):
                raise ThinkingPrerequisiteError(
                    "The persisted Ayan result belongs to a different active concept."
                )
            AyanThinkingResponse.model_validate_json(existing_result.response_json)
            return ClarioAIOrchestrator.get_state(db, session_id)
        if record.current_state == "THINKING":
            raise ThinkingInProgressError("Ayan thinking activity is already in progress.")
        if record.current_state not in {"TEACHING_READY", "THINKING_FAILED"}:
            raise ThinkingPrerequisiteError(
                "A completed Mira teaching result is required before Ayan can respond."
            )

        package_record = (
            ResearchPackageRepository.get_by_id(db, record.research_package_id)
            if record.research_package_id
            else None
        )
        teaching_record = TeachingResultRepository.get_by_session_and_attempt(
            db, session_id, attempt_number
        )
        if (
            not plan_record
            or plan_record.id != record.cala_plan_id
            or not record.research_package_id
            or not package_record
            or package_record.id != record.research_package_id
            or not teaching_record
            or teaching_record.orchestration_id != record.id
        ):
            raise ThinkingPrerequisiteError(
                "The session's CALA plan, research package, or Mira result is unavailable."
            )

        package = SharedResearchPackage.model_validate_json(package_record.package_json)
        teaching = MiraTeachingResponse.model_validate_json(
            teaching_record.response_json
        )
        try:
            current_concept = ClarioAIOrchestrator._current_concept(plan, package)
        except ResearchPackageRequiredError as exc:
            raise ThinkingPrerequisiteError(str(exc)) from exc
        if (
            plan.session_id != session_id
            or package.session_id != session_id
            or teaching.session_id != session_id
            or teaching.concept.casefold() != current_concept.title.casefold()
            or teaching.concept.casefold() != teaching_record.concept.casefold()
        ):
            raise ThinkingPrerequisiteError(
                "Saved learning context does not match this session."
            )

        sources_by_id = {
            source.source_id: source for source in package.selected_sources
        }
        references: list[MiraSourceReference] = []
        for reference in teaching.source_references:
            source = sources_by_id.get(reference.source_id)
            if source is None or source.url != reference.url:
                raise ThinkingPrerequisiteError(
                    "Mira source references do not match the session research package."
                )
            references.append(
                MiraSourceReference(
                    source_id=source.source_id,
                    title=source.title,
                    url=source.url,
                )
            )
        if not references:
            raise ThinkingPrerequisiteError(
                "Mira's teaching result has no validated research references for Ayan."
            )

        task = AyanCriticalThinkingTask(
            session_id=session_id,
            concept=teaching.concept,
            learning_goal=plan.learning_goal,
            learner_state=plan.learner_state,
            interest=plan.interest,
            current_level=teaching.learner_level,
            mira_teaching_result=teaching,
            research_source_references=references,
            critical_thinking_instruction=(
                "Create one open-ended why/how reasoning prompt for the concept Mira "
                "just taught. Do not assess the learner or make a progression decision."
            ),
        )
        OrchestrationRepository.update_state(
            db, record, "THINKING_REQUESTED", "ayan_task_created"
        )
        OrchestrationRepository.update_state(
            db, record, "THINKING", "ayan_thinking_dispatched"
        )
        try:
            response = await asyncio.to_thread(
                AyanCriticalThinkingAgent(ai_provider).create_activity, task
            )
        except AyanProviderError as exc:
            OrchestrationRepository.update_state(
                db, record, "THINKING_FAILED", "ayan_provider_failed"
            )
            raise ThinkingProviderFailure(str(exc)) from exc
        except AyanResponseError as exc:
            OrchestrationRepository.update_state(
                db, record, "THINKING_FAILED", "ayan_response_invalid"
            )
            raise ThinkingOutputInvalid(str(exc)) from exc

        try:
            result_record = ThinkingResultRepository.create_if_missing(
                db,
                session_id=session_id,
                orchestration_id=record.id,
                concept=response.concept,
                response_json=response.model_dump_json(),
                attempt_number=attempt_number,
            )
        except SQLAlchemyError as exc:
            db.rollback()
            OrchestrationRepository.update_state(
                db, record, "THINKING_FAILED", "thinking_persistence_failed"
            )
            raise ThinkingPersistenceFailure(
                "Ayan's thinking result could not be persisted."
            ) from exc

        persisted_response = AyanThinkingResponse.model_validate_json(
            result_record.response_json
        )
        OrchestrationRepository.update_state(
            db, record, "THINKING_READY", "thinking_response_received"
        )
        return ClarioAIOrchestrator._context(
            record,
            package,
            teaching,
            teaching_record.id,
            persisted_response,
            result_record.id,
        )

    @staticmethod
    def get_thinking_result(
        db: Session, session_id: str
    ) -> Optional[AyanThinkingResponse]:
        result = ThinkingResultRepository.get_by_session_id(db, session_id)
        if not result:
            return None
        return AyanThinkingResponse.model_validate_json(result.response_json)

    @staticmethod
    async def request_practical(
        db: Session,
        session_id: str,
        ai_provider: BaseAIProvider,
    ) -> ClarioOrchestrationContext:
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        if not record:
            raise PracticalPrerequisiteError(
                "Initialize CLARIO-AI orchestration before requesting practice."
            )
        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        if not plan_record or plan_record.id != record.cala_plan_id:
            raise PracticalPrerequisiteError("The session's CALA plan is unavailable.")
        plan = CalaResult.model_validate_json(plan_record.plan_json)
        attempt_number = ClarioAIOrchestrator._active_attempt(plan)
        active_concept = ClarioAIOrchestrator._active_concept(plan)
        existing_result = PracticalResultRepository.get_by_session_and_attempt(
            db, session_id, attempt_number
        )
        if existing_result:
            if (
                active_concept is None
                or existing_result.concept_id != active_concept.concept_id
            ):
                raise PracticalPrerequisiteError(
                    "The persisted Kira result belongs to a different active concept."
                )
            if record.current_state != "PRACTICAL_READY":
                OrchestrationRepository.update_state(
                    db, record, "PRACTICAL_READY", "practical_activity_received"
                )
            return ClarioAIOrchestrator.get_state(db, session_id)
        if record.current_state == "PRACTICAL":
            raise PracticalInProgressError("Kira is already preparing the practice activity.")
        if record.current_state not in {"THINKING_READY", "PRACTICAL_FAILED"}:
            raise PracticalPrerequisiteError(
                "A completed Ayan thinking result is required before Kira can prepare practice."
            )

        package_record = (
            ResearchPackageRepository.get_by_id(db, record.research_package_id)
            if record.research_package_id
            else None
        )
        teaching_record = TeachingResultRepository.get_by_session_and_attempt(
            db, session_id, attempt_number
        )
        thinking_record = ThinkingResultRepository.get_by_session_and_attempt(
            db, session_id, attempt_number
        )
        if (
            not plan_record
            or plan_record.id != record.cala_plan_id
            or not record.research_package_id
            or not package_record
            or package_record.id != record.research_package_id
            or not teaching_record
            or teaching_record.orchestration_id != record.id
            or not thinking_record
            or thinking_record.orchestration_id != record.id
        ):
            raise PracticalPrerequisiteError(
                "The session's CALA plan, research package, Mira result, or Ayan result is unavailable."
            )

        package = SharedResearchPackage.model_validate_json(package_record.package_json)
        teaching = MiraTeachingResponse.model_validate_json(
            teaching_record.response_json
        )
        thinking = AyanThinkingResponse.model_validate_json(
            thinking_record.response_json
        )
        if (
            plan.session_id != session_id
            or package.session_id != session_id
            or teaching.session_id != session_id
            or thinking.session_id != session_id
            or teaching.concept.casefold() != thinking.concept.casefold()
            or teaching.concept.casefold() != thinking_record.concept.casefold()
        ):
            raise PracticalPrerequisiteError(
                "Saved learning context does not match this session."
            )

        try:
            concept = ClarioAIOrchestrator._current_concept(plan, package)
        except ResearchPackageRequiredError as exc:
            raise PracticalPrerequisiteError(str(exc)) from exc
        if teaching.concept.casefold() != concept.title.casefold():
            raise PracticalPrerequisiteError(
                "Mira and Ayan results do not match the current CALA concept."
            )

        sources_by_id = {
            source.source_id: source for source in package.selected_sources
        }
        if any(
            reference.source_id not in sources_by_id
            or sources_by_id[reference.source_id].url != reference.url
            or sources_by_id[reference.source_id].title != reference.title
            for reference in thinking.source_references
        ):
            raise PracticalPrerequisiteError(
                "Ayan source references do not match the session research package."
            )
        research_sources = [
            KiraResearchSource(
                source_id=source.source_id,
                title=source.title,
                snippet=source.snippet,
            )
            for source in package.selected_sources
        ]
        task = KiraTask(
            session_id=session_id,
            orchestration_id=record.id,
            concept_id=concept.concept_id,
            concept_name=concept.title,
            learning_objective=plan.learning_goal,
            teaching_result_reference=KiraTeachingReference(
                result_id=teaching_record.id,
                concept_name=teaching.concept,
                explanation=teaching.explanation,
                key_points=teaching.key_points,
                examples=teaching.examples,
            ),
            thinking_result_reference=KiraThinkingReference(
                result_id=thinking_record.id,
                concept_name=thinking.concept,
                thinking_prompt=thinking.thinking_prompt,
                expected_reasoning_focus=thinking.expected_reasoning_focus,
            ),
            research_source_ids=[source.source_id for source in research_sources],
            research_summary=package.research_summary,
            research_sources=research_sources,
            learner_context=KiraLearnerContext(
                task=plan.task,
                learner_state=plan.learner_state,
                interest=plan.interest,
                learner_level=plan.learner_level,
            ),
            task_instruction=(
                "Create one grounded real-world scenario and practical task for the "
                "current concept. Do not assess the learner or make a learning decision."
            ),
        )
        OrchestrationRepository.update_state(
            db, record, "PRACTICAL_REQUESTED", "kira_task_created"
        )
        OrchestrationRepository.update_state(
            db, record, "PRACTICAL", "kira_practical_dispatched"
        )
        try:
            output = await asyncio.to_thread(
                KiraPracticalAgent(ai_provider).create_activity, task
            )
        except KiraProviderError as exc:
            OrchestrationRepository.update_state(
                db, record, "PRACTICAL_FAILED", "kira_provider_failed"
            )
            raise PracticalProviderFailure(str(exc)) from exc
        except KiraResponseError as exc:
            OrchestrationRepository.update_state(
                db, record, "PRACTICAL_FAILED", "kira_response_invalid"
            )
            raise PracticalOutputInvalid(str(exc)) from exc

        try:
            result_record = PracticalResultRepository.create_if_missing(
                db,
                session_id=session_id,
                orchestration_id=record.id,
                concept_id=output.concept_id,
                scenario=output.scenario,
                practical_task=output.practical_task,
                real_world_context=output.real_world_context,
                expected_action=output.expected_action,
                success_criteria=json.dumps(output.success_criteria),
                difficulty=output.difficulty,
                research_source_ids=json.dumps(output.research_source_ids),
                attempt_number=attempt_number,
            )
        except SQLAlchemyError as exc:
            db.rollback()
            OrchestrationRepository.update_state(
                db, record, "PRACTICAL_FAILED", "practical_persistence_failed"
            )
            raise PracticalPersistenceFailure(
                "Kira's practical activity could not be persisted."
            ) from exc

        OrchestrationRepository.update_state(
            db, record, "PRACTICAL_READY", "practical_activity_received"
        )
        return ClarioAIOrchestrator.get_state(db, session_id)

    @staticmethod
    def get_practical_result(
        db: Session, session_id: str
    ) -> Optional[KiraOutput]:
        result = PracticalResultRepository.get_by_session_id(db, session_id)
        return ClarioAIOrchestrator._practical_output(result) if result else None

    @staticmethod
    def _practical_output(result: PracticalResultRecord) -> KiraOutput:
        created_at = result.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return KiraOutput(
            agent="Kira",
            session_id=result.session_id,
            orchestration_id=result.orchestration_id,
            concept_id=result.concept_id,
            scenario=result.scenario,
            practical_task=result.practical_task,
            real_world_context=result.real_world_context,
            expected_action=result.expected_action,
            success_criteria=json.loads(result.success_criteria),
            difficulty=result.difficulty,
            research_source_ids=json.loads(result.research_source_ids),
            generated_at=created_at,
        )

    @staticmethod
    async def request_quiz(
        db: Session,
        session_id: str,
        ai_provider: BaseAIProvider,
    ) -> ZaynPresentation:
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        if not record:
            raise QuizPrerequisiteError(
                "Initialize CLARIO-AI orchestration before requesting a quiz."
            )
        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        if not plan_record or plan_record.id != record.cala_plan_id:
            raise QuizPrerequisiteError("The session's CALA plan is unavailable.")
        plan = CalaResult.model_validate_json(plan_record.plan_json)
        attempt_number = ClarioAIOrchestrator._active_attempt(plan)
        active_concept = ClarioAIOrchestrator._active_concept(plan)
        existing = QuizResultRepository.get_by_session_and_attempt(
            db, session_id, attempt_number
        )
        if existing:
            if (
                existing.orchestration_id != record.id
                or active_concept is None
                or existing.concept_id != active_concept.concept_id
            ):
                raise QuizPrerequisiteError(
                    "The persisted quiz does not belong to this active concept."
                )
            if record.current_state not in {"QUIZ_READY", "QUIZ_SUBMITTED"}:
                state = "QUIZ_SUBMITTED" if existing.status == "SUBMITTED" else "QUIZ_READY"
                step = "quiz_submitted" if existing.status == "SUBMITTED" else "quiz_ready"
                OrchestrationRepository.update_state(db, record, state, step)
            return ClarioAIOrchestrator.get_quiz_presentation(db, session_id)
        if record.current_state == "QUIZ_GENERATING":
            raise QuizInProgressError("Zayn is already generating this quiz.")
        if record.current_state not in {"PRACTICAL_READY", "QUIZ_FAILED"}:
            raise QuizPrerequisiteError(
                "A completed Kira practical activity is required before Zayn can generate a quiz."
            )

        package_record = (
            ResearchPackageRepository.get_by_id(db, record.research_package_id)
            if record.research_package_id
            else None
        )
        teaching_record = TeachingResultRepository.get_by_session_and_attempt(
            db, session_id, attempt_number
        )
        thinking_record = ThinkingResultRepository.get_by_session_and_attempt(
            db, session_id, attempt_number
        )
        practical_record = PracticalResultRepository.get_by_session_and_attempt(
            db, session_id, attempt_number
        )
        if (
            not plan_record
            or plan_record.id != record.cala_plan_id
            or not record.research_package_id
            or not package_record
            or package_record.id != record.research_package_id
            or not teaching_record
            or teaching_record.orchestration_id != record.id
            or not thinking_record
            or thinking_record.orchestration_id != record.id
            or not practical_record
            or practical_record.orchestration_id != record.id
        ):
            raise QuizPrerequisiteError(
                "The session's CALA, research, teaching, thinking, or practical context is unavailable."
            )

        package = SharedResearchPackage.model_validate_json(package_record.package_json)
        teaching = MiraTeachingResponse.model_validate_json(
            teaching_record.response_json
        )
        thinking = AyanThinkingResponse.model_validate_json(
            thinking_record.response_json
        )
        practical = ClarioAIOrchestrator._practical_output(practical_record)
        if (
            plan.session_id != session_id
            or package.session_id != session_id
            or teaching.session_id != session_id
            or thinking.session_id != session_id
            or practical.session_id != session_id
            or practical.orchestration_id != record.id
        ):
            raise QuizPrerequisiteError(
                "Saved learning context does not match this session."
            )
        try:
            concept = ClarioAIOrchestrator._current_concept(plan, package)
        except ResearchPackageRequiredError as exc:
            raise QuizPrerequisiteError(str(exc)) from exc
        if (
            teaching.concept.casefold() != concept.title.casefold()
            or thinking.concept.casefold() != concept.title.casefold()
            or practical.concept_id != concept.concept_id
        ):
            raise QuizPrerequisiteError(
                "The teaching, thinking, practical activity, and CALA concept do not match."
            )
        valid_source_ids = {source.source_id for source in package.selected_sources}
        if (
            any(
                reference.source_id not in valid_source_ids
                for reference in thinking.source_references
            )
            or any(source_id not in valid_source_ids for source_id in practical.research_source_ids)
        ):
            raise QuizPrerequisiteError(
                "Upstream worker references do not match the session research package."
            )
        difficulty: ZaynDifficulty = {
            "beginner": "EASY",
            "intermediate": "MEDIUM",
            "advanced": "HARD",
        }[plan.learner_level]
        task = ZaynTask(
            session_id=session_id,
            orchestration_id=record.id,
            concept_id=concept.concept_id,
            concept_name=concept.title,
            difficulty=difficulty,
            question_count=5,
            learning_objective=plan.learning_goal,
            teaching_result_reference=ZaynTeachingReference(
                concept_name=teaching.concept,
                explanation=teaching.explanation,
                key_points=teaching.key_points,
            ),
            thinking_result_reference=ZaynThinkingReference(
                concept_name=thinking.concept,
                thinking_prompt=thinking.thinking_prompt,
                expected_reasoning_focus=thinking.expected_reasoning_focus,
            ),
            practical_result_reference=ZaynPracticalReference(
                scenario=practical.scenario,
                practical_task=practical.practical_task,
                real_world_context=practical.real_world_context,
                expected_action=practical.expected_action,
                success_criteria=practical.success_criteria,
            ),
            research_source_ids=sorted(valid_source_ids),
            learner_context=ZaynLearnerContext(
                task=plan.task,
                learner_state=plan.learner_state,
                interest=plan.interest,
            ),
        )
        OrchestrationRepository.update_state(
            db, record, "QUIZ_REQUESTED", "zayn_task_created"
        )
        OrchestrationRepository.update_state(
            db, record, "QUIZ_GENERATING", "zayn_quiz_generation_started"
        )
        try:
            output = await asyncio.to_thread(
                ZaynQuizAgent(ai_provider).create_quiz, task
            )
        except ZaynProviderError as exc:
            OrchestrationRepository.update_state(
                db, record, "QUIZ_FAILED", "zayn_provider_failed"
            )
            raise QuizProviderFailure(str(exc)) from exc
        except ZaynResponseError as exc:
            OrchestrationRepository.update_state(
                db, record, "QUIZ_FAILED", "zayn_response_invalid"
            )
            raise QuizOutputInvalid(str(exc)) from exc

        public_questions = [
            {
                "question_id": question.question_id,
                "question": question.question,
                "options": question.options,
                "difficulty": question.difficulty,
                "concept_id": question.concept_id,
            }
            for question in output.questions
        ]
        answer_key = {
            question.question_id: ZaynAnswerKeyEntry(
                correct_answer=question.correct_answer,
                explanation=question.explanation,
            ).model_dump()
            for question in output.questions
        }
        try:
            quiz_record = QuizResultRepository.create_if_missing(
                db,
                session_id=session_id,
                orchestration_id=record.id,
                concept_id=output.concept_id,
                difficulty=output.difficulty,
                time_limit_seconds=output.time_limit_seconds,
                questions_json=json.dumps(public_questions),
                answer_key_json=json.dumps(answer_key),
                attempt_number=attempt_number,
            )
        except SQLAlchemyError as exc:
            db.rollback()
            OrchestrationRepository.update_state(
                db, record, "QUIZ_FAILED", "quiz_persistence_failed"
            )
            raise QuizPersistenceFailure(
                "Zayn's quiz could not be persisted."
            ) from exc
        if (
            quiz_record.orchestration_id != record.id
            or quiz_record.concept_id != concept.concept_id
            or quiz_record.difficulty != difficulty
        ):
            raise QuizPrerequisiteError(
                "An existing quiz does not match the current session context."
            )
        OrchestrationRepository.update_state(db, record, "QUIZ_READY", "quiz_ready")
        return ClarioAIOrchestrator.get_quiz_presentation(db, session_id)

    @staticmethod
    def get_quiz_presentation(
        db: Session, session_id: str, mark_in_progress: bool = True
    ) -> Optional[ZaynPresentation]:
        quiz = QuizResultRepository.get_by_session_id(db, session_id)
        if not quiz:
            return None
        if mark_in_progress and quiz.status == "GENERATED":
            quiz.status = "IN_PROGRESS"
            quiz.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(quiz)
        return ClarioAIOrchestrator._quiz_presentation(quiz)

    @staticmethod
    def _quiz_presentation(quiz) -> ZaynPresentation:
        created_at = quiz.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        questions = json.loads(quiz.questions_json)
        return ZaynPresentation(
            quiz_id=quiz.id,
            session_id=quiz.session_id,
            orchestration_id=quiz.orchestration_id,
            concept_id=quiz.concept_id,
            attempt_number=quiz.attempt_number,
            difficulty=quiz.difficulty,
            time_limit_seconds=quiz.time_limit_seconds,
            questions=questions,
            status=quiz.status,
            created_at=created_at,
        )

    @staticmethod
    def submit_quiz(
        db: Session,
        session_id: str,
        request: ZaynSubmissionRequest,
    ) -> ZaynSubmissionResponse:
        quiz = QuizResultRepository.get_by_id(db, request.quiz_id)
        if not quiz or quiz.session_id != session_id:
            raise QuizPrerequisiteError("Quiz not found for this learning session.")
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        practical_record = PracticalResultRepository.get_by_session_id(db, session_id)
        if (
            not record
            or quiz.orchestration_id != record.id
            or not practical_record
            or practical_record.orchestration_id != record.id
        ):
            raise QuizPrerequisiteError(
                "Quiz does not belong to the current session orchestration."
            )
        questions = json.loads(quiz.questions_json)
        expected_ids = {question["question_id"] for question in questions}
        answer_ids = set(request.answers)
        if answer_ids != expected_ids:
            invalid = answer_ids - expected_ids
            missing = expected_ids - answer_ids
            detail = []
            if invalid:
                detail.append(f"Unknown question IDs: {', '.join(sorted(invalid))}.")
            if missing:
                detail.append(f"Missing answers for: {', '.join(sorted(missing))}.")
            raise InvalidQuizSubmissionError(" ".join(detail))
        options_by_id = {
            question["question_id"]: question["options"] for question in questions
        }
        if any(
            answer not in options_by_id[question_id]
            for question_id, answer in request.answers.items()
        ):
            raise InvalidQuizSubmissionError(
                "Each submitted answer must match one of that question's options."
            )
        submitted_answers_json = json.dumps(request.answers, sort_keys=True)
        if quiz.status == "SUBMITTED":
            if quiz.submitted_answers_json != submitted_answers_json:
                raise QuizSubmissionConflict(
                    "This quiz was already submitted with different answers."
                )
            return ZaynSubmissionResponse(
                quiz_id=quiz.id,
                status="SUBMITTED",
                submitted_at=quiz.submitted_at or quiz.updated_at,
            )
        answer_key = json.loads(quiz.answer_key_json)
        correctness = {
            question_id: answer == answer_key[question_id]["correct_answer"]
            for question_id, answer in request.answers.items()
        }
        submitted_at = datetime.now(timezone.utc)
        quiz.status = "SUBMITTED"
        quiz.submitted_answers_json = submitted_answers_json
        quiz.correctness_json = json.dumps(correctness, sort_keys=True)
        quiz.submitted_at = submitted_at
        quiz.updated_at = submitted_at
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise QuizPersistenceFailure(
                "Quiz answers could not be recorded."
            ) from exc
        OrchestrationRepository.update_state(
            db, record, "QUIZ_SUBMITTED", "quiz_submitted"
        )
        return ZaynSubmissionResponse(
            quiz_id=quiz.id,
            status="SUBMITTED",
            submitted_at=submitted_at,
        )

    @staticmethod
    async def request_evaluation(
        db: Session,
        session_id: str,
        ai_provider: BaseAIProvider,
    ) -> ElaraOutput:
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        if not record:
            raise EvaluationPrerequisiteError(
                "Initialize CLARIO-AI orchestration before requesting evaluation."
            )

        quiz = QuizResultRepository.get_by_session_id(db, session_id)
        existing = ElaraEvaluationRepository.get_by_session_id(db, session_id)
        if existing:
            if (
                not quiz
                or existing.orchestration_id != record.id
                or existing.concept_id != quiz.concept_id
            ):
                raise EvaluationPrerequisiteError(
                    "The saved evaluation does not match this session's quiz."
                )
            if existing.quiz_result_id == quiz.id:
                if record.current_state != "EVALUATION_READY":
                    OrchestrationRepository.update_state(
                        db, record, "EVALUATION_READY", "evaluation_ready"
                    )
                return ElaraOutput.model_validate_json(existing.evaluation_json)

        if record.current_state == "EVALUATING":
            raise EvaluationInProgressError("Elara is already evaluating this cycle.")
        if not quiz or quiz.status != "SUBMITTED":
            raise EvaluationPrerequisiteError(
                "A submitted Zayn quiz is required before Elara can evaluate."
            )

        teaching_record = TeachingResultRepository.get_by_session_and_attempt(
            db, session_id, quiz.attempt_number
        )
        thinking_record = ThinkingResultRepository.get_by_session_and_attempt(
            db, session_id, quiz.attempt_number
        )
        practical_record = PracticalResultRepository.get_by_session_and_attempt(
            db, session_id, quiz.attempt_number
        )
        if quiz.attempt_number > 1:
            teaching_record = teaching_record or TeachingResultRepository.get_by_session_and_attempt(
                db, session_id, quiz.attempt_number - 1
            )
            thinking_record = thinking_record or ThinkingResultRepository.get_by_session_and_attempt(
                db, session_id, quiz.attempt_number - 1
            )
            practical_record = practical_record or PracticalResultRepository.get_by_session_and_attempt(
                db, session_id, quiz.attempt_number - 1
            )
        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        package_record = (
            ResearchPackageRepository.get_by_id(db, record.research_package_id)
            if record.research_package_id
            else None
        )
        if (
            not plan_record
            or plan_record.id != record.cala_plan_id
            or not package_record
            or package_record.id != record.research_package_id
            or not teaching_record
            or not thinking_record
            or not practical_record
            or any(
                result.session_id != session_id
                or result.orchestration_id != record.id
                for result in (teaching_record, thinking_record, practical_record)
            )
            or practical_record.concept_id != quiz.concept_id
            or quiz.session_id != session_id
            or quiz.orchestration_id != record.id
        ):
            raise EvaluationPrerequisiteError(
                "The session's CALA, teaching, thinking, practical, or quiz result is unavailable."
            )

        try:
            plan = CalaResult.model_validate_json(plan_record.plan_json)
            teaching = MiraTeachingResponse.model_validate_json(
                teaching_record.response_json
            )
            thinking = AyanThinkingResponse.model_validate_json(
                thinking_record.response_json
            )
            practical = ClarioAIOrchestrator._practical_output(practical_record)
            package = SharedResearchPackage.model_validate_json(
                package_record.package_json
            )
            questions = json.loads(quiz.questions_json)
            answer_key = json.loads(quiz.answer_key_json)
            submitted_answers = json.loads(quiz.submitted_answers_json or "{}")
            persisted_correctness = json.loads(quiz.correctness_json or "{}")
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise EvaluationPrerequisiteError(
                "Persisted learning evidence is malformed and cannot be evaluated."
            ) from exc

        if (
            plan.session_id != session_id
            or package.session_id != session_id
            or teaching.session_id != session_id
            or thinking.session_id != session_id
            or practical.session_id != session_id
            or practical.orchestration_id != record.id
            or teaching.concept.casefold() != thinking.concept.casefold()
            or practical.concept_id != quiz.concept_id
        ):
            raise EvaluationPrerequisiteError(
                "Saved learner evidence does not match this session's orchestration."
            )
        try:
            concept = ClarioAIOrchestrator._current_concept(plan, package)
        except (ResearchPackageRequiredError, ValueError) as exc:
            raise EvaluationPrerequisiteError(
                "The saved CALA concept or research context is unavailable."
            ) from exc
        if (
            teaching.concept.casefold() != concept.title.casefold()
            or thinking.concept.casefold() != concept.title.casefold()
            or practical.concept_id != concept.concept_id
            or quiz.concept_id != concept.concept_id
        ):
            raise EvaluationPrerequisiteError(
                "Teaching, thinking, practical, and quiz evidence must match the current concept."
            )

        question_ids = {
            question.get("question_id")
            for question in questions
            if isinstance(question, dict)
        }
        if (
            len(question_ids) != len(questions)
            or None in question_ids
            or set(answer_key) != question_ids
            or not set(submitted_answers).issubset(question_ids)
            or set(persisted_correctness) != set(submitted_answers)
        ):
            raise EvaluationPrerequisiteError(
                "The submitted quiz evidence does not match its persisted questions."
            )
        for question in questions:
            question_id = question["question_id"]
            answer_entry = answer_key[question_id]
            if (
                not isinstance(answer_entry, dict)
                or answer_entry.get("correct_answer") not in question.get("options", [])
                or (
                    question_id in submitted_answers
                    and submitted_answers[question_id] not in question.get("options", [])
                )
                or (
                    question_id in submitted_answers
                    and persisted_correctness.get(question_id)
                    != (
                        submitted_answers[question_id]
                        == answer_entry.get("correct_answer")
                    )
                )
            ):
                raise EvaluationPrerequisiteError(
                    "The quiz answer key or submitted answer is invalid."
                )

        total_questions = len(questions)
        answered_questions = len(submitted_answers)
        correct_answers = sum(
            submitted_answers[question_id] == answer_key[question_id]["correct_answer"]
            for question_id in submitted_answers
        )
        incorrect_answers = answered_questions - correct_answers
        performance = ElaraQuizPerformance(
            quiz_result_id=quiz.id,
            difficulty=quiz.difficulty,
            total_questions=total_questions,
            answered_questions=answered_questions,
            unanswered_questions=total_questions - answered_questions,
            correct_answers=correct_answers,
            incorrect_answers=incorrect_answers,
            accuracy=(
                round(correct_answers / answered_questions * 100, 2)
                if answered_questions
                else 0.0
            ),
        )
        task = ElaraTask(
            session_id=session_id,
            orchestration_id=record.id,
            concept_id=concept.concept_id,
            concept_name=concept.title,
            teaching_result_reference=ElaraTeachingReference(
                result_id=teaching_record.id,
                concept_name=teaching.concept,
                learning_objective=concept.description or plan.learning_goal,
                explanation=teaching.explanation,
                key_points=teaching.key_points,
            ),
            thinking_result_reference=ElaraThinkingReference(
                result_id=thinking_record.id,
                concept_name=thinking.concept,
                thinking_prompt=thinking.thinking_prompt,
                expected_reasoning_focus=thinking.expected_reasoning_focus,
            ),
            practical_result_reference=ElaraPracticalReference(
                result_id=practical_record.id,
                concept_id=practical.concept_id,
                scenario=practical.scenario,
                practical_task=practical.practical_task,
                real_world_context=practical.real_world_context,
                expected_action=practical.expected_action,
                success_criteria=practical.success_criteria,
            ),
            quiz_result_reference=ElaraQuizReference(performance=performance),
            learner_context=ElaraLearnerContext(
                task=plan.task,
                goal=plan.learning_goal,
                learner_state=plan.learner_state,
                interest=plan.interest,
                learner_level=plan.learner_level,
            ),
        )

        OrchestrationRepository.update_state(
            db, record, "EVALUATION_REQUESTED", "elara_task_created"
        )
        OrchestrationRepository.update_state(
            db, record, "EVALUATING", "elara_evaluation_started"
        )
        try:
            output = await asyncio.to_thread(
                ElaraEvaluationAgent(ai_provider).evaluate, task
            )
        except ElaraProviderError as exc:
            OrchestrationRepository.update_state(
                db, record, "EVALUATION_FAILED", "elara_provider_failed"
            )
            raise EvaluationProviderFailure(str(exc)) from exc
        except ElaraResponseError as exc:
            OrchestrationRepository.update_state(
                db, record, "EVALUATION_FAILED", "elara_response_invalid"
            )
            raise EvaluationOutputInvalid(str(exc)) from exc

        if (
            output.session_id != session_id
            or output.orchestration_id != record.id
            or output.concept_id != concept.concept_id
            or output.concept_name != concept.title
            or output.quiz_performance != performance
            or output.thinking_evidence != "unavailable"
            or output.practical_evidence != "unavailable"
        ):
            OrchestrationRepository.update_state(
                db, record, "EVALUATION_FAILED", "elara_response_invalid"
            )
            raise EvaluationOutputInvalid(
                "Elara returned evaluation evidence that does not match persisted session data."
            )

        try:
            evaluation_record = ElaraEvaluationRepository.create_if_missing(
                db,
                session_id=session_id,
                orchestration_id=record.id,
                concept_id=concept.concept_id,
                quiz_result_id=quiz.id,
                concept_name=concept.title,
                quiz_performance_json=performance.model_dump_json(),
                concept_strength=output.concept_strength,
                concept_weakness=output.concept_weakness,
                overall_evaluation=output.overall_evaluation,
                confidence=output.confidence,
                difficulty_signal=output.difficulty_signal,
                evidence_summary=output.evidence_summary,
                evaluation_json=output.model_dump_json(),
                evaluated_at=output.evaluated_at,
                attempt_number=quiz.attempt_number,
            )
        except SQLAlchemyError as exc:
            db.rollback()
            OrchestrationRepository.update_state(
                db, record, "EVALUATION_FAILED", "evaluation_persistence_failed"
            )
            raise EvaluationPersistenceFailure(
                "Elara's evaluation could not be persisted."
            ) from exc
        if (
            evaluation_record.orchestration_id != record.id
            or evaluation_record.concept_id != concept.concept_id
            or evaluation_record.quiz_result_id != quiz.id
        ):
            OrchestrationRepository.update_state(
                db, record, "EVALUATION_FAILED", "evaluation_persistence_failed"
            )
            raise EvaluationPersistenceFailure(
                "A saved evaluation belongs to different learning evidence."
            )
        OrchestrationRepository.update_state(
            db, record, "EVALUATION_READY", "evaluation_ready"
        )
        return ElaraOutput.model_validate_json(evaluation_record.evaluation_json)

    @staticmethod
    def get_evaluation(
        db: Session, session_id: str
    ) -> Optional[ElaraOutput]:
        result = ElaraEvaluationRepository.get_by_session_id(db, session_id)
        return ElaraOutput.model_validate_json(result.evaluation_json) if result else None

    @staticmethod
    def request_decision(
        db: Session, session_id: str
    ) -> AdaptiveDecision:
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        if not record:
            raise DecisionPrerequisiteError(
                "Initialize CLARIO-AI orchestration before requesting a decision."
            )
        evaluation_record = ElaraEvaluationRepository.get_by_session_id(
            db, session_id
        )
        if not evaluation_record:
            raise DecisionPrerequisiteError(
                "A persisted Elara evaluation is required before deciding."
            )

        existing_decision = AdaptiveDecisionRepository.get_by_session_and_evaluation(
            db, session_id, evaluation_record.id
        )
        if existing_decision:
            if (
                existing_decision.orchestration_id != record.id
                or existing_decision.concept_id != evaluation_record.concept_id
            ):
                raise DecisionPrerequisiteError(
                    "The saved decision does not match this orchestration evaluation."
                )
            if record.current_state != "DECISION_READY":
                OrchestrationRepository.update_state(
                    db, record, "DECISION_READY", "adaptive_decision_persisted"
                )
            return AdaptiveDecision.model_validate_json(
                existing_decision.decision_json
            )

        if record.current_state != "EVALUATION_READY":
            raise DecisionPrerequisiteError(
                "CLARIO-AI can decide only after the evaluation is ready."
            )
        if (
            evaluation_record.session_id != session_id
            or evaluation_record.orchestration_id != record.id
        ):
            raise DecisionPrerequisiteError(
                "The Elara evaluation does not belong to this session orchestration."
            )

        try:
            evaluation = ElaraOutput.model_validate_json(
                evaluation_record.evaluation_json
            )
            performance = ElaraQuizPerformance.model_validate_json(
                evaluation_record.quiz_performance_json
            )
            plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
            if not plan_record or plan_record.id != record.cala_plan_id:
                raise DecisionPrerequisiteError(
                    "The persisted CALA roadmap is unavailable."
                )
            plan = CalaResult.model_validate_json(plan_record.plan_json)
        except (TypeError, ValueError) as exc:
            raise DecisionPrerequisiteError(
                "Persisted evaluation or roadmap data is invalid."
            ) from exc

        if (
            evaluation.session_id != session_id
            or evaluation.orchestration_id != record.id
            or evaluation.concept_id != evaluation_record.concept_id
            or performance.quiz_result_id != evaluation_record.quiz_result_id
            or evaluation.quiz_performance != performance
        ):
            raise DecisionPrerequisiteError(
                "Evaluation data does not match its persisted session references."
            )

        current_performance = (
            SessionConceptPerformanceRepository.get_by_session_and_concept(
                db, session_id, evaluation.concept_id
            )
        )
        prior_status = (
            current_performance.mastery_status if current_performance else None
        )
        current_difficulty: ZaynDifficulty = (
            current_performance.current_difficulty
            if current_performance
            else performance.difficulty
        )
        assessment = decide_concept_outcome(
            evaluation, current_difficulty, prior_status
        )
        attempt_count = (
            current_performance.attempt_count + 1 if current_performance else 1
        )
        remediation_count = (
            current_performance.remediation_count if current_performance else 0
        )
        if assessment.remediation_required and assessment.decision in {
            "RETEACH",
            "REDUCE_DIFFICULTY",
        }:
            remediation_count += 1

        if current_performance is None:
            current_performance = SessionConceptPerformanceRecord(
                session_id=session_id,
                orchestration_id=record.id,
                concept_id=evaluation.concept_id,
                concept_name=evaluation.concept_name,
                current_difficulty=assessment.next_difficulty,
                mastery_status=assessment.mastery_status,
                strength=evaluation.concept_strength,
                weakness=evaluation.concept_weakness,
                evaluation_confidence=evaluation.confidence,
                quiz_accuracy=performance.accuracy,
                attempt_count=attempt_count,
                remediation_count=remediation_count,
                last_evaluation_id=evaluation_record.id,
            )
        else:
            current_performance.orchestration_id = record.id
            current_performance.concept_name = evaluation.concept_name
            current_performance.current_difficulty = assessment.next_difficulty
            current_performance.mastery_status = assessment.mastery_status
            current_performance.strength = evaluation.concept_strength
            current_performance.weakness = evaluation.concept_weakness
            current_performance.evaluation_confidence = evaluation.confidence
            current_performance.quiz_accuracy = performance.accuracy
            current_performance.attempt_count = attempt_count
            current_performance.remediation_count = remediation_count
            current_performance.last_evaluation_id = evaluation_record.id

        selected_action = assessment.decision
        reason = assessment.reason
        updated_plan_json: Optional[str] = None
        current_level = ClarioAIOrchestrator._active_level(plan)
        active_concept = ClarioAIOrchestrator._active_concept(plan)
        if (
            current_level is None
            or not current_level.is_unlocked
            or active_concept is None
            or active_concept.concept_id != evaluation.concept_id
        ):
            raise DecisionPrerequisiteError(
                "The evaluation does not match the active roadmap concept."
            )
        if assessment.mastery_status == "mastered" and current_level:
            concepts = ClarioAIOrchestrator._level_concepts(current_level)
            concept_ids = {concept.concept_id for concept in concepts}
            existing_performances = {
                item.concept_id: item.mastery_status
                for item in SessionConceptPerformanceRepository.list_by_session_id(
                    db, session_id
                )
            }
            existing_performances[evaluation.concept_id] = "mastered"
            level_complete = bool(concept_ids) and all(
                existing_performances.get(concept_id) == "mastered"
                for concept_id in concept_ids
            )
            if level_complete:
                later_levels = [
                    level
                    for level in plan.roadmap
                    if level.order > current_level.order and level.topics
                ]
                current_level.completion_state = "completed"
                current_level.level_state = "LEVEL_COMPLETED"
                if plan.curriculum_complete and not later_levels:
                    selected_action = "COMPLETE_GOAL"
                    reason = (
                        "Every required concept in the final generated roadmap level "
                        "is mastered; no later goal curriculum remains."
                    )
                else:
                    selected_action = "COMPLETE_LEVEL"
                    reason = (
                        "Every required concept in this roadmap level is mastered. "
                        "CLARIO-AI will validate or generate the remaining goal "
                        "curriculum before unlocking only the immediate next level."
                    )
                plan.progression_history.append(
                    LevelProgressionEvent(
                        action=selected_action,
                        level_id=current_level.level_id,
                        concept_id=evaluation.concept_id,
                        reason=reason,
                        occurred_at=datetime.now(timezone.utc),
                    )
                )
                updated_plan_json = plan.model_dump_json()

        decision = AdaptiveDecision(
            session_id=session_id,
            orchestration_id=record.id,
            level_id=current_level.level_id if current_level else None,
            concept_id=evaluation.concept_id,
            decision=selected_action,
            mastery_status=assessment.mastery_status,
            current_difficulty=assessment.current_difficulty,
            next_difficulty=assessment.next_difficulty,
            reason=reason,
            evaluation_reference=evaluation_record.id,
            remediation_required=assessment.remediation_required,
            decided_at=datetime.now(timezone.utc),
        )
        try:
            OrchestrationRepository.update_state(
                db, record, "DECISION_REQUESTED", "clario_decision_requested"
            )
            OrchestrationRepository.update_state(
                db, record, "DECIDING", "clario_decision_started"
            )
        except SQLAlchemyError as exc:
            db.rollback()
            OrchestrationRepository.update_state(
                db, record, "DECISION_FAILED", "clario_decision_failed"
            )
            raise DecisionPersistenceFailure(
                "CLARIO-AI could not persist the adaptive-decision state."
            ) from exc
        try:
            if updated_plan_json is not None:
                plan_record.plan_json = updated_plan_json
                db.add(plan_record)
            SessionConceptPerformanceRepository.stage(db, current_performance)
            persisted_decision = AdaptiveDecisionRepository.create_if_missing(
                db,
                session_id=session_id,
                orchestration_id=record.id,
                concept_id=evaluation.concept_id,
                level_id=current_level.level_id if current_level else None,
                evaluation_id=evaluation_record.id,
                decision=decision.decision,
                mastery_status=decision.mastery_status,
                current_difficulty=decision.current_difficulty,
                next_difficulty=decision.next_difficulty,
                reason=decision.reason,
                remediation_required=decision.remediation_required,
                decision_json=decision.model_dump_json(),
            )
            if (
                persisted_decision.orchestration_id != record.id
                or persisted_decision.evaluation_id != evaluation_record.id
                or persisted_decision.concept_id != evaluation.concept_id
            ):
                raise SQLAlchemyError(
                    "The persisted decision does not match the active evaluation."
                )
        except SQLAlchemyError as exc:
            db.rollback()
            OrchestrationRepository.update_state(
                db, record, "DECISION_FAILED", "clario_decision_failed"
            )
            raise DecisionPersistenceFailure(
                "CLARIO-AI's adaptive decision could not be persisted."
            ) from exc
        OrchestrationRepository.update_state(
            db, record, "DECISION_READY", "adaptive_decision_persisted"
        )
        return AdaptiveDecision.model_validate_json(
            persisted_decision.decision_json
        )

    @staticmethod
    async def advance_progression(
        db: Session,
        session_id: str,
        ai_provider: BaseAIProvider,
    ) -> LevelProgressionResult:
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        decision_record = AdaptiveDecisionRepository.get_by_session_id(db, session_id)
        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        if (
            not record
            or not decision_record
            or not plan_record
            or plan_record.id != record.cala_plan_id
        ):
            raise LevelProgressionPrerequisiteError(
                "A saved CLARIO-AI decision and CALA plan are required."
            )
        try:
            decision = AdaptiveDecision.model_validate_json(
                decision_record.decision_json
            )
            plan = CalaResult.model_validate_json(plan_record.plan_json)
        except ValueError as exc:
            raise LevelProgressionPrerequisiteError(
                "Persisted progression context is invalid."
            ) from exc
        if (
            decision.session_id != session_id
            or decision.orchestration_id != record.id
            or decision.concept_id != decision_record.concept_id
            or plan.session_id != session_id
        ):
            raise LevelProgressionPrerequisiteError(
                "The saved decision does not belong to this session."
            )

        prior_transition = next(
            (
                event
                for event in reversed(plan.progression_history)
                if event.concept_id == decision.concept_id
                and event.action
                in {"CONCEPT_ADVANCED", "UNLOCK_NEXT_LEVEL", "COMPLETE_GOAL"}
            ),
            None,
        )
        if prior_transition:
            return LevelProgressionResult(
                action=prior_transition.action,
                level_id=prior_transition.level_id,
                next_level_id=prior_transition.next_level_id,
                reason=prior_transition.reason,
                plan=plan,
            )
        if record.current_state not in {"DECISION_READY", "DECISION_APPLIED"}:
            raise LevelProgressionPrerequisiteError(
                "Progression can only follow a completed CLARIO-AI decision."
            )
        if decision.decision not in {"CONTINUE", "COMPLETE_LEVEL"}:
            raise LevelProgressionPrerequisiteError(
                "This decision does not authorize curriculum progression."
            )
        current_level = ClarioAIOrchestrator._active_level(plan)
        if (
            current_level is None
            or decision.level_id != current_level.level_id
            or not current_level.is_unlocked
        ):
            raise LevelProgressionPrerequisiteError(
                "The decision does not reference the active unlocked level."
            )
        current_concept = next(
            (
                concept
                for concept in ClarioAIOrchestrator._level_concepts(current_level)
                if concept.concept_id == decision.concept_id
            ),
            None,
        )
        performance = SessionConceptPerformanceRepository.get_by_session_and_concept(
            db, session_id, decision.concept_id
        )
        if current_concept is None or not performance or performance.mastery_status != "mastered":
            raise LevelProgressionPrerequisiteError(
                "The active concept must be mastered before progression."
            )

        if decision.decision == "CONTINUE":
            concepts = ClarioAIOrchestrator._level_concepts(current_level)
            current_index = next(
                index
                for index, concept in enumerate(concepts)
                if concept.concept_id == decision.concept_id
            )
            next_concept = next(
                (
                    concept
                    for concept in concepts[current_index + 1 :]
                    if (
                        (concept_performance := (
                            SessionConceptPerformanceRepository.get_by_session_and_concept(
                                db, session_id, concept.concept_id
                            )
                        ))
                        is None
                        or concept_performance.mastery_status != "mastered"
                    )
                ),
                None,
            )
            if next_concept is None:
                raise LevelProgressionPrerequisiteError(
                    "There is no unmastered concept remaining in this level."
                )
            latest_quiz = QuizResultRepository.get_by_session_id(db, session_id)
            plan.active_concept_id = next_concept.concept_id
            plan.active_attempt_number = (
                latest_quiz.attempt_number + 1 if latest_quiz else 1
            )
            current_level.completion_state = "in_progress"
            current_level.level_state = "LEVEL_ENTERED"
            reason = (
                "The mastered concept remains in history; CLARIO-AI activated the "
                "next unmastered concept in the same level."
            )
            plan.progression_history.append(
                LevelProgressionEvent(
                    action="CONCEPT_ADVANCED",
                    level_id=current_level.level_id,
                    concept_id=decision.concept_id,
                    next_level_id=next_concept.concept_id,
                    reason=reason,
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            action = "CONCEPT_ADVANCED"
            record.current_state = "LEVEL_ENTERED"
            record.current_step = "level_concept_advanced"
            record.research_package_id = None
            plan_record.plan_json = plan.model_dump_json()
            db.add(plan_record)
            db.add(record)
            db.commit()
            return LevelProgressionResult(
                action=action,
                level_id=current_level.level_id,
                next_level_id=next_concept.concept_id,
                reason=reason,
                plan=plan,
            )

        if current_level.completion_state != "completed":
            raise LevelProgressionPrerequisiteError(
                "The current level has not met its completion requirements."
            )
        plan.roadmap = [
            level
            for level in plan.roadmap
            if level.topics
            or level.order <= current_level.order
        ]
        later_levels = sorted(
            (
                level
                for level in plan.roadmap
                if level.order > current_level.order and level.topics
            ),
            key=lambda item: item.order,
        )
        if not later_levels and not plan.curriculum_complete:
            performances = [
                {
                    "concept_id": item.concept_id,
                    "concept_name": item.concept_name,
                    "mastery_status": item.mastery_status,
                    "strength": item.strength,
                    "weakness": item.weakness,
                    "evaluation_confidence": item.evaluation_confidence,
                    "quiz_accuracy": item.quiz_accuracy,
                    "attempt_count": item.attempt_count,
                }
                for item in SessionConceptPerformanceRepository.list_by_session_id(
                    db, session_id
                )
            ]
            try:
                generated = await asyncio.to_thread(
                    CalaPlanner.generate_remaining_curriculum,
                    ai_provider,
                    plan,
                    current_level.level_id,
                    performances,
                )
            except (TypeError, ValueError) as exc:
                raise LevelCurriculumOutputInvalid(
                    "CALA returned an invalid remaining curriculum."
                ) from exc
            except RuntimeError as exc:
                raise LevelCurriculumProviderFailure(
                    "CALA could not generate the remaining goal curriculum."
                ) from exc

            existing_concept_titles = {
                concept.title.strip().casefold()
                for level in plan.roadmap
                for concept in ClarioAIOrchestrator._level_concepts(level)
            }
            generated_titles = [
                concept.title.strip().casefold()
                for level in generated.levels
                for topic in level.topics
                for concept in topic.concepts
            ]
            if (
                (not generated.levels and not generated.goal_complete)
                or len(generated_titles) != len(set(generated_titles))
                or existing_concept_titles.intersection(generated_titles)
            ):
                raise LevelCurriculumOutputInvalid(
                    "CALA curriculum must be non-repeating or explicitly complete the goal."
                )

            next_order = current_level.order + 1
            placeholder_levels = sorted(
                (
                    level
                    for level in plan.roadmap
                    if level.order > current_level.order and not level.topics
                ),
                key=lambda item: item.order,
            )
            retained_levels = [
                level
                for level in plan.roadmap
                if level.topics or level.order <= current_level.order
            ]
            plan.roadmap = retained_levels
            for offset, generated_level in enumerate(generated.levels):
                existing_slot = (
                    placeholder_levels[offset]
                    if offset < len(placeholder_levels)
                    else None
                )
                level_order = (
                    existing_slot.order
                    if existing_slot
                    else next_order + offset
                )
                topic_data = [
                    {
                        "title": topic.title,
                        "description": topic.description,
                        "concepts": [
                            {
                                "title": concept.title,
                                "description": concept.description,
                            }
                            for concept in topic.concepts
                        ],
                    }
                    for topic in generated_level.topics
                ]
                persisted_topics = CurriculumRepository.create_generated_level(
                    db, topic_data, level_order, session_id
                )
                roadmap_topics = [
                    RoadmapTopic(
                        topic_id=topic.id,
                        title=topic.title,
                        description=topic.description,
                        order=topic.sequence_order,
                        concepts=[
                            RoadmapConcept(
                                concept_id=concept.id,
                                title=concept.title,
                                description=concept.description,
                                order=concept.sequence_order,
                            )
                            for concept in concepts
                        ],
                    )
                    for topic, concepts in persisted_topics
                ]
                plan.roadmap.append(
                    RoadmapLevel(
                        level_id=(
                            existing_slot.level_id
                            if existing_slot
                            else f"level_{level_order}_{uuid.uuid4().hex[:8]}"
                        ),
                        title=generated_level.title,
                        description=generated_level.description,
                        order=level_order,
                        is_unlocked=False,
                        completion_state="not_started",
                        level_state="LEVEL_LOCKED",
                        prerequisites=[plan.roadmap[-1].level_id],
                        topics=roadmap_topics,
                        owner_session_id=session_id,
                    )
                )
            plan.curriculum_complete = generated.goal_complete
            later_levels = sorted(
                (
                    level
                    for level in plan.roadmap
                    if level.order > current_level.order and level.topics
                ),
                key=lambda item: item.order,
            )

        next_level = later_levels[0] if later_levels else None
        if next_level is not None:
            if next_level.order != current_level.order + 1:
                raise LevelProgressionPrerequisiteError(
                    "The roadmap is missing the immediate next level; level skipping is blocked."
                )
            next_level.is_unlocked = True
            next_level.level_state = "LEVEL_UNLOCKED"
            reason = (
                f"Level {current_level.order} is complete; CLARIO-AI unlocked only "
                f"the immediate next level, {next_level.title}."
            )
            action = "UNLOCK_NEXT_LEVEL"
            plan.progression_history.append(
                LevelProgressionEvent(
                    action=action,
                    level_id=current_level.level_id,
                    concept_id=decision.concept_id,
                    next_level_id=next_level.level_id,
                    reason=reason,
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            decision = decision.model_copy(
                update={"decision": action, "reason": reason}
            )
            decision_record.decision = action
        else:
            if not plan.curriculum_complete:
                raise LevelCurriculumOutputInvalid(
                    "CALA did not provide a next level or confirm that the goal is complete."
                )
            reason = (
                "All generated curriculum levels are complete; no nonexistent "
                "level was unlocked."
            )
            action = "COMPLETE_GOAL"
            plan.progression_history.append(
                LevelProgressionEvent(
                    action=action,
                    level_id=current_level.level_id,
                    concept_id=decision.concept_id,
                    reason=reason,
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            decision = decision.model_copy(
                update={"decision": action, "reason": reason}
            )
            decision_record.decision = action
            record.current_state = "DECISION_APPLIED"
            record.current_step = "curriculum_completed"
        decision_record.reason = reason
        decision_record.decision_json = decision.model_dump_json()
        if next_level is not None:
            record.current_state = "LEVEL_UNLOCKED"
            record.current_step = "next_level_unlocked"
        plan_record.plan_json = plan.model_dump_json()
        db.add(plan_record)
        db.add(decision_record)
        db.add(record)
        db.commit()
        return LevelProgressionResult(
            action=action,
            level_id=current_level.level_id,
            next_level_id=next_level.level_id if next_level else None,
            reason=reason,
            plan=plan,
        )

    @staticmethod
    def enter_level(
        db: Session, session_id: str, level_id: str
    ) -> CalaResult:
        record = OrchestrationRepository.get_by_session_id(db, session_id)
        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        if (
            not record
            or not plan_record
            or plan_record.id != record.cala_plan_id
        ):
            raise LevelProgressionPrerequisiteError(
                "Initialize orchestration before entering a roadmap level."
            )
        plan = CalaResult.model_validate_json(plan_record.plan_json)
        level = next(
            (item for item in plan.roadmap if item.level_id == level_id), None
        )
        if level is None or level.owner_session_id not in {None, session_id}:
            raise LevelProgressionPrerequisiteError(
                "The requested level does not belong to this session roadmap."
            )
        if not level.is_unlocked or level.level_state == "LEVEL_LOCKED":
            raise LevelProgressionPrerequisiteError(
                "The requested level is still locked."
            )
        active_level = ClarioAIOrchestrator._active_level(plan)
        if active_level and active_level.level_id == level.level_id:
            if level.level_state in {"LEVEL_ENTERED", "LEVEL_RESEARCH"}:
                return plan
        elif active_level is None or active_level.completion_state != "completed":
            raise LevelProgressionPrerequisiteError(
                "The current level must be completed before entering another level."
            )

        ordered_levels = sorted(plan.roadmap, key=lambda item: item.order)
        previous_levels = [
            item for item in ordered_levels if item.order < level.order
        ]
        next_uncompleted = next(
            (
                item
                for item in ordered_levels
                if item.order > (active_level.order if active_level else 0)
            ),
            None,
        )
        if next_uncompleted is not None and next_uncompleted.level_id != level.level_id:
            raise LevelProgressionPrerequisiteError(
                "Levels must be entered in roadmap order; skipping is not allowed."
            )
        if any(item.completion_state != "completed" for item in previous_levels):
            raise LevelProgressionPrerequisiteError(
                "Every prerequisite level must be completed first."
            )
        concepts = ClarioAIOrchestrator._level_concepts(level)
        if not concepts:
            raise LevelProgressionPrerequisiteError(
                "The unlocked level has no generated concepts."
            )
        performances = {
            item.concept_id: item.mastery_status
            for item in SessionConceptPerformanceRepository.list_by_session_id(
                db, session_id
            )
        }
        active_concept = next(
            (
                concept
                for concept in concepts
                if performances.get(concept.concept_id) != "mastered"
            ),
            None,
        )
        if active_concept is None:
            raise LevelProgressionPrerequisiteError(
                "All concepts in this level are already complete."
            )
        latest_quiz = QuizResultRepository.get_by_session_id(db, session_id)
        plan.current_level_id = level.level_id
        plan.active_concept_id = active_concept.concept_id
        plan.active_attempt_number = (
            latest_quiz.attempt_number + 1 if latest_quiz else 1
        )
        level.completion_state = "in_progress"
        level.level_state = "LEVEL_ENTERED"
        plan.progression_history.append(
            LevelProgressionEvent(
                action="LEVEL_ENTERED",
                level_id=level.level_id,
                concept_id=active_concept.concept_id,
                reason="The learner entered the unlocked level in roadmap order.",
                occurred_at=datetime.now(timezone.utc),
            )
        )
        plan_record.plan_json = plan.model_dump_json()
        record.current_state = "LEVEL_ENTERED"
        record.current_step = "level_entered"
        record.research_package_id = None
        db.add(plan_record)
        db.add(record)
        db.commit()
        return plan

    @staticmethod
    def _maximum_remediation_attempts() -> int:
        configured = os.getenv(
            "CLARIO_MAX_REMEDIATION_ATTEMPTS",
            str(DEFAULT_MAX_REMEDIATION_ATTEMPTS),
        )
        try:
            maximum = int(configured)
        except ValueError as exc:
            raise AdaptiveExecutionConfigurationError(
                "CLARIO_MAX_REMEDIATION_ATTEMPTS must be a positive integer."
            ) from exc
        if maximum < 1:
            raise AdaptiveExecutionConfigurationError(
                "CLARIO_MAX_REMEDIATION_ATTEMPTS must be a positive integer."
            )
        return maximum

    @staticmethod
    def _concept_by_id(plan: CalaResult, package: SharedResearchPackage, concept_id: str):
        active_level_id = plan.current_level_id or plan.recommended_starting_level
        for level in plan.roadmap:
            for topic in level.topics:
                if (
                    level.level_id != active_level_id
                    or topic.topic_id
                    != package.research_request.current_topic.topic_id
                ):
                    continue
                for item in topic.concepts:
                    if item.concept_id == concept_id:
                        if not any(
                            source.concept_id == concept_id
                            for source in package.research_request.current_topic.concepts
                        ):
                            break
                        return ResearchConcept(
                            concept_id=item.concept_id,
                            title=item.title,
                            description=item.description,
                        )
        raise AdaptiveExecutionPrerequisiteError(
            "The decision concept is not present in this session's saved roadmap and research package."
        )

    @staticmethod
    def _adaptive_execution_output(
        record: OrchestrationRecord,
        execution: AdaptiveExecutionRecord,
        quiz: Optional[ZaynPresentation] = None,
    ) -> AdaptiveExecutionResult:
        return AdaptiveExecutionResult(
            execution_id=execution.id,
            session_id=execution.session_id,
            concept_id=execution.concept_id,
            decision_type=execution.decision_type,
            status=execution.status,
            remediation_context=RemediationContext.model_validate_json(
                execution.remediation_context_json
            ),
            error_message=execution.error_message,
            current_state=record.current_state,
            quiz=quiz,
            updated_at=execution.updated_at,
        )

    @staticmethod
    def _persist_execution_failure(
        db: Session,
        orchestration: OrchestrationRecord,
        execution: AdaptiveExecutionRecord,
        *,
        state: str,
        step: str,
        message: str,
    ) -> None:
        AdaptiveExecutionRepository.update(
            db, execution, status="FAILED", error_message=message
        )
        OrchestrationRepository.update_state(db, orchestration, state, step)

    @staticmethod
    async def execute_decision(
        db: Session,
        session_id: str,
        ai_provider: BaseAIProvider,
    ) -> AdaptiveExecutionResult:
        orchestration = OrchestrationRepository.get_by_session_id(db, session_id)
        if not orchestration:
            raise AdaptiveExecutionPrerequisiteError(
                "Initialize CLARIO-AI orchestration before executing a decision."
            )
        decision_record = AdaptiveDecisionRepository.get_by_session_id(
            db, session_id
        )
        if not decision_record or decision_record.orchestration_id != orchestration.id:
            raise AdaptiveExecutionPrerequisiteError(
                "A persisted decision is required before execution."
            )
        existing = AdaptiveExecutionRepository.get_by_decision_id(
            db, decision_record.id
        )
        if existing:
            if (
                existing.session_id != session_id
                or existing.orchestration_id != orchestration.id
                or existing.concept_id != decision_record.concept_id
            ):
                raise AdaptiveExecutionPrerequisiteError(
                    "The saved execution does not belong to this session decision."
                )
            if existing.status in {
                "AWAITING_SUBMISSION",
                "COMPLETED",
                "LIMIT_REACHED",
                "IN_PROGRESS",
            }:
                quiz = (
                    ClarioAIOrchestrator._quiz_presentation(
                        QuizResultRepository.get_by_session_and_attempt(
                            db, session_id, existing.attempt_number
                        )
                    )
                    if existing.status == "AWAITING_SUBMISSION"
                    and QuizResultRepository.get_by_session_and_attempt(
                        db, session_id, existing.attempt_number
                    )
                    else None
                )
                return ClarioAIOrchestrator._adaptive_execution_output(
                    orchestration, existing, quiz
                )
        elif orchestration.current_state != "DECISION_READY":
            raise AdaptiveExecutionPrerequisiteError(
                "The persisted decision is not ready to execute."
            )

        try:
            decision = AdaptiveDecision.model_validate_json(
                decision_record.decision_json
            )
        except ValueError as exc:
            raise AdaptiveExecutionPrerequisiteError(
                "The persisted decision is invalid."
            ) from exc
        if (
            decision.session_id != session_id
            or decision.orchestration_id != orchestration.id
            or decision.concept_id != decision_record.concept_id
            or decision.evaluation_reference != decision_record.evaluation_id
        ):
            raise AdaptiveExecutionPrerequisiteError(
                "The persisted decision references a different session or concept."
            )
        if not existing and orchestration.current_state != "DECISION_READY":
            raise AdaptiveExecutionPrerequisiteError(
                "The persisted decision is not ready to execute."
            )

        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        package_record = (
            ResearchPackageRepository.get_by_id(
                db, orchestration.research_package_id
            )
            if orchestration.research_package_id
            else None
        )
        source_evaluation = ElaraEvaluationRepository.get_by_id(
            db, decision_record.evaluation_id
        )
        if (
            not plan_record
            or plan_record.id != orchestration.cala_plan_id
            or not package_record
            or package_record.id != orchestration.research_package_id
            or not source_evaluation
            or source_evaluation.session_id != session_id
            or source_evaluation.orchestration_id != orchestration.id
            or source_evaluation.concept_id != decision.concept_id
        ):
            raise AdaptiveExecutionPrerequisiteError(
                "The decision's persisted CALA, research, or evaluation context is unavailable."
            )
        plan = CalaResult.model_validate_json(plan_record.plan_json)
        package = SharedResearchPackage.model_validate_json(
            package_record.package_json
        )
        if plan.session_id != session_id or package.session_id != session_id:
            raise AdaptiveExecutionPrerequisiteError(
                "Saved learning context does not belong to this session."
            )
        concept = ClarioAIOrchestrator._concept_by_id(
            plan, package, decision.concept_id
        )
        if source_evaluation.concept_id != concept.concept_id:
            raise AdaptiveExecutionPrerequisiteError(
                "The Elara evaluation is not for the decision concept."
            )

        teaching_record = TeachingResultRepository.get_by_session_id(
            db, session_id
        )
        thinking_record = ThinkingResultRepository.get_by_session_id(
            db, session_id
        )
        practical_record = PracticalResultRepository.get_by_session_id(
            db, session_id
        )
        if not package.selected_sources or not teaching_record:
            raise AdaptiveExecutionPrerequisiteError(
                "Validated research and previous teaching are required for an adaptive attempt."
            )
        if decision.decision == "RETEST" and (
            not thinking_record or not practical_record
        ):
            raise AdaptiveExecutionPrerequisiteError(
                "Previous thinking and practical results are required for a retest."
            )

        quiz_history = QuizResultRepository.list_by_session_id(db, session_id)
        previous_quiz = quiz_history[-1] if quiz_history else None
        is_reteach = decision.decision in {"RETEACH", "REDUCE_DIFFICULTY"}
        is_retest = decision.decision == "RETEST"
        is_executable_learning_action = is_reteach or is_retest
        if is_executable_learning_action and not previous_quiz:
            raise AdaptiveExecutionPrerequisiteError(
                "A previous quiz is required to create a concept-specific attempt."
            )
        if (
            is_executable_learning_action
            and previous_quiz
            and previous_quiz.concept_id != concept.concept_id
        ):
            raise AdaptiveExecutionPrerequisiteError(
                "The previous quiz does not match the decision concept."
            )
        attempt_number = (
            previous_quiz.attempt_number + 1 if previous_quiz else 1
        )
        if existing:
            attempt_number = existing.attempt_number

        context = RemediationContext(
            session_id=session_id,
            orchestration_id=orchestration.id,
            concept_id=concept.concept_id,
            concept_name=concept.title,
            decision_id=decision_record.id,
            decision_type=decision.decision,
            reason=decision.reason,
            previous_difficulty=decision.current_difficulty,
            new_difficulty=decision.next_difficulty,
            remediation_attempt=attempt_number,
            source_evaluation_id=source_evaluation.id,
        )
        if not existing:
            if is_executable_learning_action:
                maximum = ClarioAIOrchestrator._maximum_remediation_attempts()
                if (
                    AdaptiveExecutionRepository.count_by_session_and_concept(
                        db, session_id, concept.concept_id
                    )
                    >= maximum
                ):
                    execution, created = AdaptiveExecutionRepository.create(
                        db,
                        session_id=session_id,
                        orchestration_id=orchestration.id,
                        concept_id=concept.concept_id,
                        decision_id=decision_record.id,
                        source_evaluation_id=source_evaluation.id,
                        attempt_number=attempt_number,
                        decision_type=decision.decision,
                        status="LIMIT_REACHED",
                        remediation_context_json=context.model_dump_json(),
                    )
                    if not created:
                        return ClarioAIOrchestrator._adaptive_execution_output(
                            orchestration, execution
                        )
                    OrchestrationRepository.update_state(
                        db,
                        orchestration,
                        "REMEDIATION_LIMIT_REACHED",
                        "remediation_attempt_limit_reached",
                    )
                    return ClarioAIOrchestrator._adaptive_execution_output(
                        orchestration, execution
                    )
            execution, created = AdaptiveExecutionRepository.create(
                db,
                session_id=session_id,
                orchestration_id=orchestration.id,
                concept_id=concept.concept_id,
                decision_id=decision_record.id,
                source_evaluation_id=source_evaluation.id,
                attempt_number=attempt_number,
                decision_type=decision.decision,
                status=(
                    "IN_PROGRESS"
                    if is_executable_learning_action
                    else "COMPLETED"
                ),
                remediation_context_json=context.model_dump_json(),
            )
            if not created:
                return ClarioAIOrchestrator._adaptive_execution_output(
                    orchestration, execution
                )
            if not is_executable_learning_action:
                OrchestrationRepository.update_state(
                    db, orchestration, "DECISION_APPLIED", "adaptive_decision_applied"
                )
                return ClarioAIOrchestrator._adaptive_execution_output(
                    orchestration, execution
                )
        else:
            execution = existing
            AdaptiveExecutionRepository.update(
                db, execution, status="IN_PROGRESS", error_message=None
            )

        if is_retest:
            OrchestrationRepository.update_state(
                db, orchestration, "RETEST_REQUESTED", "concept_retest_requested"
            )
        else:
            OrchestrationRepository.update_state(
                db,
                orchestration,
                "REMEDIATION_REQUESTED",
                "concept_remediation_requested",
            )
            OrchestrationRepository.update_state(
                db, orchestration, "REMEDIATING", "concept_remediation_started"
            )

        try:
            if is_reteach:
                previous_teaching = teaching_record
                if not previous_teaching:
                    raise AdaptiveExecutionPrerequisiteError(
                        "A previous teaching result is required for reteaching."
                    )
                previous_teaching_output = MiraTeachingResponse.model_validate_json(
                    previous_teaching.response_json
                )
                learner_profile = LearnerProfileRepository.get_by_user_id(
                    db, SessionRepository.get_session(db, session_id).user_id
                )
                teaching_attempt = TeachingResultRepository.get_by_session_and_attempt(
                    db, session_id, attempt_number
                )
                if teaching_attempt:
                    teaching_output = MiraTeachingResponse.model_validate_json(
                        teaching_attempt.response_json
                    )
                else:
                    OrchestrationRepository.update_state(
                        db, orchestration, "TEACHING_REQUESTED", "mira_remediation_task_created"
                    )
                    OrchestrationRepository.update_state(
                        db, orchestration, "TEACHING", "mira_remediation_dispatched"
                    )
                    teaching_task = MiraTeachingTask(
                        session_id=session_id,
                        task=plan.task,
                        learning_goal=plan.learning_goal,
                        learner_state=plan.learner_state,
                        interest=plan.interest,
                        current_concept=concept,
                        shared_research_package=package,
                        current_level=plan.learner_level,
                        learning_preference=(
                            learner_profile.learning_preference
                            if learner_profile
                            else None
                        ),
                        remediation=MiraRemediationMetadata(
                            reason=decision.reason,
                            weakness_evidence=(
                                f"{source_evaluation.concept_strength}/"
                                f"{source_evaluation.concept_weakness}: "
                                f"{source_evaluation.evidence_summary}"
                            ),
                            previous_explanation=previous_teaching_output.explanation,
                            previous_examples=previous_teaching_output.examples,
                            current_difficulty=decision.next_difficulty,
                            remediation_attempt=attempt_number,
                        ),
                        teaching_instruction=(
                            "Reteach only the target concept. Address the persisted "
                            "weakness using a different explanation strategy and "
                            "new examples; do not repeat the previous teaching."
                        ),
                    )
                    try:
                        teaching_output = await asyncio.to_thread(
                            MiraTeachingAgent(ai_provider).teach, teaching_task
                        )
                    except MiraProviderError as exc:
                        raise AdaptiveExecutionProviderFailure(str(exc)) from exc
                    except MiraResponseError as exc:
                        raise AdaptiveExecutionOutputInvalid(str(exc)) from exc
                    teaching_record = TeachingResultRepository.create_if_missing(
                        db,
                        session_id=session_id,
                        orchestration_id=orchestration.id,
                        concept=teaching_output.concept,
                        response_json=teaching_output.model_dump_json(),
                        learner_level=teaching_output.learner_level,
                        attempt_number=attempt_number,
                    )
                if teaching_output.concept.casefold() != concept.title.casefold():
                    raise AdaptiveExecutionOutputInvalid(
                        "The remediation teaching response changed the target concept."
                    )
                OrchestrationRepository.update_state(
                    db, orchestration, "TEACHING_READY", "remediation_teaching_ready"
                )
            else:
                teaching_output = MiraTeachingResponse.model_validate_json(
                    teaching_record.response_json
                ) if teaching_record else None
            if teaching_output is None:
                raise AdaptiveExecutionPrerequisiteError(
                    "A teaching result is required to continue this attempt."
                )

            if is_reteach:
                thinking_attempt = ThinkingResultRepository.get_by_session_and_attempt(
                    db, session_id, attempt_number
                )
                if thinking_attempt:
                    thinking_output = AyanThinkingResponse.model_validate_json(
                        thinking_attempt.response_json
                    )
                else:
                    OrchestrationRepository.update_state(
                        db, orchestration, "THINKING_REQUESTED", "ayan_remediation_task_created"
                    )
                    OrchestrationRepository.update_state(
                        db, orchestration, "THINKING", "ayan_remediation_dispatched"
                    )
                    source_map = {
                        source.source_id: source
                        for source in package.selected_sources
                    }
                    source_references = []
                    for reference in teaching_output.source_references:
                        source = source_map.get(reference.source_id)
                        if source is None or source.url != reference.url:
                            raise AdaptiveExecutionPrerequisiteError(
                                "Remediation teaching referenced a source outside the session package."
                            )
                        source_references.append(
                            MiraSourceReference(
                                source_id=source.source_id,
                                title=source.title,
                                url=source.url,
                            )
                        )
                    if not source_references:
                        source = package.selected_sources[0]
                        source_references.append(
                            MiraSourceReference(
                                source_id=source.source_id,
                                title=source.title,
                                url=source.url,
                            )
                        )
                    thinking_task = AyanCriticalThinkingTask(
                        session_id=session_id,
                        concept=concept.title,
                        learning_goal=plan.learning_goal,
                        learner_state=plan.learner_state,
                        interest=plan.interest,
                        current_level=teaching_output.learner_level,
                        mira_teaching_result=teaching_output,
                        research_source_references=source_references,
                        critical_thinking_instruction=(
                            "Create a new why/how reasoning prompt that probes the "
                            "specific misconception in this remediation attempt. Do "
                            "not reuse the earlier prompt or decide mastery."
                        ),
                    )
                    try:
                        thinking_output = await asyncio.to_thread(
                            AyanCriticalThinkingAgent(ai_provider).create_activity,
                            thinking_task,
                        )
                    except AyanProviderError as exc:
                        raise AdaptiveExecutionProviderFailure(str(exc)) from exc
                    except AyanResponseError as exc:
                        raise AdaptiveExecutionOutputInvalid(str(exc)) from exc
                    thinking_record = ThinkingResultRepository.create_if_missing(
                        db,
                        session_id=session_id,
                        orchestration_id=orchestration.id,
                        concept=concept.title,
                        response_json=thinking_output.model_dump_json(),
                        attempt_number=attempt_number,
                    )
                OrchestrationRepository.update_state(
                    db, orchestration, "THINKING_READY", "remediation_thinking_ready"
                )
            else:
                thinking_output = (
                    AyanThinkingResponse.model_validate_json(
                        thinking_record.response_json
                    )
                    if thinking_record
                    else None
                )
            if thinking_output is None or not thinking_record:
                raise AdaptiveExecutionPrerequisiteError(
                    "A thinking result is required to continue this attempt."
                )

            if is_reteach:
                practical_attempt = PracticalResultRepository.get_by_session_and_attempt(
                    db, session_id, attempt_number
                )
                if practical_attempt:
                    practical_output = ClarioAIOrchestrator._practical_output(
                        practical_attempt
                    )
                else:
                    OrchestrationRepository.update_state(
                        db, orchestration, "PRACTICAL_REQUESTED", "kira_remediation_task_created"
                    )
                    OrchestrationRepository.update_state(
                        db, orchestration, "PRACTICAL", "kira_remediation_dispatched"
                    )
                    source_refs = {
                        source.source_id: source
                        for source in package.selected_sources
                    }
                    thinking_refs = []
                    for reference in thinking_output.source_references:
                        source = source_refs.get(reference.source_id)
                        if source is None or source.url != reference.url:
                            raise AdaptiveExecutionPrerequisiteError(
                                "Remediation thinking referenced a source outside the session package."
                            )
                        thinking_refs.append(reference)
                    if not thinking_refs:
                        source = package.selected_sources[0]
                        thinking_refs.append(
                            MiraSourceReference(
                                source_id=source.source_id,
                                title=source.title,
                                url=source.url,
                            )
                        )
                    kira_sources = [
                        KiraResearchSource(
                            source_id=source.source_id,
                            title=source.title,
                            snippet=source.snippet,
                        )
                        for source in package.selected_sources
                    ]
                    practical_task = KiraTask(
                        session_id=session_id,
                        orchestration_id=orchestration.id,
                        concept_id=concept.concept_id,
                        concept_name=concept.title,
                        learning_objective=plan.learning_goal,
                        teaching_result_reference=KiraTeachingReference(
                            result_id=teaching_record.id,
                            concept_name=teaching_output.concept,
                            explanation=teaching_output.explanation,
                            key_points=teaching_output.key_points,
                            examples=teaching_output.examples,
                        ),
                        thinking_result_reference=KiraThinkingReference(
                            result_id=thinking_record.id,
                            concept_name=thinking_output.concept,
                            thinking_prompt=thinking_output.thinking_prompt,
                            expected_reasoning_focus=thinking_output.expected_reasoning_focus,
                        ),
                        research_source_ids=[
                            source.source_id for source in kira_sources
                        ],
                        research_summary=package.research_summary,
                        research_sources=kira_sources,
                        learner_context=KiraLearnerContext(
                            task=plan.task,
                            learner_state=plan.learner_state,
                            interest=plan.interest,
                            learner_level=plan.learner_level,
                        ),
                        task_instruction=(
                            "Create a different, real-world practical application "
                            "for this remediation attempt. Keep it specific to the "
                            "target concept and the learner's weak evidence."
                        ),
                    )
                    try:
                        practical_output = await asyncio.to_thread(
                            KiraPracticalAgent(ai_provider).create_activity,
                            practical_task,
                        )
                    except KiraProviderError as exc:
                        raise AdaptiveExecutionProviderFailure(str(exc)) from exc
                    except KiraResponseError as exc:
                        raise AdaptiveExecutionOutputInvalid(str(exc)) from exc
                    previous_practical = (
                        PracticalResultRepository.get_latest_before_attempt(
                            db, session_id, attempt_number
                        )
                    )
                    if previous_practical and (
                        practical_output.scenario.strip().casefold()
                        == previous_practical.scenario.strip().casefold()
                        and practical_output.practical_task.strip().casefold()
                        == previous_practical.practical_task.strip().casefold()
                    ):
                        raise AdaptiveExecutionOutputInvalid(
                            "Kira repeated the previous practical scenario and task."
                        )
                    practical_record = PracticalResultRepository.create_if_missing(
                        db,
                        session_id=session_id,
                        orchestration_id=orchestration.id,
                        concept_id=practical_output.concept_id,
                        scenario=practical_output.scenario,
                        practical_task=practical_output.practical_task,
                        real_world_context=practical_output.real_world_context,
                        expected_action=practical_output.expected_action,
                        success_criteria=json.dumps(
                            practical_output.success_criteria
                        ),
                        difficulty=practical_output.difficulty,
                        research_source_ids=json.dumps(
                            practical_output.research_source_ids
                        ),
                        attempt_number=attempt_number,
                    )
                OrchestrationRepository.update_state(
                    db, orchestration, "PRACTICAL_READY", "remediation_practical_ready"
                )
            else:
                practical_output = (
                    ClarioAIOrchestrator._practical_output(practical_record)
                    if practical_record
                    else None
                )
            if practical_output is None or not practical_record:
                raise AdaptiveExecutionPrerequisiteError(
                    "A practical result is required to generate a quiz."
                )

            existing_quiz = QuizResultRepository.get_by_session_and_attempt(
                db, session_id, attempt_number
            )
            if existing_quiz:
                quiz_record = existing_quiz
            else:
                OrchestrationRepository.update_state(
                    db, orchestration, "QUIZ_REQUESTED", "adaptive_quiz_requested"
                )
                OrchestrationRepository.update_state(
                    db, orchestration, "QUIZ_GENERATING", "zayn_adaptive_quiz_generation_started"
                )
                previous_questions = [
                    question
                    for prior in quiz_history
                    for question in json.loads(prior.questions_json)
                ]
                zayn_task = ZaynTask(
                    session_id=session_id,
                    orchestration_id=orchestration.id,
                    concept_id=concept.concept_id,
                    concept_name=concept.title,
                    difficulty=decision.next_difficulty,
                    question_count=5,
                    learning_objective=plan.learning_goal,
                    teaching_result_reference=ZaynTeachingReference(
                        concept_name=teaching_output.concept,
                        explanation=teaching_output.explanation,
                        key_points=teaching_output.key_points,
                    ),
                    thinking_result_reference=ZaynThinkingReference(
                        concept_name=thinking_output.concept,
                        thinking_prompt=thinking_output.thinking_prompt,
                        expected_reasoning_focus=thinking_output.expected_reasoning_focus,
                    ),
                    practical_result_reference=ZaynPracticalReference(
                        scenario=practical_output.scenario,
                        practical_task=practical_output.practical_task,
                        real_world_context=practical_output.real_world_context,
                        expected_action=practical_output.expected_action,
                        success_criteria=practical_output.success_criteria,
                    ),
                    research_source_ids=[
                        source.source_id for source in package.selected_sources
                    ],
                    learner_context=ZaynLearnerContext(
                        task=plan.task,
                        learner_state=plan.learner_state,
                        interest=plan.interest,
                    ),
                    previous_question_ids=[
                        question["question_id"] for question in previous_questions
                    ],
                    previous_question_texts=[
                        question["question"] for question in previous_questions
                    ],
                )
                try:
                    quiz_output = await asyncio.to_thread(
                        ZaynQuizAgent(ai_provider).create_quiz, zayn_task
                    )
                except ZaynProviderError as exc:
                    raise AdaptiveExecutionProviderFailure(str(exc)) from exc
                except ZaynResponseError as exc:
                    raise AdaptiveExecutionOutputInvalid(str(exc)) from exc
                public_questions = [
                    {
                        "question_id": question.question_id,
                        "question": question.question,
                        "options": question.options,
                        "difficulty": question.difficulty,
                        "concept_id": question.concept_id,
                    }
                    for question in quiz_output.questions
                ]
                answer_key = {
                    question.question_id: ZaynAnswerKeyEntry(
                        correct_answer=question.correct_answer,
                        explanation=question.explanation,
                    ).model_dump()
                    for question in quiz_output.questions
                }
                quiz_record = QuizResultRepository.create_if_missing(
                    db,
                    session_id=session_id,
                    orchestration_id=orchestration.id,
                    concept_id=quiz_output.concept_id,
                    difficulty=quiz_output.difficulty,
                    time_limit_seconds=quiz_output.time_limit_seconds,
                    questions_json=json.dumps(public_questions),
                    answer_key_json=json.dumps(answer_key),
                    attempt_number=attempt_number,
                )
            if quiz_record.concept_id != concept.concept_id:
                raise AdaptiveExecutionOutputInvalid(
                    "The generated challenge changed the target concept."
                )
            OrchestrationRepository.update_state(
                db, orchestration, "QUIZ_READY", "adaptive_quiz_ready"
            )
            AdaptiveExecutionRepository.update(
                db, execution, status="AWAITING_SUBMISSION"
            )
            quiz_presentation = ClarioAIOrchestrator._quiz_presentation(
                quiz_record
            )
            return ClarioAIOrchestrator._adaptive_execution_output(
                orchestration, execution, quiz_presentation
            )
        except AdaptiveExecutionPrerequisiteError as exc:
            state = "RETEST_FAILED" if is_retest else "REMEDIATION_FAILED"
            ClarioAIOrchestrator._persist_execution_failure(
                db,
                orchestration,
                execution,
                state=state,
                step="adaptive_prerequisite_failed",
                message=str(exc),
            )
            raise
        except AdaptiveExecutionProviderFailure as exc:
            state = "RETEST_FAILED" if is_retest else "REMEDIATION_FAILED"
            ClarioAIOrchestrator._persist_execution_failure(
                db,
                orchestration,
                execution,
                state=state,
                step="adaptive_provider_failed",
                message=str(exc),
            )
            raise
        except AdaptiveExecutionOutputInvalid as exc:
            state = "RETEST_FAILED" if is_retest else "REMEDIATION_FAILED"
            ClarioAIOrchestrator._persist_execution_failure(
                db,
                orchestration,
                execution,
                state=state,
                step="adaptive_output_invalid",
                message=str(exc),
            )
            raise
        except SQLAlchemyError as exc:
            db.rollback()
            refreshed_execution = AdaptiveExecutionRepository.get_by_decision_id(
                db, decision_record.id
            )
            if refreshed_execution:
                ClarioAIOrchestrator._persist_execution_failure(
                    db,
                    orchestration,
                    refreshed_execution,
                    state="RETEST_FAILED" if is_retest else "REMEDIATION_FAILED",
                    step="adaptive_persistence_failed",
                    message="An adaptive learning result could not be persisted.",
                )
            raise AdaptiveExecutionPersistenceFailure(
                "Adaptive learning results could not be persisted."
            ) from exc

    @staticmethod
    def get_adaptive_execution(
        db: Session, session_id: str
    ) -> Optional[AdaptiveExecutionResult]:
        orchestration = OrchestrationRepository.get_by_session_id(db, session_id)
        execution = AdaptiveExecutionRepository.get_latest_by_session_id(
            db, session_id
        )
        if not orchestration or not execution:
            return None
        quiz_record = (
            QuizResultRepository.get_by_session_and_attempt(
                db, session_id, execution.attempt_number
            )
            if execution.status == "AWAITING_SUBMISSION"
            else None
        )
        quiz = (
            ClarioAIOrchestrator._quiz_presentation(quiz_record)
            if quiz_record
            else None
        )
        return ClarioAIOrchestrator._adaptive_execution_output(
            orchestration, execution, quiz
        )

    @staticmethod
    def get_decision(
        db: Session, session_id: str
    ) -> Optional[AdaptiveDecision]:
        result = AdaptiveDecisionRepository.get_by_session_id(db, session_id)
        return AdaptiveDecision.model_validate_json(result.decision_json) if result else None

    @staticmethod
    def get_concept_performance(
        db: Session, session_id: str
    ) -> list[SessionConceptPerformance]:
        return [
            ClarioAIOrchestrator._concept_performance_output(record)
            for record in SessionConceptPerformanceRepository.list_by_session_id(
                db, session_id
            )
        ]

    @staticmethod
    def _concept_performance_output(
        record: SessionConceptPerformanceRecord,
    ) -> SessionConceptPerformance:
        return SessionConceptPerformance.model_validate(
            {
                column: getattr(record, column)
                for column in (
                    "id",
                    "session_id",
                    "orchestration_id",
                    "concept_id",
                    "concept_name",
                    "current_difficulty",
                    "mastery_status",
                    "strength",
                    "weakness",
                    "evaluation_confidence",
                    "quiz_accuracy",
                    "attempt_count",
                    "remediation_count",
                    "last_evaluation_id",
                    "created_at",
                    "updated_at",
                )
            }
        )

    @staticmethod
    def _current_concept(plan: CalaResult, package: SharedResearchPackage):
        level = ClarioAIOrchestrator._active_level(plan)
        concept = ClarioAIOrchestrator._active_concept(plan)
        if level is None or not level.is_unlocked or concept is None:
            raise ResearchPackageRequiredError(
                "The saved CALA plan has no current concept for teaching."
            )
        topic = next(
            (
                item
                for item in level.topics
                if any(value.concept_id == concept.concept_id for value in item.concepts)
            ),
            None,
        )
        research_topic = package.research_request.current_topic
        if topic is None or topic.topic_id != research_topic.topic_id:
            raise ResearchPackageRequiredError(
                "Research package topic does not match the CALA plan."
            )
        if not any(
            item.concept_id == concept.concept_id
            for item in research_topic.concepts
        ):
            raise ResearchPackageRequiredError(
                "Research package does not contain the current CALA concept."
            )
        return ResearchConcept(
            concept_id=concept.concept_id,
            title=concept.title,
            description=concept.description,
        )

    @staticmethod
    def _context(
        record: OrchestrationRecord,
        package: Optional[SharedResearchPackage],
        teaching: Optional[MiraTeachingResponse] = None,
        teaching_result_id: Optional[str] = None,
        thinking: Optional[AyanThinkingResponse] = None,
        thinking_result_id: Optional[str] = None,
        practical: Optional[KiraOutput] = None,
        practical_result_id: Optional[str] = None,
        quiz_id: Optional[str] = None,
        quiz_difficulty: Optional[ZaynDifficulty] = None,
        quiz_status: Optional[str] = None,
        evaluation_id: Optional[str] = None,
        evaluation: Optional[ElaraOutput] = None,
        adaptive_decision: Optional[AdaptiveDecision] = None,
        concept_performance: Optional[SessionConceptPerformance] = None,
    ) -> ClarioOrchestrationContext:
        return ClarioOrchestrationContext(
            session_id=record.session_id,
            cala_plan_id=record.cala_plan_id,
            current_state=record.current_state,
            current_step=record.current_step,
            research_package_id=record.research_package_id,
            research_package=package,
            teaching_result_id=teaching_result_id,
            teaching_result=teaching,
            thinking_result_id=thinking_result_id,
            practical_result=practical,
            practical_result_id=practical_result_id,
            quiz_id=quiz_id,
            quiz_difficulty=quiz_difficulty,
            quiz_status=quiz_status,
            evaluation_id=evaluation_id,
            evaluation=evaluation,
            adaptive_decision=adaptive_decision,
            concept_performance=concept_performance,
            thinking_result=thinking,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
