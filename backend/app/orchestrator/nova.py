import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.ai.base import BaseAIProvider
from backend.app.ai.factory import get_ai_provider
from backend.app.agents.research import ResearchAgent
from backend.app.agents.teaching import TeachingAgent
from backend.app.agents.thinking import CriticalThinkingAgent
from backend.app.agents.practical import PracticalAgent
from backend.app.agents.quiz import QuizAgent
from backend.app.agents.evaluation import EvaluationAgent
from backend.app.orchestrator.state import LearningStep, ActiveSessionContext
from backend.app.orchestrator.adaptive_policy import (
    AdaptivePolicy,
    AdaptiveAction,
    AdaptiveDecision,
)
from backend.app.models.repositories import (
    SessionRepository,
    ConceptPerformanceRepository,
    CurriculumRepository,
)

class NovaOrchestrator:
    """NOVA: Central Orchestrator for CLARIO.
    Single point of control: Agents never invoke or route to each other.
    NOVA manages the adaptive learning loop:
    Plan/Research -> Teaching -> Thinking -> Practical -> Quiz -> Evaluation -> Adaptive Decision -> Targeted Remediation or Advance.
    """

    def __init__(self, ai_provider: Optional[BaseAIProvider] = None):
        self.ai_provider = ai_provider or get_ai_provider()
        self.research_agent = ResearchAgent(self.ai_provider)
        self.teaching_agent = TeachingAgent(self.ai_provider)
        self.thinking_agent = CriticalThinkingAgent(self.ai_provider)
        self.practical_agent = PracticalAgent(self.ai_provider)
        self.quiz_agent = QuizAgent(self.ai_provider)
        self.evaluation_agent = EvaluationAgent(self.ai_provider)

    def start_learning_flow(
        self,
        ctx: ActiveSessionContext,
        db: Optional[Session] = None,
        learner_level: str = "intermediate",
        learning_preference: str = "step_by_step",
    ) -> ActiveSessionContext:
        """Initiates learning flow: triggers Research if needed, then sets up Teaching."""
        # 1. Research
        if not ctx.research_data:
            ctx.current_step = LearningStep.RESEARCH
            research_out = self.research_agent.research_topic(ctx.topic_title)
            ctx.research_data = research_out

            # Select first concept if not set
            if not ctx.current_concept_title and research_out.key_concepts:
                first_concept = research_out.key_concepts[0]
                ctx.current_concept_title = first_concept.title
                ctx.difficulty_level = first_concept.base_difficulty

        # 2. Teaching
        ctx.current_step = LearningStep.TEACHING
        teaching_out = self.teaching_agent.explain_concept(
            concept=ctx.current_concept_title or ctx.topic_title,
            topic_context=ctx.research_data.overview if ctx.research_data else ctx.topic_title,
            learner_level=learner_level,
            learning_preference=learning_preference,
            is_remediation=ctx.is_remediating,
            remediation_notes=ctx.remediation_notes,
        )
        ctx.teaching_data = teaching_out

        if db:
            SessionRepository.create_activity(
                db=db,
                session_id=ctx.session_id,
                companion_type="teaching",
                content_payload=teaching_out.model_dump_json(),
                concept_id=ctx.current_concept_id,
            )

        return ctx

    def proceed_to_thinking(
        self,
        ctx: ActiveSessionContext,
        db: Optional[Session] = None,
    ) -> ActiveSessionContext:
        """Routes from Teaching to Critical Thinking (Thinking Friend)."""
        ctx.current_step = LearningStep.THINKING
        question = self.thinking_agent.generate_question(
            concept=ctx.current_concept_title or ctx.topic_title,
            concept_explanation=ctx.teaching_data.explanation if ctx.teaching_data else "",
        )
        ctx.thinking_question = question

        if db:
            SessionRepository.create_activity(
                db=db,
                session_id=ctx.session_id,
                companion_type="thinking",
                content_payload=question.model_dump_json(),
                concept_id=ctx.current_concept_id,
            )

        return ctx

    def submit_thinking_response(
        self,
        ctx: ActiveSessionContext,
        learner_response: str,
        db: Optional[Session] = None,
    ) -> ActiveSessionContext:
        """Evaluates thinking response and routes to Practical (Practical Friend)."""
        assessment = self.thinking_agent.evaluate_reasoning(
            concept=ctx.current_concept_title or ctx.topic_title,
            question=ctx.thinking_question.question if ctx.thinking_question else "",
            learner_response=learner_response,
        )
        ctx.thinking_assessment = assessment

        # Next: Practical Step
        ctx.current_step = LearningStep.PRACTICAL
        exercise = self.practical_agent.generate_exercise(
            concept=ctx.current_concept_title or ctx.topic_title,
            topic_context=ctx.research_data.overview if ctx.research_data else "",
            difficulty_level=ctx.difficulty_level,
        )
        ctx.practical_exercise = exercise

        if db:
            act = SessionRepository.create_activity(
                db=db,
                session_id=ctx.session_id,
                companion_type="practical",
                content_payload=exercise.model_dump_json(),
                concept_id=ctx.current_concept_id,
            )
            SessionRepository.record_response(db, act.id, learner_response)

        return ctx

    def proceed_to_quiz(
        self,
        ctx: ActiveSessionContext,
        db: Optional[Session] = None,
    ) -> ActiveSessionContext:
        """Routes from Practical to Quiz (Quiz Friend). Generates a non-repeated question instance."""
        ctx.current_step = LearningStep.QUIZ
        quiz_q = self.quiz_agent.generate_question(
            concept=ctx.current_concept_title or ctx.topic_title,
            difficulty_level=ctx.difficulty_level,
            attempt_number=ctx.attempt_count,
            exclude_question_ids=ctx.asked_question_ids,
        )
        ctx.quiz_question = quiz_q
        if quiz_q.question_id not in ctx.asked_question_ids:
            ctx.asked_question_ids.append(quiz_q.question_id)

        if db:
            SessionRepository.create_activity(
                db=db,
                session_id=ctx.session_id,
                companion_type="quiz",
                content_payload=quiz_q.model_dump_json(),
                concept_id=ctx.current_concept_id,
            )

        return ctx

    def submit_quiz_response(
        self,
        ctx: ActiveSessionContext,
        learner_answer: str,
        db: Optional[Session] = None,
    ) -> ActiveSessionContext:
        """Grades quiz answer, routes to Ellara for evaluation, and executes deterministic adaptive logic."""
        grading = self.quiz_agent.grade_answer(
            question=ctx.quiz_question.question_text if ctx.quiz_question else "",
            correct_answer=ctx.quiz_question.correct_answer if ctx.quiz_question else "",
            learner_answer=learner_answer,
            difficulty_level=ctx.difficulty_level,
        )
        ctx.quiz_grading = grading

        # 1. Ellara Evaluation (aggregates all evidence)
        ctx.current_step = LearningStep.EVALUATION
        eval_result = self.evaluation_agent.evaluate_mastery(
            topic=ctx.topic_title,
            concept=ctx.current_concept_title or ctx.topic_title,
            thinking_eval=ctx.thinking_assessment,
            practical_summary=ctx.practical_exercise.scenario_title if ctx.practical_exercise else None,
            quiz_grading=grading,
        )
        ctx.evaluation_result = eval_result

        # Retrieve current DB concept performance if available
        curr_perf = None
        if db and ctx.profile_id and ctx.current_concept_id:
            curr_perf = ConceptPerformanceRepository.get_by_profile_and_concept(
                db, ctx.profile_id, ctx.current_concept_id
            )

        current_status = curr_perf.status if curr_perf else ("remediating" if ctx.is_remediating else "learning")
        current_attempts = curr_perf.attempt_count if curr_perf else (ctx.attempt_count - 1)

        # 2. Deterministic Adaptive Policy Decision
        decision = AdaptivePolicy.evaluate(
            concept_title=ctx.current_concept_title or ctx.topic_title,
            current_status=current_status,
            current_difficulty=ctx.difficulty_level,
            attempt_count=current_attempts,
            evaluation=eval_result,
            quiz_score=grading.score,
        )
        decision.target_concept_id = ctx.current_concept_id
        ctx.latest_decision = decision

        # 3. Persist updated concept state to DB
        if db and ctx.profile_id and ctx.current_concept_id:
            ConceptPerformanceRepository.record_assessment(
                db=db,
                profile_id=ctx.profile_id,
                concept_id=ctx.current_concept_id,
                status=decision.new_status,
                mastery_score=grading.score,
                difficulty_level=decision.new_difficulty,
            )

        # 4. Apply State Transitions
        if decision.action == AdaptiveAction.REMEDIATE:
            # Target ONLY the weak concept
            ctx.is_remediating = True
            ctx.difficulty_level = decision.new_difficulty
            ctx.remediation_notes = decision.remediation_notes
            ctx.attempt_count = decision.attempt_number

        elif decision.action == AdaptiveAction.ADVANCE:
            ctx.is_remediating = False
            ctx.remediation_notes = None
            ctx.attempt_count = 1

            # Check if next unmastered concept exists in topic
            if db and ctx.profile_id:
                next_concept = ConceptPerformanceRepository.get_next_unmastered_concept(
                    db, ctx.profile_id, ctx.topic_id
                )
                if next_concept and next_concept.id != ctx.current_concept_id:
                    ctx.current_concept_id = next_concept.id
                    ctx.current_concept_title = next_concept.title
                    ctx.difficulty_level = next_concept.base_difficulty
                elif not next_concept:
                    decision.action = AdaptiveAction.TOPIC_COMPLETED

        return ctx

    def trigger_targeted_remediation(
        self,
        ctx: ActiveSessionContext,
        db: Optional[Session] = None,
        learner_level: str = "intermediate",
        learning_preference: str = "step_by_step",
    ) -> ActiveSessionContext:
        """Executes targeted remediation for the current weak concept without restarting the topic."""
        if not ctx.is_remediating:
            return ctx

        ctx.current_step = LearningStep.TEACHING
        teaching_out = self.teaching_agent.explain_concept(
            concept=ctx.current_concept_title or ctx.topic_title,
            topic_context=ctx.research_data.overview if ctx.research_data else ctx.topic_title,
            learner_level=learner_level,
            learning_preference=learning_preference,
            is_remediation=True,
            remediation_notes=ctx.remediation_notes,
        )
        ctx.teaching_data = teaching_out

        if db:
            SessionRepository.create_activity(
                db=db,
                session_id=ctx.session_id,
                companion_type="teaching",
                content_payload=teaching_out.model_dump_json(),
                concept_id=ctx.current_concept_id,
            )

        return ctx
