# SLO Dashboards and Alerts

Last Updated: 2026-03-17
Owner: Backend

## Service Level Objectives

1. API Availability: >= 99.9% per 30 days.
2. API Latency P95: <= 500ms for GET/POST JSON endpoints (exclude streaming).
3. Webhook Ingestion Success: >= 99.5% per 7 days.
4. Automation Worker Success Ratio: >= 99.0% per 7 days.

## Core Dashboard Panels

1. Request volume by route and status code.
2. P50/P95/P99 latency by route.
3. 4xx and 5xx error ratio.
4. Rate limit rejections by scope (user/workspace/channel).
5. Automation run outcomes (success/failed/skipped_locked).
6. Webhook processed vs duplicate vs dead-letter outcomes.

## Alert Rules

Alert rules are defined in:

1. docs/observability/alert_rules.yml

Ownership and escalation mapping are defined in:

1. docs/observability/ALERT_OWNERSHIP_MATRIX.md

## Dashboard Template

Grafana dashboard template is defined in:

1. docs/observability/grafana_slo_dashboard.json

Primary dashboard links are defined in:

1. docs/observability/ALERT_OWNERSHIP_MATRIX.md

## Incident Severity Mapping

1. Sev-1: Availability < 99.0% in 1h rolling window.
2. Sev-2: P95 latency > 1s for 15m.
3. Sev-2: 5xx ratio > 2% for 10m.
4. Sev-3: Automation failures > 5% for 30m.
