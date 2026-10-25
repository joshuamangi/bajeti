# S02: Backups: backup Pi SSD, Mac pull, offsite

**Prompt:** P1c  |  **Mode:** design-gate  |  **Depends on:** S01  |  **Suggested branch:** `feature/issue-N-backup-design`

## Goal

Design and then build backups across the app Pi, the backup Pi's SSD, your MacBook and S3, with a restore test from every tier.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `docs/pi-inventory.md` (S01), especially the backup Pi section
4. `docs/deployment-guide.md`
5. Makefile and any backup script or cron entry documented in the repo

### Outputs of earlier stages this stage relies on

- docs/pi-inventory.md from S01

## Before you start

- Reserve fixed addresses for both Pis with DHCP reservations on your router.
- Do not touch the SSD or anything on it until you have confirmed what it holds.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

Topology: two Raspberry Pis on the same LAN. The **app Pi** (`<PI_APP_HOST>`) runs Bajeti. The **backup Pi** (`<PI_BACKUP_HOST>`) has the SSD attached. Reserve fixed addresses for both with DHCP reservations on the router so the inventory never goes stale.

```
Context: Bajeti runs on the app Pi (`<PI_APP_HOST>`), booting from an SD card. A second Pi on the same LAN (`<PI_BACKUP_HOST>`) has an SSD attached. I also have a MacBook. The database is SQLite; backups currently run via cron at 02:00 on the app Pi to local storage and S3, with gaps and no restore test. I do not yet know what else the backup Pi does, its OS release, or whether it also needs the end-of-life upgrade (P1a [S01] audits it). Never write real addresses or hostnames into the repo; use the placeholders.

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
10. The backup Pi is now critical infrastructure: it needs the same hardening as the app Pi (SSH keys only, ufw, fail2ban, unattended upgrades, a supported OS) and its own health alert if it stops receiving backups. Say what happens to the other things it currently does, if any (P1a [S01] tells us), and flag any conflict between those duties and being a backup target.

Implement: Ansible inventory groups `app` and `backup` (placeholders only), a `storage` role and a `backup_target` role for the backup host, an extended `backups` role for the app host, plus scripts/mac-backup-pull.sh and an example launchd plist with placeholders only. Do not touch the real Pis; give me the commands to run, and a "what I must do by hand" list (formatting or partitioning the SSD is destructive, so write it as a clearly marked, confirm-before-run step with device-name verification, and do not touch any existing data on that SSD until I confirm what it holds).

Definition of done: restore from all three tiers succeeds on a test copy, no secrets/IPs in the diff, the app Pi cannot delete or modify backups on the backup Pi (prove with a test), and docs say how I check last night's backup.
```

## Watch out for

- Do not format or write to the SSD until you have confirmed what is on it and have a copy of anything you want.
- The app Pi must never be able to delete or overwrite its own backups. Check the design for this before approving.
- A backup that was never restored is not a backup. Do not close the stage until each tier has been restored once.
- The age private key must not live on either Pi.

## Your part (Claude cannot or should not do these)

1. Approve docs/design/storage-and-backups.md before Claude implements anything.
2. Back up anything you care about on the SSD, then run the clearly marked format step yourself after checking the device name.
3. Create the age keypair; keep the private key in your password manager only and give Claude the public key placeholder name.
4. Install the restricted SSH keys and apply firewall rules yourself, using `--check` first.
5. Apply the S3 IAM policy and run one real backup, then restore from each tier.

## Done when

- Design approved, then implemented as Ansible role drafts and scripts/mac-backup-pull.sh.
- Restore succeeds from the backup Pi SSD, the Mac and S3 on a test copy.
- The app Pi cannot modify or delete backups on the backup Pi (tested).
- Docs explain how to check last night's backup.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- docs/design/storage-and-backups.md
- infra/ansible roles: storage, backup_target, backups (drafts)
- scripts/mac-backup-pull.sh and a launchd example with placeholders

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Boot-media decision for the app Pi, where the age private key is kept, and the result of each restore test.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S03-pi-os-upgrade.md`: Pi OS end-of-life decision and upgrade runbook.
