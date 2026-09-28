import os
import sqlite3
import sys
from pathlib import Path
from typing import List


def run_migrations(db_path: str, migrations_dir: str = None) -> List[str]:
    """Runs pending SQL migrations against the SQLite database."""
    if migrations_dir is None:
        # Default to repo database/migrations directory
        current_dir = Path(__file__).resolve().parent
        repo_root = current_dir.parent.parent.parent
        migrations_dir = repo_root / "database" / "migrations"
    else:
        migrations_dir = Path(migrations_dir)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON;")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # GLITCH-PROOFING: Ensure rectification columns exist for any DB version
    try:
        cursor.execute("ALTER TABLE thinking_results ADD COLUMN learner_response TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    try:
        cursor.execute("ALTER TABLE practical_results ADD COLUMN learner_response TEXT")
    except sqlite3.alldistribution_error: # Handled as general error in sqlite3
        pass

    try:
        cursor.execute("ALTER TABLE practical_results ADD COLUMN learner_response TEXT")
    except Exception:
        pass # Column already exists

    conn.commit()


    cursor.execute("SELECT version FROM schema_migrations;")
    applied = {row[0] for row in cursor.fetchall()}

    applied_now = []
    migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])

    for fname in migration_files:
        version = fname.split("_")[0]
        if version not in applied:
            file_path = migrations_dir / fname
            with open(file_path, "r", encoding="utf-8") as f:
                sql_content = f.read()
            cursor.executescript(sql_content)
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (?);", (version,))
            conn.commit()
            applied_now.append(fname)

    conn.close()
    return applied_now


def run_postgres_migrations(connection) -> None:
    """Apply the PostgreSQL Alembic migration chain using an existing connection."""
    from alembic import command
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[3]
    config = Config(str(repo_root / "alembic.ini"))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


def upgrade_configured_database() -> None:
    from backend.app.core.database import engine

    if engine.dialect.name == "sqlite":
        database_url = engine.url
        db_path = database_url.database or ""
        run_migrations(db_path)
        return
    if engine.dialect.name == "postgresql":
        with engine.connect() as connection:
            run_postgres_migrations(connection)
        return
    raise RuntimeError(
        f"Database migrations are not supported for dialect '{engine.dialect.name}'."
    )


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["upgrade"]):
        raise SystemExit("Usage: python -m backend.app.core.migrations [upgrade]")
    upgrade_configured_database()
