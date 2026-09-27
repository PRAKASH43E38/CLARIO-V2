# CLARIO V2 Agent Roles

The CLARIO V2 Master Prompt is authoritative. Specialized agents are workers, not independent owners of the learning journey. **CLARIO-AI is the sole main orchestrator and decision engine.**

## Control flow

Target learning control flow:

```text
User inputs and learner state
  -> CALA plan
  -> CLARIO-AI roadmap and level decisions
  -> Nova research -> Tavily/web search -> relevance validation/refinement
  -> validated sources and shared research package
  -> Mira -> Ayan -> Kira -> Zayn -> Elara
  -> CLARIO-AI evaluates evidence and chooses remediate, advance, or complete
```

Current implemented path is narrower:

```text
Four session inputs -> CALA persisted plan -> CLARIO-AI state -> Nova/Tavily/source validation
-> Mira teaching -> Ayan prompt -> Kira activity -> Zayn quiz/submission
-> Elara evaluation -> CLARIO-AI EVALUATION_READY (no adaptive decision yet)
```

CLARIO-AI currently owns all persisted handoffs through Elara evaluation. It does not yet make the subsequent adaptive learning decision. Nova remains research-only; each other agent remains within its specialist boundary.

### CLARIO-AI

- Owns the learning state machine, routing, roadmap/level progression, and decisions.
- Provides workers with scoped tasks and validated context.
- Aggregates evidence, persists state, and chooses `REMEDIATE`, `ADVANCE`, or `COMPLETE`.
- Ensures weakness remediation applies to the specific weak concept; it must not restart mastered work.
- Does not delegate overall journey control to any worker.

### Specialized workers

| Worker | Sole responsibility | Boundary |
|---|---|---|
| **Nova** | Research and preparation of reliable topic knowledge using Tavily/web search. | Does not teach, assess, or control progression. |
| **Mira** | Explain concepts using the saved CALA/session context and Nova's validated shared research package. | Does not search, assess, make mastery/progression decisions, or control workflow state. |
| **Ayan** | Probe and assess conceptual reasoning; identify misconceptions. | Reports evidence to CLARIO-AI; does not route the journey. |
| **Kira** | Create practical, real-world application tasks grounded in the current concept and shared research. | Presents the activity only; does not grade, decide pass/fail, or route the journey. |
| **Zayn** | Generate adaptive quizzes/challenges and structured results. | Reports assessment evidence; does not set final mastery state. |
| **Elara** | Aggregate teaching coverage and submitted quiz evidence into a structured current-concept evaluation; mark unavailable Ayan/Kira learner responses as unavailable. | Reports strength/weakness, evidence quality, quiz metrics, evaluation confidence, and advisory difficulty signal. Does not choose the next worker, decide progression/remediation, or change difficulty; CLARIO-AI owns all final decisions. |

## Shared contracts and flow rules

- Session inputs are exactly **Task**, **Goal**, **Learner State**, and **Interest**. There is no manual “Your Level” input.
- Mind Profile is a one-time onboarding artifact, not a repeated session input.
- CALA prepares a learning plan from the learner/session context. CLARIO-AI validates and owns the roadmap and progression state.
- Research must use actual retrieved sources. Never fabricate citations or claim ten sources when fewer meet validation criteria.
- The target research package contains validated source metadata and structured knowledge shared with downstream workers. The current package persists validated source metadata, retrieved excerpts, query/validation counts, and session context; it does not claim independently verified facts. Current Mira input/output are typed, and Mira source references are resolved only against this package.
- Workers communicate through CLARIO-AI contracts; no free-form peer-to-peer orchestration.
- Every transition is based on persisted, evaluated learner evidence.

## Current code status (not target role authority)

The new session path dispatches Nova, Mira, Ayan, Kira, Zayn, and Elara through CLARIO-AI. Zayn's correct answers/explanations remain server-side; Elara receives only calculated quiz metrics and worker context, not answer keys. Ayan/Kira learner responses are not captured. CLARIO-AI adaptive decisions remain pending. The repository also retains `NovaOrchestrator` in `backend/app/orchestrator/nova.py` for legacy routes and generic agents in `backend/app/agents/`; these older paths must not be mistaken for current role ownership.
