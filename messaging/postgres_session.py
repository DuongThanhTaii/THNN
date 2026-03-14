"""PostgreSQL-backed session store for messaging state persistence.

Implements the same public methods used by ClaudeMessageHandler as SessionStore,
so the application can switch storage backend via DATABASE_URL without changing
message processing logic.
"""

import os
import threading
import logging
from datetime import UTC, datetime
from typing import Any

from psycopg import OperationalError, connect
from psycopg.types.json import Jsonb


logger = logging.getLogger(__name__)


class PostgresSessionStore:
    """Persistent session storage on PostgreSQL (e.g. Neon)."""

    def __init__(self, database_url: str):
        if not database_url or not database_url.strip():
            raise ValueError("DATABASE_URL must be set for PostgresSessionStore")

        self._database_url = database_url.strip()
        self._lock = threading.Lock()
        cap_raw = os.getenv("MAX_MESSAGE_LOG_ENTRIES_PER_CHAT", "").strip()
        try:
            self._message_log_cap: int | None = int(cap_raw) if cap_raw else None
        except ValueError:
            self._message_log_cap = None

        self._conn = self._connect()
        self._ensure_schema()

    def _connect(self):
        return connect(self._database_url, autocommit=True)

    def _ensure_connection(self) -> None:
        if self._conn.closed:
            self._conn = self._connect()

    def _retry_once(self, fn):
        try:
            self._ensure_connection()
            return fn()
        except OperationalError:
            logger.warning("PostgreSQL connection lost, reconnecting once...")
            self._conn = self._connect()
            return fn()

    def _ensure_schema(self) -> None:
        def _create() -> None:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS fcc_session_trees (
                        root_id TEXT PRIMARY KEY,
                        tree_data JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS fcc_session_node_map (
                        node_id TEXT PRIMARY KEY,
                        root_id TEXT NOT NULL REFERENCES fcc_session_trees(root_id) ON DELETE CASCADE,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS fcc_session_message_log (
                        platform TEXT NOT NULL,
                        chat_id TEXT NOT NULL,
                        message_id TEXT NOT NULL,
                        ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        direction TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        PRIMARY KEY (platform, chat_id, message_id)
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_fcc_session_message_log_chat_ts
                    ON fcc_session_message_log(platform, chat_id, ts)
                    """
                )

        self._retry_once(_create)

    def flush_pending_save(self) -> None:
        """No-op for DB-backed store (writes are immediate)."""

    def record_message_id(
        self,
        platform: str,
        chat_id: str,
        message_id: str,
        direction: str,
        kind: str,
    ) -> None:
        if message_id is None:
            return

        now_iso = datetime.now(UTC).isoformat()

        def _insert() -> None:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO fcc_session_message_log(platform, chat_id, message_id, ts, direction, kind)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (platform, chat_id, message_id) DO NOTHING
                    """,
                    (
                        str(platform),
                        str(chat_id),
                        str(message_id),
                        now_iso,
                        str(direction),
                        str(kind),
                    ),
                )

                if self._message_log_cap is not None and self._message_log_cap > 0:
                    cur.execute(
                        """
                        DELETE FROM fcc_session_message_log
                        WHERE (platform, chat_id, message_id) IN (
                            SELECT platform, chat_id, message_id
                            FROM (
                                SELECT
                                    platform,
                                    chat_id,
                                    message_id,
                                    ROW_NUMBER() OVER (
                                        PARTITION BY platform, chat_id
                                        ORDER BY ts DESC
                                    ) AS rn
                                FROM fcc_session_message_log
                                WHERE platform = %s AND chat_id = %s
                            ) ranked
                            WHERE ranked.rn > %s
                        )
                        """,
                        (str(platform), str(chat_id), self._message_log_cap),
                    )

        with self._lock:
            self._retry_once(_insert)

    def get_message_ids_for_chat(self, platform: str, chat_id: str) -> list[str]:
        def _select() -> list[str]:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT message_id
                    FROM fcc_session_message_log
                    WHERE platform = %s AND chat_id = %s
                    ORDER BY ts ASC
                    """,
                    (str(platform), str(chat_id)),
                )
                return [str(row[0]) for row in cur.fetchall()]

        with self._lock:
            return self._retry_once(_select)

    def clear_all(self) -> None:
        def _clear() -> None:
            with self._conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE fcc_session_message_log")
                cur.execute("TRUNCATE TABLE fcc_session_node_map")
                cur.execute("TRUNCATE TABLE fcc_session_trees")

        with self._lock:
            self._retry_once(_clear)

    def save_tree(self, root_id: str, tree_data: dict) -> None:
        node_ids = list((tree_data.get("nodes") or {}).keys())

        def _save() -> None:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO fcc_session_trees(root_id, tree_data, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (root_id)
                    DO UPDATE SET tree_data = EXCLUDED.tree_data, updated_at = NOW()
                    """,
                    (root_id, Jsonb(tree_data)),
                )
                cur.execute(
                    "DELETE FROM fcc_session_node_map WHERE root_id = %s",
                    (root_id,),
                )
                for node_id in node_ids:
                    cur.execute(
                        """
                        INSERT INTO fcc_session_node_map(node_id, root_id, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (node_id)
                        DO UPDATE SET root_id = EXCLUDED.root_id, updated_at = NOW()
                        """,
                        (str(node_id), str(root_id)),
                    )

        with self._lock:
            self._retry_once(_save)

    def get_tree(self, root_id: str) -> dict | None:
        def _select() -> dict | None:
            with self._conn.cursor() as cur:
                cur.execute(
                    "SELECT tree_data FROM fcc_session_trees WHERE root_id = %s",
                    (str(root_id),),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return dict(row[0])

        with self._lock:
            return self._retry_once(_select)

    def register_node(self, node_id: str, root_id: str) -> None:
        def _upsert() -> None:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO fcc_session_node_map(node_id, root_id, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (node_id)
                    DO UPDATE SET root_id = EXCLUDED.root_id, updated_at = NOW()
                    """,
                    (str(node_id), str(root_id)),
                )

        with self._lock:
            self._retry_once(_upsert)

    def remove_node_mappings(self, node_ids: list[str]) -> None:
        if not node_ids:
            return

        def _delete() -> None:
            with self._conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM fcc_session_node_map WHERE node_id = ANY(%s)",
                    (list(map(str, node_ids)),),
                )

        with self._lock:
            self._retry_once(_delete)

    def remove_tree(self, root_id: str) -> None:
        def _delete() -> None:
            with self._conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM fcc_session_trees WHERE root_id = %s",
                    (str(root_id),),
                )

        with self._lock:
            self._retry_once(_delete)

    def get_all_trees(self) -> dict[str, dict]:
        def _select() -> dict[str, dict]:
            with self._conn.cursor() as cur:
                cur.execute("SELECT root_id, tree_data FROM fcc_session_trees")
                return {str(root_id): dict(tree_data) for root_id, tree_data in cur.fetchall()}

        with self._lock:
            return self._retry_once(_select)

    def get_node_mapping(self) -> dict[str, str]:
        def _select() -> dict[str, str]:
            with self._conn.cursor() as cur:
                cur.execute("SELECT node_id, root_id FROM fcc_session_node_map")
                return {str(node_id): str(root_id) for node_id, root_id in cur.fetchall()}

        with self._lock:
            return self._retry_once(_select)

    def sync_from_tree_data(
        self, trees: dict[str, dict], node_to_tree: dict[str, str]
    ) -> None:
        def _sync() -> None:
            with self._conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE fcc_session_node_map")
                cur.execute("TRUNCATE TABLE fcc_session_trees")

                for root_id, tree_data in trees.items():
                    cur.execute(
                        """
                        INSERT INTO fcc_session_trees(root_id, tree_data, updated_at)
                        VALUES (%s, %s, NOW())
                        """,
                        (str(root_id), Jsonb(tree_data)),
                    )

                for node_id, root_id in node_to_tree.items():
                    cur.execute(
                        """
                        INSERT INTO fcc_session_node_map(node_id, root_id, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (node_id)
                        DO UPDATE SET root_id = EXCLUDED.root_id, updated_at = NOW()
                        """,
                        (str(node_id), str(root_id)),
                    )

        with self._lock:
            self._retry_once(_sync)
