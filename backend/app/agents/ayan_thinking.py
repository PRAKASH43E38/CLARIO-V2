import json
import logging
from datetime import datetime, timezone

from pydantic import ValidationError

from backend.app.agents.base import BaseAgent
from backend.app.schemas.ayan import (
    AyanCriticalThinkingTask,
    AyanGeneratedThinking,
    AyanThinkingResponse,
)

logger = logging.getLogger(__name__)


class AyanResponseError(ValueError):
    pass


class AyanProviderError(RuntimeError):
    pass


class AyanCriticalThinkingAgent(BaseAgent):
    SYSTEM_INSTRUCTION = (
        "You are Ayan, CLARIO's specialized critical-thinking worker. Focus only "
        "on the concept Mira just taught. Create a question that tests reasoning "
        "rather than recall and invites the learner to explain why or how. Where "
        "appropriate, surface assumptions, relationships, trade-offs, or "
        "consequences. Match the supplied learner level and avoid unnecessary "
        "complexity. Ground the prompt in Mira's teaching and the supplied "
        "validated research references; make no unsupported factual claims. Do not "
        "search the web, grade a learner response, decide mastery or remediation, "
        "generate a quiz, propose a practical task, change difficulty, or control "
        "workflow. Return only the requested structured thinking activity."
    )

    def create_activity(self, task: AyanCriticalThinkingTask) -> AyanThinkingResponse:
        prompt = (
            "Create one open-ended reasoning prompt for the taught concept. "
            "Expected reasoning focus lists what a thoughtful answer should explain, "
            "not an answer key. Reference only the supplied source IDs. Preserve "
            "the supplied current level as difficulty.\n\n"
            f"Critical-thinking task:\n{json.dumps(task.model_dump(mode='json'), ensure_ascii=True)}"
        )
        try:
            generated = self.ai_provider.generate_structured(
                prompt=prompt,
                response_model=AyanGeneratedThinking,
                system_instruction=self.SYSTEM_INSTRUCTION,
                temperature=0.2,
            )
        except (ValidationError, ValueError) as exc:
            raise AyanResponseError("Ayan returned malformed thinking content.") from exc
        except Exception as exc:
            logger.exception("Ayan provider failed while generating structured thinking.")
            raise AyanProviderError(
                "Ayan's AI provider failed to generate a thinking activity."
            ) from exc

        try:
            generated = AyanGeneratedThinking.model_validate(
                generated.model_dump()
                if isinstance(generated, AyanGeneratedThinking)
                else generated
            )
        except (ValidationError, TypeError, ValueError) as exc:
            raise AyanResponseError("Ayan returned malformed thinking content.") from exc

        if not generated.concept.strip() or not generated.thinking_prompt.strip() or any(
            not item.strip() for item in generated.expected_reasoning_focus
        ):
            raise AyanResponseError("Ayan returned incomplete thinking content.")
        if generated.concept.strip().casefold() != task.concept.strip().casefold():
            raise AyanResponseError(
                "Ayan response does not match the concept Mira taught."
            )
        if generated.difficulty != task.current_level:
            raise AyanResponseError(
                "Ayan response changed the CALA learner level."
            )

        sources_by_id = {
            source.source_id: source
            for source in task.research_source_references
        }
        if any(
            source_id not in sources_by_id
            for source_id in generated.source_reference_ids
        ):
            raise AyanResponseError(
                "Ayan response referenced a source outside the supplied research context."
            )

        references = [
            sources_by_id[source_id]
            for source_id in dict.fromkeys(generated.source_reference_ids)
        ]
        return AyanThinkingResponse(
            session_id=task.session_id,
            concept=task.concept,
            thinking_prompt=generated.thinking_prompt,
            expected_reasoning_focus=generated.expected_reasoning_focus,
            difficulty=generated.difficulty,
            source_references=references,
            generated_at=datetime.now(timezone.utc),
        )
