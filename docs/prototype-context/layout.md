# Layout and navigation

## Shell (templates/base.html)
`header` (sticky) -> `#pOverlay` -> `main {% block content %}` -> scripts. No footer, no bottom bar. Navigation is only the burger side drawer (Dashboard, Profile, Reports, Analytics, Settings, Logout). Reports and Settings are placeholders; Analytics says "Under Construction".

## Dashboard section order (templates/dashboard.html)
1. Alerts: missing security-question warning (amber), server error.
2. `.p-title-card`: `h1` "<Month>'s Budget", "Welcome, <name>", eye toggle (hide values).
3. Active budget: two summary cards (selected budget amount, total balance).
4. Budgets: header row with round "+" button; two columns, Savings and Expense, each a list of radio budget items with edit/delete and a "Total" pill; scrolls at 150px.
5. Categories: grid of category tiles (two columns, scrolls at 220px); tap opens a category modal (expenses, transfers, add expense, quick expense).
6. Desktop only: categories table with row actions.
7. Modals (hidden): budget modal (allocation summary, add category, allocations, targets), create/edit budget, add/edit category, category detail (progress, transfers, expenses), add expense, edit allocation, edit target, alert and confirm.
8. Toast `#pSnackBar`.

Pages outside the dashboard: login, register, forgot password, profile (security question, "log out everywhere"), reports (placeholder), settings (placeholder), analytics (placeholder).

## Hide-values toggle
Elements with `.sensitive` hold the real text; the eye button swaps them for `••••` (store the original in `data-value`/`data-orig`) and swaps `fa-eye` / `fa-eye-slash`. Default is visible. Every money amount in a prototype must be maskable.
