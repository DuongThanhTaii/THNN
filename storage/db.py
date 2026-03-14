"""PostgreSQL connection helpers."""

from contextlib import contextmanager

from psycopg import connect

from config.settings import get_settings


@contextmanager
def get_db_cursor():
    """Yield a DB cursor with automatic commit/rollback.

    This helper is intentionally synchronous to keep migration and
    lightweight admin endpoints simple.
    """
    settings = get_settings()
    if not settings.database_url.strip():
        raise RuntimeError("DATABASE_URL is not configured")

    conn = connect(settings.database_url, autocommit=False)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def can_connect() -> bool:
    """Return True when DB connection succeeds."""
    settings = get_settings()
    if not settings.database_url.strip():
        return False

    conn = connect(settings.database_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    finally:
        conn.close()
