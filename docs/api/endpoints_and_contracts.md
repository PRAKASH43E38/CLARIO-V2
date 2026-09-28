# API Endpoints and Contracts

The active API is implemented in `backend/app/api/routes/` with contracts in `backend/app/api/schemas/__init__.py`. Routes are mounted under `/api/v1`; health is exposed at `/health`. Active responses are direct JSON model payloads, not a universal `data` wrapper.

## Current route groups

- Auth: register, login, status (`auth.py`).
- Personal/Mind Profile and legacy learner profile (`learner.py`).
- Legacy onboarding (`onboarding.py`).
- Four-input new session, legacy topic-based session start, session state, session-owned CALA plans, research packages (`sessions.py`, `cala.py`, `research.py`).
- CLARIO-AI orchestration initialize/state/research continuation/teaching/thinking/practical/quiz/evaluation dispatch, quiz submission, and worker-result retrieval (`orchestration.py`).
- Thinking, practical, quiz, and remediation actions (`learning.py`).
- Dashboard and legacy concept roadmap (`dashboard.py`, `roadmap.py`).
- Health (`health.py`).

## Active new-session input

Exactly four fields are accepted:

```json
{
  "task": "A concrete task",
  "goal": "Desired outcome",
  "learner_state": "Prior knowledge or current blocker",
  "interest": "Useful context for examples"
}
```

Extra fields, including manual `current_level`, are rejected. Inputs are stored one-to-one with the created session. The current endpoint selects the first seeded topic. The frontend then creates a CALA plan and initializes CLARIO-AI; all new-path research dispatch is owned by the orchestration service.

## CALA and Nova research

The CALA plan is persisted per session and accessed through owner-checked POST/GET routes. CLARIO-AI orchestration POST initializes one state record from the saved plan, GET reloads it and its package/results, and the research continuation dispatches through an internal research service to Nova. Nova uses bounded deterministic Tavily queries, normalizes returned fields, filters/ranks candidates, and persists up to ten validated source records. Tavily must be configured on the backend; failures persist as `RESEARCH_FAILED` and do not create fabricated results. Once research is ready, the teaching endpoint assembles a typed Mira task from saved CALA/session context and the same session's package, dispatches through the existing AI provider abstraction, validates the response, and persists it. Teaching provider/response failures persist `TEACHING_FAILED` without changing the saved research-package reference. The old research POST remains as a compatibility endpoint but also dispatches through CLARIO-AI.

After Mira is ready, the owner-checked thinking endpoint assembles an Ayan task from the persisted CALA plan, Mira response, and Mira-cited source references validated against the same session's research package. Ayan creates one structured reasoning prompt at Mira's learner level; it neither receives nor grades a learner answer. The result is persisted once per session, surfaced through orchestration GET, and also available from the owner-checked thinking-result GET. Provider/output failures are recorded as `THINKING_FAILED`; repeat POST requests reuse an existing persisted result.

After Ayan is ready, the owner-checked practical endpoint assembles a Kira task from the saved CALA concept/learner context, persisted Mira and Ayan results, and same-session research summary/snippets/source IDs. Kira produces a practical scenario/task without searching, assessing answers, or deciding progression. Its output source IDs are validated against that session's package. Results are stored once per session; orchestration GET and the owner-checked practical-result GET expose the result. Provider/output failures persist `PRACTICAL_FAILED`, and duplicate POST requests reuse the existing result.

After Kira is ready, CLARIO-AI selects an initial difficulty from the persisted CALA level estimate and dispatches Zayn to generate exactly five multiple-choice questions for the current concept (30/60/90 seconds per question for EASY/MEDIUM/HARD). Generation and presentation are session-owned and idempotent. The quiz API excludes correct answers and explanations; answer submission validates every question/option and stores answer keys/correctness server-side. Submission returns only quiz ID, status, and timestamp.

After Zayn submission, CLARIO-AI validates the saved Mira/Ayan/Kira outputs and session-owned quiz, computes quiz counts/accuracy from private answer-key data, and sends Elara a strict task without raw answers, answer keys, or correctness maps. Elara returns a typed, learner-safe evaluation. Ayan/Kira learner responses are not captured and are marked `unavailable`. Evaluation results are persisted once per session/orchestration/quiz. Routes are owner-checked `POST /sessions/{session_id}/orchestration/evaluate` and `GET /sessions/{session_id}/evaluation`. Orchestration transitions `QUIZ_SUBMITTED → EVALUATION_REQUESTED → EVALUATING → EVALUATION_READY` or `EVALUATION_FAILED`. Elara's difficulty signal is advisory; CLARIO-AI adaptive decisions remain pending.

After `EVALUATION_READY`, owner-checked `POST /sessions/{session_id}/orchestration/decide` applies deterministic CLARIO-AI rules; it accepts no client-supplied score, difficulty, status, or decision. GET `/sessions/{session_id}/decision` returns the persisted action, and GET `/sessions/{session_id}/concept-performance` lists this session's concept records. Strong + accuracy ≥80% + confidence ≥0.70 satisfies mastery; weak evidence selects reteaching (with concept-only difficulty reduction when signaled); insufficient evidence selects retest without mastery. Decision/performance are idempotently persisted and session isolated.

`POST /sessions/{session_id}/orchestration/decision/execute` executes that saved decision only. The matching GET `/sessions/{session_id}/orchestration/remediation` returns the persisted execution and typed context. Reteach runs Mira → Ayan → Kira → Zayn for the same concept; retest runs Zayn only, with a new attempt and distinct question IDs/content. The frontend submits through Elara and CLARIO-AI again automatically. Execution retries reuse the decision's persisted attempt. `CLARIO_MAX_REMEDIATION_ATTEMPTS` defaults to 3; the limit yields an explicit non-mastering state/result.

## Target contracts pending

Automatic reteaching/retesting, learner-response capture for Ayan/Kira, complete multi-level curriculum/progression, persisted rewards, and final reports remain pending. Design these contracts from the master prompt, not from legacy route response examples.

The current identity convention (`user_id` query parameter) is not secure authentication. Target APIs require a server-verifiable authenticated principal.
