# GitHub Environments Setup

Last Updated: 2026-03-17
Owner: ThanhTai

## Goal

Configure staging, canary, and production environments so release workflow approvals and deploy steps run automatically.

## Required Environments

1. staging
2. canary
3. production

Workflow reference:

1. .github/workflows/release-flow.yml

## Approval Rules

1. staging: at least 1 reviewer
2. canary: at least 1 reviewer
3. production: at least 2 reviewers

## Required Environment Variables

Set these as GitHub Environment Variables in each matching environment.

1. STAGING_DEPLOY_COMMAND
2. CANARY_DEPLOY_COMMAND
3. PRODUCTION_DEPLOY_COMMAND
4. STAGING_ROLLOUT_COMMAND
5. CANARY_ROLLOUT_COMMAND
6. PRODUCTION_ROLLOUT_COMMAND

Each deploy command should be a non-interactive shell command. The workflow injects API_BASE_URL and executes the command through bash.

Example commands:

```bash
./scripts/deploy/staging.sh "$API_BASE_URL"
./scripts/deploy/canary.sh "$API_BASE_URL"
./scripts/deploy/production.sh "$API_BASE_URL"
```

Rollout command variables are the infrastructure commands executed inside each script, for example:

```bash
STAGING_ROLLOUT_COMMAND="kubectl -n app set image deploy/api api=registry.example.com/app:${GITHUB_SHA}"
CANARY_ROLLOUT_COMMAND="kubectl -n app set image deploy/api-canary api=registry.example.com/app:${GITHUB_SHA}"
PRODUCTION_ROLLOUT_COMMAND="kubectl -n app set image deploy/api api=registry.example.com/app:${GITHUB_SHA}"
```

## Required Secrets

Store deployment credentials in GitHub Environment Secrets, for example:

1. CLOUD_API_TOKEN
2. KUBE_CONFIG_B64
3. DEPLOY_SSH_KEY

The workflow exports these secrets as environment variables for deploy steps.

## Verification Checklist

1. Trigger workflow manually in Actions tab.
2. Confirm preflight passes.
3. Confirm staging deployment waits for approval and runs deploy command.
4. Confirm canary deployment waits for approval, runs deploy command, and observes canary window.
5. Confirm production deployment waits for approval and runs smoke checks.
