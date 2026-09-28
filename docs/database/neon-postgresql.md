# Neon PostgreSQL

CLARIO connects to Neon PostgreSQL from the backend through SQLAlchemy.
The frontend does not connect to the database directly and does not require
the Neon JavaScript client for persistence.

## Configuration

For production, set `DATABASE_URL` in the backend deployment environment to
the PostgreSQL connection string copied from the linked Neon branch. Keep the
value in deployment secret settings, never in source control or frontend
configuration.

For local development, `DATABASE_URL` can remain SQLite. To test against Neon,
set the Neon connection string as `DATABASE_URL`; there is no provider-specific
database URL override or fallback.

The SQLAlchemy layer accepts `postgresql://` and
`postgresql+psycopg2://` URLs. Neon connection strings enable SSL; preserve the
SSL query parameter supplied by Neon.

## Schema migrations

SQLite continues to use the existing forward-only scripts in
`database/migrations/`. PostgreSQL uses Alembic and a separate baseline
representing the current SQLAlchemy schema. The baseline includes the CLARIO
tables, foreign keys, indexes, uniqueness rules, and validation constraints;
it does not execute SQLite SQL or insert development curriculum seed data.

Apply PostgreSQL migrations as a deployment release/pre-start step before
serving traffic:

```powershell
python -m backend.app.core.migrations upgrade
```

The migration is additive and rerun-safe. Its initial downgrade is deliberately
disabled to prevent accidental deletion of learner data. Back up and verify a
database before applying future schema changes.

## Tests and existing SQLite data

The normal test suite continues to create isolated SQLite databases and apply
the existing SQLite migrations. PostgreSQL integration tests run only when
`CLARIO_TEST_DATABASE_URL` points to a disposable PostgreSQL test database.
Those tests wrap their data changes in a transaction and roll them back.

Creating the PostgreSQL schema does not copy records from a local SQLite
database. Plan and verify any required data import separately; do not delete
the SQLite database as part of connecting Neon.

## Online backend and frontend configuration

Start the API with:

```text
python -m backend.app.main
```

The backend binds to `0.0.0.0` and reads its port from `PORT` (default 8000).
Set `ENVIRONMENT=production` to reject SQLite at startup, and set
`CORS_ORIGINS` to a comma-separated list of the deployed frontend origins.
The `/health` endpoint is the configured application health route.

For a separately hosted frontend, set the build-time `VITE_API_BASE_URL` to
the backend origin without a trailing slash; the app appends `/api/v1`.
When frontend and API share an origin, leave it unset to use the relative
`/api/v1` path. The frontend never receives a database URL or database secret.
