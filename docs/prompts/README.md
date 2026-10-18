# Bajeti: Claude Code Prompt Pack

Put this file at `docs/prompts/README.md` (or split each prompt into `.claude/commands/<name>.md` so you can run it as `/name`). No secrets, IPs or credentials belong in this file or in anything it generates. The repo is public.

---

## 0. How to use this pack

Each stage has its own file under `docs/stages/` (start at `docs/stages/README.md`). The stage file lists the context to read first, includes the prompt from this pack, and says what you do yourself and how to hand off. This file is the reference copy of the prompts; if you edit a prompt in a stage file, edit it here too if you want them to stay in sync. Each prompt sits under a heading of the form `## P<n>. Title`.

1. Keep the stable project facts in `CLAUDE.md` (architecture, conventions, constraints). Use Section 1 below as its starting content.
2. Start every non-trivial task in **plan mode** (Shift+Tab twice, or `/plan`). Approve the plan, then let it implement.
3. One issue per session. Branch `feature/issue-N-short-name`. Run `/clear` between unrelated tasks.
4. Paste the prompt, replace anything in `<angle brackets>`, and keep the "Definition of done" lines. They are what make the output checkable.
5. After each task ask: "List what you changed, what you did NOT verify, and any risks." Then review the diff yourself before the PR.
6. Anything touching the Pi, secrets or auth: ask Claude to produce a **dry-run / check-mode plan first** and never to run commands against the Pi itself unless you say so.

7. The Pi's LAN address, hostnames and SSD details stay OUT of the repo (it is public). Prompts use `<PI_APP_HOST>` (the Pi running Bajeti) and `<PI_BACKUP_HOST>` (the Pi with the SSD) placeholders. Real values live in a git-ignored Ansible inventory or your `~/.ssh/config`. Give both Pis fixed addresses via DHCP reservations on the router. Anything Claude produces from an audit must be redacted before it is committed.

### Suggested order (updated: the Pi OS is end of life)

The OS has no security patches, so the Pi is now the top risk alongside the leaked key. A verified, restorable backup comes BEFORE any OS work because it is the safety net.

1. **P0** rotate SECRET_KEY (about 30 minutes, do today; independent of everything else).
2. **P1a** read-only Pi audit: find out what is installed and configured, and what is actually needed.
3. **P1c** SSD storage and backups, including a restore test from each location.
4. **P1b** OS end-of-life decision and upgrade runbook.
5. **P1** infrastructure as code, codifying only what P1a showed is needed.
6. **P1d** rebuild rehearsal, then the cutover (old SD card kept untouched as the rollback).
7. **P2 to P4** hardening and CI/CD (many items arrive for free from the rebuild).
8. **P5** backup polish: alerting, retention, automated restore tests.
9. **P6** app security fixes, **P7** Targets, **P8 to P14** epics (prototypes are in P12), **P15** prompt-writing helpers.

---

## 1. Shared context block (goes in CLAUDE.md, or paste at the start of a session)

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

---

## 2. Infrastructure as code: decision and approach

**Recommendation: Ansible (run from your Mac over SSH) plus the Docker Compose files already in the repo.**

| Option | Verdict |
|---|---|
| Ansible | Best fit. Agentless, idempotent, nothing extra to run on a 3.7 GB Pi, `--check --diff` gives dry-runs, good roles for hardening (ssh, ufw, fail2ban, unattended-upgrades, docker). |
| Terraform/OpenTofu | Good for things with APIs: the Cloudflare tunnel/DNS and the S3 bucket. Optional later; not for configuring the Pi itself. |
| Nix/NixOS | Powerful but heavy for a single Pi and a single developer. Skip. |
| Docker Compose only | Already used for the app. Keep it, but it does not cover OS hardening. |

Layout to ask Claude for (all in the public repo, with real inventory and secrets kept OUT of it):

```
infra/
  ansible/
    ansible.cfg
    inventory/
      example.ini            # placeholders only, committed
      production.ini         # real host, git-ignored
    group_vars/
      all.example.yml        # committed, placeholders
      all.vault.yml          # git-ignored or ansible-vault / sops+age encrypted
    playbooks/site.yml
    roles/
      base/                  # packages, timezone, NTP, journald limits, noatime, swap policy
      ssh_hardening/
      firewall/              # ufw
      fail2ban/
      unattended_upgrades/
      docker/                # engine, daemon.json log rotation, non-root usage
      bajeti_app/            # compose files, env template, systemd unit or compose up
      storage/               # backup Pi only: SSD mount by UUID (nofail, noatime), backup dirs
      backup_target/         # backup Pi only: pull job from the app Pi, versioned snapshots, retention
      backups/               # app Pi: sqlite .backup, age encryption, systemd timer, S3 upload, restore script
      github_runner/         # unprivileged runner user and service
      monitoring/            # disk, temp, SD wear signals, healthcheck ping
  compose/
    docker-compose.yml
    docker-compose.prod.yml
  terraform/                 # optional: cloudflare tunnel + s3 bucket + IAM (least privilege)
  README.md                  # bootstrap, how to run check mode, how to restore
```

Secrets rule: committed files hold only `*.example` placeholders. Real values live in GitHub Actions secrets, an Ansible Vault file, or sops+age. Never in the repo.

