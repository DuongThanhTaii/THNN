# Frontend Task Board

Last Updated: 2026-03-14
Legend: TODO | IN_PROGRESS | BLOCKED | DONE

## F0 - Foundation

- [x] FE-001 Initialize frontend app (Vite or Next.js) in frontend folder. (DONE)
- [x] FE-002 Define design tokens and theme system. (DONE)
- [x] FE-003 Setup routing and layout shells (auth/app/settings). (DONE)
- [x] FE-004 Setup API client and websocket client with typed contracts. (DONE)
- [ ] FE-005 Setup state management (query cache + app store). (TODO)

## F1 - Auth and Workspace UX

- [ ] FE-101 Build login and token refresh flow. (TODO)
- [ ] FE-102 Build workspace switcher and role-aware navigation. (TODO)
- [ ] FE-103 Build protected routes and permission guards. (TODO)
- [ ] FE-104 Build profile and API-key safety prompts. (TODO)

## F2 - Dashboard Core

- [ ] FE-201 Build realtime activity feed (chat, tasks, sync events). (TODO)
- [ ] FE-202 Build unified task board (kanban + list mode). (TODO)
- [ ] FE-203 Build calendar timeline view with Jira-linked markers. (TODO)
- [ ] FE-204 Build command center with quick actions. (TODO)
- [ ] FE-205 Build global search and filters. (TODO)

## F3 - Integrations UI

- [ ] FE-301 Build Jira connection wizard and status panel. (TODO)
- [ ] FE-302 Build Google Calendar connection wizard and status panel. (TODO)
- [ ] FE-303 Build provider profile manager (local/cloud selection). (TODO)
- [ ] FE-304 Build health panel for providers and integration webhooks. (TODO)

## F4 - Automation and Sync UX

- [ ] FE-401 Build automation rule builder (trigger/action/schedule). (TODO)
- [ ] FE-402 Build sync policy editor (field mapping and precedence). (TODO)
- [ ] FE-403 Build conflict resolution center with action history. (TODO)
- [ ] FE-404 Build retry/dead-letter inspection tools. (TODO)

## F5 - ESP32 and Device UX

- [ ] FE-501 Build device onboarding view for ESP32 registration. (TODO)
- [ ] FE-502 Build device status panel (online, battery, last event). (TODO)
- [ ] FE-503 Build quick command templates sent to devices. (TODO)
- [ ] FE-504 Build command/audit timeline per device. (TODO)

## F6 - Quality and Delivery

- [ ] FE-601 Add component tests for critical flows. (TODO)
- [ ] FE-602 Add E2E tests for dashboard main journeys. (TODO)
- [ ] FE-603 Add accessibility checks (keyboard, contrast, semantics). (TODO)
- [ ] FE-604 Add performance budget and bundle analysis. (TODO)
- [ ] FE-605 Add frontend release checklist and rollback notes. (TODO)

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
