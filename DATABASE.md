# CLARIO V2 Database Architecture

The target is three separate SQLite databases, as required by the CLARIO V2 Master Prompt. The current code has **not** migrated to that target.

## Current state

One SQLite database is configured through `DATABASE_URL`, one SQLAlchemy engine/session is used, and the migration runner maintains one `schema_migrations` table. The repository contains `clario.db`; application database selection remains configuration-dependent.

Migrations:

1. `001_initial_schema.sql` — users, legacy learner profiles, curriculum, concept performance, sessions, activities, responses, evaluations.
2. `002_seed_development_curriculum.sql` — ordered/described Decision Trees concepts.
3. `003_profiles_and_session_inputs.sql` — personal profile fields, one-to-one Mind Profile, one-to-one session inputs.
4. `004_cala_plans.sql` — one session-owned structured CALA plan per learning session, cascading on session deletion.
5. `005_research_packages.sql` — one session-owned serialized `SharedResearchPackage` per learning session, cascading on session deletion.
6. `006_clario_orchestrations.sql` — one persisted CLARIO-AI state per session, referencing its saved CALA plan and optional research package.
7. `007_mira_teaching_results.sql` — one session-owned typed Mira response per orchestration.
8. `008_ayan_thinking_results.sql` — one session-owned typed Ayan thinking prompt per orchestration, cascading with its session or orchestration.
9. `009_kira_practical_results.sql` — one session-owned Kira practical activity per orchestration and concept, cascading with its session, orchestration, or concept.
10. `010_zayn_quiz_results.sql` — one session-owned Zayn quiz per orchestration/concept, with learner-facing questions stored separately from the server-only answer key and submitted correctness.
11. `011_elara_evaluations.sql` — one session/orchestration evaluation tied to its submitted quiz and current concept, with typed evaluation JSON and quiz performance.
12. `012_concept_performance.sql` — adds `session_concept_performances` for concept-scoped adaptive status and `adaptive_decisions` for idempotent CLARIO-AI decision records. The existing profile-owned `concept_performances` table is unchanged.

Tables: `users`, `learner_profiles`, `mind_profiles`, `topics`, `concepts`, legacy `concept_performances`, `session_concept_performances`, `adaptive_decisions`, `learning_sessions`, `session_inputs`, `cala_plans`, `research_packages`, `clario_orchestrations`, `teaching_results`, `thinking_results`, `practical_results`, `quiz_results`, `elara_evaluations`, `activities`, `learner_responses`, `evaluations`, `schema_migrations`.

Models live in `backend/app/models/`; persistence helpers are in `repositories.py`. Concept performances reference `learner_profiles`; sessions reference users and topics; session inputs cascade with their session; activities/responses/evaluations retain their current foreign-key chain.

The current four-input session path creates one compatibility learner-profile anchor if the user lacks one. The first session's goal/interest and Mind Profile explanation preference provide legacy compatibility values; `current_level="unassessed"` and `initial_confidence=0` are sentinels, not learner evidence. Later sessions do not overwrite that account-level anchor. CALA reads the inputs and profile but does not mutate the Mind Profile or compatibility anchor. It stores the complete structured plan JSON in `cala_plans`, uniquely keyed by session ID and deleted with that session. The research worker's complete `SharedResearchPackage` JSON is stored in `research_packages`, uniquely keyed by session ID. CLARIO-AI's `clario_orchestrations` row stores the CALA plan reference, current state/step and optional research package reference, uniquely keyed by session. `teaching_results`, `thinking_results`, and `practical_results` store one typed Mira, Ayan, and Kira result per session/orchestration, with cascading session/orchestration foreign keys; practical results also reference their curriculum concept and store source IDs as JSON text. `quiz_results` stores one quiz per session/orchestration, separates safe question JSON from its server-only answer key, and records submitted answers and correctness without exposing them through learner-facing APIs. `elara_evaluations` stores one structured Elara result per session/orchestration/submitted quiz, including quiz metrics, strength/weakness, evaluation confidence, advisory difficulty signal, and evidence summary. It references the same session, orchestration, concept, and quiz with cascading foreign keys. Neither answer keys nor private correctness details are included in Elara's learner-safe API output. Ayan/Kira learner responses remain unavailable and are explicitly represented as such; no responses are fabricated. Four inputs, packages, orchestration state, and worker results remain session-scoped.

The original `concept_performances` table is account/profile-owned for legacy activity routes. Migration 012 adds the separate `session_concept_performances` table so the new adaptive path is session-isolated without rewriting historical schema. It is unique by `(session_id, concept_id)`, stores the chosen difficulty for the next attempt and mastery/evidence counters, and references its latest Elara evaluation. `adaptive_decisions` stores the deterministic CLARIO-AI outcome and references the same session, orchestration, concept, and evaluation; uniqueness by orchestration/evaluation makes retries idempotent while allowing future evaluation cycles. Both tables cascade on deletion of their owning session/evidence.

## Target and gap

The target separates storage across three SQLite databases, with ownership for identity/profile, curriculum/research knowledge, and learning/session/progress data to be finalized against the master prompt. Current persistence has no multiple engines, database-specific repositories/migrations, cross-database reference strategy, or migration/rollback plan.

Do not split or migrate databases until ownership, identifiers, consistency, and migration sequencing are designed and tested.
