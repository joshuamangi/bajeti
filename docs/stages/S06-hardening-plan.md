# S06: Pi security audit and hardening plan

**Prompt:** P2  |  **Mode:** claude  |  **Depends on:** S05  |  **Suggested branch:** `feature/issue-N-hardening-plan`

## Goal

With the rebuilt Pis in place, produce the ranked hardening plan (one weekend and longer term) and mark what the rebuild already solved.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `docs/pi-inventory.md` and infra/ (what is already enforced)
4. `docs/deployment-guide.md`, docker-compose files, Dockerfile, .github/workflows/*.yml, Makefile
5. `app/config.py`, core/security.py, routers/auth.py
6. The 'Known problems and risks' section in CLAUDE.md or your project context file

### Outputs of earlier stages this stage relies on

- S05 outputs (what the rebuild already fixed)
- S00 rotation done

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: act as a security reviewer for a single-user, self-hosted Raspberry Pi running Docker Compose behind a Cloudflare Tunnel, with the app repo public and a self-hosted GitHub Actions runner on the same Pi.

Read: docs/deployment-guide.md, docker-compose files, Dockerfile, .github/workflows/*.yml, Makefile, app/config.py, core/security.py, routers/auth.py, and section "Known problems and risks" in CLAUDE.md or the project context.

Produce docs/hardening-plan.md with two parts:
A) "One weekend" plan: ordered, each item with (1) risk it removes, (2) exact change, (3) how to verify, (4) how to roll back, (5) time estimate. Cover at least: end-of-life Pi OS (see P1a [S01] and P1b [S03]), SECRET_KEY rotation, bind port 8000 to 127.0.0.1, non-root container, .env permissions (600), SSH keys only and no root login, ufw default-deny with only what is needed, fail2ban, unattended-upgrades, pin cloudflared, journald and Docker log limits, GitHub branch protection (required PR + passing tests), requiring approval for outside collaborators' workflows, Dependabot alerts/updates.
B) "Longer term": self-hosted runner isolation (dedicated user, ephemeral or containerised runner, or move deploy to a pull-based model so a PR cannot execute on the Pi), reverse-proxy-level rate limiting, optional Tailscale for admin access instead of any open port, SD-card wear reduction or moving the DB to USB SSD, read-only root filesystem options, audit logging, restore testing.

Rank by (risk reduced) / (effort). Be explicit about the threat model: public repo, public hostname, leaked key, self-hosted runner. Do not suggest anything that needs new heavy dependencies. Flag anything you are unsure about instead of guessing.
```

## Watch out for

- This is a plan, not changes. Do not apply items from it in this stage.
- Some items may already be fixed by the rebuild. Check the new setup instead of trusting the old audit.

## Your part (Claude cannot or should not do these)

1. Approve the plan and decide which items you do now and which go on the backlog.

## Done when

- docs/hardening-plan.md with a weekend plan and a longer-term part.
- Each item has risk removed, exact change, verification, rollback and time.
- Items already solved by the rebuild are marked as such.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- docs/hardening-plan.md

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: The items you chose to do now and which later stages (S07, S08) cover them.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S07-harden-docker.md`: Harden Docker Compose and the Dockerfile.
