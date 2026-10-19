# IMPLEMENTATION.md: how to work through the Bajeti stages

This file is for Claude. Read it at the start of every session and follow it. The user does not paste any prompt; they will usually say "continue". Each stage has its own file in this folder with the context to read and the prompt to follow.

## How to work

1. Find the first stage in the table below whose status is not `done`. That is the current stage.
2. Tell the user in two lines which stage it is, its mode and what it depends on. If its status is `in-progress`, `waiting-on-you` or `blocked`, read the latest entry in `HANDOFF.md`, say where it was left, and ask whether to resume. If it is `todo`, ask whether to start it. Wait for the answer.
3. Once the user agrees, read these, in this order, and no later stage's file:
   1. `00-shared-context.md`
   2. The latest entries in `HANDOFF.md`
   3. The stage file
   4. Every file listed under "Read first" in the stage file
4. Set the stage's status to `in-progress` in the table below (change only the Status cell).
5. Follow the prompt in the stage file as written. Where it says to plan first or wait for approval, stop and wait.
6. Follow the stage's mode:
   - `claude`: implement and test inside the repo.
   - `claude+human`: finish all repo-side work, then give the user a numbered checklist with exact commands and what to paste back (redacted) for the steps only they can do. Set the status to `waiting-on-you` and stop until they report back.
   - `design-gate`: write the design, then stop for approval before any code.
7. When the work and the user's part are both done, follow "Finish and hand off" at the bottom of the stage file: verify against Done when with evidence, append to `HANDOFF.md`, set the status to `done`.
8. Ask the user: "Stage <id> is done. Start <next id>: <title>?" Do not read the next stage's file until they say yes. If this session already covered more than one stage or holds a lot of output, add that they can run `/clear` first and say "continue", because everything needed is on disk.
9. If the user names a different stage, check that every stage in its "Depends on" is `done`. If not, say which are open and ask before going on.
10. Never mark a stage `done` without evidence for each Done when item and the user's confirmation. Use `blocked` and say why if something outside your control stops the work.

The rules that apply to every stage (public repo, placeholders for hosts, no commands against the Pis, no workarounds) are in `00-shared-context.md`.

## Statuses

`todo`, `in-progress`, `waiting-on-you`, `blocked`, `done`.

## Stages

| Stage | Title | Mode | Depends on | Status |
|---|---|---|---|---|
| S00 | [Rotate the leaked SECRET_KEY](S00-rotate-secret-key.md) | claude+human | none | done |
| S01 | [Pi inventory and necessity audit (both Pis)](S01-pi-audit.md) | claude+human | none | done |
| S02 | [Backups: backup Pi SSD, Mac pull, offsite](S02-backups-two-pis.md) | design-gate | S01 | done |
| S03 | [Pi OS end-of-life decision and upgrade runbook](S03-pi-os-upgrade.md) | design-gate | S01, S02 | done |
| S04 | [Ansible infrastructure as code for both Pis](S04-ansible-iac.md) | claude+human | S01, S02, S03 | todo |
| S05 | [Rebuild rehearsal and cutover](S05-rebuild-rehearsal-cutover.md) | claude+human | S02, S03, S04 | todo |
| S06 | [Pi security audit and hardening plan](S06-hardening-plan.md) | claude | S05 | todo |
| S07 | [Harden Docker Compose and the Dockerfile](S07-harden-docker.md) | claude | S06 | todo |
| S08 | [Harden CI/CD and deploy](S08-harden-ci-cd.md) | claude+human | S07 | todo |
| S09 | [Backup automation, alerting and restore tests](S09-backup-automation.md) | claude+human | S02, S04 | todo |
| S10 | [App security fixes with tests](S10-app-security-fixes.md) | claude | S00 | todo |
| S11 | [E0 Targets (#101, #103 to #106)](S11-targets-e0.md) | claude | S10 | todo |
| S12 | [E1 Pi cleanup and performance (#110)](S12-pi-cleanup-performance.md) | claude+human | S05, S11 | todo |
| S13 | [E2 Analytics page (#111)](S13-analytics-e2.md) | design-gate | S12 | todo |
| S14 | [E3 Recurring expenses (#112)](S14-recurring-e3.md) | design-gate | S10 | todo |
| S15 | [E6 Future planning (#115), design only](S15-future-planning-e6.md) | design-gate | S11 | todo |
| S16 | [E5 PWA and prototype context bundle (#114)](S16-pwa-prototype-e5.md) | claude+human | S13 | todo |
| S17 | [E4 Payment capture (#113)](S17-payment-capture-e4.md) | design-gate | S10 | todo |
| S18 | [E7 Code and workflow improvements (#116)](S18-code-workflow-e7.md) | claude | S10 | todo |

## Other files in this folder

- `00-shared-context.md`: project summary and rules, read at the start of every stage.
- `HANDOFF.md`: log of what each finished stage produced, what is unverified, and what was decided. Newest at the bottom.
- `tools-prompt-writing.md`: prompts for writing a new stage's prompt.
- `../prompts/README.md`: the full prompt pack, kept as a reference copy.

## Notes for the user

- One line in `CLAUDE.md` is all that is needed so Claude finds this file by itself:

```
At the start of every session read docs/stages/IMPLEMENTATION.md and follow it. Do not start a stage until I agree.
```

- The prompts in the pack are numbered P0, P1a, P1b and so on, while stages are numbered S00 to S18 in the order you do them. Where a prompt mentions another prompt, the stage file shows the stage in brackets, for example "P1a [S01]".
- The prompt text inside each stage file is the working copy. If you change one there and want the reference pack to match, change it in `../prompts/README.md` too.
- To add a stage: copy an existing stage file, give it the next number, rewrite its sections, and add a row to the table above. `tools-prompt-writing.md` has prompts to draft the new prompt.
- Order matters. The Pi OS is end of life, so the Pis come first, and a verified backup comes before any OS work. S00 (rotate the leaked key) and S01 (audit) are independent and can be done straight away.
