# Hardening plan

Written for S06 on 2026-10-20, after the app Pi was rebuilt (S05). This is a plan: nothing in it was applied by this stage. Hosts are `<PI_APP_HOST>` and `<PI_BACKUP_HOST>`; `<USER>` is the login. Never add real addresses, hostnames, usernames or keys here.

## How this was checked

State was read on 2026-10-20, not copied from the old audit:

- Live app Pi, read-only over ssh (no sudo): OS, listening ports, unit states, ssh drop-in, file modes, container settings, runner, journald, Docker log config, pending updates.
- GitHub, read-only through `gh api`: branch protection, Actions permissions, fork approval policy, security settings, runners, collaborators.
- Repo files: `docker-compose.yml`, `Dockerfile`, `.github/workflows/*.yml`, `app/config.py`, `core/security.py`, `routers/auth.py`, `app/handlers/auth_handlers.py`, `services/auth_service.py`, `main.py`, `infra/ansible/roles/*`.

Not checked (needs a password for sudo, so it is yours to run): the ufw rule list, `sshd -T` effective values, `unattended-upgrades` logs, SMART health. Items that depend on these say so.

## Threat model

| Who or what | What they can do | What matters most |
|---|---|---|
| Anyone on the internet | Reach the public hostname through Cloudflare. They can try the login form, the open registration endpoint, `/docs` and `/openapi.json`, and any bug in the app | Login and registration abuse, app bugs, no rate limit behind the tunnel |
| Anyone who reads the public repo | See every file and all history: workflows, Ansible, scripts, and the old `SECRET_KEY` (burned, rotated in S00) | Nothing sensitive may be in git. The workflow shows exactly how deploys run |
| A GitHub account that can push or open PRs | Run workflow code on the Pi's self-hosted runner. That runner is the main user, who is in the `docker` group (root-equivalent) | The most dangerous path into the Pi |
| Someone on the home LAN or a guest device | Reach the Pi's open ports | Now only ssh (key only, from two addresses) per the firewall role. Not re-verified on the live Pi |
| Theft or loss of the Mac | Ssh key to both Pis, backup copies, the `age` identity file | Disk encryption and key handling on the Mac (out of scope for the Pis) |
| Failure, not attack | SD-card wear or corruption, power loss, a bad deploy | Covered by backups (S02) and the rebuild runbook |

Not in the model: a targeted attacker with physical access to the Pi; a compromise of Cloudflare or GitHub themselves.

## Already solved by the rebuild (verified on the live Pi on 2026-10-20)

| Item | Evidence |
|---|---|
| Supported OS | Debian 13 (trixie), kernel 6.18 |
| Port 8000 on loopback only | `ss` shows only `127.0.0.1:8000`, `22` and `[::]:22` listening |
| ssh: keys only, no root, `AllowUsers`, 3 tries | `/etc/ssh/sshd_config.d` drop-in read; ssh login by key works. Effective values (`sshd -T`) not read |
| ufw, fail2ban, unattended-upgrades running | `systemctl is-active` shows `active` for all three. Rules not read (needs sudo) |
| `.env` mode 600 | `stat` shows `600` |
| App container non-root, `no-new-privileges`, all capabilities dropped, memory and pid limits, healthy | `docker inspect`: user `bajeti`, `CapDrop=[ALL]`, 768 MiB, 256 pids |
| Tunnel image pinned and current | `cloudflared:2026.10.1` running with a 128 MiB limit |
| Journald and Docker log limits | journald 6.2 MB (was 4 GB); `daemon.json` has 10 MB x 3 |
| No passwordless sudo | `sudo -n true` asks for a password |
| ssh keys reduced | 2 keys in `authorized_keys` (was 3). Comments still to be reviewed by you |
| Branch protection on `main` | PR required, `test` required and up to date, no force push, no deletion |
| Outside-collaborator workflows | Approval required for all external contributors |
| Workflow token read-only | `default_workflow_permissions: read` |
| Dependabot security updates, secret scanning, push protection | All `enabled`; vulnerability alerts on |
| Deploys only for merged PRs from this repository | `if:` guard in `deploy.yml` |
| Only you have push access | Collaborators list: one account |
| Unneeded services (Samba, nginx, ngrok, Bluetooth, k3s) | Gone with the fresh install; none listening |

