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

## The real cutover on the Pi: 2026-10-20

The app Pi was rebuilt from a fresh Raspberry Pi OS Lite 64-bit (Debian 13) on the same SD card, with the old card saved as an image first. Times are local (EAT), read from log and file timestamps, so they are approximate except where a tool reported them.

| Step | Time | Measured |
|---|---|---|
| App stopped (W1) | 13:40 | |
| Final backup, checked on the app Pi, the backup Pi, the Mac and S3 (W2, W3) | 13:40 to 13:41 | backup 10 s; same SHA-256 on three tiers, S3 by size; restore test 0 s |
| Shutdown, card to the Mac (W4) | 13:46 | |
| Image of the old card (W5) | 13:50 to 14:39 | `dd` 2,911 s at 44 MB/s for 127.9 GB; 8.35 GB compressed; `gzip -t` clean |
| Flash, first boot, first SSH (W6, W7) | 14:39 to 15:01 | about 22 min including the image check; flash and boot not timed separately |
| Ansible, secrets restore, second Ansible run (W8, W9) | about 15:05 to 15:46 | about 40 min, including the fixed address and one stop at the secrets guard |
| Image build on the Pi | 15:47 to about 15:51 | under 4 min |
| Database restore, start, public check (W10, W11) | 15:51 to 15:52 | integrity `ok`, all 7 row counts equal the backup; app healthy in 25 s; tunnel registered 4 connections |

**Downtime: about 2 h 12 min** (13:40 to 15:52), against the 3 to 3.5 h estimate. Afterwards: a backup fix and a 2-minute reboot for the memory cgroup (16:07 to about 16:22), then the runner re-registered. The old card image was not needed. Its checksum is recorded in `docs/stages/HANDOFF.md`.

Checked at the cutover: the tunnel starts with the pinned image under Docker 29.6.0; the app answers on the real hostname and the login works; the app uses about 65 to 90 MiB and the tunnel about 17 to 40 MiB (limits 768 MiB and 128 MiB, applied after the cgroup fix). Not tested: starting the tunnel **without** `cert.pem` (it was in the secrets bundle).

## Manual steps that remained

| Step | Why it is manual | Status |
|---|---|---|
| Flash the card (Imager) | Needs the card in the Mac | Manual by design |
| First SSH host-key trust, then the Mac's `known_hosts` and the backup Pi's pin | Fingerprints must be compared by a person | Manual by design |
| Sudo password for the Ansible run | The fresh OS has no passwordless sudo; this is a hardening gain | Manual by design (`--ask-become-pass`) |
| Fixed address of the Pi | The router reservation did not carry over to the new install (it came up on another address) | **Now in Ansible** (`base`, `base_static_address`); applies at the next reboot |
| Run Ansible, restore the secrets bundle, run Ansible again | The app role refuses to continue without `.env` | Manual order, by design |
| Restore the database | Needs the private age key | Manual by design |
| `awscli` was missing, so the S3 copy failed | Gap in the roles | **Fixed** (#129) |
| Memory cgroup missing, so container limits were ignored | Gap in the roles | **Fixed** (#129); needs a reboot and `docker compose up -d --force-recreate` once, because the limit is stored when a container is created |
| Download and register the GitHub runner | Registration needs a one-hour token | Manual by design; downloading the program could be automated in S08 |

Other finding: the backup Pi's USB SSD lost its connection during the window (a cable problem, unrelated to the rebuild). Its `fstab` entry has `nofail`, so it does not remount by itself after a re-plug; mount it by hand with `systemctl start mnt-ssd.mount` and the other app's bind mount after it.
