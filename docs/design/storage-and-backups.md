# Storage and backups: design (S02)

Status: **approved decisions (2026-10-18), implementation in progress.** Decided: SD boot kept, backups in a folder on the existing SSD (no formatting or partitioning), pull model, `age` encryption installed now. Nothing in this document has been applied to a Pi.
Hosts are `<PI_APP_HOST>`, `<PI_BACKUP_HOST>` and `<MAC>`. No real addresses, hostnames or usernames belong here.

## 1. Where things stand (checked read-only on 2026-10-18)

| Fact | Evidence |
|---|---|
| The nightly backup is no longer cron. A systemd timer (`bajeti-backup.timer`, 02:00 plus up to 5 min, `Persistent=true`) runs `deploy/backup/backup.sh`, deployed from `main` at the merge of PR #125. | `systemctl cat`, `list-timers`, journal: last run exit 0 |
| The script uses the SQLite backup API, requires `PRAGMA integrity_check` = ok, writes `.partial` then renames, takes a lock, refuses to run with under 200 MB free or a pre-2025 clock, keeps the newest 365 copies locally and verifies the S3 copy by size. | Read in full |
| The S01 audit's "cron at 02:00 with gaps" no longer applies. Gaps stopped after the Oct 11 reboot. | HANDOFF S01 addendum, journal |
| `backup.env` sets only `S3_BUCKET` and `BACKUP_KEEP`. **No dead-man's-switch URL and no second-copy command are configured.** | Variable names listed, values not read |
| The bucket has SSE-S3 default encryption, **no lifecycle rule and no versioning**. The old S3 delete loop is gone, so objects now accumulate (about 160 KB each). | `get-bucket-lifecycle-configuration`, `get-bucket-versioning`, `get-bucket-encryption` |
| Live DB is about 160 KB, local backups about 5 MB, SD card 13% used. | `du`, `df` |
| `rsync` and Python SQLite 3.34 are present on the app Pi. `age` is not. | `command -v` |

Not verified: the IAM policy of the app Pi's AWS user (whether it can delete or overwrite objects), SMART health of the SD cards and the SSD, whether `rrsync` ships with the app Pi's rsync on bullseye, and the real free space and layout of the SSD beyond the S01 listing.

Because the data is tiny, **space is not a constraint anywhere in this design**; keep generous history.

## 2. Decisions

### 2.1 Boot media

Recommendation: **keep SD boot on both Pis for now and cut writes** (journald cap, Docker log limits, no 12 GB build cache; all already listed in the inventory and S07/S12). Move to USB-SSD boot only if SMART or errors show wear.

| Option | Trade-off |
|---|---|
| (a) SD now, fewer writes (recommended) | Free, no downtime. Card can still die, which is why the backups and the Ansible rebuild (S04/S05) matter more than the boot media. |
| (b) Second small SSD, USB boot | Better endurance. Costs money, needs EEPROM and boot-order changes, and cheap USB bridges can misbehave (UASP quirks, under-voltage). Do it at the S05 rebuild if wanted. |
| (c) Move this SSD to the app Pi | Rejected: it removes the "different machine" tier and the SSD holds personal files. |

The backup Pi boots from its own 119 GB SD card (6% used). It should keep doing so; the SSD is data only.

### 2.2 Backup storage on the backup Pi

The SSD is exFAT with about 106 GB of personal files and a 131 GB `.Trashes`. It stays exactly as it is: **no formatting, no partitioning, nothing existing is touched.** Backups go in one new folder, the same approach the other app uses for its own backups.

exFAT has three limits, and each one has a mitigation:

| Limit | Mitigation |
|---|---|
| No Unix permissions: who can read the folder is set by the mount options (not yet checked) | Backups are `age`-encrypted before they leave the app Pi, so a reader gets ciphertext. Check the mount options and keep the folder out of any share. |
| No journal: a power cut during a write can corrupt that one file | Each backup is a separate immutable file. The pull verifies a SHA-256 for every file and the Mac and S3 tiers hold independent copies. |
| No hard links | No `--link-dest` snapshots. Files are plain, timestamped and never rewritten, so none are needed. |

