# S18: E7 Code and workflow improvements (#116)

**Prompt:** P14  |  **Mode:** claude  |  **Depends on:** S10  |  **Suggested branch:** `feature/issue-116-code-improvements (one PR per item)`

## Goal

Pay down code quality in small PRs: Pydantic v2, Decimal money, CI upgrades, missing tests, shared error handling, a decision memo on the web layer.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `schema/`*.py and services/*.py
4. `tests/` and tests/conftest.py
5. `.github/workflows` (as changed in S08)
6. `app/requests.py` (dead code) and app/handlers
7. Dockerfile and migrations

### Outputs of earlier stages this stage relies on

- S08 CI changes
- S12 cleanup already removed app/requests.py if done there

## Before you start

- One item per PR; stop after each.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: plan then execute the code-quality epic in small, separate PRs. One item per PR; stop after each.

Items: (1) Pydantic v2: replace orm_mode with model_config = ConfigDict(from_attributes=True) everywhere; (2) Decimal for money in schemas, with correct JSON serialisation and no float rounding in totals (check the JS side too); (3) CI Python 3.11 + ruff + coverage threshold; (4) tests for budgets, allocations, transfers and withdrawals (create/update/delete withdrawals incl. insufficient funds on budget vs allocation, editing applies only the difference, deleting restores); (5) shared handler error handling in the web layer; (6) migration check in CI against a production-shaped DB copy; (7) run migrations in the container start script; (8) evaluate whether the web layer should call services directly instead of the API over HTTP: write a decision memo with the migration steps and risks, do NOT implement.

For each: state the risk, the test that proves nothing regressed, and the rollback. Report coverage before and after.
```

## Watch out for

- One item per PR. Stop after each.
- Money moves to Decimal one place at a time, with tests; a float to Decimal change can alter stored totals.
- The web-layer decision is a memo only. Do not start the rewrite.

## Your part (Claude cannot or should not do these)

1. Review each PR and the coverage before and after.
2. Decide what to do after reading the web-layer decision memo.

## Done when

- Each item states its risk, the test that proves nothing regressed and its rollback.
- Coverage reported before and after.
- Decision memo written for item 8; not implemented.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- One PR per item
- docs/design/web-layer-vs-services.md

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Anything deferred.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage:** none. Use `docs/stages/tools-prompt-writing.md` for new ideas.
