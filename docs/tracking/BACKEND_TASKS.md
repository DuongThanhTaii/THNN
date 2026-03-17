# Backend Task Board

Last Updated: 2026-03-17
Legend: TODO | IN_PROGRESS | BLOCKED | DONE

## B0 - Foundation

- [x] BE-001 Add PostgreSQL-backed session store abstraction. (DONE)
- [x] BE-002 Wire DB store selection by DATABASE_URL. (DONE)
- [x] BE-003 Add environment templates for deployment variables. (DONE)
- [x] BE-004 Add migration tooling (alembic or SQL migration runner). (DONE)
- [x] BE-005 Add structured config validation for new env variables. (DONE)

## B1 - Data Layer

- [x] BE-101 Create core tables: users, workspaces, channels, channel_sessions. (DONE)
- [x] BE-102 Create conversation tables: conversations, messages. (DONE)
- [x] BE-103 Create task tables: tasks, task_runs, automations, automation_runs. (DONE)
- [x] BE-104 Create integration tables: integration_accounts, jira_issue_links, calendar_event_links. (DONE)
- [x] BE-105 Create sync tables: sync_policies, sync_conflicts, processed_events. (DONE)
- [x] BE-106 Create provider tables: provider_profiles, provider_health_checks. (DONE)
- [x] BE-107 Create audit tables: audit_logs, auth_events. (DONE)

## B2 - API Platform

- [x] BE-201 Add API namespace /api/v1 with versioned routers. (DONE)
- [x] BE-202 Add auth endpoints (login, refresh, logout). (SCAFFOLDED)
- [x] BE-203 Add workspace and user management endpoints. (DONE)
- [x] BE-204 Add task CRUD endpoints with pagination/filtering. (DONE)
- [x] BE-205 Add automation CRUD endpoints. (DONE)
- [x] BE-206 Add websocket server channel for realtime updates. (DONE)
- [x] BE-207 Add role-based access control middleware. (DONE)

## B3 - Integrations (Jira)

- [x] BE-301 Implement Jira OAuth/API-token connection flow. (DONE)
- [x] BE-302 Implement Jira client wrapper (projects/issues/transitions/comments). (DONE)
- [x] BE-303 Add Jira webhook endpoint with signature validation. (DONE)
- [x] BE-304 Add Jira event normalization to internal event envelope. (DONE)
- [x] BE-305 Add Jira retry policy + dead-letter handling. (DONE)

## B4 - Integrations (Google Calendar)

- [x] BE-401 Implement Google OAuth2 connection flow. (DONE)
- [x] BE-402 Implement Google Calendar client wrapper (event CRUD/watch). (DONE)
- [x] BE-403 Add Google webhook endpoint with verification logic. (DONE)
- [x] BE-404 Add Google event normalization to internal event envelope. (DONE)
- [x] BE-405 Add Google retry policy + dead-letter handling. (DONE)

## B5 - Sync Engine

- [x] BE-501 Build Jira -> Calendar mapping service. (DONE)
- [x] BE-502 Build Calendar -> Jira mapping service. (DONE)
- [x] BE-503 Implement conflict detection and resolution policies. (DONE)
- [x] BE-504 Implement idempotency registry for webhook events. (DONE)
- [x] BE-505 Add sync status projections for dashboard. (DONE)

## B6 - Channels and Automation

- [x] BE-601 Refactor messaging platform factory to allow multi-platform active at once. (DONE)
- [x] BE-602 Add web channel adapter integrated with websocket. (DONE)
- [x] BE-603 Add ESP32 MQTT adapter with command/status topics. (DONE - contract docs added in README)
- [x] BE-604 Add scheduler and rule engine for daily automation workflows. (DONE)
- [x] BE-605 Add background worker for asynchronous action execution. (DONE)

## B7 - Reliability and Security

- [x] BE-701 Add central secret handling and key rotation guide. (DONE)
- [x] BE-702 Add rate limits per user/workspace/channel. (DONE)
- [x] BE-703 Add distributed locks for critical task execution. (DONE)
- [x] BE-704 Add tracing/metrics/log correlation IDs. (DONE)
- [x] BE-705 Add SLO dashboards and alerting definitions. (DONE)

## B8 - Quality and Release

- [x] BE-801 Add unit tests for new services and mappings. (DONE)
- [x] BE-802 Add integration tests for Jira/Google webhook flows. (DONE)
- [x] BE-803 Add E2E flow test Telegram -> Jira -> Calendar sync. (DONE)
- [x] BE-804 Add load test scenarios for burst webhook events. (DONE)
- [x] BE-805 Add release checklist and rollback runbook. (DONE)

## Status Update Format

Use this format whenever updating a task:

- Task ID:
- New Status:
- Date:
- Owner:
- PR/Commit:
- Notes:
