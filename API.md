# CLARIO V2 API

This document distinguishes active legacy-compatible endpoints from target contracts. Application routes are mounted under `/api/v1`; consult the FastAPI OpenAPI schema for exact active request/response models. Responses are generally direct JSON models, **not** a universal `data` envelope.

## Active route inventory

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service health. |
| POST | `/api/v1/auth/register` | Email/password registration. |
| POST | `/api/v1/auth/login` | Email/password login. |
| GET | `/api/v1/auth/status` | Read profile/Mind Profile completion by user ID. |
| GET / PUT | `/api/v1/profile` | Read/update personal profile. |
| GET / PUT | `/api/v1/mind-profile` | Read/save the one-time five-answer Mind Profile; repeat save returns conflict. |
| POST | `/api/v1/learning-session/create` | Create a session from exactly Task, Goal, Learner State, Interest. |
| POST | `/api/v1/sessions/{session_id}/cala-plan` | Generate and persist the deterministic CALA plan/Level 1 roadmap; idempotently returns the existing plan. |
| GET | `/api/v1/sessions/{session_id}/cala-plan` | Retrieve that session's persisted CALA plan. |
| POST | `/api/v1/sessions/{session_id}/orchestration` | Initialize or load CLARIO-AI state from the persisted CALA plan; idempotently returns current state. |
| GET | `/api/v1/sessions/{session_id}/orchestration` | Retrieve persisted orchestration state and, when available, the session's research, teaching, thinking, and practical results. |
| POST | `/api/v1/sessions/{session_id}/orchestration/research` | Continue the CLARIO-AI workflow by dispatching the research step; returns current state and package when successful. Requires backend `TAVILY_API_KEY` when no package exists. |
| POST | `/api/v1/sessions/{session_id}/orchestration/teach` | Dispatch Mira through CLARIO-AI after research is ready; returns orchestration context and the persisted teaching response. |
| GET | `/api/v1/sessions/{session_id}/teaching` | Retrieve the owner's persisted Mira teaching response. Current workflow status is available from orchestration GET. |
| POST | `/api/v1/sessions/{session_id}/orchestration/think` | After Mira is ready, dispatch Ayan through CLARIO-AI; returns state and the persisted reasoning prompt. Repeated requests reuse the session result. |
| GET | `/api/v1/sessions/{session_id}/thinking` | Retrieve the owner's persisted Ayan reasoning prompt. This is not a learner-answer or grading endpoint. |
| POST | `/api/v1/sessions/{session_id}/orchestration/practical` | After Ayan is ready, dispatch Kira through CLARIO-AI; returns state and persisted activity. Duplicate requests reuse the result. |
| GET | `/api/v1/sessions/{session_id}/practical` | Retrieve the owner's persisted Kira practical activity; learner answers are not submitted or graded here. |
| POST | `/api/v1/sessions/{session_id}/orchestration/quiz` | After Kira is ready, have CLARIO-AI dispatch Zayn to generate a five-question quiz; repeated requests reuse the persisted quiz. |
| GET | `/api/v1/sessions/{session_id}/quiz` | Retrieve the learner-safe Zayn quiz presentation; answer keys and explanations are excluded. |
| POST | `/api/v1/sessions/{session_id}/quiz/submit` | Submit one answer per question; returns only quiz ID, submitted status, and timestamp. |
| POST | `/api/v1/sessions/{session_id}/orchestration/evaluate` | After quiz submission, dispatch Elara and return a learner-safe evaluation of the current concept. |
| GET | `/api/v1/sessions/{session_id}/evaluation` | Retrieve the owner's persisted Elara evaluation. |
| POST | `/api/v1/sessions/{session_id}/orchestration/decide` | Apply deterministic CLARIO-AI rules to the persisted Elara evaluation and save the concept-specific outcome. |
| GET | `/api/v1/sessions/{session_id}/decision` | Retrieve the persisted learner-safe CLARIO-AI decision. |
| GET | `/api/v1/sessions/{session_id}/concept-performance` | Retrieve session-owned concept performance records. |
| POST | `/api/v1/sessions/{session_id}/research` | Backward-compatible research request; internally dispatches through CLARIO-AI and returns the legacy package response. |
| GET | `/api/v1/sessions/{session_id}/research` | Backward-compatible owner-checked retrieval of the session's package. |
| POST | `/api/v1/session/start` | Legacy session start by topic ID and legacy learner profile. |
| GET | `/api/v1/session/{session_id}/state` | Read session/topic/concept/activity and stored session inputs. |
| POST | `/api/v1/onboarding/submit` | Legacy five-field onboarding; not the active new-session form. |
| GET | `/api/v1/onboarding/status` | Legacy onboarding completion check. |
| GET | `/api/v1/learner/profile` | Legacy learner profile. |
| GET | `/api/v1/dashboard` | Dashboard data. |
| GET | `/api/v1/roadmap` | Legacy seeded-topic concept roadmap. |
| POST | `/api/v1/session/action` | Legacy activity action. |
| POST | `/api/v1/thinking/submit` | Legacy thinking response path. |
| POST | `/api/v1/practical/submit` | Legacy practical/quiz transition. |
| POST | `/api/v1/quiz/generate` | Legacy quiz generation. |
| POST | `/api/v1/quiz/submit` | Legacy quiz/evaluation path. |
| POST | `/api/v1/remediation/trigger` | Legacy remediation path. |

