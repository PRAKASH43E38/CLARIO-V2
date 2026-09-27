import inspect
from backend.app.agents import (
    BaseAgent,
    ResearchAgent,
    TeachingAgent,
    CriticalThinkingAgent,
    PracticalAgent,
    QuizAgent,
    EvaluationAgent,
)
from backend.app.orchestrator.nova import NovaOrchestrator

def test_agents_do_not_reference_each_other():
    """Guarantees that individual agents do not import or invoke each other directly."""
    agent_classes = [
        ResearchAgent,
        TeachingAgent,
        CriticalThinkingAgent,
        PracticalAgent,
        QuizAgent,
        EvaluationAgent,
    ]

    for agent_cls in agent_classes:
        source = inspect.getsource(agent_cls)
        # Check that no agent imports or instantiates another agent
        for other_cls in agent_classes:
            if other_cls != agent_cls:
                assert other_cls.__name__ not in source, (
                    f"{agent_cls.__name__} violates isolation rule by referencing {other_cls.__name__}"
                )

def test_nova_is_central_orchestrator():
    """NOVA alone holds references to all specialized agents."""
    nova = NovaOrchestrator()
    assert hasattr(nova, "research_agent")
    assert hasattr(nova, "teaching_agent")
    assert hasattr(nova, "thinking_agent")
    assert hasattr(nova, "practical_agent")
    assert hasattr(nova, "quiz_agent")
    assert hasattr(nova, "evaluation_agent")
