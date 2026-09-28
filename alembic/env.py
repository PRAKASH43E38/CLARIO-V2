from alembic import context
from sqlalchemy import create_engine

from backend.app.core.database import Base, normalize_database_url
from backend.app.core.config import settings
import backend.app.models  # noqa: F401


config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    raise RuntimeError(
        "Offline SQL generation is not supported for the metadata-based PostgreSQL baseline."
    )


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    connectable = create_engine(normalize_database_url(settings.DATABASE_URL))
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