## Four-input session contract

```json
{
  "task": "What I need help doing",
  "goal": "What I want to be able to do",
  "learner_state": "What I know or where I am stuck",
  "interest": "Context for relevant examples"
}
```

Only these four keys are accepted; unknown keys are rejected. Inputs are stored against one session and remain isolated from later sessions. The current endpoint selects the first seeded topic. CALA uses that session's persisted inputs for its initial plan; they are not yet supplied to downstream agent execution.

## CALA planning contract

After session creation, the frontend calls the session-owned CALA endpoint. The API verifies the supplied current user ID, checks session ownership, reads that session's four stored inputs and available Mind Profile/profile data, then returns and persists a typed plan. The response includes the inferred learner level and reason, confidence state, explicit weakness status, four session inputs, roadmap levels/topics/concepts, and planned initial agent routing. Routing is descriptive only; CALA does not execute workers.

`POST` is idempotent per session; `GET` only returns a plan when the session belongs to the requested user. Level 1 starts unlocked with the real session curriculum and `not_started` completion; future levels remain locked and contain no invented curriculum. The current planner treats `unassessed` and confidence `0` as unknown compatibility sentinels. Insufficient level evidence defaults to Beginner; absent confidence/weakness evidence stays unknown.

## CLARIO-AI orchestration and Nova research

CLARIO-AI is the central controller for this implemented session slice; Nova remains only a research worker. The initialize endpoint requires a saved CALA plan and creates or returns one session-owned orchestration record in `CALA_READY`. The research continuation persists `RESEARCH_REQUESTED`, then `RESEARCHING`, and on success `RESEARCH_READY`; known provider/configuration failures persist `RESEARCH_FAILED`. Repeated initialization and successful research requests reuse the same state/package. The GET context includes the package itself when available.

Invalid or non-owned sessions return 404; initialization or research without a persisted CALA plan returns 409; an unconfigured search provider returns 503; and a known provider failure returns 502. A failed research state can be retried through the same research continuation endpoint.

CLARIO-AI reads the persisted CALA plan and uses the existing research request builder; it does not take topic/concept input from the frontend or formulate its own search queries. Nova makes at most three deterministic search queries with at most five Tavily results each. Results are normalized, URL-canonicalized, deduplicated, screened for basic content/relevance and noisy URLs, ranked, capped at two sources per exact host and ten total. Fewer than ten are valid when fewer pass; no source is fabricated. Automated query refinement is not implemented yet.

The persisted `SharedResearchPackage` records its owning session, request context, selected source metadata, retrieved-excerpt summary, query counts, validation counts/status, and timestamp. One package and one orchestration record are stored per session. If Tavily is unconfigured, the orchestration research endpoint returns 503 and persists `RESEARCH_FAILED`; provider failures return 502 with the same failure state. These routes follow the current user-ID convention, which is not a secure authentication boundary.

## Target API not yet implemented

Automatic reteaching/retesting cycles, progression beyond mapped curriculum, automated query refinement, persisted learning events/rewards, and the final report remain pending. Authentication also needs a server-verifiable session/token contract; current endpoints use a supplied user ID and are not a secure production authentication boundary.

## Mira teaching contract

Mira receives a typed task assembled only from the persisted CALA plan, session-owned research package, and available learner-profile preference. Its level comes from CALA; unavailable preference remains `null`. The task includes the current unlocked topic's first concept and a fixed teaching instruction. Mira uses the existing configured AI provider to return a structured explanation, key points, examples, level/style, and source IDs. CLARIO-AI validates the returned concept/level/source IDs and resolves references only to sources in the package.

The persisted response includes the session, concept, explanation, key points, examples, CALA learner level, teaching style, validated source references, and generation timestamp. It is uniquely session-owned and references its orchestration row. State advances `RESEARCH_READY → TEACHING_REQUESTED → TEACHING → TEACHING_READY`; provider or malformed-output failures persist `TEACHING_FAILED`, without changing the existing research-package reference. Repeated teaching requests reuse the session's existing result.

