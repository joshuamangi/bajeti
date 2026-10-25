# S12: E1 Pi cleanup and performance (#110)

**Prompt:** P8  |  **Mode:** claude+human  |  **Depends on:** S05, S11  |  **Suggested branch:** `feature/issue-110-pi-cleanup-performance`

## Goal

Fix the spend-versus-withdrawal bug and N+1 queries, add indexes, and clean up what is filling the Pi.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. Budget service (get_budget_overview and fetch_current_budget) and its tests
4. Alembic migrations and docs/migrations.md
5. `docs/pi-inventory.md` (what the audit found about /var/log and Docker cache)
6. Makefile

### Outputs of earlier stages this stage relies on

- S05 rebuilt Pis (the /var/log and build-cache problems may already be gone)

## Before you start

- Check whether the rebuild already removed the 12 GB build cache and the 6 GB /var/log before spending time on them.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: produce a safe cleanup and performance plan, then implement the repo-side parts. Plan first.

Known: ~12 GB reclaimable Docker build cache on the Pi, /var/log is 6 GB with unknown cause, SD-card boot (reduce writes), N+1 queries in get_budget_overview, and the Expense.type == "spend" filter is commented out so withdrawals count as spending.

Do:
- Give me read-only diagnostic commands to run on the Pi to find what is filling /var/log (du, journalctl --disk-usage, largest files) and what to do for each likely cause. Do not delete anything automatically.
- Fix get_budget_overview: restore the spend-only filter (check whether any test or UI relied on the wrong behaviour), and replace the per-category loop with one grouped query. Add tests with both spend and withdrawal expenses.
- Add indexes that the main queries need (expenses by user_id+month+category_id, allocations by budget_id), as a migration with a real downgrade; show EXPLAIN QUERY PLAN before/after.
- Propose SQLite pragmas (WAL, synchronous=NORMAL, busy_timeout) with the SD-card trade-offs.
- Clean up: remove dead app/requests.py after confirming nothing imports it; simplify the confusing conditional in BudgetService.fetch_current_budget.

Definition of done: tests pass, query counts reduced (show numbers), and a Pi-side checklist for me to run.
```

## Watch out for

- Check the rebuilt Pi before cleaning anything. The 12 GB build cache and 6 GB /var/log may be gone already.
- Do not run prune commands from this stage. Claude gives diagnostics; you decide.
- SQLite pragma changes affect durability and SD-card wear. Apply one at a time.

## Your part (Claude cannot or should not do these)

1. Run the read-only diagnostic commands Claude gives you on the Pi, if the problem still exists, and report the results.
2. Approve the index migration and the SQLite pragma proposal; apply pragma changes carefully because of SD-card writes.

## Done when

- Tests with both spend and withdrawal expenses pass.
- Query counts reduced, with numbers shown.
- A Pi-side checklist for you.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- Grouped query fix
- Index migration with real downgrade
- Pragma proposal
- Removed dead app/requests.py

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Index and query changes that the analytics page (S13) will depend on.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S13-analytics-e2.md`: E2 Analytics page (#111).