Layout: `<SSD_MOUNT>/bajeti-backups/` (a plain folder), written only by the pull job. No SMB or NFS share of this folder. SMART via `smartctl -d sat` if the USB bridge passes it through (unverified); otherwise a weekly read check of the newest backup.

### 2.3 Tiers (3-2-1)

| Tier | Where | Failure domain it covers |
|---|---|---|
| 0 | Live DB and last 365 copies on the app Pi | Fast restore, same card |
| 1 | `<PI_BACKUP_HOST>` SSD folder, files pulled by that Pi | App Pi dead, compromised or card failure |
| 2 | `<MAC>`, pulled from `<PI_BACKUP_HOST>` | Backup Pi dead or compromised |
| 3 | S3, encrypted, versioned | House-wide event |

Both Pis are in the same building, so fire, theft, flood and a house-wide power event take out tiers 0 and 1. Tier 2 (the Mac) is only offsite while the laptop is elsewhere, so tier 3 stays.

### 2.4 App Pi to backup Pi: pull, not push

The existing runbook (`docs/runbooks/backup-install.md`, step 9) suggests `BACKUP_COPY_COMMAND` with `rsync` pushing from the app Pi. **That would give the internet-facing machine a key to the backup machine, so this design replaces it.** Leave `BACKUP_COPY_COMMAND` unset.

- `<PI_BACKUP_HOST>` runs a timer (03:00) and pulls with `rsync` over SSH using a dedicated key.
- On the app Pi that key is restricted in `authorized_keys`: `restrict,command="rrsync -ro ~/backups/db_backups"`. It can only read that directory.
- No `--delete`, `--ignore-existing`. Copies are immutable timestamped files, so deletion on the app Pi (the 365-copy prune) never propagates.
- The backup Pi stores them as plain timestamped files (no hard links on exFAT) and prunes on its own schedule, which the app Pi cannot influence.
- Host keys are pinned (`StrictHostKeyChecking=yes`, known_hosts managed by Ansible).
- The app Pi holds **no** credential for the backup Pi.

### 2.5 Network rules (LAN only, nothing reachable from the internet)

App Pi (ufw, default deny incoming):
```
ufw allow from <MAC> to any port 22 proto tcp
ufw allow from <PI_BACKUP_HOST> to any port 22 proto tcp
```
Port 8000 is bound to `127.0.0.1` (S07), so the tunnel is the only path to the app.

Backup Pi: keeps its existing **nftables** default-drop model (do not layer ufw on top). Rule: SSH from `<MAC>` only; outbound allowed. The pull needs no inbound rule because the backup Pi initiates it. Both rule sets go into Ansible (S04).

### 2.6 Mac pull

`scripts/mac-backup-pull.sh` plus a launchd plist (placeholders only):
- Pulls from `<PI_BACKUP_HOST>` (never from the app Pi) with a dedicated key restricted the same way (`rrsync -ro`).
- `StartCalendarInterval` daily plus `RunAtLoad`; launchd runs a missed calendar job after wake, so a sleeping laptop catches up.
- Verifies SHA-256 against a `SHA256SUMS` file the backup Pi writes beside the backups.
- Destination on the FileVault volume and **outside** iCloud Desktop/Documents or any synced folder (for example `~/BajetiBackups`).
- No Mac credentials on either Pi, no Pi admin credentials on the Mac.

### 2.7 Encryption

Encrypt with `age` on the app Pi before anything leaves it, so the backup Pi, the Mac and S3 hold only ciphertext.
- `backup.sh` gains an optional `AGE_RECIPIENT` (public key). When set, it writes `db_backup_*.db.age` next to the plaintext copy and only the `.age` file is exposed to `rrsync` and uploaded. The plaintext copies stay on the app Pi, which already holds the live database.
- The private key lives in the password manager only, never on either Pi. Restore tests fetch it for the duration of the test.
- `age` is not installed on the app Pi (bullseye, aarch64). Install a **pinned static release binary into the owner's home** (for example `~/.local/bin/age`), verify its published checksum first, and do not use `apt`. Undo: delete the file. This is a change on the Pi, so the exact commands are shown and need confirmation before they run.
- S3 keeps default encryption (SSE-S3) and gets versioning as a second layer, but with `age` the object itself is ciphertext.

