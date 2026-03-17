from integrations.sync_mapping import SyncMappingService


def test_map_jira_issue_to_calendar_event_with_due_date_and_assignee():
    service = SyncMappingService(default_timezone="Asia/Ho_Chi_Minh")

    issue = {
        "id": "10001",
        "key": "OPS-17",
        "fields": {
            "summary": "Deploy release",
            "description": "Deploy to production",
            "duedate": "2026-03-20",
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "assignee": {
                "emailAddress": "owner@example.com",
                "displayName": "Owner",
            },
        },
    }

    event = service.map_jira_issue_to_calendar_event(issue)

    assert event["summary"] == "Deploy release"
    assert event["description"] == "Deploy to production"
    assert event["start"] == {"date": "2026-03-20"}
    assert event["end"] == {"date": "2026-03-21"}
    assert event["colorId"] == "9"
    assert event["extendedProperties"]["private"]["jiraKey"] == "OPS-17"
    assert event["extendedProperties"]["private"]["jiraPriority"] == "High"
    assert event["attendees"] == [
        {"email": "owner@example.com", "displayName": "Owner"}
    ]


def test_map_jira_issue_to_calendar_event_prefers_datetime_window():
    service = SyncMappingService(default_timezone="UTC")

    issue = {
        "id": "10002",
        "key": "OPS-18",
        "fields": {
            "summary": "Incident review",
            "customfield_start": "2026-03-21T08:00:00+07:00",
            "customfield_end": "2026-03-21T09:30:00+07:00",
            "status": {"name": "Done"},
        },
    }

    event = service.map_jira_issue_to_calendar_event(issue)

    assert event["start"]["dateTime"] == "2026-03-21T08:00:00+07:00"
    assert event["end"]["dateTime"] == "2026-03-21T09:30:00+07:00"
    assert event["start"]["timeZone"] == "UTC"
    assert event["colorId"] == "10"


def test_map_calendar_event_to_jira_fields_update_operation():
    service = SyncMappingService(default_project_key="OPS", default_issue_type="Task")

    event = {
        "summary": "Review deploy",
        "description": "Post-deploy follow-up",
        "colorId": "9",
        "start": {"dateTime": "2026-03-20T08:00:00Z"},
        "end": {"dateTime": "2026-03-20T09:00:00Z"},
        "extendedProperties": {"private": {"jiraKey": "OPS-17"}},
    }

    mapped = service.map_calendar_event_to_jira_fields(event)

    assert mapped["operation"] == "update"
    assert mapped["issue_key"] == "OPS-17"
    assert mapped["fields"]["summary"] == "Review deploy"
    assert mapped["fields"]["description"] == "Post-deploy follow-up"
    assert mapped["fields"]["duedate"] == "2026-03-20"
    assert mapped["fields"]["labels"] == ["calendar-sync", "calendar-color-9"]


def test_map_calendar_event_to_jira_fields_create_operation_with_defaults():
    service = SyncMappingService(default_project_key="OPS", default_issue_type="Task")

    event = {
        "summary": "Create issue from calendar",
        "description": "No jiraKey metadata",
        "start": {"date": "2026-03-25"},
        "end": {"date": "2026-03-26"},
    }

    mapped = service.map_calendar_event_to_jira_fields(event)

    assert mapped["operation"] == "create"
    assert mapped["issue_key"] is None
    assert mapped["fields"]["project"] == {"key": "OPS"}
    assert mapped["fields"]["issuetype"] == {"name": "Task"}
    assert mapped["fields"]["duedate"] == "2026-03-25"