---

## P0. URGENT: rotate the leaked SECRET_KEY

```
Task: rotate the JWT SECRET_KEY, which was committed to git history in September 2025 in a public repo and is still used in production. Treat the old key as burned. Do NOT rewrite git history.

Plan first. Then:
1. Confirm no code path still hardcodes a key. Search the working tree for SECRET_KEY usage. Everything must come from app/config.py via environment.
2. Add a startup check in config: refuse to start in ENVIRONMENT=production if SECRET_KEY is missing, shorter than 32 bytes of entropy, or equals any known-leaked value (store only a SHA-256 hash of the old key in the check, never the key itself).
3. Give me the exact manual steps for: generating a new key (openssl rand -hex 32), updating the GitHub Actions secret, updating the Pi .env (chmod 600), recreating the container, and verifying old tokens are rejected and new logins work. Warn that all users are logged out once.
4. Add a test that an old/forged token is rejected.
5. Add a short docs/security.md section: key rotation procedure and cadence.

Definition of done: tests pass, no secret appears in the diff, and I have a numbered checklist to run on the Pi. Do not execute anything against the Pi.
```

---

## P1a. Pi inventory and necessity audit (read-only)

Claude Code runs on your Mac, which can reach the Pis on the LAN, so it should not connect to them unless you say so. It therefore writes a safe script, you run it, review the output, and give it back.

```
Task: build a read-only audit of what is installed and configured on BOTH Raspberry Pis (the app Pi `<PI_APP_HOST>` and the backup Pi `<PI_BACKUP_HOST>` that has the SSD), decide for each item whether it is necessary, and prioritise the work. Do NOT try to connect to either Pi. The script runs on one host at a time and labels its report "app" or "backup" via an argument. For the backup Pi, also report: what its services/containers are for, what is stored on the SSD (top-level directory names and sizes only, never file contents), the SSD's filesystem and mount options, and its boot device.

Step 1. Write scripts/pi-audit.sh (bash). It must be strictly read-only: no package changes, no service restarts, no file writes except one report file ./pi-audit-report.txt (git-ignored; add it to .gitignore). Collect:
- OS and hardware: /etc/os-release, kernel, architecture, Pi model, firmware/EEPROM status (`rpi-eeprom-update` with no flags), boot device.
- Support status: Debian codename, whether apt sources still resolve, count of upgradable packages, held packages, `apt-mark showmanual`.
- Services and schedules: enabled unit files, failed units, timers, crontabs for all users, /etc/cron.*.
- Network exposure: listening sockets (`ss -tulpn`), firewall rules summary, effective sshd security settings only (`sshd -T` filtered to PermitRootLogin, PasswordAuthentication, PubkeyAuthentication, AllowUsers, Port).
- Accounts: users with sudo, number of authorized_keys per user (count only, never contents), last logins.
- Docker: engine and compose versions, containers (image, ports, user), images with sizes, volumes, networks, daemon.json, `docker system df`, compose project paths.
- Storage: lsblk, mounts, fstab, df -h, SMART if available, largest directories under /var/log and /var/lib/docker, journald disk usage.
- Health: throttling/under-voltage flags (`vcgencmd get_throttled`), temperature, memory, swap, uptime, dmesg lines about mmc/usb/under-voltage errors.
- GitHub Actions runner: service name, install directory, the user it runs as, runner version (never tokens).
- Backups: what runs them, where files land, names/sizes/dates of the last 14 days.

Hard redaction rules inside the script: never print the contents of .env, *.pem, id_*, authorized_keys, shadow, tokens or any environment variable values; mask IPv4/IPv6 addresses, MAC addresses and the hostname in all output (sed). State at the top of the report that it has been redacted and must still be reviewed by me before sharing.

Step 2. After I paste the report back, produce docs/pi-inventory.md (redacted, safe to commit) with a table:
Host (app/backup) | Item | What it is | Evidence it is used | Needed? (Keep / Remove / Replace / Investigate) | Risk if removed | Action | Priority
Never mark something "Remove" on a guess; use "Investigate" and say how to find out.

Step 3. Prioritise using this order: public exposure/security > unsupported software (end-of-life OS) > data-loss risk > SD-card wear > tidiness. Output the top 10 actions with effort estimates.

Principle for everything that follows: the rebuilt Pi gets only what is justified here and expressed in Ansible. Anything undocumented that was done by hand is "drift" and is either added to Ansible or deliberately dropped.
```

---

## P1b. Pi OS end of life: decide and plan the upgrade

