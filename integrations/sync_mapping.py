"""Field mapping service for Jira <-> Google Calendar sync flows."""

from datetime import UTC, date, datetime, timedelta
from typing import Any

_STATUS_TO_COLOR_ID = {
    "to do": "5",
    "open": "5",
    "in progress": "9",
    "doing": "9",
    "done": "10",
    "resolved": "10",
    "closed": "10",
}


class SyncMappingService:
    """Maps provider payloads into sync-ready payloads for opposite systems."""

    def __init__(
        self,
        *,
        default_timezone: str = "UTC",
        default_project_key: str = "",
        default_issue_type: str = "Task",
    ) -> None:
        self.default_timezone = default_timezone
        self.default_project_key = default_project_key.strip()
        self.default_issue_type = default_issue_type

    def map_jira_issue_to_calendar_event(self, issue: dict[str, Any]) -> dict[str, Any]:
        key = str(issue.get("key") or "")
        issue_id = str(issue.get("id") or "")
        raw_fields = issue.get("fields")
        fields: dict[str, Any] = raw_fields if isinstance(raw_fields, dict) else {}

        summary = str(fields.get("summary") or key or "Untitled Jira Issue")
        description = self._stringify_description(fields.get("description"))

        start_block, end_block = self._extract_calendar_time_window(fields)

        status_name = self._status_name(fields.get("status"))
        color_id = _STATUS_TO_COLOR_ID.get(status_name.lower(), "6")

        event: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": start_block,
            "end": end_block,
            "colorId": color_id,
            "extendedProperties": {
                "private": {
                    "jiraKey": key,
                    "jiraIssueId": issue_id,
                    "jiraStatus": status_name,
                    "jiraPriority": self._priority_name(fields.get("priority")),
                }
            },
        }

        attendees = self._attendees_from_assignee(fields.get("assignee"))
        if attendees:
            event["attendees"] = attendees

        return event

    def map_calendar_event_to_jira_fields(
        self, event: dict[str, Any]
    ) -> dict[str, Any]:
        summary = str(event.get("summary") or "Untitled Calendar Event")
        description = str(event.get("description") or "")

        private_meta = self._private_extended_properties(event)
        jira_key = str(private_meta.get("jiraKey") or "").strip()

        labels = ["calendar-sync"]
        color_id = event.get("colorId")
        if isinstance(color_id, str) and color_id:
            labels.append(f"calendar-color-{color_id}")

        fields: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "labels": labels,
        }

        due_date = self._extract_due_date(event)
        if due_date:
            fields["duedate"] = due_date.isoformat()

        if jira_key:
            return {
                "operation": "update",
                "issue_key": jira_key,
                "fields": fields,
            }

        if self.default_project_key:
            fields["project"] = {"key": self.default_project_key}
            fields["issuetype"] = {"name": self.default_issue_type}

        return {
            "operation": "create",
            "issue_key": None,
            "fields": fields,
        }

    def _extract_calendar_time_window(
        self,
        fields: dict[str, Any],
    ) -> tuple[dict[str, str], dict[str, str]]:
        start_raw = self._first_present(
            fields,
            ["customfield_start", "startDate", "start"],
        )
        end_raw = self._first_present(
            fields,
            ["customfield_end", "endDate", "end"],
        )
        due_raw = fields.get("duedate")

        start_dt = self._parse_datetime(start_raw)
        end_dt = self._parse_datetime(end_raw)
        due_day = self._parse_date(due_raw)

        if start_dt and end_dt:
            return (
                {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": self.default_timezone,
                },
                {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": self.default_timezone,
                },
            )

        if due_day:
            return (
                {"date": due_day.isoformat()},
                {"date": (due_day + timedelta(days=1)).isoformat()},
            )

        now_utc = datetime.now(UTC).replace(microsecond=0)
        return (
            {
                "dateTime": now_utc.isoformat(),
                "timeZone": self.default_timezone,
            },
            {
                "dateTime": (now_utc + timedelta(hours=1)).isoformat(),
                "timeZone": self.default_timezone,
            },
        )

    @staticmethod
    def _first_present(fields: dict[str, Any], candidates: list[str]) -> Any:
        for key in candidates:
            value = fields.get(key)
            if value:
                return value
        return None

    @staticmethod
    def _stringify_description(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            if isinstance(value.get("text"), str):
                return value["text"]
            # Compact fallback for Atlassian document object descriptions.
            return str(value)
        return str(value)

    @staticmethod
    def _status_name(value: Any) -> str:
        if isinstance(value, dict):
            name = value.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        return "unknown"

    @staticmethod
    def _priority_name(value: Any) -> str:
        if isinstance(value, dict):
            name = value.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        return "unknown"

    @staticmethod
    def _attendees_from_assignee(value: Any) -> list[dict[str, str]]:
        if not isinstance(value, dict):
            return []
        email = value.get("emailAddress")
        if not isinstance(email, str) or not email.strip():
            return []
        display_name = value.get("displayName")
        attendee = {"email": email.strip()}
        if isinstance(display_name, str) and display_name.strip():
            attendee["displayName"] = display_name.strip()
        return [attendee]

    @staticmethod
    def _private_extended_properties(event: dict[str, Any]) -> dict[str, Any]:
        props = event.get("extendedProperties")
        if not isinstance(props, dict):
            return {}
        private = props.get("private")
        if isinstance(private, dict):
            return private
        return {}

    @staticmethod
    def _extract_due_date(event: dict[str, Any]) -> date | None:
        end = event.get("end")
        if not isinstance(end, dict):
            end = {}

        end_date = SyncMappingService._parse_date(end.get("date"))
        if end_date:
            return end_date - timedelta(days=1)

        end_dt = SyncMappingService._parse_datetime(end.get("dateTime"))
        if end_dt:
            return end_dt.date()

        start = event.get("start")
        if not isinstance(start, dict):
            return None

        start_date = SyncMappingService._parse_date(start.get("date"))
        if start_date:
            return start_date
        start_dt = SyncMappingService._parse_datetime(start.get("dateTime"))
        if start_dt:
            return start_dt.date()
        return None

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
