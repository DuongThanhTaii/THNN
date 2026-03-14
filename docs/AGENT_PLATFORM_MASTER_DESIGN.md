# Agent Platform Master Design

## 1) Muc tieu san pham

Xay dung mot he thong AI Agent da kenh, da provider, co kha nang:

- Quan ly va tu dong hoa cong viec hieu qua nhu OpenClaw.
- Dong bo hai chieu Jira va Google Calendar theo quy tac nghiep vu.
- Tro chuyen va dieu khien tren Telegram, CLI, Web Dashboard, ESP32.
- Cho nguoi dung tu chon model local (LM Studio, llama.cpp) hoac cloud API (OpenRouter, NVIDIA NIM).
- Van hanh on dinh, de quan sat, de mo rong, de onboarding nguoi dung.

## 2) Danh gia nen tang hien tai

Repo hien co da cung cap nen tang rat tot cho 3 lop sau:

- API + Provider Proxy:
  - [api/routes.py](api/routes.py)
  - [api/dependencies.py](api/dependencies.py)
  - [providers/openai_compat.py](providers/openai_compat.py)
- Message handling + queue theo cay + session persistence:
  - [messaging/handler.py](messaging/handler.py)
  - [messaging/trees/queue_manager.py](messaging/trees/queue_manager.py)
  - [messaging/session.py](messaging/session.py)
- Multi-provider local/cloud + model mapping:
  - [config/settings.py](config/settings.py)
  - [README.md](README.md)

Khoang trong can bo sung de dat muc tieu cua ban:

- Chua co integration layer cho Jira va Google Calendar.
- Chua co web dashboard realtime.
- Chua co adapter cho ESP32.
- Chua co event bus + state store thong nhat de sync da kenh.
- Chua co auth model cho dashboard va token vault cho OAuth.

## 3) Kien truc dich (Production-Ready)

## 3.1 Toan canh

- Edge/API Layer
  - FastAPI app hien tai tiep tuc la cong vao trung tam.
  - Them API namespace cho dashboard, auth, tasks, integrations.
- Agent Orchestrator Layer
  - Nhan event tu cac kenh va webhook.
  - Chay planner, scheduler, action runner, policy engine.
- Channel Adapter Layer
  - Telegram adapter (tai su dung code hien tai).
  - CLI adapter (interactive TUI/command mode).
  - WebSocket adapter cho dashboard.
  - ESP32 adapter qua MQTT hoac HTTP long-poll.
- Integration Layer
  - Jira connector (REST + webhook).
  - Google Calendar connector (OAuth2 + REST + push notifications).
- Provider Layer
  - Tai su dung providers hien tai: local + cloud.
- Data Layer
  - Postgres (state nghiep vu).
  - Redis (event bus, queue, cache, rate limit state).
  - Object storage (log artifacts, transcripts lon, uploads).

## 3.2 Nguyen ly thiet ke

- Event-driven, idempotent, eventually-consistent.
- Moi action co correlation_id va trace_id.
- Da tenant, da user, da workspace.
- De fallback provider, de circuit-breaker.
- Khong mat trang thai hoi thoai khi restart.

## 4) So do thanh phan chi tiet

### 4.1 Agent Core

Thanh phan moi can them:

- Conversation Router
  - Chuyen incoming message thanh normalized command-intent.
- Task Planner
  - Tach muc tieu lon thanh task graph nho.
- Action Executor
  - Chay tool actions co timeout, retry, rollback.
- Workflow Engine
  - Rule-based + schedule-based automations.
- Sync Engine
  - Dong bo state Jira <-> Calendar <-> Internal Task State.
- Notification Engine
  - Day update ra Telegram/Web/CLI/ESP32 theo policy.

### 4.2 Channel adapters

- Telegram
  - Tai su dung [messaging/platforms/telegram.py](messaging/platforms/telegram.py)
- Discord
  - Giu nguyen nhu mot kenh bo sung [messaging/platforms/discord.py](messaging/platforms/discord.py)
- Web Dashboard
  - Tao module moi: dashboard/api.py + dashboard/ws.py + dashboard/ui
- CLI
  - Them command suite quan tri: task list, task watch, provider switch
- ESP32
  - Adapter MQTT:
    - publish status, reminders, quick actions
    - receive button events, voice/text short commands

