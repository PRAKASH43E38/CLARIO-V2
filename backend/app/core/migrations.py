import os
import sqlite3
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
