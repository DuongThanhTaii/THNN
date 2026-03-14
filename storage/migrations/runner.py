"""Minimal SQL migration runner for PostgreSQL."""

from pathlib import Path

from loguru import logger

from storage.db import get_db_cursor

MIGRATIONS_DIR = Path(__file__).resolve().parent / "sql"


def run_migrations() -> int:
    """Apply all SQL files in lexical order once.

    Returns the number of newly applied migrations.
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        cur.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in cur.fetchall()}

        applied_count = 0
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = sql_file.name
            if version in applied:
                continue

            sql = sql_file.read_text(encoding="utf-8")
            logger.info("Applying migration: {}", version)
            cur.execute(sql)
            cur.execute(
                "INSERT INTO schema_migrations(version) VALUES (%s)",
                (version,),
            )
            applied_count += 1

        return applied_count
