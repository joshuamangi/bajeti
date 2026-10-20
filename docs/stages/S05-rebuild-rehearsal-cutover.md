# S05: Rebuild rehearsal and cutover

**Prompt:** P1d  |  **Mode:** claude+human  |  **Depends on:** S02, S03, S04  |  **Suggested branch:** `feature/issue-N-rebuild-rehearsal`

## Goal

Prove the app can be rebuilt from nothing, then perform the OS cutover with the old SD card kept as the rollback.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `docs/runbooks/pi-os-upgrade.md` (S03)
4. `infra/README.md` and the playbook (S04)
5. `docs/design/storage-and-backups.md` (S02)
6. Makefile, Dockerfile, docs/migrations.md

### Outputs of earlier stages this stage relies on

- S03 runbook
- S04 Ansible code
- Verified backups (S02)

## Before you start

- Take a fresh backup and restore it somewhere safe before starting. Keep the old SD card untouched.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: prove that Bajeti can be rebuilt from nothing using only the repo, secrets I hold, and a backup. Plan first.

1. Write docs/runbooks/rebuild.md and a `make rebuild` target (safe: never prunes volumes or deletes the DB) for the app layer: build image, start, run migrations, health check. Add scripts/smoke.sh that checks the health endpoint, registers/logs in a throwaway test user against a COPY of the data, and compares row counts of key tables against the backup.
2. Rehearsal A, on my Mac with Docker: build the image for linux/arm64 (buildx), restore a recent backup copy into a temp directory, run alembic upgrade head, run smoke.sh. Record timings and anything that needed manual intervention.
3. Rehearsal B, BEFORE cutover (see P1b [S03]): once the backup Pi has been rebuilt, run a staging copy of Bajeti on it (LAN-only, different port, no Cloudflare tunnel, restored from a backup copy), or use the new app-Pi media with a different hostname/tunnel. Either way production is untouched. Staging must never be exposed publicly and must not use the production SECRET_KEY.
4. Drift detection: add a monthly `ansible-playbook --check --diff` job (run from my Mac, not the Pi) that reports any manual changes on the Pi not captured in Ansible.
5. List every manual step that remained and automate it or document why it cannot be.

Definition of done: a fresh-Pi-to-running-app procedure with measured time, a green smoke test on both rehearsals, and an updated docs/pi-inventory.md marking each item as "in Ansible" or "deliberately dropped".
```

## Watch out for

- Never run the old and the new instance against different databases behind the same Cloudflare tunnel.
- Keep the old SD card unchanged and labelled until the first week after cutover has gone cleanly.
- `make rebuild` must never prune volumes or delete the database.
- Staging uses a different SECRET_KEY and is not reachable from the internet.

## Your part (Claude cannot or should not do these)

1. Run Rehearsal A on your Mac and Rehearsal B (staging on the rebuilt backup Pi, LAN-only, no tunnel, different SECRET_KEY).
2. Do the cutover yourself following the runbook, with an explicit go/no-go at each stage.
3. Re-register the GitHub self-hosted runner and check the Cloudflare tunnel.
4. Watch the first seven days using the post-cutover checklist.

## Done when

- docs/runbooks/rebuild.md with measured times, `make rebuild` that never prunes volumes or deletes the DB, and scripts/smoke.sh.
- A green smoke test on both rehearsals.
- docs/pi-inventory.md marks each item as in Ansible or deliberately dropped.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- docs/runbooks/rebuild.md
- make rebuild target
- scripts/smoke.sh
- Updated docs/pi-inventory.md

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Cutover date, anything that needed manual intervention, and the drift-check schedule.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S06-hardening-plan.md`: Pi security audit and hardening plan.
