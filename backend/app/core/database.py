from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings


def normalize_database_url(database_url: str) -> str:
    database_url = database_url.strip()
    if database_url.startswith("DATABASE_URL="):
        database_url = database_url[len("DATABASE_URL="):].strip()
    if len(database_url) >= 2 and database_url[0] == database_url[-1]:
        if database_url[0] in {"'", '"'}:
            database_url = database_url[1:-1].strip()
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql", "postgresql+psycopg"}:
        url = url.set(drivername="postgresql+psycopg2")
    return url.render_as_string(hide_password=False)


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


database_url = normalize_database_url(settings.DATABASE_URL)
engine: Engine = create_engine(
    database_url,
    connect_args=(
        {"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {}
    ),
    pool_pre_ping=True,
)
if engine.dialect.name == "sqlite":
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
