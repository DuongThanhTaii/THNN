from unittest.mock import MagicMock

from storage.distributed_lock import (
    advisory_lock_key,
    try_acquire_automation_execution_lock,
)


def test_advisory_lock_key_is_deterministic():
    key1 = advisory_lock_key("automation_execute", 3, 7)
    key2 = advisory_lock_key("automation_execute", 3, 7)
    key3 = advisory_lock_key("automation_execute", 3, 8)

    assert key1 == key2
    assert key1 != key3
    assert key1 >= 0


def test_try_acquire_automation_execution_lock_calls_pg_try_lock():
    cur = MagicMock()
    cur.fetchone.return_value = (True,)

    locked = try_acquire_automation_execution_lock(
        cur,
        workspace_id=4,
        automation_id=9,
    )

    assert locked is True
    sql, params = cur.execute.call_args.args
    assert "pg_try_advisory_xact_lock" in sql
    assert isinstance(params[0], int)
