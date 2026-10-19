# Runbook: move the app Pi to a supported OS (S03)

Status: **design, waiting for approval. Nothing here has been run.** Execution is rehearsed in S05 and needs the Ansible playbook from S04.
Placeholders: `<PI_APP_HOST>`, `<PI_BACKUP_HOST>`, `<USER>`, `<DISKN>` (the Mac's disk number for the card), `<MAC>`. No real addresses, hostnames or tokens belong in this file.
Tags: **[Mac]**, **[Pi-app]**, **[Pi-backup]** say where a step runs. Every step has a verify and a rollback.

## 1. Facts and decision

| Fact | Source |
|---|---|
| Security support for the app Pi's old release ended on 2026-08-31 (Debian LTS). | [Debian LTS wiki](https://wiki.debian.org/LTS) |
| Raspberry Pi says not to upgrade in place to a new major release and strongly recommends a fresh install. The current Raspberry Pi OS is based on Debian 13 (trixie). | [Raspberry Pi OS documentation](https://www.raspberrypi.com/documentation/computers/os.html) |
| The backup Pi already runs Debian 13 and gets automatic updates. **It needs no rebuild.** | Checked on the Pi (`os-release`) in S01 |
| The app Pi is a Pi 4 (4 GB), 64-bit, booting from a 119 GB SD card with about 15 GB used. Docker 29 and Compose 5 run the app and the tunnel. | Read-only checks |

### Options

| Option | Trade-off |
|---|---|
| a) In-place `dist-upgrade` across two major releases | Not supported by Raspberry Pi. Needs two hops, with Docker, the runner, the kernel and firmware all changing; a half-upgraded production host is the failure mode. Rejected. |
| **b) Fresh install of Raspberry Pi OS Lite 64-bit, configured by Ansible, data restored from a verified backup (recommended)** | Matches Raspberry Pi's guidance. The result is exactly what Ansible describes, with no leftovers. Costs a few hours of downtime. |
| c) Move Bajeti to the backup Pi | Rejected: 2 GB RAM, it runs another app, and it must stay the backup target. |

### Free rollback without a spare card

You have no spare card, so the old card is not kept untouched. Instead its **entire contents are saved as a compressed image on the Mac before anything is written to it** (the Mac has 150 GB free). Rollback is writing that image back to the same card: slower than swapping cards (about 1 to 1.5 hours, unmeasured), but it restores the old system exactly. Everything uses free tools: Raspberry Pi Imager, `dd`, `gzip`, `age`, Ansible.

### Two-Pi order

1. **Backup Pi: leave it alone.** It is already supported. Let unattended-upgrades finish its 7 pending updates and reboot it at a time that suits the other app. Never touch the SSD.
2. **App Pi: rebuild** as below. While it is down nothing writes to the database, so no data is at risk, and the backups stay on the backup Pi's SSD, the Mac and S3.
3. The backup Pi is also a free rehearsal target: run the playbook against it with `--check --diff` (read-only) before the window, and rehearse the restore on the Mac with Docker (step P4).

No second tier is unavailable at any point, because the backup Pi is not rebuilt.

## 2. Compatibility checklist (check during rehearsal)

| Item | Check |
|---|---|
| Docker and Compose | Install from Docker's apt repository for the new Debian codename; pin the version in Ansible. `docker compose version` |
| Memory limits | `cat /proc/cgroups` must show `memory` enabled. If not, add `cgroup_enable=memory cgroup_memory=1` to `/boot/firmware/cmdline.txt` (Ansible), reboot, re-check. Then `docker info` shows cgroup v2. |
| Firewall | Use nftables with ufw. Docker publishes ports outside ufw, so the app port must be bound to `127.0.0.1` in compose. Verify with `ss -ltn` from the Pi and a port check from the Mac. |
| SSH | New OpenSSH defaults; key-only, no root, `AllowUsers <USER>`. Check `sshd -T` and keep a second session open while changing it. |
| Networking | The new OS may use NetworkManager instead of dhcpcd. The router's fixed-address reservation keeps `<PI_APP_HOST>` stable. |
| Time | `timedatectl` shows Africa/Nairobi and "synchronized: yes" (the Pi has no clock battery; `backup.sh` refuses a pre-2025 clock). |
| Locale | Record the old one (`locale`) and set the same in Ansible. |
| Host key | The new install has new SSH host keys. The backup Pi's pull and the Mac's admin connections must be re-pinned (step W13). Expect the pull to fail until then; that is the pinning working. |

