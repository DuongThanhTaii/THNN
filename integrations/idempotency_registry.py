"""Idempotency registry backed by processed_events table."""

import hashlib
import json
from typing import Any

from config.settings import get_settings
from storage.db import get_db_cursor


class ProcessedEventRegistry:
    """Handles dedupe registration for external integration events."""

    @staticmethod
    def build_payload_hash(payload: dict[str, Any] | list[Any] | Any) -> str:
        stable = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(stable.encode("utf-8")).hexdigest()

    def register_event(self, *, source: str, event_id: str, payload_hash: str) -> str:
        database_url = get_settings().database_url.strip()
        if not database_url:
            return "processed"

        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO processed_events(source, event_id, payload_hash)
                VALUES (%s, %s, %s)
                ON CONFLICT (source, event_id)
                DO NOTHING
                """,
                (source, event_id, payload_hash),
            )
            if cur.rowcount > 0:
                return "processed"

            cur.execute(
                """
                SELECT payload_hash
                FROM processed_events
                WHERE source = %s AND event_id = %s
                """,
                (source, event_id),
            )
            row = cur.fetchone()
            existing_hash = row[0] if row and isinstance(row[0], str) else ""

        if existing_hash and existing_hash != payload_hash:
            return "hash_mismatch"
        return "duplicate"
