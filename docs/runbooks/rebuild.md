# Runbook: rebuild the app layer from nothing (S05)

Covers the app only: image, start, migrate, health check, smoke test. The OS and the Pi itself are in `pi-os-upgrade.md`; the machine setup is `infra/README.md`.
Placeholders only. Nothing here prunes volumes or deletes the database.

## Inputs you need

| Input | Where it comes from |
|---|---|
| The code | `git clone` of the public repository, branch `main` |
| `.env` (the real `SECRET_KEY` and the rest) | the encrypted secrets bundle (`pi-os-upgrade.md`, steps P3 and W9) |
| Tunnel files in `cloudflared/` (`config.yml` and the credentials JSON) | the same bundle |
| The database | the newest encrypted backup (`docs/runbooks/backup-install.md`), decrypted with the private key from the password manager |

## Steps

1. **[Pi-app]** Put the database at `data/db/data/bajeti.db` (the compose file mounts `./data` into the container). Verify: `python3 - <<<'import sqlite3;print(sqlite3.connect("data/db/data/bajeti.db").execute("pragma integrity_check").fetchall())'` prints `[('ok',)]`.
2. **[Pi-app]** `make rebuild`. It builds the image, starts the stack, runs `alembic upgrade head`, then waits up to 60 seconds for the site to answer. It never prunes anything. Verify: it ends with `healthy`.
3. **[Pi-app]** Smoke test against a **copy** of the data (it registers a throwaway user). Do not run it against the live database. See "Smoke test" below.
4. **[Mac]** Open the public hostname and log in with your own account. Compare the totals with the ones you wrote down before the rebuild.

Rollback: `docker compose down` stops the stack and leaves the data in place; put the previous `bajeti.db` back if a restore was wrong.

## Smoke test

```
scripts/smoke.sh --base-url http://127.0.0.1:<PORT> --db <path to the DB the app serves> --backup <backup .db file>
```

It checks that the site answers, that the static files its pages use load, that every table has exactly the row count of the backup, and that a throwaway user can register, log in and read its profile. It refuses a non-loopback address.

## Rehearsal A (Mac, Docker): 2026-10-19

A fresh clone of the branch, the newest backup copied into a temporary folder, the image built for arm64 (the Mac is arm64, so no emulation), then the steps above on port 18000 with a throwaway `SECRET_KEY` and no tunnel. The temporary data and image were deleted afterwards.

| Step | Measured on the Mac (10 CPUs) | On the Pi |
|---|---|---|
| Image build, no cache | 68 s | not measured, expect several times longer |
| Start container | 0.3 s | not measured |
| `alembic upgrade head` | 0.6 s (already at head) | not measured |
| Smoke test | 1.4 s | not measured |

Result: **green**. Row counts matched the backup for all 7 tables (598 expenses, 5 users). All 21 static files that the templates reference exist in the image built from a fresh clone, so a rebuild does not need Node on the Pi.

Manual interventions needed: none, except creating the throwaway `.env` and the loopback port override for the rehearsal.

## Rehearsal C (Mac, a Debian 13 container with systemd): 2026-10-20

Replaces the "staging on the backup Pi" rehearsal, which the plan cannot support: the backup Pi was not rebuilt, has no Docker, 2 GB of RAM and is another app's host. Instead the real Ansible roles were applied twice to a throwaway container, with no Pi touched.

Roles run: `base`, `ssh_hardening`, `unattended_upgrades`, `fail2ban`, `backups` (including the pinned, checksum-verified `age` download), `monitoring`, `github_runner`.

| Run | Result |
|---|---|
| 1 | 22 changes, 0 failures. Two real bugs found and fixed first: `systemd-timesyncd` is not installed on a minimal system, and `/etc/systemd/journald.conf.d` does not exist (the same risk was fixed for `/etc/docker`). |
| 2 | 25 of 26 tasks unchanged. The one change is `systemd-timesyncd`, whose unit has `ConditionVirtualization=!container`, so it can never stay running in a container. On a Pi it stays active. |

Not exercised in a container, so checked at the cutover: `firewall` (no kernel firewall in the container), `docker`, `bajeti_app`, the units that need the real `bajeti_app` stack.

## Not covered by the rehearsals (checked at the cutover instead)

The tunnel container starting with the pinned image and without `cert.pem`; the app behind the real hostname; Docker 29 on the new OS; the Pi's own build time and memory use.
