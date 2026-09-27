# ADR-004: SQLite Migrations and ORM

## Status

Accepted for current single-database persistence; target multi-database implications remain pending.

## Current implementation

SQLAlchemy models and repositories are under `backend/app/models`. `backend/app/core/migrations.py` applies ordered SQL files from `database/migrations/` and stores applied versions in one `schema_migrations` table. Migrations 001–009 define the current schema, curriculum seed, profile/session-input additions, session-owned CALA plan persistence, one session-owned research package, one session-owned CLARIO-AI orchestration state, and one session-owned Mira teaching, Ayan thinking, and Kira practical result linked to orchestration.

## Target requirements before migration

Three separate SQLite databases require independent migration histories and explicit repository/session ownership. Define atomicity limits, cross-database identifiers, upgrade order, backup, rollback, and test strategy before changing runtime database wiring.
