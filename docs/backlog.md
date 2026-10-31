# Backlog

Ideas that are not scheduled yet. Move an item into `docs/roadmap.md` and open an issue when it is picked up.

## Payment ingestion on iPhone (M-Pesa SMS and payment emails)

Open question: how do the raw messages get from the phone to Bajeti?

Options to evaluate:

- iOS Shortcuts automation on incoming message. Needs testing for reliability, because SMS automations on iOS often ask for a confirmation tap and may not fire for every message.
- Share sheet Shortcut: select the M-Pesa message, share to a Shortcut that POSTs it to `/api/pending-payments`.
- Forward payment emails to a dedicated mailbox that the Pi polls over IMAP.
- Gmail API with a filter on payment senders.
- Manual paste box in the app (the first thing to ship, works with any option above).

Decision needed after trying the share sheet Shortcut for a week.

## Other ideas

- Loading spinners (from `docs/TODO.md`)
- Consistent button and input sizes, for example Quick Expense (from `docs/TODO.md`)

## Missed-backup alerts (from S02, not urgent)

Today a missed night is silent. Both Pis already support it; it only needs two free dead-man's-switch checks (for example on healthchecks.io):

- Check 1: period 1 day, grace 3 hours. Put its URL in `BACKUP_PING_URL` in `~/.config/bajeti/backup.env` on the app Pi. `backup.sh` pings on success and at `/fail` on failure.
- Check 2: period 1 day, grace 3 hours. Put its URL in `PULL_PING_URL` in `~/.config/bajeti/pull.env` on the backup Pi. Pinged only after a fully verified pull.

The URLs are secrets: keep them only in those two files and the password manager, never in the repo. The Mac already warns by notification when its newest copy is over 7 days old.

## Monthly drift check (from S05, decision 2026-10-20)

The unattended launchd job (`scripts/drift-check.sh` plus `scripts/com.example.bajeti-drift-check.plist.example`) cannot work on the app Pi: the rebuilt Pi has no passwordless sudo, so `--check` has no way to become root without a person. It is **not installed**, on purpose.

Instead, once a month (and after any Ansible change), run it by hand from the Mac:

```
cd infra/ansible && ansible-playbook -i inventory/production.ini playbooks/site.yml --check --diff --ask-become-pass
```

Put a calendar reminder on the 1st of each month. Read the diff: a change means something was done by hand on a Pi that Ansible does not describe, so add it to Ansible or undo it.

Later, in S08 or S09: adjust the script to take `--ask-become-pass` when run in a terminal, and decide whether to keep the plist for the backup Pi only (its sudo is passwordless). Do not add a sudo rule to the Ansible user just to make the job unattended.

## Pi and app hardening (from S06, decision 2026-10-20)

The full plan is `docs/hardening-plan.md`. The owner chose to work on the Bajeti app first, so every item waits here. Pick them up after the app epics (S11 onwards), or sooner if something changes the threat model (for example more users or a new collaborator).

Most valuable first, if the time comes:

- Close open registration (`REGISTRATION_OPEN` setting, default off) and rate-limit login. Public hostname, nothing limits either today (A1, A2).
- Tunnel credentials file to mode 600 on the Pi (A6, 10 minutes, on the Pi).
- Cookie `Secure` and `SameSite`, stop logging bearer tokens, hide `/docs` and `/openapi.json` (A3, A4).
- Make `docker-compose.yml` match the Pi: cloudflared tag and healthcheck (A5).
- Pull-based deploy so the runner leaves the Pi (B1, S08). This is the biggest remaining risk: the runner is in the `docker` group.
- Dependabot version updates, and why the Oct 19 run failed (A7).
- Checks that need sudo on the Pi: `ufw status verbose`, `sshd -T`, unattended-upgrades logs, ssh key comments (A8 to A10).
- Smaller image, tunnel container hardening, read-only root, audit log, Cloudflare Access (A12, A13, B6, B7, B2).

