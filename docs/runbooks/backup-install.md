# Install the Bajeti backup (systemd timer)

Replaces the old cron job that ran `~/scripts/bajeti/backup_sqlite_to_s3.sh`. The new files are in `deploy/backup/` and reach the Pi on the next deploy (the deploy does `git reset --hard origin/main` in `~/projects/bajeti`). Placeholders: `<USER>` is your login on the app Pi, `<BUCKET>` your S3 bucket.

What changed compared with the old script:

| Old script | New script |
|---|---|
| `cp` of the live database | SQLite backup API (consistent), through `python3` because the Pi has no `sqlite3` binary |
| Never checked the copy | `PRAGMA integrity_check` must say `ok`; written as `.partial`, then renamed |
| No error handling; a failed step looked like success | `set -Eeuo pipefail`, every step checked, non-zero exit on any failure |
| Local prune looked for `*.sqlite3` so it never deleted anything | Keeps the newest 365 `db_backup_*.db` (set `BACKUP_KEEP`; pruning is permanent, and the first run on a folder that held old copies deletes everything beyond the limit, so check `ls ~/backups/db_backups | wc -l` first) |
| S3 retention loop parsed `aws s3 ls` text | S3 lifecycle rule (below); upload is verified by size |
| cron: a missed night is lost | systemd timer with `Persistent=true` runs when the Pi is next up |
| Silent failures | `OnFailure=` unit logs a critical line; optional dead-man's-switch ping alerts you when a night is missed |
| No lock | `flock` stops overlapping runs |
| Local time in names | UTC names; refuses to run if the clock says it is before 2025 |

## 1. Get the files onto the Pi

Merge the PR (it deploys). Check:

```bash
ls -l ~/projects/bajeti/deploy/backup/
python3 -c 'import sqlite3; print(sqlite3.sqlite_version)'     # 3.34 or newer is fine
```

## 2. Create the settings file

```bash
mkdir -p ~/.config/bajeti
install -m 600 ~/projects/bajeti/deploy/backup/backup.env.example ~/.config/bajeti/backup.env
nano ~/.config/bajeti/backup.env       # set S3_BUCKET=s3://<BUCKET>
ls -l ~/.config/bajeti/backup.env      # must be -rw-------
```

AWS credentials stay in `~/.aws` as they are now.

## 3. Test by hand (does not touch the live database except to read it)

```bash
set -a; . ~/.config/bajeti/backup.env; set +a
~/projects/bajeti/deploy/backup/backup.sh --dry-run
~/projects/bajeti/deploy/backup/backup.sh
echo "exit code: $?"                    # must be 0
~/projects/bajeti/deploy/backup/backup-verify.sh
aws s3 ls s3://<BUCKET>/ | tail -3     # the new file is there
```

