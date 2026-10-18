# S01: Pi inventory and necessity audit (both Pis)

**Prompt:** P1a  |  **Mode:** claude+human  |  **Depends on:** none  |  **Suggested branch:** `feature/issue-N-pi-audit`

## Goal

Find out what is installed and configured on both Pis, whether each item is needed, and what to do first.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `docs/deployment-guide.md`
4. docker-compose files, Dockerfile, Makefile
5. `.github/workflows/deploy.yml`
6. Any backup or cron scripts that live in the repo

### Outputs of earlier stages this stage relies on

- Nothing required. S00 is independent.

## Before you start

- Create a GitHub issue and a branch `feature/issue-N-pi-audit`.
- Make sure the real addresses and hostnames of both Pis stay out of the repo. Use `<PI_APP_HOST>` and `<PI_BACKUP_HOST>`.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

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

## Watch out for

- Claude must write the audit script but not run it on the Pis. You run it.
- Reports contain network details even after masking. Redact by hand and keep them out of git.
- Do not remove anything yet. This stage only classifies: Keep, Remove, Replace, Investigate.

## Your part (Claude cannot or should not do these)

1. Review `scripts/pi-audit.sh` before running it. Copy it to each Pi and run it once on the app Pi with the argument `app` and once on the backup Pi with `backup`.
2. Read each `pi-audit-report.txt` yourself and confirm IPs, MACs, hostnames and secrets are masked. Redact anything left.
3. Give the reviewed reports to Claude (paste, or a git-ignored folder). Do not commit them.
4. Tell Claude what else the backup Pi does and what is on the SSD.

## Done when

- scripts/pi-audit.sh exists and is read-only.
- docs/pi-inventory.md covers both Pis with Keep / Remove / Replace / Investigate per item.
- A ranked top-10 action list with effort estimates.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- scripts/pi-audit.sh
- docs/pi-inventory.md (redacted, safe to commit)
- .gitignore entry for pi-audit-report.txt

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Which Pi release and model each Pi runs, what the backup Pi is used for, and what is on the SSD.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S02-backups-two-pis.md`: Backups: backup Pi SSD, Mac pull, offsite.
