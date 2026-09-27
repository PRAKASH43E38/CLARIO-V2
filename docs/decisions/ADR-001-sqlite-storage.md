# ADR-001: SQLite Storage

## Status

Accepted for the current implementation; **superseded as the target topology** by the CLARIO V2 Master Prompt's three-database requirement.

## Current decision

The existing app uses a single SQLite URL, SQLAlchemy engine/session, and migration history. It remains the current storage implementation.

## Target direction

CLARIO V2 requires three separate SQLite databases. Before implementation, specify ownership, identifiers, cross-database references, transaction expectations, migration sequencing, and rollback/recovery. Do not treat this ADR as permission to keep one database in the completed target.
