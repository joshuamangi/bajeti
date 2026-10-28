# Analytics page: design

Status: approved by the owner on 2026-10-29.

The approved look and behaviour is Prototype A (`design/prototype-a/bajeti-prototype-a-evolve.html`, §5.7 of `PORT-GUIDE.md`). This note covers what the prototype does not: data, endpoints, queries and how the page is built.

## Decisions to approve

1. **Charts are plain HTML and SVG, not ECharts.** The original plan said ECharts. The prototype draws every chart by hand, and the port guide settled on that: no new dependency (ECharts is about 1 MB), nothing extra for the Pi to serve, and hiding values is simple because every number is ordinary text with the `sensitive` class. Every chart also has a table or list version.
2. **Monthly allocation snapshots, no backfill.** Today an allocation is one amount that applies to every month, so raising it would rewrite history. A new table stores each category's allocation per month from now on.
   - Spending totals (the month bars, the year view, the category's expenses) use the full history, because every expense already records its month.
   - Comparisons with an allocation ("% of allocation", "Over 4 of 6 months", "Room to spare", the month-by-month table) only count months that have a snapshot. Months before the migration show "No data" in those places.
3. **Months start in the current month and run back.** The month view opens on the current month; "next" is disabled there.

## Where spending belongs

An expense has a category, not a budget. A category is allocated to at most one budget of its type (the app only offers unallocated categories), so a budget's spending is the expenses of the categories allocated to it. Expense budgets count `spend`; savings budgets count `withdrawal`, and the wording changes to "Withdrawn".

## Data changes (one migration, reversible)

```
allocation_snapshots
  id            integer primary key
  budget_id     integer, FK budgets.id ON DELETE CASCADE
  category_id   integer, FK categories.id ON DELETE CASCADE
  month         string "YYYY-MM"
  amount        numeric
  unique (budget_id, category_id, month)
```

- Written by `AllocationService` on create, update and delete (delete writes 0 for the current month), and for the current month whenever the analytics or home endpoints find it missing. That way the first visit of a month records it even if nobody changed an allocation.
- The migration creates the table, writes the current month's snapshot from today's allocations, and adds two indexes: `expenses (user_id, month, category_id)` and `transfers (user_id, month)`. Downgrade drops the table and the indexes.

## Endpoints

All are `GET`, scoped by `user_id`. The budget and category are checked through `BudgetService.get_budget_by_id` and `CategoryService.get_category_by_id`, so another user's ids return 404 (cross-user test for each). Money is returned as strings with two decimals, from `Decimal`.

- `/api/analytics/month?budget_id&month=YYYY-MM`
  `{budget, month, spent, budgeted, used_pct, previous: {month, spent} | null, last6: [{month, spent, budgeted|null}], categories: [{id, name, spent, allocated|null, share_pct, alloc_pct|null}], changes: [{id, name, spent, previous, delta}] (top 3)}`
- `/api/analytics/trends?budget_id&end=YYYY-MM&months=6`
  `{months: [...], categories: [{id, name, cells: [{month, spent, allocated|null, transfers_in: {count, total}, transfers_out: {count, total}, active}]}], squeezed: [...], room_to_spare: [...], topped_up_most: [...], gave_most: [...]}`
- `/api/analytics/year?budget_id&year=YYYY`
  `{year, total, monthly_average, busiest: {month, spent}, months: [{month, spent}], categories: [{id, name, total, share_pct, monthly_average, allocated|null}]}`
- `/api/analytics/category/{category_id}?month=YYYY-MM`
  `{category, month, spent, previous_spent, year_total, year_average, last6: {over, months, top_ups}, year_months: [{month, spent, allocated|null}], expenses: [...]}`

The rules for "squeezed", "room to spare", "ended over" and the tips are the prototype's (`catMonth`, `squeezeRows`) and §9 of the port guide. They live in one pure Python module (`services/analytics_rules.py`) with unit tests that reproduce the prototype's examples.

## Queries

Each endpoint runs a fixed number of grouped queries, never one per category:

- spent per category per month: `SELECT category_id, month, SUM(amount), COUNT(*) FROM expenses WHERE user_id = ? AND type = ? AND category_id IN (...) AND month BETWEEN ? AND ? GROUP BY category_id, month`
- transfers in and out per category per month: the same shape on `transfers`, grouped by `to_category_id` and by `from_category_id`.
- snapshots for the months in range: one `SELECT` on `allocation_snapshots`.

Production holds about 600 expenses, so these take milliseconds even on the Pi. The two indexes keep them fast as years of data build up. I'll time them against a copy-sized test database before the page goes live.

## Page

- Server routes `/analytics` (redirects to the current month), `/analytics/<YYYY-MM>`, `/analytics/trends`, `/analytics/year/<YYYY>` and `/analytics/<YYYY-MM>/<category_id>`, each rendered by Jinja from one API call, inside the new app shell. Analytics is a tab in the bottom bar.
- Uses the active budget, with the "Showing" switcher at the top.
- States: empty ("No spending in October yet"), loading (skeleton bars) and error ("Couldn't load analytics", Try again).
- The hide-values toggle masks every amount, including the chart labels and tables; bar lengths stay, values do not.

## Order of work

1. Migration, snapshot writes and the rules module, with tests.
2. The four endpoints, with cross-user tests.
3. The pages, once the new app shell exists.