If the S3 size check fails with "Forbidden" the IAM user also needs `s3:GetObject` on the bucket (it reads the object's size back).

## 4. Install the timer

```bash
cd ~/projects/bajeti/deploy/backup
for f in bajeti-backup.service bajeti-backup-failure.service bajeti-backup.timer; do
  sed -e "s|@USER@|$(id -un)|g" -e "s|@HOME@|$HOME|g" "$f" | sudo tee "/etc/systemd/system/$f" >/dev/null
done
sudo systemctl daemon-reload
sudo systemctl start bajeti-backup.service          # run once through systemd
systemctl status bajeti-backup.service --no-pager | head -15
journalctl -u bajeti-backup.service -n 20 --no-pager
sudo systemctl enable --now bajeti-backup.timer
systemctl list-timers bajeti-backup.timer --no-pager
```

Test the failure path once (it must produce a loud log line and a failed unit, then you clean up):

```bash
sudo systemctl start bajeti-backup-failure.service
journalctl -t bajeti-backup -n 3 --no-pager
```

## 5. Retire the old cron job

Only after step 4 worked:

```bash
crontab -l | grep -v backup_sqlite_to_s3.sh | crontab -
crontab -l                                  # the 02:00 line is gone
mv ~/scripts/bajeti/backup_sqlite_to_s3.sh ~/scripts/bajeti/backup_sqlite_to_s3.sh.old
```

Never add a cron line for a script that loops forever (that exhausted the Pi's processes and caused the missed backups).

## 6. S3 retention (replaces the old delete loop)

Look at what exists first, because this call replaces any existing lifecycle configuration:

```bash
aws s3api get-bucket-lifecycle-configuration --bucket <BUCKET>
```

If it reports "NoSuchLifecycleConfiguration", set a 35-day expiry:

```bash
aws s3api put-bucket-lifecycle-configuration --bucket <BUCKET> --lifecycle-configuration '{
  "Rules": [{
    "ID": "expire-old-bajeti-backups",
    "Status": "Enabled",
    "Filter": { "Prefix": "db_backup_" },
    "Expiration": { "Days": 35 }
  }]
}'
```

If you get AccessDenied, the IAM user lacks `s3:PutLifecycleConfiguration`; add it in the AWS console or set the rule there by hand.

## 7. Alert when a night is missed (recommended)

Create a free check on a dead-man's-switch service such as healthchecks.io: period 1 day, grace 3 hours, and your email. Put its URL in `~/.config/bajeti/backup.env`:

```
BACKUP_PING_URL=https://hc-ping.com/<uuid>
```

The script pings on success and at `<URL>/fail` on failure. If the Pi is off, the timer never fires, or the script cannot start at all, the missing ping is what alerts you. Do not put this URL in the repo.

## 8. Check it regularly and restore

```bash
~/projects/bajeti/deploy/backup/backup-verify.sh        # newest backup is recent and restorable
```

Restore (replaces the live database, so keep the old file):

```bash
cd ~/projects/bajeti
docker compose stop bajeti_app
cp data/db/data/bajeti.db ~/bajeti.db.before-restore
cp ~/backups/db_backups/<FILE> data/db/data/bajeti.db
docker compose start bajeti_app
docker compose ps
```

## 9. Encryption with age (the private key never touches a Pi)

On the Mac (age is already installed there with Homebrew):

```bash
age-keygen -o ~/age-bajeti.txt          # prints the public key (age1...)
```

Put `~/age-bajeti.txt` in your password manager as a secure note, then delete the file. Send only the public key (`age1...`) to the Pi; never the `AGE-SECRET-KEY-...` line.

On the app Pi, install one pinned release binary in your home folder (no apt, nothing system-wide). Pick the same version as the Mac (`age --version`), take the file name and SHA-256 for `linux-arm64` from the release page, and compare before extracting:

```bash
cd "$(mktemp -d)"
curl -fsSLO https://github.com/FiloSottile/age/releases/download/<VERSION>/age-<VERSION>-linux-arm64.tar.gz
sha256sum age-<VERSION>-linux-arm64.tar.gz      # must equal the digest shown on the release page
tar -xzf age-<VERSION>-linux-arm64.tar.gz
mkdir -p ~/.local/bin && install -m 755 age/age ~/.local/bin/age
~/.local/bin/age --version
```

Undo: `rm ~/.local/bin/age`.

Then in `~/.config/bajeti/backup.env` (mode 600) set `AGE_RECIPIENT=age1...` and `AGE_BIN=/home/<USER>/.local/bin/age`, and run the backup once by hand (step 3). Encrypted copies appear in `~/backups/outgoing/` with a `.sha256` file each; the plain copies stay in `~/backups/db_backups/`. The S3 upload then holds the `.age` file.

## 10. Pull on the backup Pi (replaces pushing a copy from the app Pi)

Do not set `BACKUP_COPY_COMMAND`. The app Pi must hold no key for the backup Pi.

1. On the backup Pi, create a key just for this: `ssh-keygen -t ed25519 -N '' -f ~/.ssh/bajeti_pull -C bajeti-pull`.
2. On the app Pi, add its public key to `~/.ssh/authorized_keys` as one line that can only read the outgoing folder:

   ```
   restrict,command="/usr/bin/rrsync -ro /home/<USER>/backups/outgoing" ssh-ed25519 AAAA... bajeti-pull
   ```

3. Pin the app Pi's host key on the backup Pi: `ssh-keyscan -t ed25519 <PI_APP_HOST> > ~/.ssh/bajeti_pull_known_hosts`, then compare its fingerprint (`ssh-keygen -lf`) with the one shown on the app Pi (`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`) before trusting it.
4. Create the backup folder on the SSD by hand (an ordinary folder; nothing is formatted): `mkdir <SSD_MOUNT>/bajeti-backups`.
5. Copy `deploy/backup/pull-from-app.sh` to `~/bajeti-backup/` and make it executable. Create `~/.config/bajeti/pull.env` (mode 600) with `APP_SSH_TARGET=<USER>@<PI_APP_HOST>`, `DEST_DIR=<SSD_MOUNT>/bajeti-backups` and, if you made a second check, `PULL_PING_URL=...`.
6. Test: `set -a; . ~/.config/bajeti/pull.env; set +a; ~/bajeti-backup/pull-from-app.sh --dry-run`, then without `--dry-run`.
7. Install the unit and timer from `deploy/backup/bajeti-backup-pull.*` the same way as step 4 (replace `@USER@`, `@HOME@`, `@DEST_DIR@`), then `sudo systemctl enable --now bajeti-backup-pull.timer`.

Proof the app Pi cannot touch the backups: from the app Pi, `ssh <USER>@<PI_BACKUP_HOST>` must fail; from the backup Pi with the pull key, `rsync somefile <USER>@<PI_APP_HOST>:/` must be refused by `rrsync -ro`; delete the newest file on the app Pi and confirm the copy on the backup Pi is still there after the next pull.

## 11. Pull on the Mac

Same idea one step further along: a key on the Mac, restricted on the backup Pi with `restrict,command="/usr/bin/rrsync -ro <SSD_MOUNT>/bajeti-backups"`. Pin the backup Pi's host key as in step 10.3, use `scripts/mac-backup-pull.sh` with `DEST_DIR` on the FileVault volume outside iCloud and any synced folder, and schedule it with `scripts/com.example.bajeti-backup-pull.plist.example` (placeholders only).

## 12. Check last night's backup

| Where | Command | Good looks like |
|---|---|---|
| App Pi | `~/projects/bajeti/deploy/backup/backup-verify.sh` | "restore test ok", newest backup under 26 h |
| App Pi | `journalctl -u bajeti-backup.service -n 20 --no-pager` | "done", exit 0 |
| App Pi | `ls -l ~/backups/outgoing | tail -3` | a `.age` file and `.sha256` from last night |
| Backup Pi | `journalctl -u bajeti-backup-pull.service -n 20 --no-pager` | "done: 1 new" |
| Mac | `ls -lt ~/BajetiBackups | head -4` | last night's `.age` file |
| Any | `scripts/backup-restore-test.sh <file> <identity file>` | "restore test ok" |

Without monitoring a missing night is silent. Set `BACKUP_PING_URL` (step 7) and `PULL_PING_URL`, so you are told when either machine stops.
