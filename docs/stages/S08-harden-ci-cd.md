# S08: Harden CI/CD and deploy

**Prompt:** P4  |  **Mode:** claude+human  |  **Depends on:** S07  |  **Suggested branch:** `feature/issue-N-harden-ci-cd`

## Goal

Make test and deploy workflows least-privilege, add backup before deploy and rollback after a failed health check, and list the GitHub settings you must change.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `docs/hardening-plan.md` (S06)
4. `.github/workflows/test.yml` and deploy.yml
5. Dockerfile and compose files as changed in S07
6. `infra/` (github_runner role)

### Outputs of earlier stages this stage relies on

- S06 plan
- S07 Docker changes

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: harden .github/workflows/test.yml and deploy.yml. Plan first.

Context: deploy.yml runs on a self-hosted runner on the production Pi when a PR is merged to main. It pulls, rewrites .env from secrets, rebuilds with --no-cache, recreates the container and runs alembic. The repo is public.

Do:
- Align CI Python to 3.11 (matches the Docker image), add ruff lint, pytest with coverage, and pip-audit; pin all action versions to commit SHAs.
- Give workflows least-privilege `permissions:` blocks. Never expose secrets to pull_request workflows from forks. Deploy only from `push` to main after required checks pass.
- Stop using --no-cache on every deploy (it creates ~12 GB of build cache on the SD card). Use layer caching and a scheduled `docker builder prune` with a safe age filter.
- Add a pre-deploy step: backup the DB (sqlite3 .backup) and verify the file; add a post-deploy health check with automatic rollback to the previous image tag if it fails.
- Add a migration check: run `alembic upgrade head` and `alembic downgrade -1` against a COPY of a production-shaped SQLite DB in CI.
- Document the GitHub settings I must change by hand (branch protection on main, required status checks, approval for outside collaborators, Dependabot, runner groups). You cannot change them; give me click-by-click or `gh` CLI commands for me to run.

Definition of done: workflows pass lint (actionlint), no secrets echoed in logs, rollback path documented.
```

## Watch out for

- The self-hosted runner on a public repo is the highest-risk item here. Require approval for outside collaborators' workflows before anything else.
- Do not give the deploy workflow more permissions to make a check pass.
- Test the rollback deliberately; an untested rollback does not count.

## Your part (Claude cannot or should not do these)

1. Apply the GitHub settings Claude lists: branch protection on main, required checks, approval for outside collaborators' workflows, Dependabot, runner groups.
2. Test the rollback path deliberately.

## Done when

- Workflows pass actionlint and no secrets are echoed in logs.
- Rollback path documented and tested.
- A click-by-click or `gh` list of the GitHub settings, which you have applied.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- Updated workflows
- A GitHub settings checklist document

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Which GitHub settings you have applied and when.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S09-backup-automation.md`: Backup automation, alerting and restore tests.
