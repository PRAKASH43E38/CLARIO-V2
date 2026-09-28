import json
import logging
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.app.agents.base import BaseAgent
from backend.app.agents.zayn.contracts import (
    ZAYN_TIME_LIMITS,
    ZaynDifficulty,
    ZaynOutput,
    ZaynQuestion,
    ZaynTask,
)

logger = logging.getLogger(__name__)


class ZaynResponseError(ValueError):
    pass


class ZaynProviderError(RuntimeError):
    pass


class ZaynGeneratedQuiz(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[ZaynQuestion]
    difficulty: ZaynDifficulty


class ZaynQuizAgent(BaseAgent):
    SYSTEM_INSTRUCTION = (
        "You are Zayn, CLARIO's quiz and challenge worker. Create questions only "
        "for the supplied current concept, grounding them in the supplied teaching, "
        "thinking, practical, and validated research context. Each multiple-choice "
        "question must have exactly one correct option, a concise explanation, and "
        "the exact requested concept ID and difficulty. Do not assess mastery, "
        "determine learner level, decide remediation or progression, modify a "
        "roadmap, call other agents, or control workflow. Return only the requested "
        "structured quiz data."
    )

    def create_quiz(self, task: ZaynTask) -> ZaynOutput:
        prompt = (
            "Create exactly question_count distinct multiple-choice questions for "
            "the current concept. Use at least two distinct options per question, "
            "with correct_answer exactly matching one option. Each question must "
            "include a short explanation, the exact concept_id and requested "
            "difficulty. Do not include unrelated concepts. Do not change difficulty. "
            "For a retest, every question must be new: do not reuse any prior question "
            "ID or question wording listed in the task.\n\n"
            f"Zayn quiz task:\n{json.dumps(task.model_dump(mode='json'), ensure_ascii=True)}"
        )
        try:
            generated = self.ai_provider.generate_structured(
                prompt=prompt,
                response_model=ZaynGeneratedQuiz,
                system_instruction=self.SYSTEM_INSTRUCTION,
                temperature=0.2,
            )
        except (ValidationError, ValueError) as exc:
            raise ZaynResponseError("Zayn returned malformed quiz content.") from exc
        except Exception as exc:
            logger.exception("Zayn provider failed while generating a quiz.")
            raise ZaynProviderError("Zayn's AI provider failed to generate a quiz.") from exc

        try:
            generated = ZaynGeneratedQuiz.model_validate(
                generated.model_dump()
                if isinstance(generated, ZaynGeneratedQuiz)
                else generated
            )
        except (ValidationError, TypeError, ValueError) as exc:
            raise ZaynResponseError("Zayn returned malformed quiz content.") from exc

        if generated.difficulty != task.difficulty:
            raise ZaynResponseError("Zayn changed the CLARIO-AI quiz difficulty.")
        if len(generated.questions) != task.question_count:
            raise ZaynResponseError(
                f"Zayn must create exactly {task.question_count} quiz questions."
            )

        identifiers: set[str] = set()
        for question in generated.questions:
            if question.question_id in identifiers:
                raise ZaynResponseError("Zayn returned duplicate question IDs.")
            identifiers.add(question.question_id)
            if question.concept_id != task.concept_id:
                raise ZaynResponseError(
                    "Zayn returned a question for a different concept."
                )
            if question.difficulty != task.difficulty:
                raise ZaynResponseError(
                    "Zayn returned a question with a different difficulty."
                )
            if any(not option.strip() for option in question.options):
                raise ZaynResponseError("Zayn returned an empty answer option.")
            if len({option.casefold() for option in question.options}) != len(
                question.options
            ):
                raise ZaynResponseError("Zayn returned duplicate answer options.")
            if question.correct_answer not in question.options:
                raise ZaynResponseError(
                    "Each Zayn question must have one correct answer matching an option exactly."
                )
            if not question.question.strip() or not question.explanation.strip():
                raise ZaynResponseError(
                    "Zayn returned a question without wording or explanation."
                )
        previous_ids = set(task.previous_question_ids)
        previous_texts = {
            " ".join(text.casefold().split())
            for text in task.previous_question_texts
        }
        if any(
            question.question_id in previous_ids
            or " ".join(question.question.casefold().split()) in previous_texts
            for question in generated.questions
        ):
            raise ZaynResponseError(
                "Zayn reused a question from an earlier attempt."
            )

        return ZaynOutput(
            agent="Zayn",
            session_id=task.session_id,
            orchestration_id=task.orchestration_id,
            concept_id=task.concept_id,
            difficulty=task.difficulty,
            time_limit_seconds=ZAYN_TIME_LIMITS[task.difficulty],
            questions=generated.questions,
            generated_at=datetime.now(timezone.utc),
        )
