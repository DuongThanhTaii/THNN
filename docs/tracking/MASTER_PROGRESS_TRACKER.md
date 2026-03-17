# Master Progress Tracker

Last Updated: 2026-03-17
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
| M3        | Frontend dashboard and realtime UX          | Week 5-7  | In Progress | 20%        |
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
- Completed BE-103 by adding task_runs/automations/automation_runs migration with compatibility backfill from automation_rules.
- Reconciled BE-104 and BE-105 as already-covered tables in existing 001/002 migrations (integration and sync schemas).
- Completed BE-106 and BE-107 by adding provider profile/health and audit/auth event schema migration.
- Finished B1 data-layer board scope (BE-101 -> BE-107).
- Implemented BE-205 by replacing automation endpoint scaffold with workspace-scoped CRUD and API tests.
- Implemented BE-207 RBAC middleware with role checks and workspace scope enforcement (toggle via RBAC_ENFORCE).
- Implemented BE-206 realtime websocket server-push channel with workspace event broadcasting and websocket tests.
- Implemented BE-203 workspace and user management endpoints (workspace get/update + users list/get/create/update) with API tests.
- Completed B3/B4 webhook hardening: Jira/Google verification, internal event envelope normalization, retry handling, and dead-letter audit logging.
- Added webhook API tests covering signature/token validation, normalization output, duplicate handling, retries, and dead-letter fallback.
- Implemented B5 field mapping services for Jira -> Calendar and Calendar -> Jira payload transformations.
- Added unit tests for sync mapping rules (date windows, metadata links, and create/update operation shaping).
- Implemented BE-503 sync conflict service with manual, last-write-wins, and source-of-truth resolution strategies.
- Implemented BE-504 shared idempotency registry backed by processed_events and integrated webhook dedupe through the registry.
- Implemented BE-505 sync status projection endpoint for dashboard consumption with policy/conflict summaries and health states.
- Implemented BE-601 multi-platform messaging activation path (comma-separated platform config, concurrent startup/shutdown, and backward-compatible app.state aliases).
- Implemented BE-602 web messaging adapter integrated with realtime websocket client events and server-push message updates.
- Implemented BE-603 ESP32 MQTT adapter with command/status topic bridge, startup wiring, and adapter/factory/config tests.
- Implemented BE-604 daily automation scheduler and rule engine (schedule trigger evaluation, automation/task run recording, app lifespan startup/shutdown wiring, and API tests).
- Implemented BE-605 background automation action worker (async queue execution, inflight dedupe, graceful shutdown draining, scheduler enqueue flow, and worker-focused API tests).
- Implemented BE-701 centralized secret manager and rotation-ready key ring support with \*\_FILE secret sources and rotation guide documentation.
- Implemented BE-702 API rate limiting middleware with per-user/per-workspace/per-channel scopes and configurable thresholds/windows.
- Implemented BE-703 distributed lock utility using PostgreSQL advisory locks and integrated automation execution lock guard.
- Implemented BE-704 tracing and observability middleware (request/correlation IDs, response headers, structured log propagation, and in-process metrics endpoint).
- Implemented BE-705 observability package with SLO targets, dashboard template, and alert rule definitions.
- Completed BE-801 by expanding unit test coverage for secret rotation behavior, scoped rate-limiting middleware, distributed lock helper, and observability metrics utilities.
- Completed BE-802 by adding integration tests for Jira/Google webhook flows, including idempotency duplicate detection and dead-letter behavior after retry exhaustion.
- Completed BE-803 by adding an E2E integration test for Telegram-originated task intent flowing through Jira issue creation and Google Calendar event synchronization payload mapping.
- Completed BE-804 by adding burst-load webhook test scenarios for concurrent unique events, duplicate storm behavior, and retry-exhaustion dead-letter paths.
- Completed BE-805 by adding an operational release checklist and rollback runbook with deploy gates, rollback levels, and validated smoke test command set.
- Completed FE-005 by integrating TanStack Query cache + Zustand app store and refactoring dashboard/tasks/integrations pages to centralized state flows.
- Upgraded frontend shell styling with macOS-like glass UI language (window chrome, sidebar nav states, softened gradients, and responsive polish).
- Completed FE-101 by implementing login + token refresh frontend flow with persisted auth session, auto refresh timer, and sign-out controls.
- Completed FE-102 by adding workspace switcher backed by workspaces API and role-aware navigation states.
- Completed FE-103 by enforcing protected route guards with role-based page access checks and unauthorized view fallback.
- Completed FE-104 by adding profile/security page with API-key safety prompts, typed confirmations for sensitive actions, and guarded route integration.
- Completed FE-201 by wiring websocket message handling into Dashboard and rendering a capped realtime activity feed with event summaries.
- Completed FE-202 by upgrading Tasks into a unified board with toggleable kanban/list views and inline status transitions.
- Completed FE-203 by adding a 7-day calendar timeline with Jira-linked markers, calendar milestones, and task-based schedule hints.
- Completed FE-204 by introducing a dashboard command center with operator quick actions and one-click task creation.
- Completed FE-205 by implementing global search with cross-entity filters for tasks and integration accounts on the dashboard.
- Completed FE-301 by delivering a Jira connection wizard with staged steps and an explicit integration status panel.
- Completed FE-302 by delivering a Google Calendar connection wizard with staged steps and an explicit integration status panel.
- Completed FE-303 by adding provider profile management with local/cloud runtime selection and editable endpoint presets.
- Completed FE-304 by adding integration health diagnostics and webhook readiness checks in a dedicated provider health panel.
- Completed FE-401 by introducing an automation rule builder connected to automation CRUD endpoints with trigger/action/schedule controls.
- Completed FE-402 by adding a sync policy editor with field mapping and precedence toggles for source/target/manual strategies.
- Completed FE-403 by adding a conflict resolution center with strategy actions and local resolution history tracking.
- Completed FE-404 by adding retry and dead-letter inspection tools with attempt lifecycle simulation.
- Completed FE-501 by adding ESP32 device onboarding with registration form and workspace-linked device records.
- Completed FE-502 by adding a device status panel with online/offline state, battery, and last-event visibility.
- Completed FE-503 by adding quick command templates to dispatch common device operations.
- Completed FE-504 by adding per-device command/audit timeline tracking recent operational actions.
- Completed FE-601 by adding Vitest component tests for critical login and device-management flows.
- Completed FE-602 by adding Playwright end-to-end journeys covering login and core dashboard navigation.
- Completed FE-603 by adding automated accessibility checks using axe-core with Playwright.
- Completed FE-604 by adding bundle budget enforcement and analyze-mode bundle report generation.
- Completed FE-605 by adding frontend release checklist and rollback notes documentation.
- Expanded frontend hardening coverage with new unit tests for automation and integrations flows plus a broader dashboard e2e journey.
- Strengthened dashboard accessibility baseline by adding focusable timeline region and explicit accessible names for workspace/search filter selectors.
- Applied safe dependency hardening via npm override for esbuild, refreshed lockfile, and re-validated audit/build/test gates.
- Added production delivery flow playbook (staging -> canary -> production) and linked rollback criteria for operational release discipline.
- Added executable release scripts for preflight gates and post-deploy smoke verification.
- Completed FE-704 by adding GitHub Actions staged release workflow with preflight gating and staging/canary/production environment approvals.
- Completed FE-705 by adding observability dashboard links and alert ownership/escalation matrix documentation.

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
