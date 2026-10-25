# S11: E0 Targets (#101, #103 to #106)

**Prompt:** P7  |  **Mode:** claude  |  **Depends on:** S10  |  **Suggested branch:** `feature/issue-101-target-model-routes (current branch)`

## Goal

Finish Targets in five internal stages: routes, service, UI handlers, category stats, dashboard visualisation.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `data/db/models/models.py` (Target)
4. migrations: 9b38fdc94e38 and 186f1cc1a7ca, and docs/migrations.md
5. `routers/targets.py` and main.py
6. An existing service and router as the pattern, plus tests/conftest.py
7. `app/handlers`, dashboard.html, palette.css, main.css

### Outputs of earlier stages this stage relies on

- S10 cross-user test pattern

## Before you start

- You are already on the branch feature/issue-101-target-model-routes with uncommitted work; commit or stash deliberately.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: complete the Targets feature in stages; stop after each stage for my review. Plan first.

Existing: Target model (budget_id, category_id, short/mid/long term amounts, unique (budget_id, category_id)), migration 9b38fdc94e38 (downgrade is `pass`), backfill migration 186f1cc1a7ca, empty routers/targets.py not registered in main.py.

Stage 1 (#101 routes): fix the real downgrade for 9b38fdc94e38. Decide and document what to do about the backfill creating NULL-amount rows (a POST for those pairs would 409). Recommend: treat POST as upsert, or drop the backfill and create lazily; show the trade-off in two lines. Add schema/target.py (Decimal money), register the router, implement GET/POST/PUT/DELETE under /budgets/{budget_id}/targets with ownership checks, and tests including cross-user tests.
Stage 2 (#103 service): TargetService static-method class following existing services.
Stage 3 (#104 UI handlers): handlers in app/handlers calling the API via the existing httpx pattern, redirect_with_toast on result.
Stage 4 (#105): extend GET /categories/with-stats/{budget_id} with target data, avoiding N+1 queries.
Stage 5 (#106): dashboard visualisation (progress against short/mid/long term), using palette.css tokens, 4px-multiple spacing, em units, `p-` classes. Do not add a CSS framework.

Definition of done per stage: tests pass, migration upgrade+downgrade verified on a copy of the DB, issue checklist updated.
```

## Watch out for

- You are on a branch with uncommitted work. Do not let Claude reset or discard it.
- Stop after each of the five internal stages and review.
- Every Targets query must be scoped by user_id and have a cross-user test.
- Do NOT stamp production. It has no `targets` table (alembic at 877adbb8bce2), so the deploy's `alembic upgrade head` must create and backfill it. See docs/migrations.md.

## Your part (Claude cannot or should not do these)

1. Stop and review after each of the five internal stages.
2. Verify migration upgrade and downgrade on a copy of the DB (done for stages 1 and 2). Do not stamp production; let the deploy run `alembic upgrade head`.
3. Decide the backfill question (upsert versus lazy create) when Claude presents it.

## Done when

- Tests pass at each stage.
- Migration upgrade and downgrade verified on a DB copy.
- Issue checklists updated (#101, #103, #104, #105, #106).

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- Targets API, service, handlers, stats, dashboard view
- Real downgrade for 9b38fdc94e38

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: The backfill decision and the final shape of the Targets API (S15 builds on it).
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S12-pi-cleanup-performance.md`: E1 Pi cleanup and performance (#110).
