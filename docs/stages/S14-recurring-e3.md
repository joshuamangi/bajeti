# S14: E3 Recurring expenses (#112)

**Prompt:** P10  |  **Mode:** design-gate  |  **Depends on:** S10  |  **Suggested branch:** `feature/issue-112-recurring-expenses`

## Goal

Add recurring expenses computed at page load and approved with one tap, with all edge cases decided in the design first.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `models.py`, the expense service and router, schema/expense.py
4. `dashboard.html` (Quick Expense area) and the web handlers
5. Migration conventions in docs/migrations.md
6. `palette.css` and main.css

### Outputs of earlier stages this stage relies on

- S10 cross-user test pattern

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: design then implement recurring expenses. Design first and wait for approval.

Spec: RecurringExpense(name, amount Decimal, category_id, day_of_month, active, last_approved_month). API CRUD plus GET /due and POST /{id}/approve (creates a normal expense). A "Due" strip on the dashboard next to Quick Expense. No background scheduler; due items are computed on page load.

Design must resolve these edge cases explicitly with examples and tests:
- day_of_month = 29/30/31 in shorter months (clamp to last day, say so in the UI).
- Catch-up when the app was offline or the user skipped months (show each missed month separately? one combined item? recommend one and justify).
- Amount changed after earlier approvals (history must not change; the amount on the approved expense is the one stored).
- Pausing/ending a recurring item; deleting a category it points to (block or reassign).
- Approving twice (idempotent per month) and two browser tabs approving at once (unique constraint on recurring_id + month).
- Timezone: user is in Africa/Nairobi (UTC+3); decide where "today" comes from.
- Savings-type categories and withdrawals: out of scope unless I say otherwise.

Implement: migration (real downgrade), model, schema, service, router, tests with a cross-user test for every endpoint, handlers and the dashboard strip. Follow CSS conventions.
```

## Watch out for

- Settle the date edge cases (day 29 to 31, timezone, double approve) in the design with worked examples before any code.
- Approving must be idempotent. Test it from two tabs.

## Your part (Claude cannot or should not do these)

1. Approve the design's answers to the edge cases (day 29 to 31, catch-up, changed amounts, double approve, timezone).
2. Test on your iPhone, including approving twice from two tabs.

## Done when

- Edge cases settled in the design with examples and tests.
- Migration with real downgrade, model, schema, service, router, cross-user test for every endpoint, handlers and Due strip.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- docs/design/recurring-expenses.md
- Recurring expenses feature

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Any decision about savings-type categories you postponed.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S15-future-planning-e6.md`: E6 Future planning (#115), design only.
