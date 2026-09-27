import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.core.config import settings
from backend.app.core.migrations import run_migrations

def main():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
    print(f"Applying migrations to database: {db_path}...")
    applied = run_migrations(db_path)
    if applied:
        print(f"Applied migrations: {', '.join(applied)}")
    else:
        print("Database schema is already up to date.")

if __name__ == "__main__":
    main()