```
Context: the app Pi's OS has reached end of life (no security updates), and the backup Pi may be on the same release. The app Pi is a production host reachable through a Cloudflare Tunnel, so this is high priority.

Task: investigate, then write docs/runbooks/pi-os-upgrade.md. Plan first; do not execute anything.

1. From pi-audit-report.txt, identify the exact Debian / Raspberry Pi OS release and the Pi model. Verify the current support status and the latest Raspberry Pi OS release from official sources (Debian release and LTS pages, Raspberry Pi documentation) and cite the links. If the report is missing, give me the exact commands to run.
2. Compare the options, two lines of trade-off each:
   a) In-place apt dist-upgrade across major releases. Check what Raspberry Pi currently says about supporting this, whether it must step through each release, and the risk of a half-upgraded system with Docker, the runner and kernel/firmware.
   b) Fresh install of the current Raspberry Pi OS 64-bit Lite (headless) on new media, configured entirely by the Ansible playbook, data restored from a verified backup, then cut over. This is my expected recommendation unless the evidence says otherwise.
   c) Any other realistic option, only if there is a concrete reason.
3. For the recommended option, write the full runbook: preconditions (a verified restorable backup, see P1c), Raspberry Pi Imager settings (hostname placeholder, SSH key only, no default password, timezone Africa/Nairobi), first boot, Ansible bootstrap, deploying the app, restoring the database, verification, cutover, rollback.
4. Cutover design:
   - The old SD card stays untouched and is the instant rollback.
   - The old and new instances must never write to different databases behind the same tunnel at the same time (avoid split writes). Stop the old one first, or rehearse the new one on a different hostname/tunnel.
   - Re-register the GitHub self-hosted runner on the new install (new registration token; remove the old runner in GitHub settings).
   - Cloudflare tunnel credentials and all secrets are supplied from secret stores, never committed.
   - Cron/timers, firewall, SSH config, Docker engine (installed from Docker's apt repo for the new Debian codename, version pinned) all come from Ansible.
5. Compatibility checklist: Docker and compose plugin versions, cgroups and kernel settings for memory limits, nftables vs iptables backend for ufw, SSH config differences, time sync, locale.
6. Give a downtime estimate, explicit go/no-go checks at each stage, rollback criteria, and a post-cutover checklist for the first 7 days.
7. Two-Pi sequencing. The backup Pi may be on the same end-of-life OS. Propose an order and justify it. My expectation: back up first to the Mac and S3 so those tiers are verified, then rebuild the BACKUP Pi first as a low-stakes, LAN-only dry run of the Ansible playbook (reflashing only its boot media and leaving the SSD data untouched, verified by checksums before and after), and only then rebuild the app Pi. State what happens to the SSD backups during the backup Pi's rebuild and how long there is no second tier available. Confirm what else the backup Pi does before touching it (from P1a).

Definition of done: numbered, copy-pasteable steps tagged [Mac], [Pi-app] or [Pi-backup], each with a verify step and a rollback; a list of unknowns I must confirm; no IPs, hostnames or tokens in the document.
```

---

## P1c. Backups across two Pis, MacBook and offsite

Topology: two Raspberry Pis on the same LAN. The **app Pi** (`<PI_APP_HOST>`) runs Bajeti. The **backup Pi** (`<PI_BACKUP_HOST>`) has the SSD attached. Reserve fixed addresses for both with DHCP reservations on the router so the inventory never goes stale.

```
Context: Bajeti runs on the app Pi (`<PI_APP_HOST>`), booting from an SD card. A second Pi on the same LAN (`<PI_BACKUP_HOST>`) has an SSD attached. I also have a MacBook. The database is SQLite; backups currently run via cron at 02:00 on the app Pi to local storage and S3, with gaps and no restore test. I do not yet know what else the backup Pi does, its OS release, or whether it also needs the end-of-life upgrade (P1a audits it). Never write real addresses or hostnames into the repo; use the placeholders.

Task: write docs/design/storage-and-backups.md, wait for my approval, then implement. Plan first.

Decide and justify, with two-line trade-offs:
1. Boot media for the APP Pi. The SSD is on a different machine, so booting the app Pi from it is not available. Compare: (a) keep SD boot now and cut writes (journald and Docker log limits, tmpfs for /tmp, WAL trade-offs, a high-endurance card), (b) buy a small second SSD and USB-boot the app Pi (needs a Pi 4/5 with current EEPROM and boot order set; mention UASP/bridge quirks and under-voltage), (c) physically move this SSD to the app Pi and find another backup home. Recommend one. Also tell me what the backup Pi's boot media is and whether it can or should boot from its own SSD.
2. Backup Pi SSD layout: ext4, mounted by UUID with `noatime,nofail` so a missing SSD never blocks boot, a dedicated backups directory owned by a non-root backup user, no SMB/NFS sharing unless justified, SMART monitoring if the USB bridge supports it.
3. Backup tiers (3-2-1) and failure domains:
   - live DB on the app Pi,
   - a copy on the backup Pi's SSD (different machine, different power supply, different storage),
   - a copy on my MacBook, pulled from the backup Pi (not from the app Pi),
   - an encrypted offsite copy in S3.
   Note explicitly that both Pis are in the same building, so a fire, theft, flood or house-wide power event takes out both. That is why the offsite tier stays.
4. App Pi -> backup Pi transfer: use a PULL model. The backup Pi connects to the app Pi with a dedicated key restricted on the app Pi to a forced read-only command (for example rrsync -ro limited to the backups directory, with `restrict`). Reason: the app Pi is internet-facing and the likeliest to be compromised, so it must not hold credentials able to modify or delete the backup copies. The backup Pi keeps versioned snapshots (rsync --link-dest or rsnapshot style) with retention controlled only by itself, so a corrupted or malicious file from the app Pi cannot overwrite older good copies. Pin SSH host keys on both sides.
5. Network rules (ufw, LAN only): app Pi accepts SSH from my Mac and from the backup Pi's key only; backup Pi accepts SSH from my Mac only; neither backup path is reachable from the internet. Show the exact rules with placeholders.
6. Mac pull design: the Mac pulls from the BACKUP Pi using rsync over SSH with a dedicated key restricted to read-only on the backups directory. No Mac credentials on either Pi, no Pi admin credentials on the Mac. Scheduled by launchd, tolerant of the Mac being asleep (catch-up on wake), verifies checksums, stored on an encrypted volume (FileVault) and NOT inside a cloud-synced folder because the data is financial.
7. Encryption: backups encrypted with age on the app Pi before they leave it, so the backup Pi, the Mac and S3 only ever hold ciphertext. The private decryption key is stored off both Pis (password manager) so a dead Pi cannot lock me out of my backups.
8. Consistency and safety: `sqlite3 .backup` (not cp), `PRAGMA integrity_check`, checksum files, retention (7 daily / 4 weekly / 6 monthly), a free-space guard that skips and alerts instead of filling the disk, and a dead-man's-switch alert if no backup succeeded in 36 hours.
9. Restore test from EACH tier (backup Pi SSD, Mac, S3), automated where possible, with a timed result recorded in docs.
10. The backup Pi is now critical infrastructure: it needs the same hardening as the app Pi (SSH keys only, ufw, fail2ban, unattended upgrades, a supported OS) and its own health alert if it stops receiving backups. Say what happens to the other things it currently does, if any (P1a tells us), and flag any conflict between those duties and being a backup target.

Implement: Ansible inventory groups `app` and `backup` (placeholders only), a `storage` role and a `backup_target` role for the backup host, an extended `backups` role for the app host, plus scripts/mac-backup-pull.sh and an example launchd plist with placeholders only. Do not touch the real Pis; give me the commands to run, and a "what I must do by hand" list (formatting or partitioning the SSD is destructive, so write it as a clearly marked, confirm-before-run step with device-name verification, and do not touch any existing data on that SSD until I confirm what it holds).

Definition of done: restore from all three tiers succeeds on a test copy, no secrets/IPs in the diff, the app Pi cannot delete or modify backups on the backup Pi (prove with a test), and docs say how I check last night's backup.
```

