from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.app.models.user import User
from backend.app.models.learner import LearnerProfile, ConceptPerformance
from backend.app.models.curriculum import Topic, Concept
from backend.app.models.session import LearningSession, Activity, LearnerResponse, Evaluation
from backend.app.models.mind_profile import MindProfile
from backend.app.models.session_inputs import SessionInputs
from backend.app.models.cala_plan import CalaPlanRecord
from backend.app.models.research_package import ResearchPackageRecord
from backend.app.models.orchestration import OrchestrationRecord
from backend.app.models.teaching_result import TeachingResultRecord
from backend.app.models.thinking_result import ThinkingResultRecord
from backend.app.models.practical_result import PracticalResultRecord
from backend.app.models.quiz_result import QuizResultRecord
from backend.app.models.elara_evaluation import ElaraEvaluationRecord
from backend.app.models.session_concept_performance import (
    SessionConceptPerformanceRecord,
)
from backend.app.models.adaptive_decision import AdaptiveDecisionRecord

class UserRepository:
    @staticmethod
    def create(db: Session, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def update_profile(db: Session, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user


class MindProfileRepository:
    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> Optional[MindProfile]:
        return db.query(MindProfile).filter(MindProfile.user_id == user_id).first()

    @staticmethod
    def create(db: Session, user_id: str, **answers) -> MindProfile:
        profile = MindProfile(user_id=user_id, **answers)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile


class SessionInputsRepository:
    @staticmethod
    def get_by_session_id(db: Session, session_id: str) -> Optional[SessionInputs]:
        return (
            db.query(SessionInputs)
            .filter(SessionInputs.session_id == session_id)
            .first()
        )

    @staticmethod
    def create(db: Session, session_id: str, **inputs) -> SessionInputs:
        session_inputs = SessionInputs(session_id=session_id, **inputs)
        db.add(session_inputs)
        db.commit()
        db.refresh(session_inputs)
        return session_inputs


class CalaPlanRepository:
    @staticmethod
    def get_by_session_id(db: Session, session_id: str) -> Optional[CalaPlanRecord]:
        return (
            db.query(CalaPlanRecord)
            .filter(CalaPlanRecord.session_id == session_id)
            .first()
        )

    @staticmethod
    def create(
        db: Session, session_id: str, plan_json: str
    ) -> CalaPlanRecord:
        record = CalaPlanRecord(session_id=session_id, plan_json=plan_json)
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = CalaPlanRepository.get_by_session_id(db, session_id)
            if existing is None:
                raise
            return existing
        db.refresh(record)
        return record

    @staticmethod
    def stage_plan_update(record: CalaPlanRecord, plan_json: str) -> CalaPlanRecord:
        record.plan_json = plan_json
        return record


class ResearchPackageRepository:
    @staticmethod
    def get_by_session_id(db: Session, session_id: str) -> Optional[ResearchPackageRecord]:
        return (
            db.query(ResearchPackageRecord)
            .filter(ResearchPackageRecord.session_id == session_id)
            .first()
        )

    @staticmethod
    def create(
        db: Session, session_id: str, package_json: str
    ) -> ResearchPackageRecord:
        record = ResearchPackageRecord(
            session_id=session_id,
            package_json=package_json,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = ResearchPackageRepository.get_by_session_id(db, session_id)
            if existing is None:
                raise
            return existing
        db.refresh(record)
        return record


class OrchestrationRepository:
    @staticmethod
    def get_by_session_id(
        db: Session, session_id: str
    ) -> Optional[OrchestrationRecord]:
        return (
            db.query(OrchestrationRecord)
            .filter(OrchestrationRecord.session_id == session_id)
            .first()
        )

    @staticmethod
    def create_if_missing(
        db: Session,
        session_id: str,
        cala_plan_id: str,
        current_state: str,
        current_step: str,
        research_package_id: Optional[str] = None,
    ) -> OrchestrationRecord:
        record = OrchestrationRecord(
            session_id=session_id,
            cala_plan_id=cala_plan_id,
            current_state=current_state,
            current_step=current_step,
            research_package_id=research_package_id,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = OrchestrationRepository.get_by_session_id(db, session_id)
            if existing is None:
                raise
            return existing
        db.refresh(record)
        return record

    @staticmethod
    def update_state(
        db: Session,
        record: OrchestrationRecord,
        current_state: str,
        current_step: str,
        research_package_id: Optional[str] = None,
    ) -> OrchestrationRecord:
        record.current_state = current_state
        record.current_step = current_step
        if research_package_id is not None:
            record.research_package_id = research_package_id
        record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(record)
        return record


class TeachingResultRepository:
    @staticmethod
    def get_by_session_id(
        db: Session, session_id: str
    ) -> Optional[TeachingResultRecord]:
        return (
            db.query(TeachingResultRecord)
            .filter(TeachingResultRecord.session_id == session_id)
            .first()
        )

    @staticmethod
    def create_if_missing(
        db: Session,
        session_id: str,
        orchestration_id: str,
        concept: str,
        response_json: str,
        learner_level: str,
    ) -> TeachingResultRecord:
        record = TeachingResultRecord(
            session_id=session_id,
            orchestration_id=orchestration_id,
            concept=concept,
            response_json=response_json,
            learner_level=learner_level,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = TeachingResultRepository.get_by_session_id(db, session_id)
            if existing is None:
                raise
            return existing
        db.refresh(record)
        return record


class ThinkingResultRepository:
    @staticmethod
    def get_by_session_id(
        db: Session, session_id: str
    ) -> Optional[ThinkingResultRecord]:
        return (
            db.query(ThinkingResultRecord)
            .filter(ThinkingResultRecord.session_id == session_id)
            .first()
        )

    @staticmethod
    def create_if_missing(
        db: Session,
        session_id: str,
        orchestration_id: str,
        concept: str,
        response_json: str,
    ) -> ThinkingResultRecord:
        record = ThinkingResultRecord(
            session_id=session_id,
            orchestration_id=orchestration_id,
            concept=concept,
            response_json=response_json,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = ThinkingResultRepository.get_by_session_id(db, session_id)
            if existing is None:
                raise
            return existing
        db.refresh(record)
        return record


class PracticalResultRepository:
    @staticmethod
    def get_by_session_id(
        db: Session, session_id: str
    ) -> Optional[PracticalResultRecord]:
        return (
            db.query(PracticalResultRecord)
            .filter(PracticalResultRecord.session_id == session_id)
            .first()
        )

    @staticmethod
    def create_if_missing(
        db: Session,
        session_id: str,
        orchestration_id: str,
        concept_id: str,
        scenario: str,
        practical_task: str,
        real_world_context: str,
        expected_action: str,
        success_criteria: str,
        difficulty: str,
        research_source_ids: str,
    ) -> PracticalResultRecord:
        record = PracticalResultRecord(
            session_id=session_id,
            orchestration_id=orchestration_id,
            concept_id=concept_id,
            scenario=scenario,
            practical_task=practical_task,
            real_world_context=real_world_context,
            expected_action=expected_action,
            success_criteria=success_criteria,
            difficulty=difficulty,
            research_source_ids=research_source_ids,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = PracticalResultRepository.get_by_session_id(db, session_id)
            if existing is None:
                raise
            return existing
        db.refresh(record)
        return record


class QuizResultRepository:
    @staticmethod
    def get_by_session_id(db: Session, session_id: str) -> Optional[QuizResultRecord]:
        return (
            db.query(QuizResultRecord)
            .filter(QuizResultRecord.session_id == session_id)
            .first()
        )

    @staticmethod
    def get_by_id(db: Session, quiz_id: str) -> Optional[QuizResultRecord]:
        return db.query(QuizResultRecord).filter(QuizResultRecord.id == quiz_id).first()

    @staticmethod
    def create_if_missing(
        db: Session,
        session_id: str,
        orchestration_id: str,
        concept_id: str,
        difficulty: str,
        time_limit_seconds: int,
        questions_json: str,
        answer_key_json: str,
    ) -> QuizResultRecord:
        record = QuizResultRecord(
            session_id=session_id,
            orchestration_id=orchestration_id,
            concept_id=concept_id,
            difficulty=difficulty,
            time_limit_seconds=time_limit_seconds,
            questions_json=questions_json,
            answer_key_json=answer_key_json,
            status="GENERATED",
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = QuizResultRepository.get_by_session_id(db, session_id)
            if existing is None:
                raise
            return existing
        db.refresh(record)
        return record


class ElaraEvaluationRepository:
    @staticmethod
    def get_by_session_id(
        db: Session, session_id: str
    ) -> Optional[ElaraEvaluationRecord]:
        return (
            db.query(ElaraEvaluationRecord)
            .filter(ElaraEvaluationRecord.session_id == session_id)
            .first()
        )

    @staticmethod
    def create_if_missing(
        db: Session,
        *,
        session_id: str,
        orchestration_id: str,
        concept_id: str,
        quiz_result_id: str,
        concept_name: str,
        quiz_performance_json: str,
        concept_strength: str,
        concept_weakness: str,
        overall_evaluation: str,
        confidence: float,
        difficulty_signal: str,
        evidence_summary: str,
        evaluation_json: str,
        evaluated_at: datetime,
    ) -> ElaraEvaluationRecord:
        record = ElaraEvaluationRecord(
            session_id=session_id,
            orchestration_id=orchestration_id,
            concept_id=concept_id,
            quiz_result_id=quiz_result_id,
            concept_name=concept_name,
            quiz_performance_json=quiz_performance_json,
            concept_strength=concept_strength,
            concept_weakness=concept_weakness,
            overall_evaluation=overall_evaluation,
            confidence=confidence,
            difficulty_signal=difficulty_signal,
            evidence_summary=evidence_summary,
            evaluation_json=evaluation_json,
            evaluated_at=evaluated_at,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = ElaraEvaluationRepository.get_by_session_id(db, session_id)
            if existing is None:
                raise
            return existing
        db.refresh(record)
        return record


class SessionConceptPerformanceRepository:
    @staticmethod
    def get_by_session_and_concept(
        db: Session, session_id: str, concept_id: str
    ) -> Optional[SessionConceptPerformanceRecord]:
        return (
            db.query(SessionConceptPerformanceRecord)
            .filter(
                SessionConceptPerformanceRecord.session_id == session_id,
                SessionConceptPerformanceRecord.concept_id == concept_id,
            )
            .first()
        )

    @staticmethod
    def list_by_session_id(
        db: Session, session_id: str
    ) -> list[SessionConceptPerformanceRecord]:
        return (
            db.query(SessionConceptPerformanceRecord)
            .filter(SessionConceptPerformanceRecord.session_id == session_id)
            .order_by(SessionConceptPerformanceRecord.created_at)
            .all()
        )

    @staticmethod
    def stage(db: Session, record: SessionConceptPerformanceRecord):
        db.add(record)
        return record


class AdaptiveDecisionRepository:
    @staticmethod
    def get_by_session_and_evaluation(
        db: Session, session_id: str, evaluation_id: str
    ) -> Optional[AdaptiveDecisionRecord]:
        return (
            db.query(AdaptiveDecisionRecord)
            .filter(
                AdaptiveDecisionRecord.session_id == session_id,
                AdaptiveDecisionRecord.evaluation_id == evaluation_id,
            )
            .first()
        )

    @staticmethod
    def get_by_session_id(
        db: Session, session_id: str
    ) -> Optional[AdaptiveDecisionRecord]:
        return (
            db.query(AdaptiveDecisionRecord)
            .filter(AdaptiveDecisionRecord.session_id == session_id)
            .order_by(AdaptiveDecisionRecord.created_at.desc())
            .first()
        )

    @staticmethod
    def create_if_missing(
        db: Session,
        *,
        session_id: str,
        orchestration_id: str,
        concept_id: str,
        evaluation_id: str,
        decision: str,
        mastery_status: str,
        current_difficulty: str,
        next_difficulty: str,
        reason: str,
        remediation_required: bool,
        decision_json: str,
    ) -> AdaptiveDecisionRecord:
        record = AdaptiveDecisionRecord(
            session_id=session_id,
            orchestration_id=orchestration_id,
            concept_id=concept_id,
            evaluation_id=evaluation_id,
            decision=decision,
            mastery_status=mastery_status,
            current_difficulty=current_difficulty,
            next_difficulty=next_difficulty,
            reason=reason,
            remediation_required=int(remediation_required),
            decision_json=decision_json,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = AdaptiveDecisionRepository.get_by_session_and_evaluation(
                db, session_id, evaluation_id
            )
            if existing is None:
                raise
            return existing
        db.refresh(record)
        return record


class LearnerProfileRepository:
    @staticmethod
    def create(
        db: Session,
        user_id: str,
        learning_goal: str,
        current_level: str,
        learning_preference: str,
        interests: str,
        initial_confidence: int,
    ) -> LearnerProfile:
        profile = LearnerProfile(
            user_id=user_id,
            learning_goal=learning_goal,
            current_level=current_level,
            learning_preference=learning_preference,
            interests=interests,
            initial_confidence=initial_confidence,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> Optional[LearnerProfile]:
        return db.query(LearnerProfile).filter(LearnerProfile.user_id == user_id).first()

    @staticmethod
    def get_or_create_learning_anchor(
        db: Session,
        user_id: str,
        goal: str,
        interest: str,
        preferred_explanation: str,
    ) -> LearnerProfile:
        profile = LearnerProfileRepository.get_by_user_id(db, user_id)
        if profile is not None:
            return profile

        preference = preferred_explanation.lower()
        if "step" in preference:
            learning_preference = "step_by_step"
        elif "hand" in preference or "practice" in preference:
            learning_preference = "practical_first"
        else:
            learning_preference = "example_first"

        profile = LearnerProfile(
            user_id=user_id,
            learning_goal=goal,
            current_level="unassessed",
            learning_preference=learning_preference,
            interests=interest,
            initial_confidence=0,
        )
        db.add(profile)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            profile = LearnerProfileRepository.get_by_user_id(db, user_id)
            if profile is None:
                raise
            return profile
        db.refresh(profile)
        return profile

    @staticmethod
    def update(db: Session, profile: LearnerProfile, **kwargs) -> LearnerProfile:
        for k, v in kwargs.items():
            setattr(profile, k, v)
        profile.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(profile)
        return profile

class CurriculumRepository:
    @staticmethod
    def create_topic(db: Session, title: str, description: Optional[str] = None, sequence_order: int = 1) -> Topic:
        topic = Topic(title=title, description=description, sequence_order=sequence_order)
        db.add(topic)
        db.commit()
        db.refresh(topic)
        return topic

    @staticmethod
    def create_concept(
        db: Session,
        topic_id: str,
        title: str,
        base_difficulty: int = 1,
        description: str = "",
        sequence_order: Optional[int] = None,
    ) -> Concept:
        if sequence_order is None:
            sequence_order = db.query(Concept).filter(Concept.topic_id == topic_id).count() + 1
        concept = Concept(
            topic_id=topic_id,
            title=title,
            description=description,
            base_difficulty=base_difficulty,
            sequence_order=sequence_order,
        )
        db.add(concept)
        db.commit()
        db.refresh(concept)
        return concept

    @staticmethod
    def get_topic(db: Session, topic_id: str) -> Optional[Topic]:
        return db.query(Topic).filter(Topic.id == topic_id).first()

    @staticmethod
    def get_concept(db: Session, concept_id: str) -> Optional[Concept]:
        return db.query(Concept).filter(Concept.id == concept_id).first()

    @staticmethod
    def list_topics(db: Session) -> List[Topic]:
        return db.query(Topic).order_by(Topic.sequence_order).all()

    @staticmethod
    def list_concepts_by_topic(db: Session, topic_id: str) -> List[Concept]:
        return (
            db.query(Concept)
            .filter(Concept.topic_id == topic_id)
            .order_by(Concept.sequence_order, Concept.id)
            .all()
        )

class ConceptPerformanceRepository:
    @staticmethod
    def get_or_create(db: Session, profile_id: str, concept_id: str) -> ConceptPerformance:
        perf = db.query(ConceptPerformance).filter(
            ConceptPerformance.profile_id == profile_id,
            ConceptPerformance.concept_id == concept_id,
        ).first()
        if not perf:
            perf = ConceptPerformance(
                profile_id=profile_id,
                concept_id=concept_id,
                status="learning",
                difficulty_level=1,
                mastery_score=0.0,
                attempt_count=0,
            )
            db.add(perf)
            db.commit()
            db.refresh(perf)
        return perf

    @staticmethod
    def get_by_profile_and_concept(db: Session, profile_id: str, concept_id: str) -> Optional[ConceptPerformance]:
        return db.query(ConceptPerformance).filter(
            ConceptPerformance.profile_id == profile_id,
            ConceptPerformance.concept_id == concept_id,
        ).first()

    @staticmethod
    def get_next_unmastered_concept(db: Session, profile_id: str, topic_id: str) -> Optional[Concept]:
        all_concepts = (
            db.query(Concept)
            .filter(Concept.topic_id == topic_id)
            .order_by(Concept.sequence_order, Concept.id)
            .all()
        )
        for concept in all_concepts:
            perf = db.query(ConceptPerformance).filter(
                ConceptPerformance.profile_id == profile_id,
                ConceptPerformance.concept_id == concept.id,
            ).first()
            if not perf or perf.status != "mastered":
                return concept
        return None

    @staticmethod
    def record_assessment(
        db: Session,
        profile_id: str,
        concept_id: str,
        status: str,
        mastery_score: float,
        difficulty_level: Optional[int] = None,
    ) -> ConceptPerformance:
        perf = ConceptPerformanceRepository.get_or_create(db, profile_id, concept_id)
        perf.status = status
        perf.mastery_score = mastery_score
        if difficulty_level is not None:
            perf.difficulty_level = difficulty_level
        perf.attempt_count += 1
        perf.last_assessed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(perf)
        return perf

    @staticmethod
    def list_by_profile(db: Session, profile_id: str) -> List[ConceptPerformance]:
        return db.query(ConceptPerformance).filter(ConceptPerformance.profile_id == profile_id).all()

class SessionRepository:
    @staticmethod
    def create_session(db: Session, user_id: str, topic_id: str) -> LearningSession:
        sess = LearningSession(user_id=user_id, topic_id=topic_id)
        db.add(sess)
        db.commit()
        db.refresh(sess)
        return sess

    @staticmethod
    def create_activity(
        db: Session,
        session_id: str,
        companion_type: str,
        content_payload: str,
        concept_id: Optional[str] = None,
    ) -> Activity:
        act = Activity(
            session_id=session_id,
            companion_type=companion_type,
            content_payload=content_payload,
            concept_id=concept_id,
        )
        db.add(act)
        db.commit()
        db.refresh(act)
        return act

    @staticmethod
    def record_response(db: Session, activity_id: str, response_text: str) -> LearnerResponse:
        resp = LearnerResponse(activity_id=activity_id, response_text=response_text)
        db.add(resp)
        db.commit()
        db.refresh(resp)
        return resp

    @staticmethod
    def record_evaluation(
        db: Session,
        response_id: str,
        evaluator_name: str,
        score: float,
        feedback_payload: str,
        remediation_required: bool,
    ) -> Evaluation:
        evl = Evaluation(
            response_id=response_id,
            evaluator_name=evaluator_name,
            score=score,
            feedback_payload=feedback_payload,
            remediation_required=1 if remediation_required else 0,
        )
        db.add(evl)
        db.commit()
        db.refresh(evl)
        return evl

    @staticmethod
    def get_session(db: Session, session_id: str) -> Optional[LearningSession]:
        return db.query(LearningSession).filter(LearningSession.id == session_id).first()
