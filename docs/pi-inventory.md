# Pi inventory and necessity audit

Date: 2026-10-17. Source: `scripts/pi-audit.sh` run read-only on both Pis (reports kept out of git).
Hosts are written as `<PI_APP_HOST>` and `<PI_BACKUP_HOST>`. Never add real addresses, hostnames or usernames here.

- `<PI_APP_HOST>`: Raspberry Pi 4 Model B (4 GB), Debian 11 bullseye, kernel 6.1.21 (April 2023). Runs Bajeti and cloudflared in Docker, the GitHub Actions runner for the Bajeti repo, and the nightly DB backup cron. Boots from a 119 GB SD card (30% used).
- `<PI_BACKUP_HOST>`: Raspberry Pi 4 Model B (2 GB), Debian 13 trixie, kernel 6.18 (September 2026). Runs the other app with its own timers, nginx, cloudflared (as a system service) and a GitHub Actions runner under a dedicated user. Boots from a 119 GB SD card (6% used). Has a 931 GB USB SSD (exFAT) mounted at `/mnt/ssd`.

Classification: Keep, Remove, Replace, Investigate. Nothing here is marked Remove unless the report shows it is unused.

**Status (2026-10-20):** the app Pi was rebuilt on a supported OS and its Priority 1 items are fixed (see "Status against Ansible" at the end). The tables below describe the old system as audited on 2026-10-17 and are kept as the record of why each decision was made. Details of the other app on the backup Pi are deliberately left out.

## `<PI_APP_HOST>` (Bajeti)

