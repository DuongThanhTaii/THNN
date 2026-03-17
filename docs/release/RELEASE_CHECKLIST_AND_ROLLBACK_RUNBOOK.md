# Release Checklist and Rollback Runbook

Last Updated: 2026-03-17
Owner: Backend Team
Scope: free-claude-code backend and integration webhooks

## 1) Release Checklist

### 1.1 Pre-Release (T-24h to T-1h)

- Confirm release branch is merged and CI is green.
- Confirm no pending schema-migration risk is unresolved.
- Confirm secrets are available in target environment:
  - `JWT_SECRET`
  - `ENCRYPTION_MASTER_KEY`
  - `ENCRYPTION_FALLBACK_KEYS` (if rotating)
  - `JIRA_WEBHOOK_SECRET`
  - `GOOGLE_WEBHOOK_SECRET`
- Confirm integration credentials are valid (Jira and Google OAuth app config).
- Confirm database snapshot backup exists and timestamp is recorded.

### 1.2 Deployment Readiness Gates (T-30m)

- Health endpoint baseline (before deploy):
  - `GET /api/v1/system/status` returns `status=ok`.
- Metrics endpoint baseline (before deploy):
  - `GET /api/v1/system/metrics` responds successfully.
- Verify webhook endpoints are reachable from public ingress:
  - `POST /webhooks/jira`
  - `POST /webhooks/google-calendar`

### 1.3 Release Execution

1. Pull the target release commit/tag on the deployment host.
2. Install/update dependencies:

```bash
uv sync --frozen
```

3. Export/refresh environment values from deployment secret store.
4. Run migrations (idempotent):

```bash
uv run python -c "from storage.migrations.runner import run_migrations; print(run_migrations())"
```

5. Restart application process:

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8082 --timeout-graceful-shutdown 5
```

### 1.4 Post-Deploy Verification (T+0 to T+15m)

- Health check:
  - `GET /api/v1/system/status` returns `status=ok` and expected environment/provider.
- Metrics check:
  - `GET /api/v1/system/metrics` returns counters and latency fields.
- Webhook canary checks:
  - Send one signed Jira webhook test event and verify HTTP 200.
  - Send one valid Google webhook header set and verify HTTP 200.
- Idempotency check:
  - Replay the same webhook event id and verify duplicate handling path.
- Dead-letter check:
  - Ensure no abnormal spike in `webhook.dead_letter` audit logs.

### 1.5 Sign-Off Criteria

- No elevated 5xx rate for 15 minutes after deploy.
- No auth, migration, or lock-related runtime errors in logs.
- No unexpected rise in webhook retry exhaustion.
- Team sign-off recorded in release notes.

## 2) Rollback Runbook

### 2.1 Rollback Triggers

Trigger rollback if any of the following occurs after release:

- Sustained 5xx error rate above SLO threshold.
- Authentication failures impacting normal traffic.
- Webhook ingestion failing for Jira or Google for more than 5 minutes.
- Critical data consistency issue detected in task/sync paths.

### 2.2 Rollback Levels

#### Level A: Fast App Rollback (Code-only)

Use when database schema is still compatible with previous release.

1. Stop current app process.
2. Checkout previous stable release commit/tag.
3. Start app with previous release image/code.
4. Verify:

- `GET /api/v1/system/status`
- webhook canary success

#### Level B: Feature-Flag Mitigation (No code rollback)

Use when incident is isolated to specific subsystems.

- Disable scheduler worker:
  - `AUTOMATION_SCHEDULER_ENABLED=false`
- Reduce API pressure:
  - tighten rate-limit env values and restart.
- Temporarily disable unstable channel adapters if needed:
  - `ENABLE_ESP32=false`

#### Level C: Data Recovery Rollback

Use when data corruption risk exists.

1. Stop write traffic (maintenance mode / ingress block).
2. Restore database from latest known-good snapshot.
3. Re-deploy last known-good application release.
4. Re-run smoke checks and business canaries.

## 3) Incident Execution Checklist

- Assign incident commander.
- Record start timestamp and suspected blast radius.
- Capture failing request samples and correlation IDs.
- Execute rollback level (A/B/C).
- Validate recovery endpoints and webhook behavior.
- Publish incident update and ETA.

## 4) Post-Rollback Actions

- Freeze new releases until root cause is identified.
- Produce RCA with concrete fix and test additions.
- Add regression tests for the exact failure mode.
- Update this runbook if any missing step was discovered.

## 5) Smoke Test Command Set

Run these commands from project root after deploy or rollback:

```bash
uv run pytest -q tests/integrations/test_webhook_flows.py
uv run pytest -q tests/integrations/test_webhook_burst_load.py
uv run pytest -q tests/integrations/test_e2e_telegram_jira_calendar_sync.py
```
