from app.config import _normalize_database_url


def test_postgres_scheme_is_rewritten_for_sqlalchemy():
    url = "postgres://user:pw@ep-example.neon.tech/db?sslmode=require"
    assert _normalize_database_url(url) == (
        "postgresql://user:pw@ep-example.neon.tech/db?sslmode=require"
    )


def test_postgresql_and_sqlite_urls_are_left_alone():
    assert _normalize_database_url("postgresql://u@h/db") == "postgresql://u@h/db"
    assert _normalize_database_url("sqlite:///./reviewreply.db") == "sqlite:///./reviewreply.db"
