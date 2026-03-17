"""Distributed locking utilities backed by PostgreSQL advisory locks."""

from __future__ import annotations

import hashlib


def advisory_lock_key(*parts: object) -> int:
    """Create deterministic signed 63-bit key for advisory lock usage."""
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return value & 0x7FFF_FFFF_FFFF_FFFF


def try_acquire_automation_execution_lock(
    cur,
    *,
    workspace_id: int,
    automation_id: int,
) -> bool:
    """Try acquiring transaction-scoped lock for one automation execution."""
    key = advisory_lock_key("automation_execute", workspace_id, automation_id)
    cur.execute("SELECT pg_try_advisory_xact_lock(%s)", (key,))
    row = cur.fetchone()
    return bool(row and row[0])