Stages that carry these: S07 (Docker), S08 (CI/CD), S10 (app code).

## Log cleanup (from S10, 2026-10-20)

`core/security.py` logs `Current user resolved: id=... email=...` at INFO on every authenticated request, which puts the owner's email in the journal and `docker logs` and drowns real events. Move it to DEBUG or log the user id only. While there, check other INFO lines that carry personal data, and decide on one log format (time, level, request id) so the logs can be searched later (see the monitoring item).

## Smaller items left by S10

- Run `alembic upgrade head` before the new container takes traffic. Today the deploy starts the container, waits 10 seconds and then migrates, so any deploy that adds a column returns 500 on login for about 15 seconds. Fix in S08 (CI/CD).
- Replace the inline `onclick=` handlers and `style=` attributes in the templates, then remove `'unsafe-inline'` from the CSP in `core/security_headers.py`.
- `docker-compose.yml` still pins cloudflared 2025.9.1 while the Pi runs 2026.10.1 through the Ansible override (hardening plan A5).
- Registration still answers 409 for an existing email. With registration closed this only matters while `REGISTRATION_OPEN` is on.

## Monitoring and alerts (from S10, 2026-10-20)

Today the Pi health check (every 15 minutes) and the backup timer only write to the journal, so nobody is told when something fails, and Docker logs keep only 3 x 10 MB per container. Recommended order, all free and light:

1. Alerts that reach the owner, no new software on the Pi: Cloudflare tunnel-health notifications, an external uptime check on the public URL with email alerts, the planned healthchecks.io pings for backups, and a third ping from the Pi health check carrying disk, temperature and memory. Free-plan limits not verified.
2. After the log cleanup: one request-log line per request (method, route, status, duration, user id, no email or token) and a small weekly summary script (5xx, 401 and 429 counts, slowest routes, startup and migration errors).
3. Optional, only if 1 and 2 are not enough: Netdata on loopback behind an ssh tunnel. Skip Prometheus, Grafana, Loki, and anything that needs the Docker socket.

## Dependabot configuration (hardening plan A7)

Add `.github/dependabot.yml` for pip, npm, docker and github-actions (weekly, small PR limit) once the monitoring items are done. Open alerts when this was written: pytest (fix 9.0.3, dev only) and picomatch (build tooling). Never close a Dependabot PR without merging unless the alert is dismissed with a reason: PR #121 was closed unmerged and left the python-multipart alerts open for three days.

## Admin area (from the Prototype A design, 2026-10-28)

Prototype A (`design/prototype-a/`, §5.10 of `PORT-GUIDE.md`) includes an owner-only Admin hub. Issue #152 (2026-10-31) decided the role model, a single owner flag (`users.is_owner`, set with `python -m cli.set_owner <email>`), and built the hub from a section registry (`ADMIN_SECTIONS` in `app/handlers/admin_handlers.py`) with Users → Reset access. The rest stays parked; each section is one registry entry.

Sections drawn in the prototype:

- Users: add a member through a 24-hour invite link, remove with Undo. (Reset access is done, #152.)
- Registration: open/closed switch (the `REGISTRATION_OPEN` setting exists; it would move to a stored `setting`), with a warning while open.
- Backups: last backup, status, size, last restore test (warn after 30 days), "Record restore test", "Back up now". Ties to S09.
- System health: app, database size, version, uptime, service worker, connection.
- Activity log: filters All, Money, Access, Admin. Auto recurring items are recorded here (decided 2026-10-28), so the log table may land earlier than the hub.
- Feature switches: Analytics, Recurring, Payments, Targets; turning one off hides it for everyone and deletes nothing.
- Data export: CSV and JSON.

Needs: `user.role` (or owner flag), `setting`, `feature_flag`, `activity_log`, an invite token table, owner-only dependency in `core/security.py`, and a test that a member gets 403/404 on every admin route.