## 3. Preparation (days before; the app stays up)

**P1 [Mac] Confirm the backups.** Run `scripts/backup-restore-test.sh` on the newest copy from the backup Pi, the Mac and S3 (S02 docs). Verify: three "restore test ok". Rollback: none, read-only. **Gate: all three pass, newest under 24 hours old.**

**P2 [Mac] Check the tools.** An SD card reader works (`diskutil list` shows the card when inserted). Free space is over 60 GB (`df -h ~`). Install Raspberry Pi Imager (free). Verify: Imager opens and lists the card. Rollback: none.

**P3 [Pi-app] Build the secrets bundle.** It holds what the new install cannot get from git: the app `.env`, the tunnel credential files, AWS credentials, the backup settings, and the power-failure scripts and their settings. Encrypt with the same `age` public key that protects the backups; the private key is never on the Pi.

```
cd ~ && tar -czf - projects/bajeti/.env projects/bajeti/cloudflared .aws .config/bajeti .config/power_failures scripts/power_failures \
  | ~/.local/bin/age -r <AGE_RECIPIENT> -o ~/secrets-bundle.tar.gz.age
```

Then **[Mac]** copy it (`scp <USER>@<PI_APP_HOST>:secrets-bundle.tar.gz.age ~/`) and verify it opens: `age -d -i <identity file> ~/secrets-bundle.tar.gz.age | tar -tzf - | head`. Delete the identity file afterwards. Rollback: delete the bundle on the Pi (`rm ~/secrets-bundle.tar.gz.age`). Keep the Mac copy until day 7 after cutover.

**P4 [Mac] Rehearse the restore.** Use the dev compose (`docker-compose.dev.yml`) with a restored copy of a recent backup in a scratch folder, and log in. Verify: login works and the row counts equal the restore test. Rollback: delete the scratch folder.

**P5 [Mac] Rehearse the playbook** (needs S04). `ansible-playbook -i inventory.ini site.yml --limit backup --check --diff` shows what it would change on the already-supported backup Pi and changes nothing. Verify: the diff is understood and empty of surprises.

**P6 Choose the window.** A night, about 4 hours. Tell the other users of the app.

**P7 [Mac] Get a runner registration token** only at the start of the window (it expires after about an hour): GitHub, the repository's Settings, Actions, Runners. Never paste it into a file in the repo.

## 4. The window

**Go/no-go before starting:** P1 to P5 done, token ready, power stable, the card reader on your desk, about 4 hours free.

**W1 [Pi-app] Stop the app.** `cd ~/projects/bajeti && docker compose down`. Verify: the public site no longer answers and `docker ps` is empty. Rollback: `docker compose up -d`.

**W2 [Pi-app] Final backup.** `sudo systemctl start bajeti-backup.service`, then `journalctl -u bajeti-backup.service -n 15 --no-pager`. Verify: "encrypted ok" and "s3 copy verified". Rollback: none needed.

**W3 [Pi-backup] and [Mac] Copy it to the other tiers.** Run the pull on the backup Pi (`sudo systemctl start bajeti-backup-pull.service`) and the Mac script (`scripts/mac-backup-pull.sh`). Verify: the same file name and the same `sha256` on the app Pi, the backup Pi, the Mac and S3; run `scripts/backup-restore-test.sh` on the Mac copy and write down the row counts. **Gate 1 (no-go if it fails): the final file exists and restores on three tiers.**

