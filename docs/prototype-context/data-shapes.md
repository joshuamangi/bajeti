# Data shapes (fake data only)

Currency is shown as plain numbers today (the owner is in Kenya; default KES). Months are `"YYYY-MM"`.

## Existing (what the dashboard receives)
```json
{
  "user": {"first_name": "Amani", "last_name": "Demo"},
  "current_month": "October", "now": "2026-10",
  "budget_details": {"id": 1, "name": "Monthly", "type": "expense", "amount": 70000},
  "all_budgets": [
    {"id": 1, "name": "Monthly", "type": "expense", "amount": 70000},
    {"id": 2, "name": "Holiday Fund", "type": "savings", "amount": 45000}
  ],
  "total_expense_amount": 70000, "total_savings_amount": 45000,
  "budget_allocations": {
    "budget": {"id": 1, "name": "Monthly", "amount": 70000},
    "summary": {"total_allocated": 58860, "unallocated": 11140},
    "allocations": [{"allocation_id": 1, "category_id": 1, "category_name": "Rent", "allocated_amount": 25000}]
  },
  "categories_with_stats": [
    {"id": 1, "name": "Rent", "type": "expense", "allocated_amount": 25000, "used": 25000, "balance": 0,
     "expense_count": 1,
     "expenses": [{"id": 11, "amount": 25000, "month": "2026-10", "description": "October rent", "type": "spend"}],
     "transfers_in": [], "transfers_out": [], "total_transfers_in": 0, "total_transfers_out": 0,
     "target": null},
    {"id": 2, "name": "Groceries", "type": "expense", "allocated_amount": 12000, "used": 8450.5, "balance": 3549.5,
     "expense_count": 9, "expenses": [], "transfers_in": [], "transfers_out": [], "target": null},
    {"id": 3, "name": "Emergency Fund", "type": "savings", "allocated_amount": 20000, "used": 0, "balance": 20000,
     "expense_count": 0, "expenses": [], "transfers_in": [], "transfers_out": [],
     "target": {"id": 9,
       "short_term": {"amount": "30000.00", "percent": 66.7, "remaining": "10000.00"},
       "mid_term":   {"amount": "60000.00", "percent": 33.3, "remaining": "40000.00"},
       "long_term": null}}
  ],
  "target_totals": {"short_term": "30000.00", "mid_term": "60000.00", "long_term": "0"}
}
```
Expense `type` is `spend` or `withdrawal` (a withdrawal from a savings budget lowers its balance).

## Proposed (new screens; shapes are suggestions the design may change)
```json
{
  "analytics_month": {"month": "2026-10", "spent": 41230.5, "budgeted": 58860, "previous_month_spent": 44810,
    "by_category": [{"category": "Rent", "spent": 25000}, {"category": "Groceries", "spent": 8450.5}],
    "by_month": [{"month": "2026-08", "spent": 39100}, {"month": "2026-09", "spent": 44810}, {"month": "2026-10", "spent": 41230.5}]},
  "recurring": [{"id": 1, "name": "Rent", "amount": 25000, "category": "Rent", "every": "month", "day": 1,
    "next_due": "2026-11-01", "mode": "ask_first", "paused": false},
    {"id": 2, "name": "Internet", "amount": 3500, "category": "Utilities", "every": "month", "day": 15,
    "next_due": "2026-10-28", "mode": "auto", "paused": false}],
  "due_now": [{"recurring_id": 2, "name": "Internet", "amount": 3500, "due": "2026-10-28"}],
  "pending_payments": [{"id": 5, "source": "mpesa_sms", "received": "2026-10-26T12:40:00",
    "raw": "ABC123XYZ Confirmed. Ksh450.00 paid to Demo Grocer on 26/10/26 at 12:38 PM.",
    "parsed": {"amount": 450.0, "payee": "Demo Grocer", "reference": "ABC123XYZ"},
    "suggested_category": "Groceries", "status": "needs_category"}],
  "admin": {"users": [{"id": 1, "name": "Amani Demo", "created": "2026-03-01", "last_login": "2026-10-26"}],
    "registration_open": false, "backups": {"last": "2026-10-26T02:00", "ok": true},
    "system": {"app": "healthy", "db_mb": 4.2, "version": "2026.10"}}
}
```
