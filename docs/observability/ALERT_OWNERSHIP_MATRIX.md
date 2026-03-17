# Alert Ownership Matrix

Last Updated: 2026-03-17
Owner: Platform Ops

## Dashboard Links

1. API Reliability Dashboard: https://grafana.example.com/d/backend-slo/api-reliability
2. Webhook Pipeline Dashboard: https://grafana.example.com/d/webhook-pipeline/webhook-pipeline
3. Automation Worker Dashboard: https://grafana.example.com/d/automation-worker/automation-worker

## Alert Routing and On-call Ownership

| Alert Name                | Severity | Primary Owner        | Secondary Owner | Slack Channel            | Escalation         |
| ------------------------- | -------- | -------------------- | --------------- | ------------------------ | ------------------ |
| ApiHigh5xxRatio           | Sev-2    | Backend On-call      | SRE On-call     | #ops-backend-alerts      | 15m to SRE lead    |
| ApiHighLatencyP95         | Sev-2    | Backend On-call      | SRE On-call     | #ops-backend-alerts      | 15m to SRE lead    |
| AutomationRunFailureSpike | Sev-3    | Integrations On-call | Backend On-call | #ops-integrations-alerts | 30m to Eng manager |
| WebhookRetryExhausted     | Sev-2    | Integrations On-call | SRE On-call     | #ops-integrations-alerts | 15m to SRE lead    |
| WebhookDeadLetterSpike    | Sev-2    | Integrations On-call | Backend On-call | #ops-integrations-alerts | 15m to Eng manager |

## Incident Hand-off Rules

1. Primary owner acknowledges within SLA window based on severity.
2. If no acknowledgement in SLA window, secondary owner is paged.
3. If unresolved after one escalation window, incident commander is assigned.
4. All Sev-1/Sev-2 incidents require post-incident RCA within 48 hours.
