# ADR-005: Deterministic Adaptive Decisions

## Status

Legacy adaptive policy remains reusable; its current NOVA ownership is superseded by the CLARIO V2 Master Prompt.

## Current implementation

`backend/app/orchestrator/adaptive_policy.py` defines score thresholds and difficulty adjustment rules. `NovaOrchestrator` currently invokes that policy and persists concept performance only when a learner-profile anchor is available.

## Target decision

Deterministic policy may remain an implementation mechanism, but CLARIO-AI owns the durable state machine and final transition. Evaluation evidence, current concept/level, attempt history, difficulty, remediation outcome, and next action must be persisted. Weakness is isolated to the relevant concept; mastered concepts are preserved. Thresholds and level-completion rules must be explicitly specified and tested before being treated as product policy.
