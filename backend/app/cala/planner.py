import re
import json
from typing import Optional

from backend.app.ai.base import BaseAIProvider
from backend.app.cala.schemas import (
    AgentRoutingStep,
    CalaResult,
    ConfidenceState,
    GeneratedRemainingCurriculum,
    RoadmapConcept,
    RoadmapLevel,
    RoadmapTopic,
)
from backend.app.models.curriculum import Concept, Topic
from backend.app.models.learner import LearnerProfile
from backend.app.models.mind_profile import MindProfile
from backend.app.models.session_inputs import SessionInputs


class CalaPlanner:
    """Builds an explainable, session-scoped initial learner plan."""

    _LEVEL_CUES = {
        "advanced": (
            "advanced",
            "expert",
            "extensive experience",
            "years of experience",
            "deep understanding",
            "professional experience",
            "proficient",
        ),
        "intermediate": (
            "some experience",
            "know the basics",
            "understand the basics",
            "basic understanding",
            "familiar with",
            "used before",
        ),
        "beginner": (
            "beginner",
            "new to",
            "no experience",
            "never used",
            "starting from scratch",
            "just starting",
            "have not learned",
            "haven't learned",
            "do not know",
            "don't know",
        ),
    }

    @classmethod
    def create_plan(
        cls,
        session_id: str,
        session_inputs: SessionInputs,
        topic: Topic,
        concepts: list[Concept],
        mind_profile: Optional[MindProfile],
        learner_profile: Optional[LearnerProfile],
    ) -> CalaResult:
        learner_level, learner_level_reason = cls._infer_learner_level(
            session_inputs.learner_state,
            learner_profile.current_level if learner_profile else "",
        )
        confidence_state = cls._infer_confidence(
            session_inputs.learner_state,
            learner_profile.initial_confidence if learner_profile else 0,
        )
        teaching_preference = (
            mind_profile.preferred_explanation if mind_profile else None
        )

        level_one_topic = RoadmapTopic(
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
        roadmap = [
            RoadmapLevel(
                level_id="level_1",
                title="Beginner",
                description="Start with the available foundational curriculum.",
                order=1,
                is_unlocked=True,
                completion_state="not_started",
                level_state="LEVEL_UNLOCKED",
                topics=[level_one_topic],
                owner_session_id=session_id,
            ),
        ]

        return CalaResult(
            session_id=session_id,
            learner_level=learner_level,
            learner_level_reason=learner_level_reason,
            weakness_type="unknown",
            weakness_reason=(
                "No evaluated concept-performance evidence is available yet; "
                "no weakness is inferred from the compatibility profile."
            ),
            confidence_state=confidence_state,
            recommended_starting_level="level_1",
            recommended_starting_level_reason=(
                "Level 1 is the available starting level. Later levels remain "
                "unmaterialized until the current learning evidence supports progression."
            ),
            current_level_id="level_1",
            active_concept_id=concepts[0].id if concepts else None,
            learning_goal=session_inputs.goal,
            task=session_inputs.task,
            learner_state=session_inputs.learner_state,
            interest=session_inputs.interest,
            roadmap=roadmap,
            initial_agent_routing=[
                AgentRoutingStep(agent="Nova", purpose="Research for the planned learning level."),
                AgentRoutingStep(
                    agent="Mira",
                    purpose=(
                        f"Teach the current concept using the learner's "
                        f"{teaching_preference} preference."
                        if teaching_preference
                        else "Teach the current concept using an adaptive explanation."
                    ),
                ),
                AgentRoutingStep(agent="Ayan", purpose="Probe conceptual understanding."),
                AgentRoutingStep(agent="Kira", purpose="Apply learning in a practical context."),
                AgentRoutingStep(agent="Zayn", purpose="Assess understanding."),
                AgentRoutingStep(agent="Elara", purpose="Evaluate learning evidence."),
            ],
        )

    @staticmethod
    def generate_remaining_curriculum(
        ai_provider: BaseAIProvider,
        plan: CalaResult,
        current_level_id: str,
        concept_performance: list[dict[str, object]],
    ) -> GeneratedRemainingCurriculum:
        current_level = next(
            (level for level in plan.roadmap if level.level_id == current_level_id),
            None,
        )
        if current_level is None:
            raise ValueError("The completed level is not in this CALA roadmap.")

        context = {
            "goal": plan.learning_goal,
            "task": plan.task,
            "learner_state": plan.learner_state,
            "interest": plan.interest,
            "initial_learner_level": plan.learner_level,
            "completed_level": current_level.model_dump(mode="json"),
            "existing_roadmap": [
                level.model_dump(mode="json") for level in plan.roadmap
            ],
            "concept_performance": concept_performance,
        }
        prompt = (
            "Prepare the remaining ordered curriculum for this learner's goal. "
            "Return every remaining level needed to reach the goal, or return an "
            "empty levels list and goal_complete=true if no further levels are "
            "needed. Do not impose a fixed number of levels. Each level must "
            "progress beyond previously taught concepts, have ordered topics and "
            "at least one distinct concept per topic, and remain tightly grounded "
            "in the learner context. Do not repeat completed or existing concepts. "
            "Return only the requested structured curriculum; do not make mastery "
            "or progression decisions.\n\n"
            f"Learning context:\n{json.dumps(context, ensure_ascii=True)}"
        )
        generated = ai_provider.generate_structured(
            prompt=prompt,
            response_model=GeneratedRemainingCurriculum,
            system_instruction=(
                "You are CALA, CLARIO's curriculum planning component. Plan "
                "goal-relevant ordered learning levels only. CLARIO-AI retains "
                "exclusive authority over evidence evaluation and progression."
            ),
            temperature=0.2,
        )
        return GeneratedRemainingCurriculum.model_validate(
            generated.model_dump()
            if isinstance(generated, GeneratedRemainingCurriculum)
            else generated
        )

    @classmethod
    def _infer_learner_level(
        cls, learner_state: str, prior_level: str
    ) -> tuple[str, str]:
        statement = learner_state.casefold()
        for level in ("beginner", "advanced", "intermediate"):
            matching_cue = None
            for cue in cls._LEVEL_CUES[level]:
                if cue not in statement:
                    continue
                escaped_cue = re.escape(cue)
                if re.search(rf"\b(?:not|never)\s+(?:yet\s+)?{escaped_cue}\b", statement):
                    continue
                matching_cue = cue
                break
            if matching_cue:
                return (
                    level,
                    f"The learner state explicitly says {matching_cue}; "
                    "this is an initial estimate, not a mastery decision.",
                )

        normalized_prior = prior_level.strip().casefold()
        if normalized_prior in {"beginner", "intermediate", "advanced"}:
            return (
                normalized_prior,
                "No explicit level evidence was stated for this session; using "
                "the existing recorded learner level as a historical baseline.",
            )

        return (
            "beginner",
            "There is not enough reliable level evidence yet; starting safely "
            "at Beginner until learning evidence is available.",
        )

    @staticmethod
    def _infer_confidence(
        learner_state: str, prior_confidence: int
    ) -> ConfidenceState:
        statement = learner_state.casefold()
        if re.search(
            r"\b(not(?: very)? confident|do not feel confident|don't feel confident|"
            r"unsure|uncertain|lack confidence)\b",
            statement,
        ):
            return ConfidenceState(level="low", evidence="learner_state")
        if re.search(r"\b(somewhat confident|fairly confident|moderately confident)\b", statement):
            return ConfidenceState(level="moderate", evidence="learner_state")
        if re.search(r"\b(very confident|highly confident|confident)\b", statement):
            return ConfidenceState(level="high", evidence="learner_state")

        if 1 <= prior_confidence <= 5:
            if prior_confidence <= 2:
                level = "low"
            elif prior_confidence == 3:
                level = "moderate"
            else:
                level = "high"
            return ConfidenceState(
                level=level,
                evidence="legacy_self_report",
                self_reported_score=prior_confidence,
            )

        return ConfidenceState(level="unknown")
