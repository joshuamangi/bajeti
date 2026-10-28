# Bajeti

## Session start

At the start of every session read `docs/stages/IMPLEMENTATION.md` and follow it. Do not start a stage until the user agrees.

## About

Personal budgeting app: FastAPI + SQLite. Production runs in Docker on a Raspberry Pi behind a Cloudflare Tunnel.
This repository is PUBLIC. Never commit secrets, IP addresses, credentials, database files or backups.

## Architecture

Two layers in one repo. The web layer calls the API over HTTP.

- JSON API (`/api/...`): `routers/` -> `services/` -> `data/db/models/models.py`, validated by `schema/`.
  - Services are classes of static methods (`ExpenseService`, `AllocationService`, ...).
  - Auth is a JWT bearer token, resolved by `core/security.py::get_current_user`.
- Web UI: `app/routers/requests_router.py` -> `app/handlers/` -> `app/services/` (httpx calls to the API) -> Jinja templates in `app/templates/`.
  - JWT lives in the `access_token` cookie; the selected budget in `active_budget_id`.
  - Frontend is vanilla JS and CSS in `app/static`, built with esbuild into `app/static/dist` (ignored by git). ECharts is planned for the analytics page but is not used yet.
- `app/requests.py` is an old duplicate of the web layer; do not extend it.

## Domain

- Budget (`expense` or `savings`) -> Allocation (budget x category) and Target (budget x category, short/mid/long-term amounts).
- Category type must match budget type. Expense type is `spend` or `withdrawal`.
- A withdrawal lowers both `budget.amount` and `allocation.allocated_amount`; update and delete reverse that (`services/expense_service.py`).
- Months are strings `"YYYY-MM"`.

## Commands

- Tests: `pytest -q` (uses `./test.db`, created and dropped by `tests/conftest.py`).
- Migrations: `alembic upgrade head`, `alembic revision --autogenerate -m "..."`. After a production migration, record the revision in `docs/migrations.md`.
- Frontend build: `npm run dev` / `npm run build`.
- Docker: `make up`, `make logs-bajeti`, `make deploy`.
  - Do NOT run `make prune` or `make clean` casually: they run `docker system prune -af --volumes` and `docker volume prune -f`.
- Deploys: merging a PR to `main` runs `.github/workflows/deploy.yml` on the Pi (rebuild, `alembic upgrade head`). Direct `workflow_dispatch` skips the deploy job.

## Conventions

- Match surrounding code. Python style as in `services/allocation_service.py`.
- CSS: spacing in multiples of 4, `em` units, tokens in `app/static/css/palette.css`.
- Every query is scoped by `user_id`. Ownership is checked through `BudgetService.get_budget_by_id` / `CategoryService.get_category_by_id`.
- New endpoints need a test that a second user gets 404 on the first user's resources.
- Money: use `Decimal`; avoid `float` for new code.

## Security rules

- Never read, print or commit `.env`, `*.pem`, `cloudflared/*.json`, `*.db`, tokens or keys. Compare secrets by hash.
- The old `SECRET_KEY` was committed in git history (`routers/auth.py`) and must be treated as burned. Production must use a rotated key stored only in the GitHub Actions secret and the Pi `.env`.
- Read-only commands against the Pis are fine and expected: investigate first, then bring findings and a recommendation. Any change (services, packages, config, files, GitHub settings) or destructive command (docker prune, recursive deletes on data, history rewrites) needs the user's confirmation of that specific change first. Show what will change and how to undo it.
- Verify before reporting status. Never say something is done or not done from assumption; check it, or say it is unchecked.
- Never mark a stage `done` without the user's confirmation. Present the evidence and ask.
- Bring recommendations with the decision the user has to make, not lists of options or questions you could answer by investigating. This matches `docs/stages/00-shared-context.md`.
- Never write real IPs, hostnames or tokens into code or docs; use placeholders such as `<PI_APP_HOST>`.
- Check `git diff --staged` before every commit.

## Workflow

- One GitHub issue per epic with a checklist; parked ideas in `docs/backlog.md`.
- Stage status lives in the table in `docs/stages/IMPLEMENTATION.md`; what each stage produced and left unverified goes in `docs/stages/HANDOFF.md`.
- `docs/roadmap.md` and the issue checklists track epic-level progress only. Tick them when a stage completes an epic item.
- Branch `feature/issue-N-short-name` -> PR (template in `.github/pull_request_template.md`) -> merge to `main` -> auto deploy.

## UI redesign (Prototype A)

- Spec: design/prototype-a/PORT-GUIDE.md and design/prototype-a/bajeti-prototype-a-evolve.html
- The prototype is a reference, not code to paste. Keep Jinja + vanilla JS + esbuild; no frameworks.
- Work one stage per branch. Plan first, then implement, then verify against the prototype at 375px and 1200px, light and dark.
