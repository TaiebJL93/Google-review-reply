from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

is_sqlite = settings.database_url.startswith("sqlite")
is_sqlite_memory = settings.database_url in ("sqlite://", "sqlite:///:memory:")

engine_kwargs = {"connect_args": {"check_same_thread": False}} if is_sqlite else {}
if is_sqlite_memory:
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def upgrade_schema() -> None:
    """Adds columns introduced after a table already exists locally.

    Base.metadata.create_all() only creates missing tables, it never alters
    an existing one — this project has no migration tool, so new nullable
    columns get patched in here instead of requiring users to delete their
    local reviewreply.db. Must run after create_all() so the table exists.
    """
    if not is_sqlite:
        return

    with engine.connect() as conn:
        existing_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(drafts)")}
        if "saved_at" not in existing_columns:
            conn.exec_driver_sql("ALTER TABLE drafts ADD COLUMN saved_at DATETIME")
            conn.commit()
