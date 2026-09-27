import json
import logging
from datetime import datetime, timezone

from pydantic import ValidationError

from backend.app.agents.base import BaseAgent
from backend.app.agents.kira.contracts import (
    KiraGeneratedPractical,
    KiraOutput,
    KiraTask,
)

logger = logging.getLogger(__name__)


class KiraResponseError(ValueError):
    pass


class KiraProviderError(RuntimeError):
    pass


class KiraPracticalAgent(BaseAgent):
    SYSTEM_INSTRUCTION = (
        "You are Kira, CLARIO's specialized practical application worker. Create "
        "one realistic, learner-appropriate activity applying only the supplied "
        "concept and Mira/Ayan context. Ground factual details in the supplied "
        "research summary and sources; reference only supplied source IDs. Do not "
        "search the web, grade a learner, define pass/fail, decide mastery, change "
        "difficulty, propose remediation, modify a roadmap, call another agent, "
        "or control workflow. Return only the requested structured activity."
    )

    def create_activity(self, task: KiraTask) -> KiraOutput:
        prompt = (
            "Create a practical scenario and task that applies the taught concept "
            "in a plausible real-world context. Set difficulty exactly to the "
            "learner level supplied. Success criteria should describe observable "
            "steps, not score, grade, or pass/fail. Return only source IDs included "
            "in the task; use an empty list when no source is needed.\n\n"
            f"Kira practical task:\n{json.dumps(task.model_dump(mode='json'), ensure_ascii=True)}"
        )
        try:
            generated = self.ai_provider.generate_structured(
                prompt=prompt,
                response_model=KiraGeneratedPractical,
                system_instruction=self.SYSTEM_INSTRUCTION,
                temperature=0.2,
            )
        except (ValidationError, ValueError) as exc:
            raise KiraResponseError("Kira returned malformed practical content.") from exc
        except Exception as exc:
            logger.exception("Kira provider failed while generating a practical activity.")
            raise KiraProviderError(
                "Kira's AI provider failed to generate a practical activity."
            ) from exc

        try:
            generated = KiraGeneratedPractical.model_validate(
                generated.model_dump()
                if isinstance(generated, KiraGeneratedPractical)
                else generated
            )
        except (ValidationError, TypeError, ValueError) as exc:
            raise KiraResponseError("Kira returned malformed practical content.") from exc

        generated_text = (
            generated.scenario,
            generated.practical_task,
            generated.real_world_context,
            generated.expected_action,
            *generated.success_criteria,
        )
        if any(not value.strip() for value in generated_text):
            raise KiraResponseError("Kira returned incomplete practical content.")
        if generated.difficulty != task.learner_context.learner_level:
            raise KiraResponseError("Kira changed the supplied learner difficulty.")
        if any(source_id not in task.research_source_ids for source_id in generated.research_source_ids):
            raise KiraResponseError(
                "Kira referenced a source outside the session research package."
            )

        return KiraOutput(
            agent="Kira",
            session_id=task.session_id,
            orchestration_id=task.orchestration_id,
            concept_id=task.concept_id,
            scenario=generated.scenario,
            practical_task=generated.practical_task,
            real_world_context=generated.real_world_context,
            expected_action=generated.expected_action,
            success_criteria=generated.success_criteria,
            difficulty=generated.difficulty,
            research_source_ids=list(dict.fromkeys(generated.research_source_ids)),
            generated_at=datetime.now(timezone.utc),
        )