**W4 [Pi-app] Shut down and remove the card.** `sudo shutdown -h now`; wait for the green light to stop; unplug power; remove the card. Rollback: put the card back and power on.

**W5 [Mac] Save the old card.** Insert it. `diskutil list` and read the size and name to confirm which disk is the card (**do not guess the number**). Then:

```
diskutil unmountDisk /dev/disk<DISKN>
sudo dd if=/dev/rdisk<DISKN> bs=4m status=progress | gzip -1 > ~/pi-app-old-card.img.gz
gzip -t ~/pi-app-old-card.img.gz && shasum -a 256 ~/pi-app-old-card.img.gz
```

Verify: `gzip -t` succeeds and the size is sensible (a few GB, since most of the card is empty). Write the checksum down. Rollback: none; this only reads the card. **Gate 2: the image tests clean.**

**W6 [Mac] Flash the new OS** to the same card with Raspberry Pi Imager: Raspberry Pi OS Lite (64-bit). Settings: hostname `<PI_APP_HOSTNAME>`, user `<USER>`, SSH with your public key only and password login off, timezone Africa/Nairobi, keyboard to match. Leave verification on. Verify: Imager reports success. Rollback: step R below.

**W7 [Pi-app] First boot.** Insert the card, connect the cable if used, power on, wait about 3 minutes. **[Mac]** `ssh <USER>@<PI_APP_HOST>`. Verify: `cat /etc/os-release` shows the new release, `uname -m` shows `aarch64`, `timedatectl` is synchronized. The first SSH connection trusts the key blindly; this is a LAN, so accept it once and compare the fingerprint in W13. Rollback: step R.

**W8 [Mac] Bootstrap with Ansible.** First `--check --diff`, read it, then run for real: `ansible-playbook -i inventory.ini site.yml --limit app`. Brings in Docker (pinned), firewall, SSH hardening, unattended-upgrades, journald limits, `age` (pinned, checksum verified), the backup timers and units. Verify per role: `docker --version`, `systemctl is-active bajeti-backup.timer`, `sshd -T | grep -E 'passwordauthentication|permitrootlogin'`, and a login from a second terminal before closing the first. Rollback: step R.

**W9 [Mac] Restore secrets.** Decrypt on the Mac and stream over SSH, so plaintext never lands on a disk:
`age -d -i <identity file> ~/secrets-bundle.tar.gz.age | ssh <USER>@<PI_APP_HOST> 'tar -xzf - -C ~ && chmod 600 ~/projects/bajeti/.env ~/.config/bajeti/backup.env'`.
Verify: the files exist with mode 600 (`ls -l`). Delete the identity file. Rollback: remove them on the Pi.

**W10 [Pi-app] Deploy and restore the database.** `git clone https://github.com/<OWNER>/bajeti ~/projects/bajeti` (keeping the restored `.env`, `cloudflared/` and `data/` in place; clone into a temp folder and move `.git` if the folder exists), `docker compose build`. Restore the final backup the same way, from the Mac:
`age -d -i <identity file> <final .age file> | ssh <USER>@<PI_APP_HOST> 'cat > ~/projects/bajeti/data/db/data/bajeti.db'`.
Verify: `scripts/backup-restore-test.sh` logic on the Pi: `PRAGMA integrity_check` is `ok` and the row counts equal those recorded in W3. Rollback: delete the restored file.

**W11 [Pi-app] Start and test.** `docker compose up -d`. Verify in order: (1) `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/` returns 200 or a redirect, (2) the public hostname loads from the Mac, (3) you can log in and see the same totals as before. **Gate 3 (rollback if it fails within 30 minutes): login works and the data matches.**

**W12 Re-register the runner.** GitHub, Settings, Actions, Runners: delete the old runner (offline), then follow the new-runner instructions on the Pi with the token from P7. Verify: the runner shows Idle and a no-op workflow run reaches it. Rollback: remove the new runner.

