# ADR-002: Orchestration Ownership

## Status

Legacy decision superseded by the CLARIO V2 Master Prompt.

## Legacy implementation

The original code routes agents through `NovaOrchestrator`. This accurately records current behavior but is no longer the target design.

## Target decision

CLARIO-AI is the single orchestration and decision engine. Nova is the research worker. Mira, Ayan, Kira, Zayn, and Elara are scoped workers. Workers do not control the global learning journey or invoke each other peer-to-peer. Elara evaluates evidence; CLARIO-AI chooses remediation, advancement, or completion.