---

## P1d. Rebuild rehearsal: prove the app can be rebuilt from scratch

```
Task: prove that Bajeti can be rebuilt from nothing using only the repo, secrets I hold, and a backup. Plan first.

1. Write docs/runbooks/rebuild.md and a `make rebuild` target (safe: never prunes volumes or deletes the DB) for the app layer: build image, start, run migrations, health check. Add scripts/smoke.sh that checks the health endpoint, registers/logs in a throwaway test user against a COPY of the data, and compares row counts of key tables against the backup.
2. Rehearsal A, on my Mac with Docker: build the image for linux/arm64 (buildx), restore a recent backup copy into a temp directory, run alembic upgrade head, run smoke.sh. Record timings and anything that needed manual intervention.
3. Rehearsal B, BEFORE cutover (see P1b): once the backup Pi has been rebuilt, run a staging copy of Bajeti on it (LAN-only, different port, no Cloudflare tunnel, restored from a backup copy), or use the new app-Pi media with a different hostname/tunnel. Either way production is untouched. Staging must never be exposed publicly and must not use the production SECRET_KEY.
4. Drift detection: add a monthly `ansible-playbook --check --diff` job (run from my Mac, not the Pi) that reports any manual changes on the Pi not captured in Ansible.
5. List every manual step that remained and automate it or document why it cannot be.

Definition of done: a fresh-Pi-to-running-app procedure with measured time, a green smoke test on both rehearsals, and an updated docs/pi-inventory.md marking each item as "in Ansible" or "deliberately dropped".
```

---

## P1. Build the Pi infrastructure-as-code (Ansible)

```
Task: create infrastructure-as-code for the Raspberry Pi that runs Bajeti, using Ansible, in infra/ as laid out in docs/prompts section 2. First inspect the repo (docker-compose files, Dockerfile, .github/workflows/deploy.yml, Makefile, docs/deployment-guide.md, docs/migrations.md) and summarise how the Pi is currently set up and deployed. List assumptions and questions before writing code.

Requirements:
- Ansible roles: base, ssh_hardening, firewall (ufw), fail2ban, unattended_upgrades, docker, storage (SSD mount, see P1c), bajeti_app, backups, monitoring, github_runner (dedicated unprivileged user, documented registration step).
- Start from docs/pi-inventory.md (P1a): include only items marked Keep or Replace. Anything marked Investigate must be listed as an open question, not silently included.
- The playbook must work on a fresh Raspberry Pi OS image for the release chosen in P1b, so the same code serves the OS rebuild and any future disaster recovery.
- Two inventory groups, `app` (`<PI_APP_HOST>`) and `backup` (`<PI_BACKUP_HOST>`), with placeholders in the committed example. Common roles (base, ssh_hardening, firewall, fail2ban, unattended_upgrades) apply to both; bajeti_app, docker and github_runner only to `app`; storage and backup_target only to `backup`. Firewall rules per group follow P1c (LAN-only, least access between the Pis).
- Idempotent. Every role must pass `ansible-playbook --check --diff` and a second run must report zero changes.
- Public repo: only *.example inventory and vars are committed; real inventory and secrets are git-ignored. Support Ansible Vault or sops+age for secrets and document which you chose and why.
- Pi/SD-card friendly: limit journald size, Docker json-file log rotation (max-size/max-file), noatime, no verbose debug logging, avoid unnecessary writes, optional tmpfs for /tmp.
- Docker: pinned image versions (including cloudflared), non-root container user, ports bound to 127.0.0.1, healthchecks, resource limits suited to 3.7 GB RAM.
- A lock-out safety: never apply ssh/firewall changes without first confirming key login works and keeping an existing session open. Add pre-flight assertions.
- Include a README with: bootstrap from a fresh Pi OS image, first run, check-mode run, how to add a new role, rollback notes.
- Add a CI job (GitHub-hosted runner, not the Pi) running ansible-lint and yamllint on infra/.

Do not connect to or modify the real Pi. Produce everything so that I run it myself. End with a "what I must do manually" checklist and a list of what you could not verify.

Definition of done: ansible-lint clean, check-mode instructions work, no secrets or IPs in the diff.
```