| Item | What it is | Evidence | Needed? | Risk if removed | Action | Priority |
|---|---|---|---|---|---|---|
| Debian 11 bullseye | The OS | `os-release`; the `bullseye-security` Release file returns 404, so security updates are gone | Replace | Without a new OS there are no security fixes | Rebuild on a supported release (S03 to S05), do not dist-upgrade in place | P1 |
| Port 8000 published on all interfaces | Docker publishes the app to the whole LAN (IPv4 and IPv6) | `ss` shows docker-proxy on 8000 for both families | Replace | None. Cloudflared reaches the app over the Docker network | Bind to `127.0.0.1:8000` in compose | P1 |
| No host firewall | iptables INPUT policy is ACCEPT; ufw/nftables absent | `iptables -S`, empty `nft` output | Replace | None | Add a default-deny firewall in the rebuild (copy the backup Pi's model); install packages only on the new OS | P1 |
| sshd allows passwords | `passwordauthentication yes`, `permitrootlogin without-password`, no `AllowUsers` | `sshd -T` | Replace | Lockout if keys are wrong | Key-only, no root, `AllowUsers` (as on the backup Pi). Test from a second session first | P1 |
| Passwordless sudo for the main user | `NOPASSWD: ALL` | sudoers | Investigate | Automation may rely on it | Decide whether the runner or scripts need it; limit if not | P2 |
| 3 ssh keys for the main user | `authorized_keys` count | report | Investigate | Locking out a device | List key comments (not contents) and remove ones you do not recognise | P2 |
| fail2ban, unattended-upgrades | Installed but inactive | `systemctl is-active` | Replace | None | Enable on the new OS (unattended-upgrades is active on the backup Pi) | P2 |
| Samba (`smbd`, `nmbd`) | File sharing on 445/139/137/138 to the LAN | `ss`, enabled units | Investigate | A share may be in use | Check `testparm -s` and whether any device uses a share. If none, leave it out of the rebuild | P2 |
| nginx on port 80 and `certbot.timer` | A web server and certificate renewal | `ss`, timers | Investigate | A site may rely on it | Check what nginx serves (`nginx -T` summary). Bajeti is served through the Cloudflare tunnel | P2 |
| `ngrok.service`, image `wernight/ngrok` | Old tunnel tool | enabled unit, image 2 years old | Investigate | Probably none (Cloudflare is the tunnel) | Confirm it is unused, then leave it out of the rebuild | P3 |
| Leftover containers `cf-login`, `sleepy_wing`, image `hello-world` | One-off containers | Created / Exited 3 years ago | Remove | None | `docker rm` them. Safe | P3 |
| Docker build cache, 12.5 GB | Cache from `--no-cache` deploys | `docker system df`: 0 active, 12.48 GB reclaimable | Remove | Slower next build | `docker builder prune`. Safe. Also drop `--no-cache` from the deploy workflow | P3 |
| Journald, 4.0 GB | Most of `/var/log` (6.2 GB) | `journalctl --disk-usage`, `du /var/log` | Replace | None | Set `SystemMaxUse` (for example 200M) and vacuum | P2 |
| Bajeti container runs as root | App process | `docker inspect`: user empty | Replace | App must not need root | Non-root user in Dockerfile, read-only root where possible | P2 |
| `cloudflared:latest` as root, image 12 months old | Tunnel client | `docker ps`, `docker images` | Replace | Tunnel downtime if the new version differs | Pin a current version, test the tunnel | P2 |
| Extra Docker networks `bajeti-net`, `bajeti_default` | Leftovers beside `bajeti_bajeti-net` | `docker network ls` | Investigate | Low | Remove if nothing is attached | P3 |
| Bluetooth, `hciuart`, ModemManager, triggerhappy, iscsid/open-iscsi, rpi-display-backlight | Hardware/services a headless server does not use | enabled units | Investigate | Low | Leave out of the rebuild unless something uses them | P3 |
| avahi-daemon | mDNS announcements | `ss` on 5353 | Investigate | `.local` names stop working | Keep only if you use `.local` names | P3 |
| Node 20 from NodeSource | JS runtime on the host | apt sources | Investigate | Builds on the host may need it | Check whether `npm run build` runs on the Pi or in CI | P3 |
| GitHub Actions runner v2.337.0, runs as the main user, who is in the `docker` group | Self-hosted CI/deploy runner for a public repo | systemd unit, `getent group docker` | Replace | Deploys stop | Dedicated unprivileged user, branch protection, outside-collaborator approval (S08). Update the runner | P1 |
| Nightly DB backup (cron 02:00) | `backup_sqlite_to_s3.sh` | crontab | Keep | Data loss | Keep, but fix gaps (see next row) | P1 |
| Backup gaps | Local copies missing on about 15 of the last 38 days. All days since the Oct 11 reboot succeeded | `ls`, `backup_log.txt`, journal, process list | Investigate (cause found and fixed, see note) | Data loss | Root cause: cron started `pi_uptime.sh` about 850 times a day until Oct 11. The script is an endless loop, so every launch stayed running and the Pi ran out of processes (about 280 "can't fork" errors a day), which broke cron, `sqlite3` and `aws`. The cron entry is gone since the Oct 11 reboot and only the systemd service runs the script now. Remaining: make the backup script fail loudly and alert on a missed night (S09), and never re-add a cron line for a looping script | P1 |
| Backups only on the same SD card and in S3 | Local copies are in the home directory; `/mnt/pi_share` is empty | listing | Replace | Data loss if the SD card fails and S3 is unavailable | Pull a copy to the SSD on `<PI_BACKUP_HOST>` and test a restore (S02) | P1 |
| SD card as the only disk, no SMART | Boot and data on one 119 GB card | `lsblk` | Investigate | Card wear | Move data and logs to an SSD, or at least keep verified off-device backups | P2 |
| Docker 29.6 and Compose 5.1.4 | Container engine | `dpkg` | Keep | | Keep. Update on the new OS | |
| `pi-uptime.service` and the power-failure scripts | Your own uptime/outage logging | crontab, service | Keep | | Keep and add to Ansible | |
| Health | Temp 58 C, no throttling, 3.2 GB free memory | `vcgencmd`, `free` | Keep | | Nothing to do | |
| Swap of 99 MB | `dphys-swapfile` | `free -h` | Investigate | Low | Revisit when rebuilding | P3 |

## `<PI_BACKUP_HOST>` (second app and backups)

| Item | What it is | Evidence | Needed? | Risk if removed | Action | Priority |
|---|---|---|---|---|---|---|
| Debian 13 trixie, kernel 6.18 | Current OS | `os-release` | Keep | | 7 package updates are pending. Let unattended-upgrades run, then reboot when convenient | P3 |
| nftables default-drop firewall, SSH from one address only | Host firewall | `nft list ruleset` | Keep | | Use as the model for the app Pi. Add to Ansible | |
| sshd: key-only, no root, `AllowUsers` | Hardened ssh | `sshd -T` | Keep | | Same | |
| unattended-upgrades active | Automatic updates | `systemctl is-active` | Keep | | | |
| fail2ban inactive | | | Investigate | Low (ssh is limited to one address and keys) | Decide whether it adds anything here | P3 |
| The other app (its service, nginx on 8080, cloudflared service, backup/optimize/reminders timers) | The other app | running units, timers | Keep | | Keep. Not part of the Bajeti rebuild | |
| Two failed failure-alert units (names omitted) | Failure alert units that themselves failed | `systemctl --failed` | Investigate | The alerts may not be sending | Read `journalctl -u` for them. Fix or remove | P2 |
| GitHub runner under a dedicated user | CI for the other repo | systemd unit | Keep | | Good pattern to copy for the app Pi | |
| 931 GB SanDisk SSD, exFAT, mounted at `/mnt/ssd` | USB SSD | `lsblk`, fstab | Keep | | See the next three rows | |
| exFAT filesystem for backups | No journaling, no Unix permissions | `findmnt` | Replace | Corruption after a power cut | Carve out an ext4 partition or use a second disk for backups. Keep exFAT for the personal files | P2 |
| Personal files on the SSD (names omitted) | Not part of any app | `du` of top-level names | Investigate | Data loss | Decide whether backups share a disk with personal data. Do not delete anything without checking | P3 |
| `.Trashes`, 131 GB | A macOS trash folder | `du` | Investigate | Data loss | Review what is in it. This may free 131 GB | P3 |
| The other app's backups, 16 MB on the SSD | its backups directory | `du` | Keep | | Keep | |
| Bajeti backups | Not present on this SSD | file listing | Replace | Data loss | Add a daily pull/push of the Bajeti DB (S02) and test the restore | P1 |
| `rpi-connect-lite` | Raspberry Pi Connect remote access | package list | Investigate | Locks out remote access | Check whether it is enabled and signed in. Remove if unused | P2 |
| `cloud-init` services | First-boot provisioning | enabled units | Investigate | Low | Disable after first boot if not needed | P3 |
| `gdb`, `strace`, `build-essential`, `mkvtoolnix`, `p7zip-full` | Developer and media tools | manual package list | Investigate | Low | Leave out of the rebuild if unused | P3 |
| Hardware | 2 GB RAM, no throttling, 58 C | `vcgencmd`, `free` | Keep | | No Docker here. Do not move Bajeti to this Pi without checking memory | |

## Top 10 actions

Order: public exposure and security, then unsupported software, then data loss, then SD-card wear, then tidiness.

| # | Action | Hosts | Effort | Who |
|---|---|---|---|---|
| 1 | Require a PR plus passing tests on `main`, require approval for outside collaborators' workflows, and move the runner to an unprivileged user outside the `docker` group | app | 1 to 2 hours | You (GitHub settings), me (workflow) |
| 2 | Bind port 8000 to `127.0.0.1` and confirm the tunnel still works | app | 30 min | Me (compose), you (deploy and check) |
| 3 | ssh key-only, no root, `AllowUsers`, after confirming key access from a second session | app | 30 min | You |
| 4 | Add a default-deny firewall (copy the backup Pi's nft rules) | app | 1 hour on the current OS if nftables is available, otherwise in the rebuild | You, me for the rules |
| 5 | Find out why backups skipped Oct 6, 7, 9 and 11, and add failure alerting | app | 1 to 2 hours | You read the log, me the script |
| 6 | Copy the Bajeti DB daily to the SSD on the backup Pi, on an ext4 partition, and run a restore test | both | 3 to 4 hours | Design in S02 |
| 7 | Rebuild the app Pi on a supported release with Ansible, rehearse, then cut over. Keep the old card as rollback | app | 1 to 2 days across S03 to S05 | Both |
| 8 | Cap journald at about 200 MB, vacuum the 4 GB, prune the build cache and the leftover containers and images, and drop `--no-cache` from deploys | app | 45 min | You confirm, me the workflow change |
| 9 | Run the app and cloudflared containers as non-root, pin the cloudflared version, add resource limits | app | 2 hours | Me |
| 10 | Investigate and then drop unused services from the rebuild: Samba, nginx and certbot, ngrok, Bluetooth, ModemManager, iscsid, triggerhappy, avahi | app | 1 hour of checking | You |

Also open from this audit: the two failed alert units on the backup Pi (P2), Raspberry Pi Connect on the backup Pi (P2), and the `.Trashes` folder (131 GB) on the SSD.

## Principle for the rebuild

The rebuilt app Pi gets only what is justified in this document and expressed in Ansible. Anything done by hand that is not written down is drift: either add it to Ansible or deliberately drop it.

## Status against Ansible (S05, 2026-10-20)

| Item | Status |
|---|---|
| Rebuild on a supported OS | Done through the rebuild (S03 runbook), configured by Ansible |
| App port on loopback only | In Ansible (`bajeti_app` compose override) |
| Firewall on the app Pi | In Ansible (`firewall`, ufw) |
| SSH key-only, no root, AllowUsers | In Ansible (`ssh_hardening`) |
| fail2ban (app Pi) | In Ansible (`fail2ban`) |
| unattended-upgrades | In Ansible (`unattended_upgrades`) |
| Journald cap, Docker log rotation | In Ansible (`base`, `docker`) |
| Docker engine and compose, pinned | In Ansible (`docker`) |
| Tunnel image pinned, memory limits | In Ansible (`bajeti_app` override) |
| Backups (timer, age, outgoing, pull key) | In Ansible (`backups`, `backup_target`) |
| Health signals (disk, throttling, temperature) | In Ansible (`monitoring`) |
| GitHub runner | Folder in Ansible; re-registered by hand at the cutover (token). It still runs as the main user, who is in the `docker` group: dedicated user and branch protection are S08 |
| pi-uptime and power-failure scripts | In the encrypted secrets bundle; a permanent Ansible copy is still open |
| Passwordless sudo, 3 SSH keys | Deliberately not changed; review the keys by hand (their comments, not contents) |
| Container run as non-root | Image already runs as UID 1000; the tunnel container still runs as root (S07) |
| Samba, port-80 web server and certbot, ngrok, Bluetooth, ModemManager, iscsid, triggerhappy, avahi | Deliberately dropped |
| k3s, `~/setup`, `~/Containers`, `~/shared` | Deliberately dropped (kept only in the old-card image) |
| Leftover containers, build cache, extra networks | Gone with the fresh install |
| Node 20 on the host | Deliberately dropped: Rehearsal A showed a fresh clone needs no host Node |
| Backup Pi: OS, firewall, SSH, updates | Left as it is (another project manages its firewall) |
| Backup Pi: pull job and folder | In Ansible (`storage`, `backup_target`) |
| Backup Pi: Raspberry Pi Connect, cloud-init, developer tools | Open question for the owner |
| Fixed address of the app Pi | In Ansible (`base`, `base_static_address`); the router reservation did not survive the fresh install |
| `awscli` for the S3 copy | In Ansible (`backups`); it was missing on the fresh install and broke the first backup |
| Memory cgroup for container limits | In Ansible (`base`, `cmdline.txt`); applies after a reboot, and containers must be recreated once |
| Backup Pi: USB SSD dropped during the window | Cable problem, unrelated to the rebuild. `fstab` has `nofail`, so it needs a manual `systemctl start mnt-ssd.mount` after a re-plug. An `fsck` is still open |
| Bajeti backups on the backup Pi's SSD | Done in S02 (pull job, checked again after the cutover) |