**W13 Backups on the new Pi.** (1) **[Pi-app]** `sudo systemctl start bajeti-backup.service`: verify "encrypted ok" and "s3 copy verified". (2) **[Pi-app]** `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`. (3) **[Pi-backup]** re-pin: `ssh-keyscan -t ed25519 <PI_APP_HOST> > ~/.ssh/bajeti_pull_known_hosts; ssh-keygen -lf ~/.ssh/bajeti_pull_known_hosts`, and **compare with step 2** (if they differ, stop). (4) Make sure the pull key line in the app Pi's `authorized_keys` is back (the `backups` Ansible role does this). (5) **[Pi-backup]** `sudo systemctl start bajeti-backup-pull.service`: verify "done: 1 new". (6) **[Mac]** update `~/.ssh/known_hosts` for `<PI_APP_HOST>` after comparing fingerprints. Rollback: step R.

Total downtime is from W1 to the end of W11.

## 5. Rollback (step R)

Use it if a gate fails, or any of: the tunnel is not up within 30 minutes of W11, the login or data check fails, Docker or the kernel misbehaves.

1. **If the new system took any writes you want to keep,** take a backup first (`bajeti-backup.service`) and copy it to the Mac.
2. **[Mac]** Insert the card. Confirm the disk with `diskutil list`. `diskutil unmountDisk /dev/disk<DISKN>`, then `gunzip -c ~/pi-app-old-card.img.gz | sudo dd of=/dev/rdisk<DISKN> bs=4m status=progress`. Verify the checksum of the image file first (`shasum -a 256`, must match W5).
3. **[Pi-app]** Put the card in, power on, wait, then `ssh <USER>@<PI_APP_HOST>` (the old host key returns, so pinned entries match again) and `cd ~/projects/bajeti && docker compose up -d`.
4. Verify: login works. Restore any newer data with a backup from step 1 if needed.

Estimated rollback time: 1 to 1.5 hours (unmeasured).

## 6. Downtime estimate (unmeasured, to be timed in S05)

Imaging 60 to 90 minutes, flashing 15, first boot and Ansible 30 to 45, restore and deploy 20, checks 20: **about 3 to 3.5 hours; plan a 4-hour night window.** A failed attempt that rolls back adds 1 to 1.5 hours.

## 7. First 7 days

| Day | Check |
|---|---|
| 0 | Gates 1 to 3 passed; runner Idle; backup ran with S3 verified; pull and Mac pull work after re-pinning. |
| 1 | The 02:00 backup and 03:00 pull ran by themselves (`journalctl`). The site is up. |
| 2 | `systemctl --failed` is empty; `free -h`, `vcgencmd get_throttled` and temperature are normal; memory limits apply (`docker stats`). |
| 3 | Unattended-upgrades ran (`/var/log/unattended-upgrades`). Disk use under control (`df -h`, journald size). |
| 7 | Seven nights of backups on every tier. Restore one on the Mac. Only then delete `~/pi-app-old-card.img.gz` and the secrets bundle, and note the date in `docs/backup-restore-log.md`. |

## 8. Unknowns you must confirm

1. Does the app Pi use the network cable or Wi-Fi? (If Wi-Fi, set it in Imager.)
2. Is the Mac card reader fast? (Imaging time depends on it.)
3. Do you still need anything from the leftover folders in the home directory (`~/setup`, `~/Containers`, `~/shared`, the old k3s files)? The k3s service is inactive and is left out. They are saved in the old-card image, not carried over.
4. Which services are really used: file sharing, the web server on port 80, the old tunnel tool? (These are left out of the rebuild unless you say otherwise.)
5. Do the power-failure scripts need anything beyond their folder and settings (they email you)?
6. The runner setup: keep it as it is until S08 hardens it, or harden during the rebuild?
7. A date and time for the window.