### 2.8 Consistency, retention and alerts

Already done by `backup.sh`: backup API, integrity check, partial-then-rename, checksum by size on S3, free-space guard, lock, clock guard, failure unit.

To add:
- **Dead-man's switch.** Set `BACKUP_PING_URL` (free check, 1 day period, 3 h grace; or 36 h overall). The URL is a secret; it lives only in `backup.env` and the password manager.
- **Second switch on `<PI_BACKUP_HOST>`:** it pings only after a successful pull and a checksum pass. This alerts if the backup Pi stops receiving backups, which the app Pi's ping cannot show.
- **Retention.** The brief asked for 7 daily, 4 weekly, 6 monthly. Files are 160 KB, so keep more: app Pi 365 (already), backup Pi all dailies for 400 days, S3 lifecycle: expire current objects after 400 days and non-current versions after 90.
- **S3 delete protection.** Turn on versioning, then apply the lifecycle rule. Narrow the app Pi's IAM user to `s3:PutObject` and `s3:GetObject` on the bucket if the policy allows (to be read first; the post-backup size check needs `GetObject`).

### 2.9 Restore tests

One script, `scripts/backup-restore-test.sh <file>`: decrypts if `.age`, opens a copy with Python's `sqlite3`, runs `integrity_check`, compares table row counts with the live DB, prints elapsed seconds. Run once per tier, with the result and the time appended to `docs/backup-restore-log.md` (no secrets). Existing `backup-verify.sh` stays for the app Pi's tier 0.

### 2.10 The backup Pi is critical infrastructure

Already good: current OS (Debian 13), key-only SSH with `AllowUsers`, default-drop firewall, unattended-upgrades. Gaps: 7 pending updates, fail2ban inactive (low value with one allowed source), no health alert (fixed by the second switch).

Conflict to decide: it also runs **another app and a GitHub Actions runner for another repository**. A job on that runner runs as its own user, so mitigations are: contents encrypted with `age` (exFAT cannot enforce owners or modes, so this is the real protection), the folder outside any share, and the mount options checked so the runner's user is not given blanket access. Remaining risk: a compromised runner could still stop the machine or fill the disk. Keep the runner on its dedicated user and keep the other app's tasks away from the backup folder. Also: the other app and Bajeti backups should not share resource spikes (2 GB RAM; `rsync` is light).

## 3. Proof that the app Pi cannot alter backups

1. From the app Pi, `ssh <PI_BACKUP_HOST>` fails (no key, firewall).
2. From the backup Pi, using the restricted key, `rsync` a file **to** the app Pi: rejected by `rrsync -ro`.
3. Delete the newest file on the app Pi; the next pull leaves the backup Pi copy intact.
4. Corrupt a file on the app Pi (checksum mismatch); the pull reports it and older copies are unchanged.

## 4. What I will build after approval

- `infra/ansible/` with groups `app` and `backup` (placeholders only), roles `storage`, `backup_target`, `backups` (drafts, nothing applied).
- `deploy/backup/backup.sh`: `AGE_RECIPIENT` support only.
- `deploy/backup/` pull script, unit and timer for `<PI_BACKUP_HOST>`.
- `~/backups/outgoing/` on the app Pi: ciphertext only, the only directory `rrsync -ro` exposes.
- `scripts/mac-backup-pull.sh` and an example launchd plist.
- `scripts/backup-restore-test.sh` and `docs/backup-restore-log.md`.
- A "check last night's backup" section in `docs/runbooks/backup-install.md`.

## 5. What you do by hand

1. Router: reserve fixed addresses for both Pis. Don't paste the addresses into the repo.
2. Create the `bajeti-backups` folder on the SSD (a normal folder; nothing is formatted). Do not touch anything else on it.
3. Create the age keypair; store the private key in the password manager only; give me only the public key.
4. Create the two dead-man's-switch checks.
5. Install the restricted SSH keys and firewall rules (Ansible `--check` first).
6. Run one real backup, then one restore per tier.
