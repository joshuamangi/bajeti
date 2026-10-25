# Shared context (read at the start of every stage)

These facts and rules apply to every stage. Claude reads this at the start of every stage.

## The project in short

Bajeti is a personal and household budgeting web app built and run by one developer. FastAPI, SQLAlchemy 2, Alembic, SQLite, Jinja2 with vanilla JS and hand-written CSS. It runs in Docker Compose on a Raspberry Pi behind a Cloudflare Tunnel. A second Pi on the same LAN has an SSD for backups. The repository is public. For full detail see the project context file or CLAUDE.md.

## Rules for every stage

(The step-by-step flow is in `docs/stages/IMPLEMENTATION.md`.)

1. Plan first: show the plan or design and wait for approval before changing anything that is hard to undo.
2. For steps the stage file marks as the user's (changes on the Pis, GitHub settings, real secrets), give a numbered checklist with exact commands and say what to paste back, redacted. Read-only investigation on the Pis is allowed without asking; do it first so the checklist and recommendations rest on evidence.
3. Never write secrets, IPs, hostnames, tokens, .env contents or real data into code, docs, tests or examples. Use `<PI_APP_HOST>` and `<PI_BACKUP_HOST>`. Real values live in a git-ignored Ansible inventory or `~/.ssh/config`.
4. Read-only commands against the Pis are fine. Any change on a Pi, any GitHub settings change, and any destructive command (docker prune, recursive deletes on data, history rewrites) needs the user's confirmation of that specific change first, with what will change and how to undo it.
5. Do not work around a block. If something is refused or fails, say so and ask.
6. At the end, report what changed, what was NOT verified, and any risks. Do not claim a check passed unless it was run, and never report a state (done, not done, enabled, disabled) without checking it.
7. Never mark a stage `done` without the user's confirmation. Present the evidence for each "Done when" item and ask.

## Shared context block (from the prompt pack, section 1)

```
Project: Bajeti, a personal/household budgeting app. One developer, one Raspberry Pi (64-bit, ~3.7 GB RAM, SD-card boot), SQLite, Docker Compose, Cloudflare Tunnel, GitHub Actions with a self-hosted runner on the Pi. The repo is PUBLIC.

Stack: FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, JWT auth; web layer = Jinja2 + vanilla JS + hand-written CSS (tokens in palette.css, spacing in multiples of 4, em units, `p-` class prefix, dark theme). The web layer calls the JSON API over HTTP.

Rules for every change:
- Every query is scoped by user_id. Every new endpoint ships with a cross-user test proving user B cannot read or change user A's data.
- Alembic migrations must be safe on production data, have a real downgrade, and be tested against a copy of the production schema.
- Prefer simple, low-memory solutions. No new heavy dependencies. Pin versions.
- Services are classes of static methods. Follow existing patterns before inventing new ones.
- Never write secrets, IPs, hostnames, tokens, .env contents or real data into code, docs, tests or examples. Use placeholders and environment variables.
- Never run destructive commands (docker system prune, rm -rf on data dirs, git history rewrites, DB deletes) without asking.
- Money is Decimal, not float. Months are "YYYY-MM" strings.

Workflow: plan first, small commits, tests alongside code, update docs/ and the relevant GitHub issue checklist, summarise what was and wasn't verified.
```

## Mode meanings

- `claude`: Claude can implement and test inside the repo.
- `claude+human`: Claude prepares code, scripts and exact commands; the user runs the Pi, GitHub-settings or secret steps.
- `design-gate`: Claude writes a design first and stops for approval before any code.
