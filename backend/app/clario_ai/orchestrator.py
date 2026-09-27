import asyncio
import json
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
from backend.app.cala.schemas import CalaResult
from backend.app.models.orchestration import OrchestrationRecord
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
from backend.app.schemas.mira import MiraTeachingResponse, MiraTeachingTask
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


class ClarioAIOrchestrator:
    """Owns session workflow transitions and dispatches bounded worker tasks."""

    @staticmethod
    def initialize_from_cala(
        db: Session, session_id: str
    ) -> ClarioOrchestrationContext:
        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        if not plan_record:
            raise CalaPlanRequiredError("Create the CALA plan before orchestration.")

        existing_package = ResearchPackageRepository.get_by_session_id(db, session_id)
        initial_state = "CALA_READY"
        initial_step = "cala_plan_loaded"
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
            package_record = ResearchPackageRepository.get_by_session_id(db, session_id)
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
            ResearchPackageRepository.get_by_session_id(db, session_id)
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
            db, session_id, package.model_dump_json()
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
        existing_result = TeachingResultRepository.get_by_session_id(db, session_id)
        if existing_result:
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

        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        package_record = ResearchPackageRepository.get_by_session_id(db, session_id)
        if (
            not plan_record
            or plan_record.id != record.cala_plan_id
            or not package_record
            or package_record.id != record.research_package_id
        ):
            raise ResearchPackageRequiredError(
                "The session's CALA plan or research package is unavailable."
            )
        plan = CalaResult.model_validate_json(plan_record.plan_json)
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
        existing_result = ThinkingResultRepository.get_by_session_id(db, session_id)
        if existing_result:
            AyanThinkingResponse.model_validate_json(existing_result.response_json)
            return ClarioAIOrchestrator.get_state(db, session_id)
        if record.current_state == "THINKING":
            raise ThinkingInProgressError("Ayan thinking activity is already in progress.")
        if record.current_state not in {"TEACHING_READY", "THINKING_FAILED"}:
            raise ThinkingPrerequisiteError(
                "A completed Mira teaching result is required before Ayan can respond."
            )

        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        package_record = ResearchPackageRepository.get_by_session_id(db, session_id)
        teaching_record = TeachingResultRepository.get_by_session_id(db, session_id)
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

        plan = CalaResult.model_validate_json(plan_record.plan_json)
        package = SharedResearchPackage.model_validate_json(package_record.package_json)
        teaching = MiraTeachingResponse.model_validate_json(
            teaching_record.response_json
        )
        if (
            plan.session_id != session_id
            or package.session_id != session_id
            or teaching.session_id != session_id
            or teaching.concept.casefold()
            != next(
                (
                    concept.title.casefold()
                    for level in plan.roadmap
                    if level.level_id == plan.recommended_starting_level
                    for topic in level.topics[:1]
                    for concept in topic.concepts[:1]
                ),
                None,
            )
            or package.research_request.current_topic.topic_id
            != next(
                (
                    topic.topic_id
                    for level in plan.roadmap
                    if level.level_id == plan.recommended_starting_level
                    for topic in level.topics[:1]
                ),
                None,
            )
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
        existing_result = PracticalResultRepository.get_by_session_id(db, session_id)
        if existing_result:
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

        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        package_record = ResearchPackageRepository.get_by_session_id(db, session_id)
        teaching_record = TeachingResultRepository.get_by_session_id(db, session_id)
        thinking_record = ThinkingResultRepository.get_by_session_id(db, session_id)
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

        plan = CalaResult.model_validate_json(plan_record.plan_json)
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
        existing = QuizResultRepository.get_by_session_id(db, session_id)
        if existing:
            if existing.orchestration_id != record.id:
                raise QuizPrerequisiteError(
                    "The persisted quiz does not belong to this orchestration."
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

        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        package_record = ResearchPackageRepository.get_by_session_id(db, session_id)
        teaching_record = TeachingResultRepository.get_by_session_id(db, session_id)
        thinking_record = ThinkingResultRepository.get_by_session_id(db, session_id)
        practical_record = PracticalResultRepository.get_by_session_id(db, session_id)
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

        plan = CalaResult.model_validate_json(plan_record.plan_json)
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

        existing = ElaraEvaluationRepository.get_by_session_id(db, session_id)
        quiz = QuizResultRepository.get_by_session_id(db, session_id)
        if existing:
            if (
                not quiz
                or existing.orchestration_id != record.id
                or existing.quiz_result_id != quiz.id
                or existing.concept_id != quiz.concept_id
            ):
                raise EvaluationPrerequisiteError(
                    "The saved evaluation does not match this session's quiz."
                )
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

        teaching_record = TeachingResultRepository.get_by_session_id(db, session_id)
        thinking_record = ThinkingResultRepository.get_by_session_id(db, session_id)
        practical_record = PracticalResultRepository.get_by_session_id(db, session_id)
        plan_record = CalaPlanRepository.get_by_session_id(db, session_id)
        package_record = ResearchPackageRepository.get_by_session_id(db, session_id)
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
        current_level = next(
            (
                level
                for level in plan.roadmap
                if level.level_id == plan.recommended_starting_level
                and level.is_unlocked
            ),
            None,
        )
        if assessment.mastery_status == "mastered" and current_level:
            concept_ids = {
                concept.concept_id
                for topic in current_level.topics
                for concept in topic.concepts
            }
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
                later_levels = sorted(
                    (level for level in plan.roadmap if level.order > current_level.order),
                    key=lambda level: level.order,
                )
                if later_levels and later_levels[0].topics:
                    selected_action = "UNLOCK_NEXT_LEVEL"
                    reason = (
                        "Every concept in the current roadmap level is mastered; "
                        "CLARIO-AI unlocked only the next populated level."
                    )
                    roadmap_data = plan.model_dump(mode="json")
                    for level_data in roadmap_data["roadmap"]:
                        if level_data["level_id"] == current_level.level_id:
                            level_data["completion_state"] = "completed"
                        elif level_data["level_id"] == later_levels[0].level_id:
                            level_data["is_unlocked"] = True
                    updated_plan_json = json.dumps(roadmap_data)
                elif not later_levels:
                    selected_action = "COMPLETE_GOAL"
                    reason = (
                        "Every mapped roadmap concept is mastered and the roadmap "
                        "has no later level."
                    )
                    roadmap_data = plan.model_dump(mode="json")
                    for level_data in roadmap_data["roadmap"]:
                        if level_data["level_id"] == current_level.level_id:
                            level_data["completion_state"] = "completed"
                    updated_plan_json = json.dumps(roadmap_data)
                else:
                    selected_action = "COMPLETE_LEVEL"
                    reason = (
                        "Every concept in the current roadmap level is mastered. "
                        "Later roadmap levels have no mapped curriculum to unlock."
                    )
                    roadmap_data = plan.model_dump(mode="json")
                    for level_data in roadmap_data["roadmap"]:
                        if level_data["level_id"] == current_level.level_id:
                            level_data["completion_state"] = "completed"
                    updated_plan_json = json.dumps(roadmap_data)

        decision = AdaptiveDecision(
            session_id=session_id,
            orchestration_id=record.id,
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
        level = next(
            (
                item
                for item in plan.roadmap
                if item.level_id == plan.recommended_starting_level
                and item.is_unlocked
            ),
            None,
        )
        if level is None or not level.topics or not level.topics[0].concepts:
            raise ResearchPackageRequiredError(
                "The saved CALA plan has no current concept for teaching."
            )
        topic = level.topics[0]
        research_topic = package.research_request.current_topic
        if topic.topic_id != research_topic.topic_id:
            raise ResearchPackageRequiredError(
                "Research package topic does not match the CALA plan."
            )
        concept = topic.concepts[0]
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
