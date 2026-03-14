# Git Naming and Push Standard (Company Workflow)

## 1. Branch Naming Standard

Format:

- `type/scope-short-description`

Allowed `type`:

- `feat` new feature
- `fix` bug fix
- `refactor` code restructuring without behavior change
- `chore` maintenance/non-feature change
- `docs` documentation update
- `test` test-only changes

Examples:

- `feat/backend-task-api`
- `feat/frontend-integrations-panel`
- `fix/webhook-secret-validate`
- `docs/deployment-playbook`

## 2. Commit Message Standard

Use Conventional Commits:

- `type(scope): short summary`

Examples:

- `feat(api): add v1 task list and create endpoints`
- `feat(frontend): connect tasks page to backend API`
- `docs(git): add naming and push standard`

Rules:

- Use present tense, imperative mood.
- Keep first line under 72 characters.
- Add body when context is needed.

## 3. Task-level Commit and Push Policy

Each completed task should follow this sequence:

1. Stage only related files.
2. Commit with one clear task-focused message.
3. Push immediately to remote branch.
4. Update progress tracker with commit hash.

Recommended commands:

```bash
git checkout -b feat/backend-task-api
# edit files

git add api/v1/ storage/ docs/tracking/
git commit -m "feat(api): add task and integration scaffold"
git push -u origin feat/backend-task-api
```

## 4. Remote Setup Standard

If repository already has `origin`, do not run `git remote add origin ...` again.

Use one of these:

```bash
# replace origin URL
git remote set-url origin https://github.com/DuongThanhTaii/THNN.git

# or keep current origin and add secondary remote
git remote add company https://github.com/DuongThanhTaii/THNN.git
```

## 5. Merge Policy

- Direct push to `main` only for emergency hotfix with approval.
- Default flow: feature branch -> PR -> review -> squash merge.
- Require green checks before merge:
  - lint
  - tests
  - build

## 6. Tagging and Release Naming

- Semantic version tags: `vMAJOR.MINOR.PATCH`
- Release branch naming: `release/vX.Y.Z`

## 7. Secret Handling Rules

- Never commit real keys in tracked files.
- Keep secrets in `.env` (gitignored) or secret manager.
- Rotate credentials immediately if leaked.

## 8. Daily Push Cadence

- Minimum: push every finished task or every 2 hours.
- End-of-day: push all local commits and update tracker.

## 9. Mandatory Tracker Update

After each push, update:

- `docs/tracking/MASTER_PROGRESS_TRACKER.md`
- `docs/tracking/BACKEND_TASKS.md`
- `docs/tracking/FRONTEND_TASKS.md`

Include:

- task id
- status
- date
- commit hash
