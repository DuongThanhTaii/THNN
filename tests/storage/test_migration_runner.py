from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

from storage.migrations import runner


def test_run_migrations_applies_new_files_in_order(tmp_path, monkeypatch):
    (tmp_path / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "002_second.sql").write_text("SELECT 2;", encoding="utf-8")

    cur = MagicMock()
    cur.fetchall.return_value = []

    @contextmanager
    def fake_get_db_cursor():
        yield cur

    monkeypatch.setattr(runner, "MIGRATIONS_DIR", Path(tmp_path))
    monkeypatch.setattr(runner, "get_db_cursor", fake_get_db_cursor)

    applied = runner.run_migrations()

    assert applied == 2
    assert (
        cur.execute.call_args_list[0]
        .args[0]
        .strip()
        .startswith("CREATE TABLE IF NOT EXISTS schema_migrations")
    )
    assert (
        cur.execute.call_args_list[1].args[0] == "SELECT version FROM schema_migrations"
    )

    insert_calls = [
        call.args[1][0]
        for call in cur.execute.call_args_list
        if "INSERT INTO schema_migrations(version) VALUES (%s)" in call.args[0]
    ]
    assert insert_calls == ["001_first.sql", "002_second.sql"]


def test_run_migrations_skips_applied_versions(tmp_path, monkeypatch):
    (tmp_path / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "002_second.sql").write_text("SELECT 2;", encoding="utf-8")

    cur = MagicMock()
    cur.fetchall.return_value = [("001_first.sql",)]

    @contextmanager
    def fake_get_db_cursor():
        yield cur

    monkeypatch.setattr(runner, "MIGRATIONS_DIR", Path(tmp_path))
    monkeypatch.setattr(runner, "get_db_cursor", fake_get_db_cursor)

    applied = runner.run_migrations()

    assert applied == 1
    insert_calls = [
        call.args[1][0]
        for call in cur.execute.call_args_list
        if "INSERT INTO schema_migrations(version) VALUES (%s)" in call.args[0]
    ]
    assert insert_calls == ["002_second.sql"]


def test_be101_channel_migration_defines_expected_tables():
    migration_file = runner.MIGRATIONS_DIR / "003_channel_tables.sql"
    sql = migration_file.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS channels" in sql
    assert "CREATE TABLE IF NOT EXISTS channel_sessions" in sql


def test_be101_users_compat_migration_exists_and_backfills():
    migration_file = runner.MIGRATIONS_DIR / "004_users_table_compat.sql"
    sql = migration_file.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS users" in sql
    assert "FROM app_users" in sql
    assert "REFERENCES users(id)" in sql


def test_be102_conversation_migration_defines_expected_tables_and_indexes():
    migration_file = runner.MIGRATIONS_DIR / "005_conversation_tables.sql"
    sql = migration_file.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS conversations" in sql
    assert "CREATE TABLE IF NOT EXISTS messages" in sql
    assert "REFERENCES conversations(id) ON DELETE CASCADE" in sql
    assert "REFERENCES channel_sessions(id) ON DELETE SET NULL" in sql
    assert "REFERENCES users(id) ON DELETE SET NULL" in sql
    assert "idx_conversations_workspace_status" in sql
    assert "idx_messages_conversation_created" in sql


def test_be103_task_and_automation_run_migration_defines_expected_tables():
    migration_file = runner.MIGRATIONS_DIR / "006_task_run_and_automation_tables.sql"
    sql = migration_file.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS task_runs" in sql
    assert "CREATE TABLE IF NOT EXISTS automations" in sql
    assert "CREATE TABLE IF NOT EXISTS automation_runs" in sql
    assert "REFERENCES tasks(id) ON DELETE CASCADE" in sql
    assert "REFERENCES automations(id) ON DELETE CASCADE" in sql
    assert "FROM automation_rules ar" in sql
    assert "idx_task_runs_workspace_status" in sql
    assert "idx_automation_runs_workspace_status" in sql


def test_be104_integration_tables_exist_in_core_migration():
    migration_file = runner.MIGRATIONS_DIR / "001_core_tables.sql"
    sql = migration_file.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS integration_accounts" in sql
    assert "CREATE TABLE IF NOT EXISTS jira_issue_links" in sql
    assert "CREATE TABLE IF NOT EXISTS calendar_event_links" in sql


def test_be105_sync_tables_exist_across_core_and_sync_migrations():
    core_sql = (runner.MIGRATIONS_DIR / "001_core_tables.sql").read_text(
        encoding="utf-8"
    )
    sync_sql = (runner.MIGRATIONS_DIR / "002_sync_tables.sql").read_text(
        encoding="utf-8"
    )

    assert "CREATE TABLE IF NOT EXISTS processed_events" in core_sql
    assert "CREATE TABLE IF NOT EXISTS sync_policies" in sync_sql
    assert "CREATE TABLE IF NOT EXISTS sync_conflicts" in sync_sql


def test_be106_and_be107_provider_and_audit_migration_defines_expected_tables():
    migration_file = runner.MIGRATIONS_DIR / "007_provider_and_audit_tables.sql"
    sql = migration_file.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS provider_profiles" in sql
    assert "CREATE TABLE IF NOT EXISTS provider_health_checks" in sql
    assert "CREATE TABLE IF NOT EXISTS audit_logs" in sql
    assert "CREATE TABLE IF NOT EXISTS auth_events" in sql
    assert "idx_provider_profiles_workspace_enabled" in sql
    assert "idx_auth_events_user_occurred" in sql
