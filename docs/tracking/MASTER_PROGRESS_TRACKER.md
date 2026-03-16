# Master Progress Tracker

Last Updated: 2026-03-16
Owner: ThanhTai
Project: Multi-channel Agent Platform (Jira + Google Calendar + Telegram + CLI + Web + ESP32)

## Goal

Track end-to-end implementation progress so no critical work is missed.

## Milestones

| Milestone | Scope                                       | Target    | Status      | Completion |
| --------- | ------------------------------------------- | --------- | ----------- | ---------- |
| M0        | Foundation setup and project governance     | Week 1    | In Progress | 20%        |
| M1        | Backend core platform and data layer        | Week 2-4  | Not Started | 0%         |
| M2        | Integrations (Jira + Google Calendar)       | Week 4-6  | Not Started | 0%         |
| M3        | Frontend dashboard and realtime UX          | Week 5-7  | Not Started | 0%         |
| M4        | ESP32 channel and automation flow           | Week 7-8  | Not Started | 0%         |
| M5        | Hardening, security, observability, release | Week 8-10 | Not Started | 0%         |

## Current Sprint

Sprint: S0-Foundation
Window: 2026-03-14 -> 2026-03-21

### Sprint Objectives

- [x] Add PostgreSQL session persistence support (Neon-ready).
- [x] Add deploy-ready environment template values.
- [x] Create comprehensive task trackers for backend and frontend.
- [x] Create DB migration framework and first core schema migrations.
- [x] Add Jira and Google integration skeleton modules.
- [x] Add dashboard API skeleton (auth/tasks/providers/integrations/webhooks).

### Latest Delta (2026-03-14)

- Implemented SQL migration runner and initial schema under `storage/migrations/sql`.
- Added API v1 router structure with system/auth/tasks/automations/integrations/providers endpoints.
- Added webhook endpoints for Jira and Google Calendar ingestion scaffold.
- Scaffolded React + Vite frontend app under `frontend/` with dashboard/tasks/integrations pages.
- Added frontend API client + websocket client baseline and connected dashboard/tasks/integrations pages to backend.
- Added bootstrap demo workspace endpoint and integration OAuth callback skeleton endpoints.
- Added company-standard Git naming and push guideline document.
- Added realtime websocket endpoint scaffold at `/ws/workspaces/{workspace_id}` with heartbeat/echo.
- Expanded task workflow with API-side filter/pagination/update/delete and frontend controls for status transitions and deletion.
- Added workspace management API scaffold (list/create/delete) to support multi-workspace flows.
- Implemented integration account persistence for Jira/Google callback flow and added `/api/v1/integrations/accounts` listing endpoint.
- Updated integrations frontend to support workspace-aware connect payloads, callback simulation, and connected accounts display.
- Replaced integration token obfuscation with Fernet encryption derived from `ENCRYPTION_MASTER_KEY`.
- Completed BE-101 core data-layer baseline by adding channels/channel_sessions migrations and users-table compatibility migration.
- Implemented Jira OAuth code flow with signed state validation and live token exchange endpoint handling.
- Implemented Google OAuth code flow with signed state validation and live token exchange endpoint handling.
- Implemented Jira API client wrapper methods for projects/issues/transitions/comments.
- Implemented Google Calendar client wrapper methods for calendar/event CRUD and watch registration.
- Completed BE-102 by adding conversations/messages schema migration with FK and index coverage.

## Risk Register

| ID    | Risk                                 | Impact | Mitigation                                         | Status |
| ----- | ------------------------------------ | ------ | -------------------------------------------------- | ------ |
| R-001 | Secrets accidentally pushed to git   | High   | Keep .env gitignored, use secret manager in deploy | Open   |
| R-002 | API quota/rate limits from providers | Medium | Provider fallback chain and retries                | Open   |
| R-003 | Jira/Google webhook duplication      | High   | Idempotency keys and processed_events table        | Open   |
| R-004 | Multi-channel state divergence       | High   | Event bus + canonical task state model             | Open   |
| R-005 | ESP32 network instability            | Medium | MQTT QoS + reconnect + buffered commands           | Open   |

## Weekly Status Template

### Week YYYY-MM-DD

- Wins:
- Blockers:
- Decisions:
- Scope changes:
- Next actions:

## Tracking Rules

1. Update this file at least once per working day.
2. Update [docs/tracking/BACKEND_TASKS.md](docs/tracking/BACKEND_TASKS.md) and [docs/tracking/FRONTEND_TASKS.md](docs/tracking/FRONTEND_TASKS.md) whenever task status changes.
3. Mark completed tasks with date and commit hash.
4. If scope changes, add the reason in Weekly Status.
