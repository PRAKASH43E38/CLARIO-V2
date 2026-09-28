# CLARIO V2 Specialized Workers

All workers receive a scoped task from CLARIO-AI and return structured evidence. No worker independently controls the learner's overall journey.

| Target worker | Responsibility | Current reusable implementation |
|---|---|---|
| Nova | Tavily/web research, relevance validation/refinement, source package preparation. | `backend/app/agents/nova_research.py` performs bounded Tavily research, validation/ranking, and package assembly when dispatched by CLARIO-AI. `backend/app/agents/research.py` remains a generic LLM research foundation. Automated query refinement is not implemented. |
| Mira | Explain the CALA-selected concept using persisted learner/session context and Nova's validated shared research package. | `backend/app/agents/mira_teaching.py` accepts a typed task, uses the configured AI provider, validates concept/level/source references, and returns a typed response. It does not search, assess, or make workflow decisions. `backend/app/agents/teaching.py` remains the legacy teaching implementation. |
| Ayan | Generate one why/how reasoning prompt for the concept Mira taught. | `backend/app/agents/ayan_thinking.py` accepts a typed task with Mira's persisted teaching result, the CALA/session context, and only validated source references cited by Mira. It uses the configured AI provider, validates concept/level/source IDs, and does not receive or grade a learner answer. |
| Kira | Turn the current taught concept into a grounded real-world practice activity. | `backend/app/agents/kira/practical.py` receives typed CALA/session context, persisted Mira/Ayan references, and source context from the same session's `SharedResearchPackage`. It validates source IDs and preserves the supplied learner level; it does not grade or make workflow decisions. |
| Zayn | Generate a five-question multiple-choice challenge for the current concept at the difficulty selected by CLARIO-AI; retain answer keys and explanations on the server. | `backend/app/agents/zayn/quiz.py` validates provider output. CLARIO-AI persists learner answers and correctness privately; answer keys are never exposed to learners. |
| Elara | Evaluate current-concept teaching coverage and submitted quiz evidence; represent uncaptured Ayan/Kira learner responses as unavailable. | `backend/app/agents/elara/evaluation.py` returns typed strength/weakness, evidence summary, evaluation confidence, quiz performance, and advisory difficulty signal. Elara does not decide mastery/progression/remediation or apply the signal. |

CLARIO-AI dispatches Nova, Mira, Ayan, Kira, Zayn, and Elara in the current vertical slice. Ayan follows Mira, Kira follows Ayan, Zayn follows Kira, and Elara follows quiz submission. Each result is persisted per session. After Elara, CLARIO-AI—not an agent—applies deterministic rules, then persists the concept-specific decision and performance. Weak evidence can select reteaching and advisory-signal-based difficulty reduction; insufficient evidence selects a retest without mastery. Automatic worker-loop execution remains pending.

## Shared research context

Downstream workers should receive one validated shared research package rather than make unverified source claims. Mira receives the current session's persisted package; source references in its response are accepted only when the source ID exists in that package. Ayan receives only sources Mira cited, checked against that same package. Kira receives summary/snippets/source IDs from the same session package and cannot search; its generated source IDs are checked against that package. Never fabricate URLs or citations. Target ten relevant validated sources when sufficient quality results exist; fewer are valid when fewer pass validation.

## Adaptive sequence

`Mira → Ayan → Kira → Zayn → Elara → CLARIO-AI decision` is implemented as explicit handoffs through a persisted current-concept outcome. When that persisted decision selects `RETEACH`/`REDUCE_DIFFICULTY`, CLARIO-AI runs a new concept-specific Mira → Ayan → Kira → Zayn attempt; `RETEST` runs a new Zayn attempt only. Results are persisted by attempt, prior quiz rows remain unchanged, and Zayn rejects repeated question IDs or exact question wording. The submitted attempt returns through Elara and CLARIO-AI. No worker makes workflow decisions. Ayan/Kira learner responses are not captured and Elara marks them unavailable.

For a weak concept, CLARIO-AI directs Mira to explain differently, Kira to offer a different application example, and Zayn to retest. Previously mastered concepts remain mastered.
