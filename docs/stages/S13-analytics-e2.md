# S13: E2 Analytics page (#111)

**Prompt:** P9  |  **Mode:** design-gate  |  **Depends on:** S12  |  **Suggested branch:** `feature/issue-111-analytics-page`

## Goal

Replace the Analytics stub with a drill-down: month totals, category breakdown, expense list, using ECharts.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. Expense routers and services (by-month and by-category-month endpoints), schema/expense.py
4. `app/templates` analytics stub, app handlers, esbuild config
5. `palette.css`, main.css, modal.css
6. `docs/design/` for any existing design notes

### Outputs of earlier stages this stage relies on

- S12 query and index work

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: design and build the Analytics page. Design first; wait for my approval before coding.

Behaviour: month totals (spend only, exclude withdrawals) -> click a month -> category breakdown -> click a category -> expense list. Charts with ECharts. Reuse /expenses/by-month and /expenses/by-category-month where possible.

Design deliverable (docs/design/analytics.md): endpoint list and JSON response shapes, SQL for each aggregation, indexes needed, the ECharts options for each drill-down level, mobile layout (iPhone width), empty/loading/error states, how ECharts is bundled (esbuild, pinned version, loaded only on this page), and how it stays fast on SQLite with several years of data.

Then implement in small PRs: API aggregations + tests (including cross-user), handler + template, charts. Follow the existing CSS conventions (palette tokens, 4px multiples, em, `p-` prefix). Hide-values toggle must also hide chart values.

Definition of done: works at 375px width, no new heavy dependencies beyond pinned ECharts, tests pass.
```

## Watch out for

- No code before you have approved the design.
- Hide-values mode must hide chart values and tooltips as well as the table.
- Check what any aggregation query costs on the Pi before building the page on it.

## Your part (Claude cannot or should not do these)

1. Approve docs/design/analytics.md before any coding.
2. Test at 375px width on your iPhone and check the hide-values toggle hides chart values.

## Done when

- Design approved; then API aggregations with cross-user tests, handler and template, charts in small PRs.
- Works at 375px; only pinned ECharts added as a dependency.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- docs/design/analytics.md
- Analytics endpoints, page and charts

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Response shapes and chart conventions reused by later screens.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S14-recurring-e3.md`: E3 Recurring expenses (#112).