## Part A: one weekend

Ordered by (risk removed) / (effort). Each item says which stage normally carries it: S07 (Docker), S08 (CI/CD), S10 (app code). "Weekend" means you may pull it forward.

### A1. Stop open registration on the public hostname
- **Risk removed:** `POST /api/auth/` and `/register` let anyone on the internet create an account, store data, and probe the app as an authenticated user. This is the biggest app-level exposure for a household app.
- **Change:** add a setting `REGISTRATION_OPEN` (default `false`, read in `app/config.py`). When false, the API register route and the web register page return 404. Set it `true` only while you add a household member. Add a test: closed means 404, open works. This is S10 work; it is code, so it goes through a PR with tests.
- **Verify:** `curl -s -o /dev/null -w '%{http_code}' -X POST https://<PUBLIC_HOST>/api/auth/ -H 'content-type: application/json' -d '{}'` returns 404. Existing users still log in.
- **Roll back:** set `REGISTRATION_OPEN=true` in the GitHub secret and redeploy, or revert the PR.
- **Time:** 1 hour including the test.

### A2. Rate-limit login at Cloudflare (free, no new software)
- **Risk removed:** password guessing against `/api/auth/token` and the web login. There is no rate limit anywhere; fail2ban only watches ssh.
- **Change:** in the Cloudflare dashboard add a rate-limiting rule on the zone: match the paths `/api/auth/token` and `/login`, 10 requests per minute per IP, action Block for 10 minutes. **Unsure:** how many rules and which options the free plan allows today. Check the dashboard before relying on this. If the free plan cannot do it, fall back to A2b.
- **A2b (fallback, in-app):** a small in-memory limiter on failed logins per email and per client IP (`CF-Connecting-IP`, trusted only because the app is reachable only through the tunnel). No new dependency; a dict with timestamps. This is S10 work.
- **Verify:** 15 wrong logins in a minute from a terminal, the later ones get HTTP 429 (Cloudflare) or the in-app error. A correct login afterwards still works from another IP.
- **Roll back:** disable or delete the rule in the dashboard; revert the PR.
- **Time:** 30 minutes (rule), 2 hours (in-app).

### A3. Cookie flags and token logging
- **Risk removed:** `access_token` is set with `httponly=True` only (`app/handlers/auth_handlers.py:27`, `dashboard_handlers.py:259`): no `Secure`, no `SameSite`. `core/security.py:38` logs the full token on every failed validation, so a bearer token can end up in the journal and in `docker logs`.
- **Change:** add `secure=IS_PRODUCTION` and `samesite="lax"` to both `set_cookie` calls; stop logging the token (log a short hash or nothing). Tests for cookie attributes.
- **Verify:** `curl -si -d 'username=...&password=...' https://<PUBLIC_HOST>/login | grep -i set-cookie` shows `Secure` and `SameSite=lax`. Grep the logs after a bad token: no token text.
- **Roll back:** revert the PR.
- **Time:** 1 hour.

### A4. Turn off `/docs`, `/redoc` and `/openapi.json` in production
- **Risk removed:** gives anyone a full map of the API. Low risk alone, but free to remove.
- **Change:** `FastAPI(..., docs_url=None, redoc_url=None, openapi_url=None)` when `IS_PRODUCTION`. The container healthcheck in `docker-compose.yml` calls `/openapi.json`, so change it to `/` at the same time (the Ansible override already uses `/`, so the Pi is fine; the repo file is stale).
- **Verify:** `curl -s -o /dev/null -w '%{http_code}' https://<PUBLIC_HOST>/docs` returns 404; `docker compose ps` shows healthy.
- **Roll back:** revert the PR.
- **Time:** 20 minutes. Do this with A3.

