# CLARIO V2 System Overview

## Target architecture

```text
User/Profile
  -> one-time Mind Profile
  -> per-session Task, Goal, Learner State, Interest
  -> CALA plan
  -> CLARIO-AI roadmap/state machine
  -> Nova -> Tavily -> relevance validation/refinement
  -> validated top sources -> shared research package
  -> Mira -> Ayan -> Kira -> Zayn -> Elara
  -> CLARIO-AI decision: remediate / advance / complete
  -> persisted learner state, progress, and eventual final report
```

The application target uses three separate SQLite databases. Their exact table ownership and cross-database reference policy must be finalized before migration. CLARIO-AI remains the only overall orchestrator; agents are specialized workers.

## Current code map

- Frontend: React/TypeScript/Vite under `frontend/src`; entry `main.tsx`, route root `App.tsx`, pages/components/hooks and API client under `services/api.ts`.
- Backend: FastAPI app `backend/app/main.py`; routes under `backend/app/api/routes`; SQLAlchemy models/repositories under `backend/app/models`.
- Initial planning: CALA uses the current session's four stored inputs, available profile/Mind Profile data, and curriculum; it persists a structured plan and a Level 1 unlocked roadmap. It performs deterministic evidence-based estimation, leaves unknown confidence/weakness unknown, and only describes (does not execute) future worker routing.
- Current orchestration: `ClarioAIOrchestrator` loads the saved CALA plan, persists Nova research and worker/evaluation results, applies deterministic decisions, and executes saved remediation decisions. Reteach dispatches Mira → Ayan → Kira → Zayn for the same concept; retest dispatches Zayn only. Each decision has one idempotent adaptive execution. Evaluation/decision cycles reuse the existing Elara and CLARIO-AI boundaries.
- Current research: Nova derives its typed request from the persisted CALA plan via the shared request builder, uses the backend Tavily adapter for up to three deterministic queries, validates/ranks actual results, and persists one session-owned shared research package. Query refinement and downstream worker invocation are not implemented.
- Current teaching: Mira receives a typed task with the CALA-selected concept, session context, available learner-profile preference, and persisted shared research package. Mira is not dispatched when the package has no validated sources. The existing configured AI provider returns structured teaching; Mira validates concept/level/source IDs and the result is persisted once per session.
- Current critical thinking: after Mira is ready, Ayan receives the saved plan context, Mira response, and Mira-cited sources verified against the session's research package. Ayan generates a single structured reasoning prompt at the level Mira used; it does not grade an answer or control progression. One response is persisted per session.
- Current practical application: after Ayan is ready, Kira receives the persisted CALA goal/session context, Mira and Ayan result references, and research source summaries/IDs from the same session package. Kira generates one structured scenario/task, preserves the CALA learner level, and can cite only package source IDs. It does not collect or grade answers or control progression. One result is persisted per session.
- Current quiz: after Kira is ready, CLARIO-AI selects an initial difficulty from the persisted CALA learner-level estimate and dispatches Zayn to generate exactly five multiple-choice questions for the current concept. EASY/MEDIUM/HARD uses 30/60/90 seconds per question. The answer key and explanations are stored separately from learner-facing question JSON. Submissions are validated against the quiz's questions/options, and correctness is persisted privately; APIs do not return answers, explanations, scores, or correctness.
- Current evaluation: after quiz submission, CLARIO-AI derives aggregate quiz metrics from the private answer key/submission and dispatches Elara with teaching coverage and scoped worker context. Ayan/Kira learner responses are explicitly unavailable. Elara returns typed concept strength/weakness, evaluation confidence, evidence summary, and an advisory difficulty signal; CLARIO-AI retains decision authority.
- Current adaptive decision: CLARIO-AI applies deterministic, concept-specific rules after evaluation and persists the action plus `session_concept_performances`. Mastery requires strong evidence, at least 80% quiz accuracy, and at least 0.70 evaluation confidence. Weak evidence selects reteaching (and reduces difficulty only when Elara signals decrease); insufficient evidence selects retest without mastery. Reteach/retest output is stored by attempt and the previous quiz remains unchanged. A per-session/concept execution guard defaults to three attempts and reports an explicit limit state without marking mastery. Roadmap completion/unlock requires all mapped concepts at the boundary to be mastered; empty future levels remain locked.
- Legacy orchestration: `NovaOrchestrator`, in-memory context and deterministic adaptive policy remain under `backend/app/orchestrator` for older learning routes; the new CALA-to-research session path is CLARIO-AI controlled.
- Agent/provider layer: generic agents under `backend/app/agents`, provider abstraction and Gemini/mock under `backend/app/ai`.
- Storage: one configured SQLite database and one migration runner; migrations 001–013. Migration 013 adds attempt-number uniqueness across teaching, thinking, practical, quiz, and evaluation records, plus the session-owned `clario_adaptive_executions` table. The older profile-owned `concept_performances` table remains separate.

## Status boundary

Current code includes CLARIO-AI orchestration through persisted deterministic post-Elara decisions and automatic concept-specific reteach/retest execution. It does not yet include Ayan/Kira learner-response capture/grading, automated research query refinement, three physical databases, persisted gamification, or final report. Research validation/package creation is assigned to Nova; teaching to Mira; prompt generation to Ayan; practical-task generation to Kira; quiz generation to Zayn; evaluation to Elara; final learning decisions to CLARIO-AI. Keep current implementation and target design distinct in diagrams, tests, and release claims.
