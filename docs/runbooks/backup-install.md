# Install the Bajeti backup (systemd timer)

Replaces the old cron job that ran `~/scripts/bajeti/backup_sqlite_to_s3.sh`. The new files are in `deploy/backup/` and reach the Pi on the next deploy (the deploy does `git reset --hard origin/main` in `~/projects/bajeti`). Placeholders: `<USER>` is your login on the app Pi, `<BUCKET>` your S3 bucket.

What changed compared with the old script:

| Old script | New script |
|---|---|
| `cp` of the live database | SQLite backup API (consistent), through `python3` because the Pi has no `sqlite3` binary |
| Never checked the copy | `PRAGMA integrity_check` must say `ok`; written as `.partial`, then renamed |
| No error handling; a failed step looked like success | `set -Eeuo pipefail`, every step checked, non-zero exit on any failure |
| Local prune looked for `*.sqlite3` so it never deleted anything | Keeps the newest 30 `db_backup_*.db` |
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

## 9. Second copy on the other Pi

Set `BACKUP_COPY_COMMAND` in `backup.env`, for example `rsync -a "$1" <USER>@<PI_BACKUP_HOST>:/srv/bajeti-backups/`, after creating a restricted ssh key for it (stage S02 designs this). Until then the copies are on the Pi's SD card and in S3.
