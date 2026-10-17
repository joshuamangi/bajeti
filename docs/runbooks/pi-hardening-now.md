# Pi hardening: what to do now

Companion to the PR "Pi quick wins" (issue #110) and `docs/pi-inventory.md`. Hosts are placeholders: `<PI_APP_HOST>` (runs Bajeti), `<PI_BACKUP_HOST>` (second Pi with the SSD), `<USER>` (your login), `<LAN_CIDR>` (for example your home network in CIDR form). Never paste real addresses or keys into this file.

Rules: keep one ssh session open while changing ssh or the firewall, test from a second one, and know the rollback before you start.

## What the PR already changes (nothing to do except check before merging)

- Port 8000 is published on `127.0.0.1` only. cloudflared still reaches the app over the Docker network.
- The app container runs as UID 1000 (not root), with `no-new-privileges`, all capabilities dropped, a 768 MB memory limit, and a healthcheck.
- Docker logs rotate at 10 MB x 3 files per container.
- The image no longer contains `.env`, any database, tests or git history (before this, `COPY . .` copied `.env` into the image).
- Deploys write `.env` with mode 600, no longer use `--no-cache`, prune old build cache, and run only for merged PRs from this repository. Workflow tokens are read-only.

### Check on `<PI_APP_HOST>` BEFORE you merge the PR (merging deploys it)

```bash
id -u                                   # expect 1000; if not, the Dockerfile UID must change
cd ~/projects/bajeti
stat -c '%u:%g %a %n' data data/db data/db/data data/db/data/bajeti.db
```

Every line should start with `1000:`. If any shows `0:0` (created by the old root container), fix it:

```bash
sudo chown -R 1000:1000 ~/projects/bajeti/data
```

After the merge and deploy:

```bash
docker compose ps                                  # bajeti_app should become "healthy"
docker compose exec bajeti_app id                  # uid=1000(bajeti)
docker compose exec bajeti_app alembic current
ss -tln | grep 8000                                # should show 127.0.0.1:8000 only
```

Then open the site through the tunnel and log in. Rollback: revert the PR on GitHub and merge the revert (or `git revert` and push through a PR).

## 1. Protect `main` and the deploy runner (you, GitHub)

Branch protection (requires a PR and passing tests, but lets you merge your own PRs):

```bash
gh api -X PUT repos/<OWNER>/<REPO>/branches/main/protection --input - <<'EOF'
{
  "required_status_checks": { "strict": true, "contexts": ["test"] },
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null
}
EOF
```

Outside collaborators' workflows (web UI): repo Settings, Actions, General, "Fork pull request workflows from outside collaborators", choose "Require approval for all outside collaborators". Also in Settings, Code security, enable "Dependabot security updates".

Runner: it runs as your main user, who is in the `docker` group (equal to root on the Pi). Moving it to its own user does not remove the need for docker access, so the real protections are branch protection, the fork guard in the workflow, and a private-repo option later. The dedicated-user setup is stage S08. Until then keep outside write access to the repo closed.

## 2. Port 8000 on localhost

Done by the PR. Verify after deploy with the `ss` command above and, from another machine on the LAN, `curl -m 5 http://<PI_APP_HOST>:8000/` should now fail.

## 3. ssh: keys only (you, on `<PI_APP_HOST>`)

First, from your Mac, prove key login works without a password:

```bash
ssh -o PasswordAuthentication=no -o PubkeyAuthentication=yes <USER>@<PI_APP_HOST> 'echo key login ok'
```

On the Pi, see which keys are installed (type and comment only):

```bash
awk '{print NR": "$1, $NF}' ~/.ssh/authorized_keys
```

Remove any you do not recognise. Then:

```bash
grep -n '^Include' /etc/ssh/sshd_config            # expect Include /etc/ssh/sshd_config.d/*.conf
sudo tee /etc/ssh/sshd_config.d/10-hardening.conf >/dev/null <<'EOF'
PasswordAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
AllowUsers <USER>
EOF
sudo sshd -t && sudo systemctl reload ssh
```

Keep your current session open, open a new terminal and log in. Check the effective settings: `sudo sshd -T | grep -E '^(passwordauthentication|permitrootlogin|allowusers) '`.
Rollback: `sudo rm /etc/ssh/sshd_config.d/10-hardening.conf && sudo systemctl reload ssh`.

## 4. Firewall (you, on `<PI_APP_HOST>`)

This is a stop-gap on the old OS, replaced by the rebuild. The Pi has no firewall now, and Samba, nginx and ssh are open to the LAN.

```bash
sudo apt-get install -y ufw        # if apt-get update complains about bullseye-security, that is the end-of-life repo; install still works
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from <LAN_CIDR> to any port 22 proto tcp comment 'ssh from LAN'
sudo ufw enable
sudo ufw status verbose
```

The tunnel only makes outbound connections, so it keeps working. Rollback: `sudo ufw disable`. Test: log in from a second terminal, load the site through the tunnel, and check deploys still run on the next merge.

## 5. Why backups were missed (you read, then tell me)

On `<PI_APP_HOST>`:

```bash
tail -n 100 ~/scripts/bajeti/backup_log.txt
grep -n -i -E 'error|fail|denied|unable|timeout' ~/scripts/bajeti/backup_log.txt | tail -30
last -x reboot shutdown | head -20            # were there reboots or power cuts on Oct 6, 7, 9, 11?
journalctl --since 2026-10-05 --until 2026-10-12 --no-pager -t CRON | head -40
ls -l ~/backups/db_backups | tail -20
```

Integrity and restore check on the newest file (copy it, never open the live DB):

```bash
cp ~/backups/db_backups/db_backup_<DATE>_*.db /tmp/restore-test.db
sqlite3 /tmp/restore-test.db 'PRAGMA integrity_check; SELECT count(*) FROM users; SELECT count(*) FROM expenses;'
rm /tmp/restore-test.db
```

Check S3 has them: `aws s3 ls s3://<BUCKET>/ | tail -20`.
Send me the output (with any bucket name, keys and addresses removed) and a copy of `backup_sqlite_to_s3.sh` with secrets stripped; I will fix the script and add failure alerting.

## 6. A second copy on `<PI_BACKUP_HOST>` (stage S02 finalises this)

Do not put database backups only on the exFAT SSD (no journaling, no permissions). The second Pi's SD card is ext4 and has about 100 GB free, so use that as the primary copy and the SSD as an extra copy.

On `<PI_BACKUP_HOST>`:

```bash
sudo install -d -m 700 -o <USER> -g <USER> /srv/bajeti-backups
ssh-keygen -t ed25519 -f ~/.ssh/bajeti_pull -N '' -C 'bajeti backup pull'
cat ~/.ssh/bajeti_pull.pub
```

On `<PI_APP_HOST>`, add that public key to `~/.ssh/authorized_keys`, restricted to read-only access of one folder:

```
restrict,command="rrsync -ro /home/<USER>/backups/db_backups" ssh-ed25519 AAAA... bajeti backup pull
```

(`rrsync` ships with the `rsync` package; confirm with `which rrsync` or `dpkg -L rsync | grep rrsync`.) Back on `<PI_BACKUP_HOST>`, test, then schedule at 03:30:

```bash
rsync -a -e 'ssh -i ~/.ssh/bajeti_pull' <USER>@<PI_APP_HOST>:/ /srv/bajeti-backups/
( crontab -l 2>/dev/null; echo '30 3 * * * rsync -a -e "ssh -i ~/.ssh/bajeti_pull" <USER>@<PI_APP_HOST>:/ /srv/bajeti-backups/ && rsync -rt --no-perms --no-owner --no-group /srv/bajeti-backups/ /mnt/ssd/bajeti-backups/' ) | crontab -
```

Then run the restore test from section 5 on a file in `/srv/bajeti-backups`.

## 7. Rebuild on a supported OS (stages S03 to S05, not tonight)

Do not run a release upgrade in place. Plan: finish the verified backups (sections 5 and 6), pick the OS image (the second Pi already runs Debian 13 trixie, which is a good choice), write the Ansible roles (S04), rehearse on a spare card or SSD (S05), cut over, and keep the old card untouched as rollback for a few weeks.

## 8. Reclaim space on `<PI_APP_HOST>` (you)

Find what is filling the journal first, then cap it and clean up:

```bash
journalctl --disk-usage
journalctl -b --no-pager -o short | awk '{print $5}' | sed 's/\[.*//' | sort | uniq -c | sort -rn | head
sudo mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=200M\nSystemMaxFileSize=50M\n' | sudo tee /etc/systemd/journald.conf.d/size.conf
sudo systemctl restart systemd-journald
sudo journalctl --vacuum-size=200M

docker builder prune -f                       # about 12 GB of build cache, safe
docker rm cf-login sleepy_wing                # one-off leftovers
docker rmi hello-world wernight/ngrok         # only if nothing uses ngrok (see section 10)
df -h /
```

## 9. cloudflared version

The image is about a year old and unpinned. Find what runs now and pin it:

```bash
docker exec cloudflared cloudflared --version
```

Tell me the version and I will set `image: cloudflare/cloudflared:<version>` in the compose file. To upgrade deliberately, pick a newer release tag, change the line in a PR, and check the tunnel after deploy.
The app container is already non-root after this PR; cloudflared stays root for now because it reads root-owned credentials.

## 10. Check before disabling services (you, on `<PI_APP_HOST>`)

```bash
testparm -s 2>/dev/null | grep -E '^\[|path'     # any shares defined?
sudo smbstatus 2>/dev/null | head                # anyone connected?
sudo nginx -T 2>/dev/null | grep -E 'server_name|listen|root|proxy_pass' | head -30
systemctl status ngrok --no-pager | head -8
sudo certbot certificates 2>/dev/null | head -12
systemctl is-active bluetooth ModemManager triggerhappy iscsid avahi-daemon
```

If a service is clearly unused, disable it (reversible):

```bash
sudo systemctl disable --now smbd nmbd         # example
```

Send me the output and I will mark each item Keep or Remove in the inventory and leave it out of the Ansible roles.

## Order I would do this in

1. Pre-merge check on the Pi, then merge the PR (sections above, "Check before you merge").
2. Section 1 (GitHub settings), section 3 (ssh), section 4 (firewall).
3. Section 8 (cleanup), section 5 (backup log), section 6 (second copy).
4. Section 10 and 9, then the rebuild (7).