### 4.3 Integration services

- Jira Service
  - OAuth/API token, projects, issues, transitions, comments, labels, assignee
- Google Calendar Service
  - OAuth2, events CRUD, reminders, attendees, conferenceData
- Sync Policy Service
  - Mapping issue fields -> calendar event fields
  - conflict resolution policy
  - retry + dead-letter

## 5) Dong bo Jira va Google Calendar

## 5.1 Mapping nghiep vu de xuat

- Jira issue -> Calendar event
  - issue.key -> event.extendedProperties.private.jiraKey
  - summary -> title
  - description -> description
  - due date/start/end -> start/end
  - assignee -> attendee (neu co email)
  - status change -> update event color/metadata

- Calendar event -> Jira issue/task update
  - event update co jiraKey thi update issue lien quan
  - event moi thuoc project rule co the tao issue moi

## 5.2 Conflict resolution

- Nguon su that mac dinh: Jira cho status va owner; Calendar cho timeslot.
- Last-write-wins co vector clock metadata.
- Neu xung dot field quan trong:
  - Tao sync_conflict record
  - Gui canh bao den Telegram + dashboard
  - Cho phep user chon merge policy

## 5.3 Idempotency

- Moi webhook event co integration_event_id duy nhat.
- Luu processed_events de bo qua duplicate.
- Action update issue/event su dung idempotency key.

## 6) Provider architecture cho nguoi dung

## 6.1 Muc tieu UX

- User co trang setup wizard:
  - Chon Local Model hoac API Model.
  - Kiem tra ket noi ngay lap tuc.
  - Luu profile provider theo workspace.
- Cho phep fallback chain:
  - local primary -> openrouter secondary -> nvidia_nim tertiary

## 6.2 Provider profile schema

- provider_profile
  - id
  - owner_user_id
  - type (lmstudio, llamacpp, open_router, nvidia_nim)
  - base_url
  - api_key_ref (khong luu plain text)
  - model_map (opus/sonnet/haiku/default)
  - health_status
  - last_checked_at

## 6.3 Tai su dung code hien tai

- Model parsing va routing giu nguyen tu [config/settings.py](config/settings.py)
- Provider instantiation pattern giu nguyen tu [api/dependencies.py](api/dependencies.py)
- SSE conversion giu nguyen tu [providers/openai_compat.py](providers/openai_compat.py)

## 7) Du lieu va CSDL

## 7.1 Bang can co (Postgres)

- users
- workspaces
- channels
- channel_sessions
- conversations
- messages
- tasks
- task_runs
- automations
- automation_runs
- integration_accounts
- jira_issue_links
- calendar_event_links
- sync_policies
- sync_conflicts
- processed_events
- provider_profiles
- audit_logs

## 7.2 Redis keys

- queue:events:incoming
- queue:events:retry
- lock:task:{id}
- rate:channel:{id}
- ws:presence:{workspace}

## 8) API contract de xuat

## 8.1 Public API

- POST /api/v1/chat/send
- GET /api/v1/chat/stream
- GET /api/v1/tasks
- POST /api/v1/tasks
- PATCH /api/v1/tasks/{id}
- POST /api/v1/automations
- POST /api/v1/integrations/jira/connect
- POST /api/v1/integrations/google/connect
- POST /api/v1/providers/profile
- POST /api/v1/providers/test
- POST /api/v1/providers/select

## 8.2 Webhooks

- POST /webhooks/jira
- POST /webhooks/google-calendar

## 8.3 Internal event envelope

- event_id
- trace_id
- correlation_id
- workspace_id
- actor
- source
- type
- payload
- created_at

## 9) Web Dashboard

## 9.1 Chuc nang

- Realtime conversation timeline.
- Board task + calendar unified view.
- Integration center (Jira, Google, provider).
- Automation rules editor (if-this-then-that + cron).
- Audit va observability panel.

## 9.2 Giao tiep realtime

- WebSocket channel:
  - ws://.../ws/workspaces/{workspace_id}
- Server push:
  - task.updated
  - sync.conflict
  - message.delta
  - provider.health

## 10) ESP32 design

## 10.1 Kieu ket noi

Phuong an uu tien: MQTT

- Toi uu cho thiet bi IoT, on dinh tren mang yeu.
- Ho tro retain, QoS, reconnect.

