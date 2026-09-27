# CLARIO V2 Implementation Status and Order

The current source of truth is the latest CLARIO V2 Master Prompt. This plan records the implemented foundation separately from the unfinished target.

## Completed foundation

- Canonical React/TypeScript/Vite frontend entry and TSX source of truth.
- Development curriculum seed in the existing schema/migration architecture.
- Email/password registration and login with password hashing; personal profile setup.
- One-time five-answer Mind Profile.
- Exactly four per-session inputs with strict schema and isolated persistence.
- Learner-profile compatibility anchor created for first session so concept-performance foreign keys can be satisfied; learner level/confidence are explicitly unassessed sentinels.
- CALA deterministic structured plan contract, session-owned persistence, owner-checked API, and a Level 1 unlocked roadmap with future levels locked.
- Frontend four-input → CALA loading → roadmap display → CLARIO-AI coordination loading/error/source display.
- CLARIO-AI orchestration foundation: saved-CALA-plan initialization, session-owned persisted state and timestamps, deterministic research transitions/failure state, Nova dispatch through an internal research service, package reference and package in returned context.
- Mira teaching foundation: typed CALA/session/research task, existing AI-provider structured generation, validated source references, persisted one-per-session response, and CLARIO-AI-owned teaching states.
- Nova research-only worker using a backend Tavily adapter, a bounded set of deterministic queries, normalized result fields, URL/content/relevance validation and ranking, and a maximum of ten real sources.
- Owner-checked orchestration initialization/state/research APIs; the legacy research POST routes through CLARIO-AI for compatibility.
- Owner-checked research GET, one idempotently reused shared research package per session, and a frontend source list with loading/error handling.
- Migration 006 persists one CLARIO-AI orchestration record per session, with CALA plan and optional package references.
- Migration 007 persists one Mira teaching result per session and links it to the orchestration state.
- Ayan critical-thinking foundation: CLARIO-AI explicitly dispatches a typed Ayan task after Mira; Ayan returns a reasoning prompt (not an assessment), and one session-owned result is persisted and retrievable.
- Kira practical foundation: CLARIO-AI explicitly dispatches a typed task after Ayan; Kira returns a research-grounded real-world activity without grading or progression decisions, and one session-owned result is persisted/retrievable.
- Zayn assessment foundation: CLARIO-AI dispatches five-question quiz generation after Kira, owns difficulty selection, keeps answer keys/explanations server-side, validates submissions, and persists private correctness.
- Elara evaluation foundation: after quiz submission CLARIO-AI dispatches Elara with typed teaching/thinking/practical references and server-calculated quiz metrics. Ayan/Kira learner responses are explicitly unavailable. Evaluations are session/orchestration/quiz-owned, idempotent, and learner-safe; Elara does not make progression or remediation decisions.
- CLARIO-AI adaptive decision foundation: deterministic post-Elara rules select CONTINUE, RETEACH, RETEST, REDUCE_DIFFICULTY, INCREASE_DIFFICULTY, or roadmap-supported completion actions. Decision outcomes and session-owned concept performance persist with attempt/remediation counts; only the evaluated concept changes. Empty future roadmap levels are not unlocked.

## Target work still pending

- Secure authentication and configured OAuth provider(s).
- Dynamic learner state/level assessment; remove legacy manual-level pathways.
- Expand CALA to use evaluated evidence and a curriculum-level roadmap only after evidence/rules are specified.
- Full CLARIO-AI learning state machine, evidence aggregation and decision engine for later worker handoffs (CALA-to-research-to-Mira teaching-to-Ayan prompt generation is implemented).
- Automated query refinement and stronger evidence validation. Current Nova uses a bounded deterministic query set, filters/ranks returned results, and persists the selected sources in a shared package.
- Target learner response capture/grading for Ayan and Kira; current Elara evidence is limited to teaching coverage and submitted quiz evidence.
- Automatic CLARIO-AI remediation cycle (Mira reteaching, fresh Zayn retest, and repeated Elara evaluation) and learner-response evidence for Ayan/Kira.
- Three separate SQLite databases with migration/ownership design.
- Persisted history, XP, streaks, daily goals, achievements; final report.
- End-to-end and frontend tests for the target user journey.
- Documentation verification as implementation advances.

## Recommended controlled order

1. Establish the durable learner-state model anchored to the current profile/session flow; eliminate dependence on fabricated legacy profile fields.
2. Extend the current CLARIO-AI foundation into durable learning events/evidence and later worker routing without delegating orchestration to a worker.
3. Add research query refinement and strengthen source validation based on explicit quality criteria.
4. Add learner-response capture for Ayan and Kira; expand Elara's evidence only from real persisted responses.
5. Wire persisted `RETEACH`/`RETEST` decisions into a concept-isolated Mira → Ayan → Kira → Zayn → Elara repeat cycle; then complete level/goal reporting when curriculum supports it.
6. Design and migrate to the three-database architecture only after data ownership and migration plan are tested.
7. Add persisted rewards/history and finish responsive product UI, dedicated source container, and end-to-end validation.

Do not mark a target capability complete from a placeholder, mock response, UI-only value, or legacy implementation with different ownership.
