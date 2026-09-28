import json
import logging
from datetime import datetime, timezone

from pydantic import ValidationError

from backend.app.agents.base import BaseAgent
from backend.app.schemas.mira import (
    MiraGeneratedTeaching,
    MiraTeachingResponse,
    MiraTeachingTask,
)

logger = logging.getLogger(__name__)


class MiraResponseError(ValueError):
    pass


class MiraProviderError(RuntimeError):
    pass


class MiraTeachingAgent(BaseAgent):
    SYSTEM_INSTRUCTION = (
        "You are Mira, CLARIO's specialized teaching worker. Teach only the "
        "requested concept. Begin from the learner's stated understanding, avoid "
        "unnecessary complexity, explain step by step when useful, and use "
        "examples connected to the learner's interest when appropriate. Ground "
        "factual teaching in the supplied CALA concept context and validated "
        "SharedResearchPackage only. Do not invent facts, sources, or citations. "
        "If research support is insufficient, state the limitation and keep the "
        "explanation within supported context. Do not answer unrelated questions, "
        "search the web, assess mastery, decide remediation, generate quizzes, or "
        "make workflow decisions. Return only the requested structured teaching "
        "content."
    )

    def teach(self, task: MiraTeachingTask) -> MiraTeachingResponse:
        prompt = (
            "Teach the concept described in this task. Use source_reference_ids "
            "only for source IDs present in the supplied research package. Return "
            "the learner level exactly as provided.\n\n"
            f"Teaching task:\n{json.dumps(task.model_dump(mode='json'), ensure_ascii=True)}"
        )
        if task.remediation:
            prompt += (
                "\n\nThis is a remediation attempt. Address the stated weakness "
                "using a meaningfully different teaching strategy, a fresh example, "
                "and a restructured explanation. Do not repeat the previous "
                "explanation or examples."
            )
        try:
            generated = self.ai_provider.generate_structured(
                prompt=prompt,
                response_model=MiraGeneratedTeaching,
                system_instruction=self.SYSTEM_INSTRUCTION,
                temperature=0.2,
            )
        except (ValidationError, ValueError) as exc:
            raise MiraResponseError("Mira returned malformed teaching content.") from exc
        except Exception as exc:
            logger.exception("Mira provider failed while generating structured teaching.")
            raise MiraProviderError("Mira's AI provider failed to generate teaching.") from exc

        try:
            generated = MiraGeneratedTeaching.model_validate(
                generated.model_dump()
                if isinstance(generated, MiraGeneratedTeaching)
                else generated
            )
        except (ValidationError, TypeError, ValueError) as exc:
            raise MiraResponseError("Mira returned malformed teaching content.") from exc

        if generated.concept.strip().casefold() != task.current_concept.title.strip().casefold():
            raise MiraResponseError("Mira response does not match the requested concept.")
        if generated.learner_level != task.current_level:
            raise MiraResponseError("Mira response changed the CALA learner level.")
        if task.remediation:
            previous_explanation = " ".join(
                task.remediation.previous_explanation.casefold().split()
            )
            generated_explanation = " ".join(generated.explanation.casefold().split())
            previous_examples = {
                " ".join(example.casefold().split())
                for example in task.remediation.previous_examples
            }
            generated_examples = {
                " ".join(example.casefold().split())
                for example in generated.examples
            }
            if (
                generated_explanation == previous_explanation
                or generated_examples == previous_examples
            ):
                raise MiraResponseError(
                    "Mira repeated the previous remediation explanation or examples."
                )

        sources_by_id = {
            source.source_id: source
            for source in task.shared_research_package.selected_sources
        }
        if any(source_id not in sources_by_id for source_id in generated.source_reference_ids):
            raise MiraResponseError(
                "Mira response referenced a source outside the research package."
            )

        source_references = [
            {
                "source_id": source_id,
                "title": sources_by_id[source_id].title,
                "url": sources_by_id[source_id].url,
            }
            for source_id in dict.fromkeys(generated.source_reference_ids)
        ]
        return MiraTeachingResponse(
            session_id=task.session_id,
            concept=task.current_concept.title,
            explanation=generated.explanation,
            key_points=generated.key_points,
            examples=generated.examples,
            learner_level=generated.learner_level,
            teaching_style=generated.teaching_style,
            source_references=source_references,
            generated_at=datetime.now(timezone.utc),
        )
