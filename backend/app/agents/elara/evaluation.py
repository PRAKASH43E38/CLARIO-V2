import json
import logging
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.app.agents.base import BaseAgent
from backend.app.agents.elara.contracts import (
    ConceptStrength,
    ConceptWeakness,
    DifficultySignal,
    ElaraOutput,
    ElaraQuizPerformance,
    ElaraTask,
)

logger = logging.getLogger(__name__)


class ElaraResponseError(ValueError):
    pass


class ElaraProviderError(RuntimeError):
    pass


class ElaraGeneratedEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_strength: ConceptStrength
    concept_weakness: ConceptWeakness
    quiz_performance: ElaraQuizPerformance
    thinking_evidence: Literal["unavailable"]
    practical_evidence: Literal["unavailable"]
    overall_evaluation: str
    confidence: float
    difficulty_signal: DifficultySignal
    evidence_summary: str


class ElaraEvaluationAgent(BaseAgent):
    SYSTEM_INSTRUCTION = (
        "You are Elara, CLARIO's evaluation worker. Evaluate only the supplied "
        "current concept evidence. The quiz metrics are calculated from the "
        "persisted quiz submission and must be returned unchanged. Ayan and Kira "
        "learner responses are unavailable; mark both evidence fields exactly "
        "'unavailable' and do not infer or invent learner responses. Use "
        "insufficient_evidence when the evidence does not support a conclusion. "
        "Confidence is confidence in this evaluation, not a psychological claim "
        "about the learner. A difficulty signal is advisory only. Do not choose "
        "the next agent, change difficulty, decide progression/mastery/remediation, "
        "modify a roadmap/profile, call agents, or control workflow. Return only "
        "the requested structured evaluation fields."
    )

    def evaluate(self, task: ElaraTask) -> ElaraOutput:
        prompt = (
            "Evaluate this current-concept learning cycle. Use teaching coverage, "
            "quiz performance, learner context, and the stated absence of Ayan/Kira "
            "learner responses. Preserve the quiz metrics exactly. Do not claim "
            "learner evidence that is not present.\n\n"
            f"Elara evaluation task:\n"
            f"{json.dumps(task.model_dump(mode='json'), ensure_ascii=True)}"
        )
        try:
            generated = self.ai_provider.generate_structured(
                prompt=prompt,
                response_model=ElaraGeneratedEvaluation,
                system_instruction=self.SYSTEM_INSTRUCTION,
                temperature=0.1,
            )
        except (ValidationError, ValueError) as exc:
            raise ElaraResponseError("Elara returned malformed evaluation content.") from exc
        except Exception as exc:
            logger.exception("Elara provider failed while evaluating a learning cycle.")
            raise ElaraProviderError(
                "Elara's AI provider failed to evaluate the learning cycle."
            ) from exc

        try:
            generated = ElaraGeneratedEvaluation.model_validate(
                generated.model_dump()
                if isinstance(generated, ElaraGeneratedEvaluation)
                else generated
            )
            return ElaraOutput(
                agent="Elara",
                session_id=task.session_id,
                orchestration_id=task.orchestration_id,
                concept_id=task.concept_id,
                concept_name=task.concept_name,
                concept_strength=generated.concept_strength,
                concept_weakness=generated.concept_weakness,
                quiz_performance=generated.quiz_performance,
                thinking_evidence=generated.thinking_evidence,
                practical_evidence=generated.practical_evidence,
                overall_evaluation=generated.overall_evaluation,
                confidence=generated.confidence,
                difficulty_signal=generated.difficulty_signal,
                evidence_summary=generated.evidence_summary,
                evaluated_at=datetime.now(timezone.utc),
            )
        except (ValidationError, TypeError, ValueError) as exc:
            raise ElaraResponseError("Elara returned invalid evaluation fields.") from exc
