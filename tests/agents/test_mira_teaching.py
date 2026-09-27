import json

import pytest
from pydantic import ValidationError

from backend.app.agents.mira_teaching import MiraResponseError, MiraTeachingAgent
from backend.app.ai.mock_provider import MockAIProvider
from backend.app.schemas.mira import MiraGeneratedTeaching, MiraTeachingTask


def test_mira_task_contract_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        MiraTeachingTask.model_validate({"session_id": "ses_1", "manual_level": "expert"})


def test_mock_mira_returns_structured_teaching_grounded_in_task():
    task_data = {
        "session_id": "ses_1",
        "task": "Understand information gain",
        "learning_goal": "Explain decision trees",
        "learner_state": "I know basic probability",
        "interest": "Sports analytics",
        "current_concept": {
            "concept_id": "con_1",
            "title": "Information Gain",
            "description": "Measure the value of a split.",
        },
        "shared_research_package": {
            "session_id": "ses_1",
            "research_request": {
                "session_id": "ses_1",
                "learning_goal": "Explain decision trees",
                "task": "Understand information gain",
                "learner_state": "I know basic probability",
                "interest": "Sports analytics",
                "learner_level": "beginner",
                "recommended_starting_level": "level_1",
                "current_topic": {
                    "topic_id": "top_1",
                    "title": "Decision Trees",
                    "concepts": [{
                        "concept_id": "con_1",
                        "title": "Information Gain",
                        "description": "Measure the value of a split.",
                    }],
                },
                "research_objective": "Find learning materials.",
            },
            "research_summary": "Retrieved a relevant source excerpt.",
            "key_concepts": [{
                "concept_id": "con_1",
                "title": "Information Gain",
                "description": "Measure the value of a split.",
            }],
            "selected_sources": [{
                "source_id": "src_1",
                "title": "Information Gain Guide",
                "url": "https://example.edu/information-gain",
                "domain": "example.edu",
                "snippet": "Information gain compares the value of a split in a tree.",
                "relevance_score": 0.8,
                "source_type": "article",
                "published_date": None,
                "validation_status": "validated",
            }],
            "research_timestamp": "2026-09-27T00:00:00Z",
            "queries": [],
            "validation_information": {
                "status": "partial",
                "candidates_received": 1,
                "sources_validated": 1,
                "sources_rejected": 0,
                "duplicate_sources_removed": 0,
                "maximum_sources_per_domain": 2,
            },
        },
        "current_level": "beginner",
        "learning_preference": None,
        "teaching_instruction": "Explain the current concept clearly.",
    }
    task = MiraTeachingTask.model_validate(task_data)
    provider = MockAIProvider()

    response = MiraTeachingAgent(provider).teach(task)

    assert response.session_id == task.session_id
    assert response.concept == "Information Gain"
    assert response.learner_level == "beginner"
    assert response.source_references[0].source_id == "src_1"
    assert isinstance(response.generated_at.isoformat(), str)
    call = provider.call_history[0]
    assert call["model_name"] == MiraGeneratedTeaching.__name__
    serialized_task = json.loads(call["prompt"].partition("Teaching task:\n")[2])
    assert serialized_task["interest"] == "Sports analytics"
    assert serialized_task["shared_research_package"]["selected_sources"][0]["source_id"] == "src_1"


def test_mira_rejects_source_reference_not_present_in_package():
    task = MiraTeachingTask.model_validate({
        "session_id": "ses_1",
        "task": "Understand information gain",
        "learning_goal": "Explain decision trees",
        "learner_state": "Basic probability",
        "interest": "Sports",
        "current_concept": {
            "concept_id": "con_1",
            "title": "Information Gain",
            "description": "Measure the value of a split.",
        },
        "shared_research_package": {
            "session_id": "ses_1",
            "research_request": {
                "session_id": "ses_1",
                "learning_goal": "Explain decision trees",
                "task": "Understand information gain",
                "learner_state": "Basic probability",
                "interest": "Sports",
                "learner_level": "beginner",
                "recommended_starting_level": "level_1",
                "current_topic": {
                    "topic_id": "top_1",
                    "title": "Decision Trees",
                    "concepts": [{
                        "concept_id": "con_1",
                        "title": "Information Gain",
                        "description": "Measure the value of a split.",
                    }],
                },
                "research_objective": "Find learning materials.",
            },
            "research_summary": "No matching source.",
            "key_concepts": [],
            "selected_sources": [],
            "research_timestamp": "2026-09-27T00:00:00Z",
            "queries": [],
            "validation_information": {
                "status": "no_sources",
                "candidates_received": 0,
                "sources_validated": 0,
                "sources_rejected": 0,
                "duplicate_sources_removed": 0,
                "maximum_sources_per_domain": 2,
            },
        },
        "current_level": "beginner",
        "teaching_instruction": "Teach the concept.",
    })
    provider = MockAIProvider(custom_responses={
        "MiraGeneratedTeaching": {
            "concept": "Information Gain",
            "explanation": "A supported short explanation.",
            "key_points": ["Compare splits."],
            "examples": ["A simple example."],
            "learner_level": "beginner",
            "teaching_style": "step by step",
            "source_reference_ids": ["forged-source"],
        }
    })

    with pytest.raises(MiraResponseError, match="outside the research package"):
        MiraTeachingAgent(provider).teach(task)
