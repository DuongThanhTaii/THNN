# Production Delivery Flow

Last Updated: 2026-03-17
Owner: ThanhTai

## Goal

Define one repeatable release flow from staging to canary to production.

## Flow Overview

1. Stage Gate: run full preflight and deploy to staging.
2. Canary Gate: deploy a limited slice of production traffic.
3. Production Gate: full rollout only after canary and smoke pass.

CI/CD workflow entrypoint:

1. .github/workflows/release-flow.yml (manual dispatch + environment approvals)
2. docs/release/GITHUB_ENVIRONMENTS_SETUP.md (approval and deploy command setup)
3. scripts/deploy/staging.sh, scripts/deploy/canary.sh, scripts/deploy/production.sh (deploy entrypoints)

## Stage Gate

1. Ensure branch is merged and CI is green.
2. Run local preflight:

```bash
bash scripts/release/preflight.sh
```

3. Deploy to staging environment.
4. Verify:

- Backend health and metrics endpoints respond.
- Frontend smoke journey: login -> dashboard -> tasks -> integrations -> automation.

## Canary Gate

1. Deploy release to canary target (5-10% traffic).
2. Observe 15 minutes minimum:

- No elevated 5xx error rate.
- No auth/session spike.
- No webhook retry/dead-letter spike.

3. Run post-deploy smoke:

```bash
bash scripts/release/post_deploy_smoke.sh https://<api-base-url>
```

## Production Gate

1. Roll out to 100% traffic.
2. Keep enhanced monitoring for 30 minutes.
3. If any Sev-1/Sev-2 trigger appears, execute rollback runbook immediately.

## Rollback Trigger Summary

- Sustained 5xx above threshold.
- Login/session failure for majority users.
- Webhook ingestion failures beyond 5 minutes.
- Data integrity issues in sync/task automation.

See detailed runbook in:

- docs/release/RELEASE_CHECKLIST_AND_ROLLBACK_RUNBOOK.md
- docs/tracking/FRONTEND_RELEASE_CHECKLIST.md

Observability ownership and dashboard links:

- docs/observability/ALERT_OWNERSHIP_MATRIX.md
