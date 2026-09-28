"""Create the current CLARIO PostgreSQL schema.

This baseline represents the application schema in SQLite migrations 001-014.
The SQLite migration chain remains unchanged and is still used for local tests.
"""

from alembic import op
from sqlalchemy import inspect

from backend.app.core.database import Base
import backend.app.models  # noqa: F401


revision = "0001_postgresql_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_clario_tables = set(Base.metadata.tables).intersection(
        inspect(bind).get_table_names()
    )
    if existing_clario_tables:
        raise RuntimeError(
            "CLARIO tables already exist without an Alembic baseline; "
            "inspect and baseline this database before migrating."
        )
    Base.metadata.create_all(bind=bind, checkfirst=False)


def downgrade() -> None:
    raise NotImplementedError(
        "The initial PostgreSQL schema is forward-only; do not drop learner data."
    )