### A5. Make the repo's compose file match the Pi (cloudflared and healthcheck)
- **Risk removed:** `docker-compose.yml` pins `cloudflared:2025.9.1` while the Pi runs `2026.10.1` through the Ansible override. A `make rebuild` or a restore on a machine without the override would silently downgrade the tunnel.
- **Change:** set the base file to `2026.10.1` and change the healthcheck URL; keep the override only for what is host-specific (memory limits, the bind address).
- **Verify:** `docker compose config | grep image` on the Pi and in CI shows the same tag; Ansible `--check` shows no change.
- **Roll back:** revert the PR.
- **Time:** 20 minutes. Fits S07.

### A6. Tunnel credentials file is world-readable
- **Risk removed:** `cloudflared/<id>.json` has mode `644`; any local user or container process that reaches the folder can read it. `cert.pem` is already `600`.
- **Change:** `chmod 600 ~/projects/bajeti/cloudflared/*.json` and set the same mode in the `bajeti_app` role. The container runs as root, so it still reads the file.
- **Verify:** `stat -c '%a' cloudflared/*.json` shows `600`; `docker compose restart cloudflared`; the tunnel reports 4 connections; the site loads.
- **Roll back:** `chmod 644` the file.
- **Time:** 10 minutes. Your step on the Pi (a file change on the Pi needs your confirmation).

### A7. Dependabot version updates and pinned actions
- **Risk removed:** Dependabot security alerts are on, but there is no `.github/dependabot.yml`, so no routine updates for pip, npm, Docker base image or Actions. Actions are referenced by tag (`checkout@v4`, `setup-python@v4`), not by commit. The latest Dependabot run on `main` failed on Oct 19 (not looked into).
- **Change:** add `dependabot.yml` for `pip`, `npm`, `docker` and `github-actions`, weekly, with a small PR limit. Update `setup-python` to the current major. Look at why the Oct 19 run failed. Pinning to full commit SHAs is optional; tags from GitHub-owned actions are an acceptable risk here.
- **Verify:** Dependabot opens its first PRs within a day; the Insights, Dependency graph, Dependabot tab shows no errors.
- **Roll back:** delete the file.
- **Time:** 30 minutes plus triage of the first PRs.

### A8. Check that automatic updates really apply
- **Risk removed:** `unattended-upgrades` is active but 16 packages are upgradable (9 look like security updates) on a Pi that has been up for one day. That is probably just timing; it must be checked, not assumed.
- **Change:** none yet. You run `sudo journalctl -u unattended-upgrades --since today --no-pager | tail -30` and `sudo unattended-upgrade --dry-run -d | tail -30`, and paste the output.
- **Verify:** day 3 of the first-week checklist already covers this; the pending count should fall to near zero.
- **Roll back:** not applicable.
- **Time:** 10 minutes.

### A9. Confirm the firewall and ssh values you could not be read
- **Risk removed:** the ufw rules and the effective sshd values were not read; only the unit state and the drop-in file were.
- **Change:** none. You run `sudo ufw status verbose` and `sudo sshd -T | grep -E '^(passwordauthentication|permitrootlogin|allowusers|maxauthtries) '`, redact addresses, and paste them.
- **Verify:** default deny incoming; port 22 only from the two listed sources; nothing else.
- **Roll back:** not applicable.
- **Time:** 5 minutes.

### A10. Review the two remaining ssh keys
- **Risk removed:** a key from an old device keeps working forever.
- **Change:** `awk '{print NR": "$1, $NF}' ~/.ssh/authorized_keys` on the Pi, and delete any line you do not recognise. Comments only, not key bodies.
- **Verify:** log in from a second terminal before closing the first.
- **Roll back:** re-add the line from your Mac's `.pub` file.
- **Time:** 10 minutes.