---

## P2. Pi security audit and hardening plan (weekend + long-term)

```
Task: act as a security reviewer for a single-user, self-hosted Raspberry Pi running Docker Compose behind a Cloudflare Tunnel, with the app repo public and a self-hosted GitHub Actions runner on the same Pi.

Read: docs/deployment-guide.md, docker-compose files, Dockerfile, .github/workflows/*.yml, Makefile, app/config.py, core/security.py, routers/auth.py, and section "Known problems and risks" in CLAUDE.md or the project context.

Produce docs/hardening-plan.md with two parts:
A) "One weekend" plan: ordered, each item with (1) risk it removes, (2) exact change, (3) how to verify, (4) how to roll back, (5) time estimate. Cover at least: end-of-life Pi OS (see P1a and P1b), SECRET_KEY rotation, bind port 8000 to 127.0.0.1, non-root container, .env permissions (600), SSH keys only and no root login, ufw default-deny with only what is needed, fail2ban, unattended-upgrades, pin cloudflared, journald and Docker log limits, GitHub branch protection (required PR + passing tests), requiring approval for outside collaborators' workflows, Dependabot alerts/updates.
B) "Longer term": self-hosted runner isolation (dedicated user, ephemeral or containerised runner, or move deploy to a pull-based model so a PR cannot execute on the Pi), reverse-proxy-level rate limiting, optional Tailscale for admin access instead of any open port, SD-card wear reduction or moving the DB to USB SSD, read-only root filesystem options, audit logging, restore testing.

Rank by (risk reduced) / (effort). Be explicit about the threat model: public repo, public hostname, leaked key, self-hosted runner. Do not suggest anything that needs new heavy dependencies. Flag anything you are unsure about instead of guessing.
```

---

## P3. Harden Docker Compose and the Dockerfile

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

---

## P4. Harden CI/CD and deploy

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

---

## P5. Backups and a real restore test

```
Task: make backups reliable and prove they restore. Plan first. P1c already designs the destinations (SSD, Mac pull, S3); this prompt is for the automation, alerting and polish on top of that design.

Context: cron at 02:00 copies the SQLite file locally and to S3. Some local copies are missing for several dates and there has never been a restore test.

Do:
- Replace file copy with `sqlite3 <db> ".backup <dest>"` (safe while the app is running). Enable WAL mode if appropriate and explain the SD-card write trade-offs.
- Write infra/ansible/roles/backups: a systemd timer (preferred over cron for logging and Persistent=true so missed runs catch up), retention policy (e.g. 7 daily, 4 weekly, 6 monthly), integrity check (`PRAGMA integrity_check`), checksum, encrypted upload to S3 (server-side encryption or age) using a least-privilege IAM policy (write-only for the Pi, give me the policy JSON with placeholders).
- A `restore.sh` that restores into a temporary location and runs integrity_check plus a row-count sanity query, and a monthly automated restore test that alerts on failure.
- Alerting: a simple healthcheck ping (for example a dead-man's-switch URL kept in a secret) when a backup does not complete.
- Document RPO/RTO and the manual disaster-recovery steps for a dead SD card (fresh Pi OS -> run the Ansible playbook -> restore latest backup).

Definition of done: restore script works against a sample DB in CI, no credentials in the diff, docs explain how I verify last night's backup.
```

---

## P6. App security fixes (with tests)

```
Task: fix these app-level security issues, one commit each, each with tests. Plan first.

1. Allocation update/delete endpoints filter only by budget_id, not by current user. Add ownership checks via BudgetService.get_budget_by_id and write cross-user tests (user B gets 404/403 and nothing changes).
2. users.security_answer is stored in plain text. Hash it (bcrypt via passlib, normalised: strip + casefold), add an Alembic migration that rehashes existing values safely (a data migration cannot reverse hashes, so document the downgrade limits explicitly), and keep password reset working. Add a test.
3. Cookies: set Secure (in production), HttpOnly, SameSite=Lax on access_token and active_budget_id in every code path.
4. Rate limiting on /auth/token and /users/password/reset (in-memory limiter is fine for a single process; justify the choice). Return generic errors so emails cannot be enumerated.
5. Token lifetime: shorten the access token and propose a refresh approach, but do not implement a refresh flow without showing me the design first.
6. Set a security headers middleware (CSP compatible with the current templates, X-Content-Type-Options, Referrer-Policy, frame protection).

Definition of done: full pytest passes, each fix has a failing-before / passing-after test, and a summary table of what changed and what behaviour users will notice.
```