## 10.2 Topic de xuat

- agent/{device_id}/in/cmd
- agent/{device_id}/in/event
- agent/{device_id}/out/status
- agent/{device_id}/out/notify
- agent/{device_id}/out/voice

## 10.3 Payload schema ngan

- cmd message:
  - id
  - ts
  - workspace_id
  - text
  - quick_action
- status message:
  - state
  - active_task_count
  - next_reminder

## 10.4 Capability ESP32

- Nut bam quick actions: Done, Snooze, Create Jira task.
- OLED/LCD status hien thi lich va task sap den han.
- Voice short command (neu them mic + STT upstream).

## 11) Bao mat

- OAuth2 PKCE cho Google, OAuth/JWT cho dashboard.
- Token vault:
  - Ma hoa AES-GCM, key tu KMS/secret manager.
- RBAC:
  - owner, admin, member, viewer.
- Mọi webhook verify signature.
- API rate limiting theo user/workspace.
- Audit log bat buoc cho action quan trong.

## 12) Reliability va van hanh

- Retry policy:
  - exponential backoff + jitter.
- Dead-letter queue cho event loi qua nguong.
- Circuit breaker cho integration API.
- Health checks:
  - provider
  - webhook processor
  - queue lag
- SLO de xuat:
  - chat ack < 2s (p95)
  - action completion < 30s (p95)
  - sync consistency < 60s (p95)

## 13) Kiem thu

- Unit tests cho parser, planner, mapping.
- Contract tests cho Jira/Google APIs (mock server).
- Integration tests cho webhook + sync loop.
- E2E tests:
  - Telegram -> task create -> Jira -> Calendar
  - Dashboard action -> update all channels
  - ESP32 button -> Jira transition
- Chaos tests:
  - provider timeout
  - duplicate webhook
  - queue worker restart

## 14) Roadmap trien khai de xuat

## Phase 1 (MVP 3-4 tuan)

- Integration Jira + Google basic CRUD.
- Sync one-way Jira -> Calendar.
- Telegram + CLI + basic web dashboard.
- Provider profile basic + health check.

## Phase 2 (4-6 tuan)

- Two-way sync + conflict center.
- Rule engine va scheduler.
- Web dashboard realtime day du.
- ESP32 MQTT adapter + quick actions.

## Phase 3 (3-5 tuan)

- Hardening: RBAC, audit, metrics, DLQ, backup/restore.
- Multi-workspace, multi-tenant governance.
- Auto onboarding wizard cho provider va integrations.

## 15) Refactor plan tu repo hien tai

- Giu nguyen:
  - [providers](providers)
  - [api/models](api/models)
  - [messaging/trees](messaging/trees)
- Tach them module:
  - core/orchestrator
  - core/workflows
  - integrations/jira
  - integrations/google_calendar
  - channels/web
  - channels/esp32
  - dashboard
  - storage

## 16) Dinh nghia hoan tat (Definition of Done)

- User co the:
  - Chat voi agent tren Telegram, CLI, Web, ESP32.
  - Tao/cap nhat issue Jira bang ngon ngu tu nhien.
  - Tao/cap nhat lich Google va duoc sync voi Jira.
  - Chon provider local hoac cloud qua wizard.
- He thong dat:
  - Logging, metrics, tracing day du.
  - Retry + DLQ + idempotency cho webhook/sync.
  - Test coverage muc tieu > 80% cho core logic.

## 17) Quyet dinh ky thuat khuyen nghi

- Backend: FastAPI + Celery/RQ worker + Redis + Postgres.
- Frontend dashboard: Next.js hoac Vite + React + WebSocket.
- ESP32 protocol: MQTT truoc, HTTP fallback sau.
- Auth: Keycloak/Auth0 hoac tu xay JWT + refresh token.

## 18) Tuyen bo kha thi

Du an cua ban kha thi rat cao neu di theo kien truc tren va tai su dung dung cac module co san.

Danh gia kha thi tong the:

- Nen tang hien tai: 8.5/10
- Do phuc tap tich hop bo sung: 7.5/10
- Kha nang dat muc tieu OpenClaw-like: 8/10

Ket luan: Co the xay ban day du, on dinh, da kenh tren repo nay ma khong can viet lai tu dau.
