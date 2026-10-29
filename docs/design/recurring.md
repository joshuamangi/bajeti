# Recurring expenses: design

Status: approved by the owner on 2026-10-29, monthly only (weekly and yearly removed for now).

Look and behaviour: Prototype A (`design/prototype-a/`, PORT-GUIDE §5.8 and the Due now cards in §5.2). This note settles the data and the edge cases the stage asks for.

## Decisions to approve

1. **Monthly only** (owner decision; weekly and yearly may come later). Each item stores its next due date; approving or skipping moves it on by one month.
2. **No background job.** Due items are worked out when a page loads. "Auto-add" items whose date has come are recorded then, the next time anyone opens the app. They appear in a "Recently added" list on the Recurring page (your decision: no push or email, log only).
3. **Expense budgets only.** Savings withdrawals stay out of scope, as the stage says. The category list in the form shows expense categories only.
4. **Deleting a category that has recurring items is blocked**, with the message "Gym has 2 recurring items. Delete or move them first." I recommend blocking over deleting them silently, because the items are your record of what you pay regularly.
5. **"Today" is Nairobi time** (UTC+3, no daylight saving), from a setting `APP_TIMEZONE_OFFSET_HOURS=3`. A bill due on the 1st shows as due at midnight in Nairobi, not at 3 am.

## Data (one migration, reversible)

```
recurring_expenses
  id, user_id, category_id (FK categories, no cascade: see decision 4)
  name, amount (Decimal)
  anchor_day      the day of the month it is due (1..31)
  next_due        date
  mode            ask_first | auto
  paused          bool
  created_at, updated_at

recurring_runs                       one row per due date that was handled
  id, recurring_id (FK, cascade), user_id, due_date
  action          approved | skipped | auto
  expense_id      nullable (the expense it created)
  amount          the amount used that time
  created_at
  unique (recurring_id, due_date)    stops double approval, also from two tabs
```

## Edge cases, with examples

- **Days 29 to 31.** Monthly items keep their anchor day and use the last day of shorter months. An item anchored on the 31st is due 31 Jan, 28 Feb (29 in a leap year), 31 Mar, 30 Apr. The form says "Due on the 31st, or the last day of shorter months" when the day is 29 or later.
- **Catch-up after missed periods.** One card per item, oldest due date first. Approving or skipping moves the item on by one period. If it is still due, the next card appears at once with its own date. I recommend this over one combined item: each payment belongs to its own month, so analytics stay right, and you can skip a month you did not actually pay. If an item is more than one period behind, the card says "3 payments overdue" and has **Approve all**, which records each one in its own month in one step.
- **Due now window.** Ask-first items show from 5 days before the due date (decision already made). Auto items are recorded on or after the due date only.
- **Amount changed later.** The expense stores the amount at the time it was approved, and `recurring_runs.amount` keeps it too. Editing the item changes future payments only.
- **Approving twice.** The unique (recurring_id, due_date) row is written in the same transaction as the expense. A second approval of the same date gets 409 and the page shows "Already recorded" with no second expense. Tested with two requests at once.
- **Pause and resume.** Paused items are never due. Resuming keeps `next_due`. If that date has passed, the card shows as overdue, so you choose to approve or skip.
- **Ending an item.** Delete it, with Undo. Past expenses stay.
- **Undo.** Undoing an approval deletes the expense and the run, and moves `next_due` back to that date. Undoing a skip removes the run and moves the date back.
- **Expense month.** The expense is recorded in the month of the due date, not the day you tap Approve. A bill due on 31 Oct and approved on 2 Nov counts in October.

## Endpoints (all scoped by user, each with a cross-user 404 test)

- `GET/POST /api/recurring`, `PUT/DELETE /api/recurring/{id}`, `POST /api/recurring/{id}/pause`, `/resume`
- `GET /api/recurring/due?budget_id` returns due ask-first items for the active budget, and records due auto items first.
- `POST /api/recurring/{id}/approve {due_date}`, `/skip {due_date}`, `/approve-all`, and `DELETE /api/recurring/{id}/runs/{due_date}` for Undo.

## Screens

- **Home:** the Due now cards (Skip, Approve), shown only when something is due. The More tab gets a red count of due items.
- **More → Recurring:** the budget switcher, "About X a month across n active items", the Due now cards, then the list (Ask first or Auto-add tag, next date or Paused, with Pause, Edit and Delete). Under it, "Recently added": the last 10 approvals, skips and auto-adds.
- **Form:** name, amount, category (expense categories of the active budget, A to Z), next due date (it repeats monthly), and mode as two radio cards.
