# Backend Task Board

Last Updated: 2026-03-16
Legend: TODO | IN_PROGRESS | BLOCKED | DONE

## B0 - Foundation

- [x] BE-001 Add PostgreSQL-backed session store abstraction. (DONE)
- [x] BE-002 Wire DB store selection by DATABASE_URL. (DONE)
- [x] BE-003 Add environment templates for deployment variables. (DONE)
- [x] BE-004 Add migration tooling (alembic or SQL migration runner). (DONE)
- [x] BE-005 Add structured config validation for new env variables. (DONE)

## B1 - Data Layer

- [x] BE-101 Create core tables: users, workspaces, channels, channel_sessions. (DONE)
- [ ] BE-102 Create conversation tables: conversations, messages. (TODO)
- [ ] BE-103 Create task tables: tasks, task_runs, automations, automation_runs. (TODO)
- [ ] BE-104 Create integration tables: integration_accounts, jira_issue_links, calendar_event_links. (TODO)
- [ ] BE-105 Create sync tables: sync_policies, sync_conflicts, processed_events. (TODO)
- [ ] BE-106 Create provider tables: provider_profiles, provider_health_checks. (TODO)
- [ ] BE-107 Create audit tables: audit_logs, auth_events. (TODO)

## B2 - API Platform

- [x] BE-201 Add API namespace /api/v1 with versioned routers. (DONE)
- [x] BE-202 Add auth endpoints (login, refresh, logout). (SCAFFOLDED)
- [ ] BE-203 Add workspace and user management endpoints. (SCAFFOLDED)
- [x] BE-204 Add task CRUD endpoints with pagination/filtering. (DONE)
- [ ] BE-205 Add automation CRUD endpoints. (TODO)
- [ ] BE-206 Add websocket server channel for realtime updates. (SCAFFOLDED)
- [ ] BE-207 Add role-based access control middleware. (TODO)

## B3 - Integrations (Jira)

- [ ] BE-301 Implement Jira OAuth/API-token connection flow. (IN_PROGRESS)
- [ ] BE-302 Implement Jira client wrapper (projects/issues/transitions/comments). (TODO)
- [ ] BE-303 Add Jira webhook endpoint with signature validation. (TODO)
- [ ] BE-304 Add Jira event normalization to internal event envelope. (TODO)
- [ ] BE-305 Add Jira retry policy + dead-letter handling. (TODO)

## B4 - Integrations (Google Calendar)

- [ ] BE-401 Implement Google OAuth2 connection flow. (IN_PROGRESS)
- [ ] BE-402 Implement Google Calendar client wrapper (event CRUD/watch). (TODO)
- [ ] BE-403 Add Google webhook endpoint with verification logic. (TODO)
- [ ] BE-404 Add Google event normalization to internal event envelope. (TODO)
- [ ] BE-405 Add Google retry policy + dead-letter handling. (TODO)

## B5 - Sync Engine

- [ ] BE-501 Build Jira -> Calendar mapping service. (TODO)
- [ ] BE-502 Build Calendar -> Jira mapping service. (TODO)
- [ ] BE-503 Implement conflict detection and resolution policies. (TODO)
- [ ] BE-504 Implement idempotency registry for webhook events. (TODO)
- [ ] BE-505 Add sync status projections for dashboard. (TODO)

## B6 - Channels and Automation

- [ ] BE-601 Refactor messaging platform factory to allow multi-platform active at once. (TODO)
- [ ] BE-602 Add web channel adapter integrated with websocket. (TODO)
- [ ] BE-603 Add ESP32 MQTT adapter with command/status topics. (TODO)
- [ ] BE-604 Add scheduler and rule engine for daily automation workflows. (TODO)
- [ ] BE-605 Add background worker for asynchronous action execution. (TODO)

## B7 - Reliability and Security

- [ ] BE-701 Add central secret handling and key rotation guide. (IN_PROGRESS)
- [ ] BE-702 Add rate limits per user/workspace/channel. (TODO)
- [ ] BE-703 Add distributed locks for critical task execution. (TODO)
- [ ] BE-704 Add tracing/metrics/log correlation IDs. (TODO)
- [ ] BE-705 Add SLO dashboards and alerting definitions. (TODO)

## B8 - Quality and Release

- [ ] BE-801 Add unit tests for new services and mappings. (TODO)
- [ ] BE-802 Add integration tests for Jira/Google webhook flows. (TODO)
- [ ] BE-803 Add E2E flow test Telegram -> Jira -> Calendar sync. (TODO)
- [ ] BE-804 Add load test scenarios for burst webhook events. (TODO)
- [ ] BE-805 Add release checklist and rollback runbook. (TODO)

## Status Update Format

Use this format whenever updating a task:

- Task ID:
- New Status:
- Date:
- Owner:
- PR/Commit:
- Notes:
