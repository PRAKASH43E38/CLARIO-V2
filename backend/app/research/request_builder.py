from backend.app.cala.schemas import CalaResult
from backend.app.schemas.research import ResearchConcept, ResearchRequest, ResearchTopicContext


def research_request_from_cala(plan: CalaResult) -> ResearchRequest:
    level = next(
        (
            roadmap_level
            for roadmap_level in plan.roadmap
            if roadmap_level.level_id == plan.recommended_starting_level
            and roadmap_level.is_unlocked
        ),
        None,
    )
    if level is None or not level.topics:
        raise ValueError("CALA plan has no unlocked starting-level topic.")
    topic = level.topics[0]
    if not topic.concepts:
        raise ValueError("CALA starting topic has no concepts to research.")

    return ResearchRequest(
        session_id=plan.session_id,
        learning_goal=plan.learning_goal,
        task=plan.task,
        learner_state=plan.learner_state,
        interest=plan.interest,
        learner_level=plan.learner_level,
        recommended_starting_level=plan.recommended_starting_level,
        current_topic=ResearchTopicContext(
            topic_id=topic.topic_id,
            title=topic.title,
            concepts=[
                ResearchConcept(
                    concept_id=concept.concept_id,
                    title=concept.title,
                    description=concept.description,
                )
                for concept in topic.concepts
            ],
        ),
        research_objective=(
            f"Find learning resources that support the learner's goal to "
            f"{plan.learning_goal} and task: {plan.task}. Focus on the "
            f"Level {level.order} topic and concepts."
        ),
    )
