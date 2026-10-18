# S09: Backup automation, alerting and restore tests

**Prompt:** P5  |  **Mode:** claude+human  |  **Depends on:** S02, S04  |  **Suggested branch:** `feature/issue-N-backup-automation`

## Goal

Make backups reliable: systemd timer, retention, integrity checks, alerting, monthly automated restore test, disaster-recovery docs.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `docs/design/storage-and-backups.md` (S02)
4. `infra/ansible` roles: backups and backup_target (S02, S04)
5. `docs/runbooks/rebuild.md` (S05)

### Outputs of earlier stages this stage relies on

- S02 design and roles
- S04 playbook
- S05 rebuild runbook

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: make backups reliable and prove they restore. Plan first. P1c [S02] already designs the destinations (SSD, Mac pull, S3); this prompt is for the automation, alerting and polish on top of that design.

Context: cron at 02:00 copies the SQLite file locally and to S3. Some local copies are missing for several dates and there has never been a restore test.

Do:
- Replace file copy with `sqlite3 <db> ".backup <dest>"` (safe while the app is running). Enable WAL mode if appropriate and explain the SD-card write trade-offs.
- Write infra/ansible/roles/backups: a systemd timer (preferred over cron for logging and Persistent=true so missed runs catch up), retention policy (e.g. 7 daily, 4 weekly, 6 monthly), integrity check (`PRAGMA integrity_check`), checksum, encrypted upload to S3 (server-side encryption or age) using a least-privilege IAM policy (write-only for the Pi, give me the policy JSON with placeholders).
- A `restore.sh` that restores into a temporary location and runs integrity_check plus a row-count sanity query, and a monthly automated restore test that alerts on failure.
- Alerting: a simple healthcheck ping (for example a dead-man's-switch URL kept in a secret) when a backup does not complete.
- Document RPO/RTO and the manual disaster-recovery steps for a dead SD card (fresh Pi OS -> run the Ansible playbook -> restore latest backup).

Definition of done: restore script works against a sample DB in CI, no credentials in the diff, docs explain how I verify last night's backup.
```

## Watch out for

- Never store backup credentials or the dead-man's-switch URL in the repo.
- The restore test must run against a copy, never the live database.
- Alert noise gets ignored. Alert on missing backups, not on every run.

## Your part (Claude cannot or should not do these)

1. Create the dead-man's-switch check and store its URL in your secret store.
2. Apply the least-privilege IAM policy and run the restore tests, including one full disaster-recovery drill.

## Done when

- restore.sh works against a sample DB in CI.
- No credentials in the diff.
- Docs give RPO/RTO and explain how to verify last night's backup.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- restore.sh and the monthly restore test
- DR documentation

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Measured RPO/RTO and the date of the last full DR drill.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S10-app-security-fixes.md`: App security fixes with tests.
