# CLARIO V2 Adaptive Learning Loop

## Target owner and sequence

CLARIO-AI owns all transitions:

```text
Plan → Teach → Think → Apply → Quiz → Evaluate
                                      ├─ weak concept: Remediate → retest → Evaluate
                                      ├─ mastery: Advance to next concept/level
                                      └─ final level complete: Complete → Final Report
```

Mira teaches, Ayan probes reasoning, Kira validates application, Zayn assesses, and Elara aggregates evidence. Elara's recommendation is evidence for CLARIO-AI; it is not a transition command.

## Concept-specific remediation

When evaluation identifies a weak concept, CLARIO-AI must:

1. Keep mastered concepts mastered and retain their evidence.
2. Mark only the weak concept as remediating.
3. Reduce difficulty for that concept when the evidence supports it.
4. Ask Mira for an alternate explanation and Kira for a different application/example.
5. Have Zayn issue a fresh retest for the same concept.
6. Ask Elara to evaluate the new evidence and decide again.

Do not restart the whole topic or reuse the same question as a retest.

## Existing behavior (legacy)

`backend/app/orchestrator/adaptive_policy.py` contains deterministic thresholds and concept-targeted decisions; `backend/app/orchestrator/nova.py` currently owns sequencing and transitions. The current session context is reconstructed from recent activity records, and performance persistence requires a learner-profile anchor. This is a reusable foundation, not the target CLARIO-AI state machine.

## Implemented vertical slice

The current new-session path dispatches Nova research, Mira teaching, Ayan prompt generation, Kira practical-task generation, Zayn quiz generation/submission, and Elara evaluation through CLARIO-AI. CLARIO-AI then applies persisted deterministic decision rules and stores a session-owned concept-performance record.

Rules: strong + no weakness + quiz accuracy ≥80% + evaluation confidence ≥0.70 satisfies mastery; weak evidence selects `RETEACH`, and `REDUCE_DIFFICULTY` is selected only when Elara also signals decrease (and the concept is above EASY). Insufficient evidence selects `RETEST` and never marks mastery. Strong evidence + at least 80% quiz accuracy + an increase signal selects `INCREASE_DIFFICULTY` for that concept's next attempt; evaluation confidence must still reach 0.70 before the concept is marked mastered. Without an increase signal, meeting the full mastery condition selects `CONTINUE`; otherwise the concept is retested. Completion/unlock actions require all mapped concepts at the relevant roadmap boundary to be mastered. The current placeholder future levels are empty and remain locked. Only the evaluated concept's performance row is updated.

Quiz performance is calculated server-side using Zayn's private answer key and submitted answers. Elara evaluates teaching coverage and quiz evidence; Ayan/Kira learner responses remain unavailable and are not fabricated. Elara's difficulty signal is advisory; CLARIO-AI chooses any change. Decision states are `EVALUATION_READY → DECISION_REQUESTED → DECIDING → DECISION_READY` or `DECISION_FAILED`. The decision is persisted and idempotent. Automatic Mira reteaching, retest execution, learner-response capture, and progression through future levels remain unimplemented.