### A11. Tidy the workflow: no username in a public file
- **Risk removed:** `deploy.yml` hardcodes the home path including the real username and repeats it five times. Not a secret, but it gives an attacker one of the two pieces for ssh brute force and it breaks if the user changes.
- **Change:** use `working-directory: ${{ vars.APP_DIR }}` (a repository variable) or `$HOME/projects/bajeti`. Do this together with the S08 rewrite rather than separately.
- **Verify:** the next deploy succeeds.
- **Roll back:** revert the PR.
- **Time:** 20 minutes. S08.

### A12. Smaller image and Python version alignment
- **Risk removed:** the production image keeps `build-essential` and the SQLite dev headers after installing dependencies, and `python:3.11-slim` has no digest pin. CI tests on Python 3.9 while the image runs 3.11, so a 3.11-only bug (or fix) is not seen in tests.
- **Change:** multi-stage build (build deps only in the first stage), pin the base image by digest, bump CI to 3.11. Keep the image under the Pi's memory budget.
- **Verify:** `docker images` size drops; tests pass on 3.11; app starts and is healthy.
- **Roll back:** revert the PR; the previous image is still on disk until the next prune.
- **Time:** 1.5 hours. S07.

### A13. Harden the tunnel container
- **Risk removed:** `cloudflared` runs as root with all capabilities, a writable root filesystem and no pid limit. A bug in it would own the container.
- **Change:** `cap_drop: [ALL]`, `read_only: true` with a tmpfs for `/tmp`, `pids_limit: 128`. Running as a non-root user needs the credentials folder readable by that user (set mode 640 with a matching group), which is a bigger change; try it only after the rest works.
- **Verify:** `docker compose up -d cloudflared`, 4 tunnel connections, the site loads, `docker inspect` shows the new settings.
- **Roll back:** remove the lines and recreate the container.
- **Time:** 45 minutes. S07.

## Part B: longer term

### B1. Take the CI runner off the Pi's deploy path (biggest remaining risk)
- **Risk removed:** the runner executes workflow code as your main user, who is in the `docker` group. Anyone who gets a malicious change merged, or your GitHub account, gets root on the Pi, the `.env`, the tunnel credentials and the database.
- **Options, ranked:**
  1. **Pull-based deploy (recommended).** Remove the runner from the Pi. A systemd timer on the Pi runs a small script every few minutes: `git fetch`, deploy only if `origin/main` has a new commit whose tests passed (check the commit status through the public GitHub API, no token needed for a public repo), then build, migrate, health-check, roll back to the previous image on failure. Nothing from GitHub runs code on the Pi except a script you wrote. Cost: deploy takes up to a few minutes after a merge, and the secrets stop coming from the workflow (`.env` is written once by Ansible from the vault).
  2. Dedicated unprivileged runner user plus a root-owned deploy script the runner may call through a single `sudoers` rule. Smaller change, but the runner can still change what that script deploys.
  3. Ephemeral or containerised runner. More moving parts on a 4 GB Pi.
- **Verify:** `systemctl list-units 'actions.runner*'` is empty; a merge results in a deploy within the timer interval; a bad commit rolls back.
- **Roll back:** re-register the runner (token from GitHub) and restore the old `deploy.yml`.
- **Time:** 3 to 4 hours. S08. This is the decision for you; see the summary at the end.

### B2. Put Cloudflare Access in front of the hostname
- **Risk removed:** with Access the login page is never reachable by strangers; only the people you allow get past a one-time email code first.
- **Change:** add an Access application for the hostname with an allow-list of household emails. **Unsure:** current free-plan limits and how it interacts with the phone and a later PWA (an installed PWA can fail on the Access redirect). Test with one device first.
- **Verify:** a private window gets the Access screen, a household email gets in.
- **Roll back:** delete the Access application.
- **Time:** 1 hour.

### B3. Reverse-proxy-level protection
- **Risk removed:** abuse beyond login: scraping, floods, slow requests.
- **Change:** use the Cloudflare rules from A2 (free) for the first line. Adding a proxy such as Caddy on the Pi would be one more container; not recommended on a 4 GB Pi unless A2 is not enough.
- **Time:** none beyond A2.

