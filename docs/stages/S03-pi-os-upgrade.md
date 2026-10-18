# S03: Pi OS end-of-life decision and upgrade runbook

**Prompt:** P1b  |  **Mode:** design-gate  |  **Depends on:** S01, S02  |  **Suggested branch:** `feature/issue-N-pi-os-upgrade`

## Goal

Decide how to move both Pis off the end-of-life OS and write the runbook, including sequencing and rollback.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `docs/pi-inventory.md` (S01)
4. `docs/design/storage-and-backups.md` (S02)
5. The reviewed audit reports (kept out of git)

### Outputs of earlier stages this stage relies on

- docs/pi-inventory.md (S01)
- docs/design/storage-and-backups.md (S02)
- Verified backups from S02 (this stage assumes they exist)

## Before you start

- Confirm a verified, restorable backup exists on at least two tiers before any OS work is planned for execution.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Context: the app Pi's OS has reached end of life (no security updates), and the backup Pi may be on the same release. The app Pi is a production host reachable through a Cloudflare Tunnel, so this is high priority.

Task: investigate, then write docs/runbooks/pi-os-upgrade.md. Plan first; do not execute anything.

1. From pi-audit-report.txt, identify the exact Debian / Raspberry Pi OS release and the Pi model. Verify the current support status and the latest Raspberry Pi OS release from official sources (Debian release and LTS pages, Raspberry Pi documentation) and cite the links. If the report is missing, give me the exact commands to run.
2. Compare the options, two lines of trade-off each:
   a) In-place apt dist-upgrade across major releases. Check what Raspberry Pi currently says about supporting this, whether it must step through each release, and the risk of a half-upgraded system with Docker, the runner and kernel/firmware.
   b) Fresh install of the current Raspberry Pi OS 64-bit Lite (headless) on new media, configured entirely by the Ansible playbook, data restored from a verified backup, then cut over. This is my expected recommendation unless the evidence says otherwise.
   c) Any other realistic option, only if there is a concrete reason.
3. For the recommended option, write the full runbook: preconditions (a verified restorable backup, see P1c [S02]), Raspberry Pi Imager settings (hostname placeholder, SSH key only, no default password, timezone Africa/Nairobi), first boot, Ansible bootstrap, deploying the app, restoring the database, verification, cutover, rollback.
4. Cutover design:
   - The old SD card stays untouched and is the instant rollback.
   - The old and new instances must never write to different databases behind the same tunnel at the same time (avoid split writes). Stop the old one first, or rehearse the new one on a different hostname/tunnel.
   - Re-register the GitHub self-hosted runner on the new install (new registration token; remove the old runner in GitHub settings).
   - Cloudflare tunnel credentials and all secrets are supplied from secret stores, never committed.
   - Cron/timers, firewall, SSH config, Docker engine (installed from Docker's apt repo for the new Debian codename, version pinned) all come from Ansible.
5. Compatibility checklist: Docker and compose plugin versions, cgroups and kernel settings for memory limits, nftables vs iptables backend for ufw, SSH config differences, time sync, locale.
6. Give a downtime estimate, explicit go/no-go checks at each stage, rollback criteria, and a post-cutover checklist for the first 7 days.
7. Two-Pi sequencing. The backup Pi may be on the same end-of-life OS. Propose an order and justify it. My expectation: back up first to the Mac and S3 so those tiers are verified, then rebuild the BACKUP Pi first as a low-stakes, LAN-only dry run of the Ansible playbook (reflashing only its boot media and leaving the SSD data untouched, verified by checksums before and after), and only then rebuild the app Pi. State what happens to the SSD backups during the backup Pi's rebuild and how long there is no second tier available. Confirm what else the backup Pi does before touching it (from P1a [S01]).

Definition of done: numbered, copy-pasteable steps tagged [Mac], [Pi-app] or [Pi-backup], each with a verify step and a rollback; a list of unknowns I must confirm; no IPs, hostnames or tokens in the document.
```

## Watch out for

- No OS work happens before S02's restore tests pass.
- Verify Raspberry Pi's current upgrade guidance yourself before approving the recommended option. Claude can be out of date.
- Rebuild the backup Pi first. Leave the SSD data in place and compare checksums before and after.

## Your part (Claude cannot or should not do these)

1. Confirm the Pi models, OS releases and boot media of both Pis.
2. Approve the chosen option and the order (backup Pi first, then app Pi).
3. Choose a maintenance window and accept the downtime estimate.
4. Decide whether to buy a small SSD for the app Pi.

## Done when

- docs/runbooks/pi-os-upgrade.md with numbered steps tagged [Mac], [Pi-app] or [Pi-backup], each with verify and rollback.
- Explicit go/no-go checks and a first-7-days checklist.
- A list of unknowns you must confirm.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- docs/runbooks/pi-os-upgrade.md

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: The chosen upgrade option, the order of the two Pis, and the unknowns still open.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S04-ansible-iac.md`: Ansible infrastructure as code for both Pis.
