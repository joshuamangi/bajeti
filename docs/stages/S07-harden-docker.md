# S07: Harden Docker Compose and the Dockerfile

**Prompt:** P3  |  **Mode:** claude  |  **Depends on:** S06  |  **Suggested branch:** `feature/issue-N-harden-docker`

## Goal

Make the container setup safer and smaller for the Pi: pinned versions, non-root, localhost-only port, limits, healthcheck, migrations at start.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `docs/hardening-plan.md` (S06)
4. Dockerfile, docker-compose files, Makefile
5. `infra/compose` (if S04 created it)

### Outputs of earlier stages this stage relies on

- S06 plan
- S04 compose files

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: harden the Docker setup for a Raspberry Pi (arm64, 3.7 GB RAM). Plan first, then change docker-compose*.yml and Dockerfile.

Do:
- Pin base image and cloudflared to specific versions (not :latest). Use a slim base and a multi-stage build; keep the final image small.
- Run the app as a non-root user. Make the SQLite data directory a bind mount owned by that user.
- Bind the published port to 127.0.0.1 only (cloudflared reaches the app over the Docker network).
- Add: healthcheck, restart: unless-stopped, mem_limit/cpus suitable for the Pi, read_only: true with tmpfs for /tmp where possible, cap_drop: [ALL], security_opt: no-new-privileges, json-file logging with max-size and max-file.
- Run `alembic upgrade head` in the container start script (with a lock so two starts cannot race), not as a separate manual step.
- Keep production data safe: the DB is a bind mount, so confirm no command in the Makefile (prune, clean) can delete it, and make those targets safer or remove them. Never run them.

Definition of done: `docker compose config` is valid, the container still starts locally on my Mac, the healthcheck passes, and you list every behaviour change. Do not touch the Pi.
```

## Watch out for

- If cloudflared runs in Docker and reaches the app by service name, binding the port to 127.0.0.1 can break the tunnel. Check how it connects first.
- A non-root user can break writes to the SQLite volume. Test with a real volume, not only a fresh one.
- Pinned image versions need a plan for updates (Dependabot or a calendar reminder).

## Your part (Claude cannot or should not do these)

1. Test locally on your Mac: `docker compose config`, start it, check the healthcheck.
2. Review the list of behaviour changes before merging. Deployment then happens through your normal pipeline or Ansible.

## Done when

- `docker compose config` is valid; the container starts locally and the healthcheck passes.
- Every behaviour change is listed.
- Makefile prune and clean targets are made safe or removed.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- Updated Dockerfile and compose files
- Safer Makefile

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Behaviour changes that S08 (deploy rollback) and S12 must account for.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S08-harden-ci-cd.md`: Harden CI/CD and deploy.