---

## P7. E0: finish Targets (#101, #103, #104, #105, #106)

```
Task: complete the Targets feature in stages; stop after each stage for my review. Plan first.

Existing: Target model (budget_id, category_id, short/mid/long term amounts, unique (budget_id, category_id)), migration 9b38fdc94e38 (downgrade is `pass`), backfill migration 186f1cc1a7ca, empty routers/targets.py not registered in main.py.

Stage 1 (#101 routes): fix the real downgrade for 9b38fdc94e38. Decide and document what to do about the backfill creating NULL-amount rows (a POST for those pairs would 409). Recommend: treat POST as upsert, or drop the backfill and create lazily; show the trade-off in two lines. Add schema/target.py (Decimal money), register the router, implement GET/POST/PUT/DELETE under /budgets/{budget_id}/targets with ownership checks, and tests including cross-user tests.
Stage 2 (#103 service): TargetService static-method class following existing services.
Stage 3 (#104 UI handlers): handlers in app/handlers calling the API via the existing httpx pattern, redirect_with_toast on result.
Stage 4 (#105): extend GET /categories/with-stats/{budget_id} with target data, avoiding N+1 queries.
Stage 5 (#106): dashboard visualisation (progress against short/mid/long term), using palette.css tokens, 4px-multiple spacing, em units, `p-` classes. Do not add a CSS framework.

Definition of done per stage: tests pass, migration upgrade+downgrade verified on a copy of the DB, issue checklist updated.
```

---

## P8. E1: Pi cleanup and performance (#110)

```
Task: produce a safe cleanup and performance plan, then implement the repo-side parts. Plan first.

Known: ~12 GB reclaimable Docker build cache on the Pi, /var/log is 6 GB with unknown cause, SD-card boot (reduce writes), N+1 queries in get_budget_overview, and the Expense.type == "spend" filter is commented out so withdrawals count as spending.

Do:
- Give me read-only diagnostic commands to run on the Pi to find what is filling /var/log (du, journalctl --disk-usage, largest files) and what to do for each likely cause. Do not delete anything automatically.
- Fix get_budget_overview: restore the spend-only filter (check whether any test or UI relied on the wrong behaviour), and replace the per-category loop with one grouped query. Add tests with both spend and withdrawal expenses.
- Add indexes that the main queries need (expenses by user_id+month+category_id, allocations by budget_id), as a migration with a real downgrade; show EXPLAIN QUERY PLAN before/after.
- Propose SQLite pragmas (WAL, synchronous=NORMAL, busy_timeout) with the SD-card trade-offs.
- Clean up: remove dead app/requests.py after confirming nothing imports it; simplify the confusing conditional in BudgetService.fetch_current_budget.

Definition of done: tests pass, query counts reduced (show numbers), and a Pi-side checklist for me to run.
```

---

## P9. E2: Analytics page (#111)

```
Task: design and build the Analytics page. Design first; wait for my approval before coding.

Behaviour: month totals (spend only, exclude withdrawals) -> click a month -> category breakdown -> click a category -> expense list. Charts with ECharts. Reuse /expenses/by-month and /expenses/by-category-month where possible.

Design deliverable (docs/design/analytics.md): endpoint list and JSON response shapes, SQL for each aggregation, indexes needed, the ECharts options for each drill-down level, mobile layout (iPhone width), empty/loading/error states, how ECharts is bundled (esbuild, pinned version, loaded only on this page), and how it stays fast on SQLite with several years of data.

Then implement in small PRs: API aggregations + tests (including cross-user), handler + template, charts. Follow the existing CSS conventions (palette tokens, 4px multiples, em, `p-` prefix). Hide-values toggle must also hide chart values.

Definition of done: works at 375px width, no new heavy dependencies beyond pinned ECharts, tests pass.
```

---

## P10. E3: Recurring expenses (#112)

```
Task: design then implement recurring expenses. Design first and wait for approval.

Spec: RecurringExpense(name, amount Decimal, category_id, day_of_month, active, last_approved_month). API CRUD plus GET /due and POST /{id}/approve (creates a normal expense). A "Due" strip on the dashboard next to Quick Expense. No background scheduler; due items are computed on page load.

Design must resolve these edge cases explicitly with examples and tests:
- day_of_month = 29/30/31 in shorter months (clamp to last day, say so in the UI).
- Catch-up when the app was offline or the user skipped months (show each missed month separately? one combined item? recommend one and justify).
- Amount changed after earlier approvals (history must not change; the amount on the approved expense is the one stored).
- Pausing/ending a recurring item; deleting a category it points to (block or reassign).
- Approving twice (idempotent per month) and two browser tabs approving at once (unique constraint on recurring_id + month).
- Timezone: user is in Africa/Nairobi (UTC+3); decide where "today" comes from.
- Savings-type categories and withdrawals: out of scope unless I say otherwise.

Implement: migration (real downgrade), model, schema, service, router, tests with a cross-user test for every endpoint, handlers and the dashboard strip. Follow CSS conventions.
```