### B4. Admin access without any open port (optional)
- **Risk removed:** ssh is open to two addresses on the LAN; a Tailscale-style mesh would let you reach the Pi from outside without opening anything.
- **Cost:** new software on the Pi, an extra account, and another thing to patch. You work from home; ssh from the LAN is enough. **Recommend skipping** unless you need remote admin.

### B5. SD-card wear and the database on a USB SSD
- **Risk removed:** the SD card is the only disk; a failure loses the database (backups cover the data, not the downtime).
- **Change:** a small USB SSD on the app Pi for `data/` and Docker's data root. This needs hardware; per your rule no purchases are suggested. The zram swap and the journald limits are already in place. Keep checking backups instead.
- **Time:** not planned.

### B6. Read-only root filesystem for the app container
- **Risk removed:** a code-execution bug can not drop files into the container.
- **Change:** `read_only: true` with a tmpfs for `/tmp` and the SQLite directory mounted writable. SQLite needs write access to its folder (journal); test carefully.
- **Verify:** app healthy; creating an expense works; migrations still run.
- **Roll back:** remove the line.
- **Time:** 1 hour. S07.

### B7. Audit logging
- **Risk removed:** nothing logs who changed what. If an account is abused you cannot reconstruct it.
- **Change:** log login success and failure, registration, password change, and data deletion with user id and client IP (never the token or password). Rotate with the existing Docker log limits. Add a weekly look at failed logins.
- **Time:** 2 hours. S10 or S18.

### B8. Restore testing on a schedule
- **Risk removed:** backups that cannot be restored.
- **Change:** S09 covers the automated check and the missed-backup alert (parked in the backlog). Do the first-week restore test from `docs/runbooks/pi-os-upgrade.md`, then monthly with the drift check.
- **Time:** S09.

### B9. Backup Pi hygiene (not Bajeti, but it holds the backups)
- Open from the audit: Raspberry Pi Connect, `cloud-init`, two failed alert units, the USB SSD cable and a `fsck.exfat`, the 131 GB `.Trashes`. The backup Pi's firewall is managed by another project, so changes there go through its owner. Keep these on the list; none changes Bajeti's exposure.

## Things I am not sure about

- Cloudflare free-plan limits for rate limiting and Access (A2, B2): check in the dashboard.
- Whether ufw has exactly the rules the Ansible role describes, and whether unattended-upgrades is applying security updates (A8, A9): needs your sudo.
- Whether the Oct 19 Dependabot failure matters (A7): not read.
- Whether moving cloudflared off root works with the credentials file permissions (A13): not tried.

## Ranked summary

| Rank | Item | Risk removed | Effort | Stage |
|---|---|---|---|---|
| 1 | A1 close open registration | High | 1 h | S10 |
| 2 | A2 rate limit login | High | 0.5 to 2 h | S10 / dashboard |
| 3 | A6 tunnel credentials to 600 | Medium | 10 min | you on the Pi |
| 4 | A3 cookie flags, stop logging tokens | Medium | 1 h | S10 |
| 5 | A4 hide `/docs` and `/openapi.json` | Low | 20 min | S10 |
| 6 | A5 compose matches the Pi | Medium | 20 min | S07 |
| 7 | A8, A9, A10 checks on the Pi | Medium | 25 min | you |
| 8 | A7 Dependabot updates | Medium | 30 min | S08 |
| 9 | A13 tunnel container hardening | Medium | 45 min | S07 |
| 10 | A12 smaller image, Python 3.11 in CI | Medium | 1.5 h | S07 |
| 11 | B1 pull-based deploy, no runner on the Pi | High | 3 to 4 h | S08 |
| 12 | A11 no username in the workflow | Low | 20 min | S08 |
| 13 | B2 Cloudflare Access | High | 1 h | you |
| 14 | B6, B7 read-only root, audit log | Low/Medium | 3 h | S07 / S10 |