If the research package contains no validated sources, Mira is not invoked; the request returns 409 and leaves orchestration at `RESEARCH_READY` so no unsupported teaching content is produced.

## Zayn quiz contract

Once Kira is ready, CLARIO-AI derives the quiz difficulty from CALA's persisted starting-level estimate (`beginner → EASY`, `intermediate → MEDIUM`, `advanced → HARD`) and asks Zayn for exactly five distinct multiple-choice questions for the current concept. Time limits are 30, 60, or 90 seconds per question for EASY, MEDIUM, or HARD, respectively. Zayn does not select difficulty or decide progression.

Quiz generation moves orchestration through `QUIZ_REQUESTED → QUIZ_GENERATING → QUIZ_READY`; provider or output failures persist `QUIZ_FAILED`. Successful quiz creation is idempotent per session/orchestration. GET moves an unstarted quiz to `IN_PROGRESS`. Submission requires exactly one valid option for each quiz question and moves orchestration to `QUIZ_SUBMITTED`. Repeating the identical submission is safe; a different second submission conflicts.

The learner-facing quiz and submission response deliberately omit correct answers, explanations, and per-question correctness. Answers and correctness are stored server-side for evaluation.

## Elara evaluation contract

After a Zayn quiz is submitted, `POST /orchestration/evaluate` validates the persisted CALA plan, Mira/Ayan/Kira results, and same-session quiz. CLARIO-AI calculates quiz question counts and accuracy from the server-side answer key and submission. Elara receives only those aggregate metrics, teaching coverage, and scoped worker context; raw answers, answer keys, correctness maps, internal prompts, and provider responses are not returned to the frontend.

Elara returns concept strength/weakness, quiz performance, evaluation confidence, evidence summary, and an advisory difficulty signal. Ayan and Kira learner responses are not currently captured; their evidence is explicitly `unavailable`, not inferred. Elara does not decide progression, mastery, remediation, or a difficulty change. State transitions are `QUIZ_SUBMITTED → EVALUATION_REQUESTED → EVALUATING → EVALUATION_READY`, with `EVALUATION_FAILED` for provider, invalid-output, or persistence failures. Repeated requests for the same submitted quiz reuse the persisted evaluation. GET is owner-checked and returns 404 when no evaluation exists.

## CLARIO-AI adaptive decision

`POST /orchestration/decide` is deterministic and accepts no learner-controlled decision fields. A concept is mastered only when Elara strength is `strong`, weakness is `none`, quiz accuracy is at least 80%, and evaluation confidence is at least 0.70. Weak evidence selects `RETEACH`; if Elara signals `decrease`, CLARIO-AI selects `REDUCE_DIFFICULTY` for that concept only (difficulty bottoms at EASY). Insufficient evidence selects `RETEST` and never marks the concept mastered. A mastered concept with Elara's `increase` signal and quiz accuracy of at least 80% receives a concept-specific `INCREASE_DIFFICULTY`; otherwise the outcome is `CONTINUE`. Complete-level/unlock/goal actions are emitted only when the persisted CALA roadmap's mapped concepts support them. Current empty placeholder levels are not unlocked.

Migration 012 stores decisions in `adaptive_decisions` and per-session/per-concept status in `session_concept_performances`; migration 013 adds attempt-owned worker results and `clario_adaptive_executions`. The legacy profile-owned `concept_performances` table remains separate. Repeated decision requests for the same evaluation return the persisted result.

Owner-checked `POST /sessions/{session_id}/orchestration/decision/execute` accepts no decision parameters; it executes the latest persisted server-side decision. `GET /sessions/{session_id}/orchestration/remediation` returns its typed execution/remediation context and learner-safe quiz when available. `RETEACH`/`REDUCE_DIFFICULTY` execute a new Mira → Ayan → Kira → Zayn attempt for the same concept; `RETEST` creates a new Zayn quiz for that concept. Quiz attempts have new IDs and question IDs/content are checked against earlier questions. Submitted attempts continue through the existing Elara evaluation and CLARIO-AI decision endpoints; the frontend automatically evaluates and routes each submitted adaptive attempt. Repeated execution reuses the same execution and results. `CLARIO_MAX_REMEDIATION_ATTEMPTS` configures the per-session/concept execution cap; default is 3. Reaching it returns explicit `LIMIT_REACHED` and does not mark mastery.

Decision execution states include `REMEDIATION_REQUESTED → REMEDIATING`, worker-specific stage states, `REMEDIATION_FAILED`, `RETEST_REQUESTED`, `RETEST_FAILED`, `REMEDIATION_LIMIT_REACHED`, and `DECISION_APPLIED`. Quiz/evaluation/decision cycles continue through the existing states. Provider failures persist an explicit failure state, and retry resumes the same decision execution.
