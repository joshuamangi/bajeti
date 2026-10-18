# S04: Ansible infrastructure as code for both Pis

**Prompt:** P1  |  **Mode:** claude+human  |  **Depends on:** S01, S02, S03  |  **Suggested branch:** `feature/issue-N-ansible-iac`

## Goal

Describe both Pis entirely in Ansible so an OS rebuild or a dead SD card is a repeatable procedure.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `docs/pi-inventory.md` (S01): only Keep and Replace items go into Ansible
4. `docs/runbooks/pi-os-upgrade.md` (S03)
5. `docs/design/storage-and-backups.md` and the role drafts (S02)
6. docker-compose files, Dockerfile, .github/workflows/deploy.yml, Makefile, docs/deployment-guide.md, docs/migrations.md

### Outputs of earlier stages this stage relies on

- S01 inventory
- S02 role drafts and design
- S03 runbook (chosen OS release)

## Before you start

- Install ansible, ansible-lint and yamllint on your Mac.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: create infrastructure-as-code for the Raspberry Pi that runs Bajeti, using Ansible, in infra/ as laid out in the Reference section below this prompt. First inspect the repo (docker-compose files, Dockerfile, .github/workflows/deploy.yml, Makefile, docs/deployment-guide.md, docs/migrations.md) and summarise how the Pi is currently set up and deployed. List assumptions and questions before writing code.

Requirements:
- Ansible roles: base, ssh_hardening, firewall (ufw), fail2ban, unattended_upgrades, docker, storage (SSD mount, see P1c [S02]), bajeti_app, backups, monitoring, github_runner (dedicated unprivileged user, documented registration step).
- Start from docs/pi-inventory.md (P1a [S01]): include only items marked Keep or Replace. Anything marked Investigate must be listed as an open question, not silently included.
- The playbook must work on a fresh Raspberry Pi OS image for the release chosen in P1b [S03], so the same code serves the OS rebuild and any future disaster recovery.
- Two inventory groups, `app` (`<PI_APP_HOST>`) and `backup` (`<PI_BACKUP_HOST>`), with placeholders in the committed example. Common roles (base, ssh_hardening, firewall, fail2ban, unattended_upgrades) apply to both; bajeti_app, docker and github_runner only to `app`; storage and backup_target only to `backup`. Firewall rules per group follow P1c [S02] (LAN-only, least access between the Pis).
- Idempotent. Every role must pass `ansible-playbook --check --diff` and a second run must report zero changes.
- Public repo: only *.example inventory and vars are committed; real inventory and secrets are git-ignored. Support Ansible Vault or sops+age for secrets and document which you chose and why.
- Pi/SD-card friendly: limit journald size, Docker json-file log rotation (max-size/max-file), noatime, no verbose debug logging, avoid unnecessary writes, optional tmpfs for /tmp.
- Docker: pinned image versions (including cloudflared), non-root container user, ports bound to 127.0.0.1, healthchecks, resource limits suited to 3.7 GB RAM.
- A lock-out safety: never apply ssh/firewall changes without first confirming key login works and keeping an existing session open. Add pre-flight assertions.
- Include a README with: bootstrap from a fresh Pi OS image, first run, check-mode run, how to add a new role, rollback notes.
- Add a CI job (GitHub-hosted runner, not the Pi) running ansible-lint and yamllint on infra/.

Do not connect to or modify the real Pi. Produce everything so that I run it myself. End with a "what I must do manually" checklist and a list of what you could not verify.

Definition of done: ansible-lint clean, check-mode instructions work, no secrets or IPs in the diff.
```

### Reference: the infrastructure layout and decisions the prompt above points to

**Recommendation: Ansible (run from your Mac over SSH) plus the Docker Compose files already in the repo.**

| Option | Verdict |
|---|---|
| Ansible | Best fit. Agentless, idempotent, nothing extra to run on a 3.7 GB Pi, `--check --diff` gives dry-runs, good roles for hardening (ssh, ufw, fail2ban, unattended-upgrades, docker). |
| Terraform/OpenTofu | Good for things with APIs: the Cloudflare tunnel/DNS and the S3 bucket. Optional later; not for configuring the Pi itself. |
| Nix/NixOS | Powerful but heavy for a single Pi and a single developer. Skip. |
| Docker Compose only | Already used for the app. Keep it, but it does not cover OS hardening. |

Layout to ask Claude for (all in the public repo, with real inventory and secrets kept OUT of it):

```
infra/
  ansible/
    ansible.cfg
    inventory/
      example.ini            # placeholders only, committed
      production.ini         # real host, git-ignored
    group_vars/
      all.example.yml        # committed, placeholders
      all.vault.yml          # git-ignored or ansible-vault / sops+age encrypted
    playbooks/site.yml
    roles/
      base/                  # packages, timezone, NTP, journald limits, noatime, swap policy
      ssh_hardening/
      firewall/              # ufw
      fail2ban/
      unattended_upgrades/
      docker/                # engine, daemon.json log rotation, non-root usage
      bajeti_app/            # compose files, env template, systemd unit or compose up
      storage/               # backup Pi only: SSD mount by UUID (nofail, noatime), backup dirs
      backup_target/         # backup Pi only: pull job from the app Pi, versioned snapshots, retention
      backups/               # app Pi: sqlite .backup, age encryption, systemd timer, S3 upload, restore script
      github_runner/         # unprivileged runner user and service
      monitoring/            # disk, temp, SD wear signals, healthcheck ping
  compose/
    docker-compose.yml
    docker-compose.prod.yml
  terraform/                 # optional: cloudflare tunnel + s3 bucket + IAM (least privilege)
  README.md                  # bootstrap, how to run check mode, how to restore
```

Secrets rule: committed files hold only `*.example` placeholders. Real values live in GitHub Actions secrets, an Ansible Vault file, or sops+age. Never in the repo.

## Watch out for

- Nothing connects to a Pi from Claude's session. You run every playbook, in check mode first.
- Keep a second SSH session open while SSH or firewall rules change, or you can lock yourself out.
- Only `*.example` files are committed. The real inventory and vault stay git-ignored.
- Anything marked Investigate in the inventory is a question, not a task.

## Your part (Claude cannot or should not do these)

1. Create the real inventory and vault file yourself; they stay git-ignored.
2. Run `ansible-playbook --syntax-check`, then `--check --diff` against the backup Pi first, then the app Pi. Read every diff.
3. Keep an existing SSH session open while SSH or firewall changes are applied.

## Done when

- ansible-lint clean and a second run reports zero changes in check mode.
- Only *.example inventory and vars are committed; no secrets or IPs in the diff.
- infra/README.md covers bootstrap, first run, check mode, adding a role and rollback.
- CI job runs ansible-lint and yamllint on infra/.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- infra/ansible (roles, playbook, example inventory and vars)
- infra/README.md
- CI job for lint

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Which items from the inventory were deliberately dropped, and any open questions from the Investigate list.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S05-rebuild-rehearsal-cutover.md`: Rebuild rehearsal and cutover.
