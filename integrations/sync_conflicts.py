"""Conflict detection and resolution service for sync operations."""

from contextlib import suppress
from datetime import datetime
from typing import Any, Literal

from config.settings import get_settings
from storage.db import get_db_cursor

ResolutionPolicy = Literal["manual", "last_write_wins", "source_of_truth"]


class SyncConflictService:
    """Detects and resolves cross-system field conflicts."""

    def detect_and_resolve(
        self,
        *,
        workspace_id: int,
        source_system: str,
        target_system: str,
        entity_ref: str,
        source_fields: dict[str, Any],
        target_fields: dict[str, Any],
        policy: ResolutionPolicy = "manual",
        field_owners: dict[str, str] | None = None,
        source_updated_at: str | None = None,
        target_updated_at: str | None = None,
        persist_conflicts: bool = True,
    ) -> dict[str, Any]:
        fields = sorted(set(source_fields) | set(target_fields))
        owner_map = field_owners or {}

        source_dt = self._parse_datetime(source_updated_at)
        target_dt = self._parse_datetime(target_updated_at)

        resolved_fields: dict[str, Any] = {}
        conflicts: list[dict[str, Any]] = []

        for field in fields:
            source_value = source_fields.get(field)
            target_value = target_fields.get(field)

            has_source = source_value is not None
            has_target = target_value is not None

            if has_source and not has_target:
                resolved_fields[field] = source_value
                continue
            if has_target and not has_source:
                resolved_fields[field] = target_value
                continue
            if source_value == target_value:
                resolved_fields[field] = source_value
                continue

            conflict = {
                "field": field,
                "source_value": source_value,
                "target_value": target_value,
            }

            selected_value, status = self._resolve_field_value(
                field=field,
                source_value=source_value,
                target_value=target_value,
                policy=policy,
                owner_map=owner_map,
                source_updated_at=source_dt,
                target_updated_at=target_dt,
            )

            conflict["status"] = status
            conflict["selected_value"] = selected_value
            conflicts.append(conflict)
            resolved_fields[field] = selected_value

        open_conflicts = [c for c in conflicts if c["status"] == "open"]
        if persist_conflicts and open_conflicts:
            self._persist_conflicts(
                workspace_id=workspace_id,
                source_system=source_system,
                target_system=target_system,
                entity_ref=entity_ref,
                policy=policy,
                conflicts=open_conflicts,
            )

        return {
            "resolved_fields": resolved_fields,
            "conflicts": conflicts,
            "has_unresolved_conflicts": bool(open_conflicts),
            "policy": policy,
        }

    def _resolve_field_value(
        self,
        *,
        field: str,
        source_value: Any,
        target_value: Any,
        policy: ResolutionPolicy,
        owner_map: dict[str, str],
        source_updated_at: datetime | None,
        target_updated_at: datetime | None,
    ) -> tuple[Any, str]:
        if policy == "source_of_truth":
            owner = str(owner_map.get(field) or "source").strip().lower()
            if owner == "target":
                return target_value, "resolved"
            return source_value, "resolved"

        if policy == "last_write_wins":
            if source_updated_at and target_updated_at:
                if source_updated_at >= target_updated_at:
                    return source_value, "resolved"
                return target_value, "resolved"
            return source_value, "resolved"

        # manual policy creates an unresolved conflict for operator review.
        return target_value, "open"

    def _persist_conflicts(
        self,
        *,
        workspace_id: int,
        source_system: str,
        target_system: str,
        entity_ref: str,
        policy: ResolutionPolicy,
        conflicts: list[dict[str, Any]],
    ) -> None:
        database_url = get_settings().database_url.strip()
        if not database_url:
            return

        for conflict in conflicts:
            details = {
                "policy": policy,
                "field": conflict["field"],
                "source_value": conflict["source_value"],
                "target_value": conflict["target_value"],
            }
            reason = f"field mismatch: {conflict['field']}"
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sync_conflicts(
                        workspace_id,
                        source_system,
                        target_system,
                        entity_ref,
                        reason,
                        status,
                        details
                    )
                    VALUES (%s, %s, %s, %s, %s, 'open', %s::jsonb)
                    """,
                    (
                        workspace_id,
                        source_system,
                        target_system,
                        entity_ref,
                        reason,
                        self._to_json(details),
                    ),
                )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"
        with suppress(ValueError):
            return datetime.fromisoformat(candidate)
        return None

    @staticmethod
    def _to_json(value: dict[str, Any]) -> str:
        # Import locally to keep module import graph lightweight.
        import json

        return json.dumps(value)