---

## P11. E4: Payment capture (#113)

```
Task: design then build payment capture. Design first; wait for approval.

Spec: PendingPayment(raw_text, amount, merchant, reference, received_at, status). Parsers for M-Pesa SMS and payment emails, an authenticated POST /pending-payments, a "paste message" box, and an inbox where I pick a category and convert each item to an expense. Manual paste ships first; the iPhone transport is decided later.

Design must cover:
- M-Pesa message types: paid to, sent to, received, withdraw, airtime, fuliza (and fees/balance lines). For each type: expected fields, whether it is an expense, income or ignored, and how to treat the transaction fee.
- Parser design: a small library of regexes per type, a table-driven test file with many anonymised sample messages (use fake names and fake numbers; never real ones), safe failure (unparseable text stays in the inbox with raw_text intact).
- Dedupe by transaction code (unique per user), and what happens on re-paste.
- Privacy: raw messages are sensitive; do not log them; delete or redact raw_text after conversion (configurable).
- iPhone options with trade-offs in two lines each: Shortcuts automation on incoming message (may need a confirmation tap, may not fire reliably), share-sheet Shortcut that POSTs the text with a per-user API token, forwarding emails to a mailbox polled over IMAP, Gmail API with sender filter. Recommend one, including how a long-lived, revocable, scope-limited API token for the Shortcut would work (separate from the login JWT).

Then implement in PRs: model+migration, parser+tests, API, paste box + inbox UI.
```

---

## P12. E5: PWA and the prototype context bundle (#114)

Two steps: first have Claude Code build the context bundle from the repo, then use it to prompt a prototype tool.

```
Task: create a "prototype context bundle" in docs/prototype-context/ that lets a designer-model (Claude on the web or Claude Design) generate a faithful prototype of a new Bajeti screen without seeing the codebase.

Produce:
1. design-tokens.md: every token from app/static/css/palette.css (colours with HSL values, font family, type scale), spacing rules (multiples of 4, em units), radii, shadows, breakpoints, dark/light behaviour.
2. components.md: each existing component (buttons, inputs, cards, modals, toasts, table/card list, radio budget list, Quick Expense) with its class names, states and a minimal HTML+CSS snippet copied from the real code.
3. layout.md: base.html structure, dashboard.html section order, navigation, Font Awesome icon names in use.
4. conventions.md: naming (`p-` prefix, BEM-ish), accessibility expectations, hide-values toggle behaviour, mobile-first rules and iPhone safe-area needs.
5. screenshots/ README listing the exact screens I must capture (dashboard, modal, table view, mobile view) and the filenames to use. You cannot take screenshots; give me the list.
6. data-shapes.md: realistic fake JSON for the screen data (fake names and amounts only).

Keep the bundle under ~15k tokens total so it fits comfortably in one chat. Do not include secrets or real user data. At the end, list anything in the CSS that is inconsistent so I can decide whether to normalise it before the prototype.
```

Then the prototype prompt (paste in Claude on the web, with the bundle attached or pasted):

```
You are a senior product designer/front-end engineer prototyping a new screen for Bajeti, a personal budgeting web app. The attached bundle is the source of truth for design tokens, components, layout and conventions. Match the existing look and feel exactly: dark theme, Manrope font, Font Awesome 6.4 icons, `p-` class prefix, spacing in multiples of 4 using em units, tokens from palette.css only (no new colours unless you list them separately).

Screen to prototype: <name, e.g. "Analytics: month totals with drill-down">
User goal: <one sentence>
Data available: <paste the relevant fake JSON from data-shapes.md>
States to show: default, empty, loading, error, and the hide-values toggle on.
Target: iPhone width (375px) first, then desktop. Must be usable one-handed and respect safe-area insets.

Output: a single self-contained HTML file with inline CSS and vanilla JS (no frameworks; ECharts via a pinned CDN only if charts are needed), using the real class names from the bundle where they exist. Mark new components with a comment `/* NEW COMPONENT */`. After the code, list: (1) new CSS tokens or classes introduced, (2) what the backend must provide, (3) accessibility notes, (4) what you assumed. Ask up to three clarifying questions first only if something is genuinely ambiguous; otherwise proceed.
```

Then port it:

```
Task: port the approved prototype in <path> into the real app. Map every class to existing ones where possible; add new CSS only in the existing files following the conventions; no inline styles; make it a Jinja2 template extending base.html; wire the handler and API. Show me a diff summary of new CSS tokens/classes first and wait for approval.
```

PWA implementation prompt:

```
Task: make Bajeti an installable PWA on iPhone and desktop. Plan first.

Do: web app manifest (name, icons incl. maskable, theme/background colours from palette.css), service worker with a strict rule NEVER to cache authenticated responses or API calls (cache only static assets; version the cache), offline fallback page, iOS meta tags (apple-touch-icon, status-bar style, apple-mobile-web-app-capable), safe-area insets in CSS, an install hint for iOS (Add to Home Screen) since iOS has no install prompt. Serve the service worker from the root scope with correct headers; make sure it works behind the Cloudflare Tunnel.

Security: a logout must clear caches; confirm no personal data can be read from the cache after logout. Add a short test checklist (airplane mode, update flow, logout) and note iOS limitations (storage eviction, no background sync).
```

---

## P13. E6: Future planning (#115)

```
Task: design (do not code yet) the future-planning feature. Output docs/design/future-planning.md and wait for my approval.

Spec: fixed 1, 5 and 10 year horizons. Per horizon, goals with target amounts linked to categories and a progress view (saved so far vs needed per month). Plus restructure scenarios (recession, retrenchment, raise) that copy current allocations, adjust them, and show how categories are cut or repurposed and how goal dates move.

Cover:
- Schema: Goal(horizon, name, target_amount, category_id?, target_date), Scenario(name, kind, parameters), ScenarioAllocation(scenario_id, category_id, amount); how this relates to existing Target (short/mid/long) so we do not duplicate concepts; recommend merging or linking and justify.
- Calculations with formulas and worked examples: required monthly saving = (target - saved) / months remaining; goal date shift when monthly saving changes; optional inflation adjustment (state the default and make it editable); income change handling.
- Essential vs discretionary: how categories get a flag (new column? tag?), and the default cut order in a recession scenario. Make the rules transparent and editable, never hidden.
- Scenario semantics: a scenario NEVER changes real allocations; "apply scenario" is an explicit, confirmed action that is undoable.
- What stays computed on read versus stored; performance on SQLite.
- UI sketches in words for mobile, and which parts need a prototype (use P12's workflow).
- Anything ambiguous: list as open questions for me.
```

---

## P14. E7: Code and workflow improvements (#116)

```
Task: plan then execute the code-quality epic in small, separate PRs. One item per PR; stop after each.

Items: (1) Pydantic v2: replace orm_mode with model_config = ConfigDict(from_attributes=True) everywhere; (2) Decimal for money in schemas, with correct JSON serialisation and no float rounding in totals (check the JS side too); (3) CI Python 3.11 + ruff + coverage threshold; (4) tests for budgets, allocations, transfers and withdrawals (create/update/delete withdrawals incl. insufficient funds on budget vs allocation, editing applies only the difference, deleting restores); (5) shared handler error handling in the web layer; (6) migration check in CI against a production-shaped DB copy; (7) run migrations in the container start script; (8) evaluate whether the web layer should call services directly instead of the API over HTTP: write a decision memo with the migration steps and risks, do NOT implement.

For each: state the risk, the test that proves nothing regressed, and the rollback. Report coverage before and after.
```

---

## P15. Meta-prompts: make Claude write the prompts for you

Use this whenever a new backlog item or idea appears.

```
I want to build/improve: <idea, in plain words>.
First read CLAUDE.md, docs/roadmap.md and docs/backlog.md, and the code areas this touches. Then write me a Claude Code prompt for it, saved as docs/prompts/<nn>-<slug>.md, with these sections:
- Task (one paragraph) and why it matters
- Context to read first (exact file paths)
- Constraints (security, user_id scoping, migrations, Pi resources, CSS conventions, public repo)
- Steps, in stages, with a "stop for review" after any design, migration or security change
- Edge cases to handle explicitly
- Tests required (including cross-user)
- Definition of done (verifiable)
- What NOT to do
- Open questions for me
Keep it under 60 lines. Ask me up to three questions first only if truly needed.
```

Prompt reviewer (run before using any prompt):

```
Review this prompt as a skeptical staff engineer: <paste prompt>. Find ambiguity, missing constraints, ways it could cause data loss or a security regression, and missing verification. Rewrite it tighter, and list what you changed.
```

Backlog grooming:

```
Read docs/backlog.md and docs/roadmap.md. Turn each backlog item into a GitHub-issue-ready epic with a checklist of small stories, an estimate (S/M/L), dependencies, and risks. Suggest an order that respects the agreed roadmap and the Pi's constraints. Output markdown only; do not create issues.
```

Weekly hygiene (a good `/weekly` slash command):

```
Run a weekly review: list open PRs and issues, check that docs match the code, scan the last week's diffs for secrets or IPs, check pip-audit/Dependabot output, confirm backups exist for each of the last 7 days (read-only commands I can run, give them to me), and list the 3 highest-value next tasks.
```

---

## Reusable slash commands (optional)

Create these in `.claude/commands/` so you can type `/plan-feature`, `/security-review`, `/migration-check`:

- `plan-feature.md`: "Read CLAUDE.md and the issue <$ARGUMENTS>. Produce a design with schema, endpoints, edge cases, tests and rollout. Do not code."
- `security-review.md`: "Review the current branch diff for authz gaps (user_id scoping), injection, secrets, unsafe migrations and cookie/headers issues. List findings by severity with file:line."
- `migration-check.md`: "For the newest Alembic revision: verify upgrade and downgrade on a copy of the DB, check data safety, and list production risks."

Consider also a small subagent for security review and one for test writing, each with a narrow tool list, so the main session stays focused.
