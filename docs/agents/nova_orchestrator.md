# CLARIO V2 Orchestration and Nova

## Target role split

**CLARIO-AI is the sole main orchestrator and decision engine.** It owns durable session state, worker routing, roadmap/level progression, evidence aggregation, and `REMEDIATE` / `ADVANCE` / `COMPLETE` decisions.

**Nova is the research worker.** Nova receives a bounded topic/question from CLARIO-AI, searches through Tavily/web search, validates relevance, refines queries as needed, and returns genuine source records plus structured knowledge. Nova does not teach, evaluate mastery, or control progression.

CALA is a separate initial learner-state identification/planning component. Its current implementation returns descriptive planned routing only; it does not call Nova or execute any specialist.

```text
Four session inputs + profile/evidence
  -> CALA plan
  -> CLARIO-AI
  -> Nova -> Tavily -> validation/refinement
  -> shared research package -> specialist workers
  -> Elara evidence -> CLARIO-AI decision
```

## Current implementation warning

`backend/app/orchestrator/nova.py` still defines `NovaOrchestrator` for legacy learning routes. The new four-input session path is controlled by `ClarioAIOrchestrator`, which loads CALA's persisted plan, maintains the research workflow state, and dispatches bounded work to `NovaResearchAgent` through the research service boundary. Nova uses Tavily, validates/ranks actual candidates, and returns a package persisted per session. It does not perform automated query refinement or invoke downstream learning workers. `backend/app/agents/research.py` remains a separate generic LLM ResearchAgent. The legacy overall orchestration implementation is retained only for existing routes, not as the target architecture.

## Current teaching handoff

After Nova's package is ready, CLARIO-AI constructs a typed Mira teaching task from the saved CALA plan, current session context, learner-profile preference when available, and that session's SharedResearchPackage. Mira returns a structured teaching response with source references restricted to the package. The result is persisted per session and CLARIO-AI advances to `TEACHING_READY`. Mira is skipped if no validated sources are available.

## Target boundaries

- All control transitions are explicit, validated, and persisted by CLARIO-AI.
- Worker output is typed and scoped to the active level/concept/session.
- Elara evaluates evidence and recommends; CLARIO-AI owns the actual transition.
- Weakness handling targets only the weak concept and preserves mastered concepts.
- No worker may route directly to another worker or independently advance the learner.
