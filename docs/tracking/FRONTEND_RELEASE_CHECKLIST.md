# Frontend Release Checklist and Rollback Notes

Last Updated: 2026-03-17
Owner: ThanhTai

## Pre-release Checklist

- Confirm `npm run build` passes in `frontend/`.
- Confirm `npm run test:run` passes.
- Confirm `npm run perf:budget` passes after build.
- Run `npm run build:analyze` and review `frontend/dist/stats.html` for unusual growth.
- Verify critical journeys manually:
  - Login -> Dashboard.
  - Dashboard -> Tasks -> Devices navigation.
  - Integrations wizard basic connect simulation.
  - Automation page create/delete rule smoke flow.
- Confirm environment variables for production API base URLs are correct.
- Validate browser smoke in latest Chrome and Firefox.

## Release Steps

1. Merge approved PR to the release branch.
2. Tag the release in git with semantic version.
3. Build production assets.
4. Deploy static assets to hosting target.
5. Run post-deploy smoke checks against production.

## Rollback Notes

### Trigger Conditions

- Login flow broken for majority of users.
- App cannot fetch core dashboard data.
- Severe accessibility regression in top-level navigation.
- Bundle budget breach causing unacceptable load time.

### Rollback Procedure

1. Identify last known good release tag.
2. Redeploy static assets from last known good tag.
3. Purge CDN cache for frontend asset paths.
4. Re-run smoke checks for login/dashboard/tasks/devices.
5. Announce rollback in release channel with incident summary.

### Post-rollback Follow-up

- Collect failing build/test output.
- Open a hotfix task with regression root cause.
- Add or tighten automated test coverage for escaped issue.
