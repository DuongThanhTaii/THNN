# Frontend Task Board

Last Updated: 2026-03-17
Legend: TODO | IN_PROGRESS | BLOCKED | DONE

## F0 - Foundation

- [x] FE-001 Initialize frontend app (Vite or Next.js) in frontend folder. (DONE)
- [x] FE-002 Define design tokens and theme system. (DONE)
- [x] FE-003 Setup routing and layout shells (auth/app/settings). (DONE)
- [x] FE-004 Setup API client and websocket client with typed contracts. (DONE)
- [x] FE-005 Setup state management (query cache + app store). (DONE)

## F1 - Auth and Workspace UX

- [x] FE-101 Build login and token refresh flow. (DONE)
- [x] FE-102 Build workspace switcher and role-aware navigation. (DONE)
- [x] FE-103 Build protected routes and permission guards. (DONE)
- [x] FE-104 Build profile and API-key safety prompts. (DONE)

## F2 - Dashboard Core

- [x] FE-201 Build realtime activity feed (chat, tasks, sync events). (DONE)
- [x] FE-202 Build unified task board (kanban + list mode). (DONE)
- [x] FE-203 Build calendar timeline view with Jira-linked markers. (DONE)
- [x] FE-204 Build command center with quick actions. (DONE)
- [x] FE-205 Build global search and filters. (DONE)

## F3 - Integrations UI

- [x] FE-301 Build Jira connection wizard and status panel. (DONE)
- [x] FE-302 Build Google Calendar connection wizard and status panel. (DONE)
- [x] FE-303 Build provider profile manager (local/cloud selection). (DONE)
- [x] FE-304 Build health panel for providers and integration webhooks. (DONE)

## F4 - Automation and Sync UX

- [x] FE-401 Build automation rule builder (trigger/action/schedule). (DONE)
- [x] FE-402 Build sync policy editor (field mapping and precedence). (DONE)
- [x] FE-403 Build conflict resolution center with action history. (DONE)
- [x] FE-404 Build retry/dead-letter inspection tools. (DONE)

## F5 - ESP32 and Device UX

- [x] FE-501 Build device onboarding view for ESP32 registration. (DONE)
- [x] FE-502 Build device status panel (online, battery, last event). (DONE)
- [x] FE-503 Build quick command templates sent to devices. (DONE)
- [x] FE-504 Build command/audit timeline per device. (DONE)

## F6 - Quality and Delivery

- [x] FE-601 Add component tests for critical flows. (DONE)
- [x] FE-602 Add E2E tests for dashboard main journeys. (DONE)
- [x] FE-603 Add accessibility checks (keyboard, contrast, semantics). (DONE)
- [x] FE-604 Add performance budget and bundle analysis. (DONE)
- [x] FE-605 Add frontend release checklist and rollback notes. (DONE)

## F7 - Productionization Flow

- [x] FE-701 Define staging -> canary -> production release flow. (DONE)
- [x] FE-702 Add release preflight script for backend+frontend gates. (DONE)
- [x] FE-703 Add post-deploy smoke script for health/metrics/webhook checks. (DONE)
- [x] FE-704 Integrate release flow into CI/CD pipeline with manual approvals. (DONE)
- [x] FE-705 Add production dashboard links and alert ownership matrix. (DONE)

## Suggested Frontend Folder Plan

Create this structure during implementation:

- frontend/src/app
- frontend/src/features/auth
- frontend/src/features/dashboard
- frontend/src/features/tasks
- frontend/src/features/integrations
- frontend/src/features/automation
- frontend/src/features/devices
- frontend/src/shared/api
- frontend/src/shared/ws
- frontend/src/shared/ui

## Status Update Format

Use this format whenever updating a task:

- Task ID:
- New Status:
- Date:
- Owner:
- PR/Commit:
- Notes:
