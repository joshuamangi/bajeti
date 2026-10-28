# Design tokens (source of truth: app/static/css/palette.css)

**Default theme is LIGHT.** `<body class="p-container light">` turns on `body.light`. The `:root` block is the dark set (used when `light` is removed). Today the page hard-codes `light` and there is no switch yet; the dark set already exists, so every prototype must work in both and should include a theme toggle. Colours are defined in HSL, then overridden with OKLCH where supported (values below are the HSL fallbacks).

## Colour tokens (dark `:root` -> light `body.light`)
| Token | Dark | Light | Use |
|---|---|---|---|
| --bg-dark | hsl(220 35% 5%) | hsl(210 40% 93%) | page background, inset panels, list wells |
| --bg | hsl(220 25% 8%) | hsl(210 40% 97%) | modal and card base |
| --bg-light | hsl(220 20% 12%) | hsl(210 40% 100%) | inputs, icon buttons, raised surfaces |
| --gradient / --gradient-hover | bg to bg-light vertical | same | card backgrounds |
| --text | hsl(210 40% 96%) | hsl(220 25% 10%) | headings, strong text |
| --text-muted | hsl(210 15% 70%) | hsl(220 10% 40%) | body text (body colour), captions |
| --highlight | hsl(180 20% 45%) | hsl(180 25% 45%) | table header text |
| --border / --border-muted | hsl(220 15% 25%) / (220 15% 15%) | hsl(220 15% 70%) / (220 25% 80%) | lines, bar tracks |
| --primary | hsl(190 80% 70%) | hsl(190 90% 35%) | main actions, links (teal/cyan) |
| --secondary | hsl(38 80% 65%) | hsl(40 85% 45%) | amounts spent, "zero" state (amber) |
| --tertiary | hsl(280 45% 65%) | hsl(280 45% 60%) | purple accent (transfers) |
| --success / --warning / --danger / --info | hsl(155 55% 55%) / (42 80% 60%) / (4 70% 60%) / (210 70% 65%) | 40-45% lightness versions | status |
| --text-100 ... --text-0 | text scale from near-white to near-black | reversed | extra greys |

Header bar is inverted on purpose: `header { background: var(--text); color: var(--bg) }` (dark bar in light theme, light bar in dark theme), with `--bg-light` logo and nav links.

## Type (font: Manrope, local woff2 weights 200-800, `font-display: swap`)
`--h1: 500 1.5rem/1.25`, `--h2: 500 1.25rem/1.4`, `--h3: 500 1.125rem/1.5`, `--h4: 500 1rem/1.5`, `--p: 400 .875rem/1.75`, `--small: 400 .75rem/1.6`, `--tiny: 400 .625rem/1.6`. Body text colour is `--text-muted`; h1-h4 use `--text`. Form text on mobile is forced to 16px (stops iOS zoom).

## Shadow, radius, spacing
- `--shadow: 0 2px 3px hsla(0,0%,0%,.25), 0 4px 6px hsla(0,0%,0%,.15)` (lighter in light theme).
- Radii in use: .2em (bars), .4em (buttons, cards, wells, inputs), .6em (budget items, toast), .75rem (modal), 4px (compact inputs), 50% (round add button).
- **Spacing rule: multiples of 4, written in `em`** (0.4em, 0.8em, 1.2em; 4px, 8px, 28px/32px controls). Existing code also uses 0.1em, 0.2em, 0.3em, 0.6em and a few rem values (see README, inconsistencies).
- Breakpoint: one, `768px` (below = phone layout with cards, above = table). Mobile first.

## Motion
.2s transforms on hover (scale 1.02-1.05), bars `width .4s ease`, modal `fadeIn .2s` + `slideUp .25s`, toast slide `.4s`, sidenav `.4s`.
# Components (real class names; copy the markup shapes)

All classes use the `p-` prefix. Show amounts with class `sensitive` so the hide-values toggle can mask them.

## Buttons
- Base `button`: `padding .4rem 1rem; background var(--primary); color var(--bg-light); border-radius .4em; box-shadow var(--shadow)`.
- Square action buttons (28-32px): `<button class="p-actions-btns p-actions-btns-primary"><i class="fa fa-plus"></i></button>`; colour variants `-secondary -warning -tertiary -danger -info` (1px coloured border + coloured icon on `--bg-light`).
- Small icon buttons in lists: `p-icon-btn-warning` (edit pencil), `p-icon-btn-danger` (trash), also `-primary -info -tertiary -secondary`; `3.2em x 2.4em`, `font-size .8em`.
- Wide modal buttons: `p-modal-btn-primary|secondary|tertiary|warning|danger` (100% width, `.8em`).
- Full-width call to action: `p-button-info`. Round add button: `p-budget-create-btn` (32px circle).

## Inputs (in modals and inline forms)
Inline rows use a grid, `grid-template-columns: 1fr 1fr 28px; gap: .5em`, 28px high inputs, `font-size: .8rem`, 1px `--border-muted`, 4px radius, a 28px `--primary` square submit button with `fa-add`. Modal inputs get `min-height 44px` and 16px text on phones.

## Cards
- Summary pair: `.p-summary-card > .p-summary-cards` (gradient, shadow, centred label + `h3.p-summary-value` in `--success`; negative values add `p-negative`).
- Category tile: `.p-category-item > .p-category-header (span.p-category-name + span.p-category-status ok|exceeded|zero) + .p-progress-wrapper (.p-progress-bar > .p-progress-fill p-ok-fill|p-exceeded-fill|p-zero-fill, span.p-progress-percent)`; two-column grid in `.p-category-progress-list`.
- Detail card (wide): `.p-detail-card`, 3-column grid, 0.4em coloured left border.
- Budget radio list: `.p-budget-item` (gradient, `.6em` radius) holding a custom round radio (`input[type=radio]` styled with `::before`), label, pencil and trash icon buttons; grouped under `.p-budget-title` ("Savings" / "Expense") with a `.p-budget-total` pill.

## Lists and wells
`.p-category-progress-ul` (no bullets, `--bg-dark` well, `.4em` radius) with `.p-category-progress-li` rows (flex or grid, `.8em` text, 1px bottom border). Scroll box: `max-height 200px; overflow-y auto; border 1px solid var(--border-muted); radius 6px`. Empty state: `.p-category-progress-no-content` (centred, `--bg-dark` well, `.8em`).

## Progress bars
`.p-progress-bar` (6px, track `--border-muted`) + `.p-progress-fill` (+ `p-ok-fill` green, `p-exceeded-fill` red, `p-zero-fill` amber). Status text `.p-category-status ok|exceeded|zero` (`.9em`).

## Modal
`.p-modal` (fixed overlay, `rgba(0,0,0,.5)` + blur) toggled by setting `display:flex`; `.p-modal-content` (90% wide, max 400px, `.75rem` radius, 1.5rem padding, max-height 90vh and scrolls); `a.p-close` top-right `fa-close`; title `h2|h3.p-modal-limit-name` (engraved pill); form body `.p-modal-form-content` (`--bg-dark` well, labels above inputs); sections separated by `.p-category-progress-transfer-divider` (1px top border) with an `h4` (.9em). Opened with `generateModal(modalId, closeId, closeBtnId)`.

## Toast (snackbar)
`#pSnackBar` fixed bottom-centre, pill `.6em`, text `--bg-light`, variants `.success .error .warning .info` (matching status colours), auto-hides after about 3s, slides up from below.

## Alerts
`.p-alert-warning` (amber banner with `fa-exclamation-triangle`, dismiss `×`) and `.p-alert-error`. Confirm dialog `#pConfirm` (`.p-confirm`, OK and Cancel `.p-btn`) via `confirmSubmit(form, message)`.

## Navigation
Sticky `header` (logo link "Bajeti" left, `fa-bars` right). The burger opens `.p-sidenav` (slides in from the right, 250px, links: Dashboard, Profile, Reports, Analytics; footer: Settings, Logout in `--danger`) over `.p-overlay`.

## Table (desktop, above 768px)
`table.p-table#categoriesTable`: header row text `--highlight`, rows with dashed bottom borders, action cells holding `p-actions-btns` (bolt = Quick Expense, plus = add expense, pencil, trash). Below 768px the table is hidden and the category tiles are used (rows can also turn into stacked label/value cards).

## Targets section (new, inside the budget modal, below Allocations)
Category select + add button, three amount inputs (Short / Mid / Long term), a 3-column totals card (`--bg-dark` well, label `.8em` muted, value `.9em` bold), then a list: per category, a name, edit and delete icon buttons, and one progress bar per term with "% . amount to go" or "Target reached".

## Icons
Font Awesome Free 6.4 (self-hosted). In use: bars, close, eye, eye-slash, pencil, trash, plus, add, bolt, undo, save, list, th-large, home, cog, sign-out, key, arrow-left, spinner, exclamation-circle, exclamation-triangle, wrench.
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
# Conventions

- **Naming:** every class starts with `p-` (BEM-ish, hyphenated: `p-category-progress-li`). A few legacy ids and classes are unprefixed (`tableView`, `categoriesTable`, `table-responsive`); do not copy them.
- **CSS:** vanilla, tokens only (no hard-coded colours), spacing multiples of 4 in `em`, no framework. Hand-written files per area (`main.css`, `modal.css`, `toast.css`, `home.css`, ...).
- **JS:** vanilla ES, no build-time framework (esbuild bundles files). Charts: Apache ECharts via a pinned version, planned for analytics.
- **Mobile first:** design at 375px; one breakpoint at 768px. Controls at least 44px high in modals on phones; inputs 16px text to stop iOS zoom; one-handed reach (primary actions in the lower half).
- **iPhone / PWA:** respect `env(safe-area-inset-*)` for the header, any bottom bar and the toast; `viewport-fit=cover`; the app will be installable (manifest, service worker for static files only, never cache signed-in pages or API responses).
- **Accessibility:** buttons need labels (`title` or `aria-label` for icon-only), visible focus, 4.5:1 contrast for text in both themes, status never by colour alone (text like "over" / "left"), modals trap focus and close on Escape and backdrop tap, respect `prefers-reduced-motion`.
- **Money:** shown with thousands separators, 0 or 2 decimals; never raw floats in labels; negative amounts use `--danger`, positive `--success`; currency symbol is not shown today (add one setting, default KES).
- **Months** are `YYYY-MM`. Every list needs default, empty, loading and error states.
- **Security of the data:** prototypes use fake names and amounts only.
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
# Product brief: redesign Bajeti as a progressive web app

Bajeti is a personal and household budgeting app (one household, a handful of users). Today it is a dashboard of budgets, categories, allocations, expenses, transfers and the new Targets. The redesign keeps the owner's visual language (see design-tokens.md) and turns it into an installable, phone-first PWA that feels professional and can grow.

## Goals
1. Phone first (iPhone 375px, one-handed), installable, with a calm, trustworthy, professional feel.
2. Add four capabilities that do not exist yet: **analytics**, **recurring expenses**, **payment capture**, **admin**.
3. A navigation model that scales (today there is only a burger drawer).
4. Keep the privacy feature: a hide-values eye toggle that masks every amount.

## Screens to cover
| Area | What it must do |
|---|---|
| Home / dashboard | This month's picture: budget total, balance, "due now" strip (recurring), pending payments badge, category tiles, quick expense, targets progress. Active budget switcher (Savings and Expense budgets). |
| Budgets and categories | Create/edit budgets, allocate to categories, targets (short/mid/long term) with progress and totals, transfers between categories. |
| Add expense | Fast: amount first, category chips, one-tap Quick Expense (adds the category's allocated amount). |
| **Analytics** | Month totals (spend only; withdrawals excluded), compare with last month, category breakdown for a month, trend over several months, drill-down month -> category -> expense list, budget vs actual, targets progress. Charts: Apache ECharts is planned; any chart must also have a readable table or list for accessibility. |
| **Recurring expenses** | List with next due date, create/edit/pause, per item mode "ask first" (appears in a "Due" strip with one-tap approve) or "auto-add". Frequencies: weekly, monthly, yearly. |
| **Payment capture** | M-Pesa SMS and payment emails become *pending payments*: a "paste message" box and an inbox where each item shows the parsed amount and payee and asks for a category (and optionally "remember this payee"). One tap to approve, swipe or button to dismiss. |
| **Admin** (grows over time) | Owner-only area with a section list that can take new sections: users (add household member, reset access), registration open/closed switch, backups status and last restore test, system health (app, database size, version), activity/audit log, feature switches, data export. Design it as a settings-style hub with cards that link to sub-pages, so adding a section later needs no redesign. |
| Account | Profile, security question, "log out everywhere", theme (light/dark), hide values default, currency setting. |
| Auth | Login, register (closed by default), forgot password. |

## PWA requirements the design must show
Bottom tab bar with 4-5 items plus a prominent add button, safe-area insets, install hint for iOS ("Add to Home Screen"), offline shell page, "update available" banner, pull-to-refresh feel without custom gestures, no reliance on hover.

## Two prototypes to generate
**Prototype A, "Evolve":** same dashboard-first structure the owner knows (title card, summary cards, budgets, category tiles), reorganised and polished, with a bottom tab bar (Home, Budgets, Add, Analytics, More). Admin, Recurring and Payments live under More. Lowest risk; closest to today's code.

**Prototype B, "Insight first":** home is a glanceable "month at a glance" (spend ring or bar versus budget, targets progress, due and pending items as a to-do stack) with analytics one swipe or tap away; budgets and categories sit one level down. Add button is a floating action. Admin is a hub reached from the profile menu. More opinionated; bolder.

Both: dark and light, 375px and 768px+ layouts, states default / empty / loading / error / values hidden, and the same data (data-shapes.md).

## Prompt to paste into Claude on the web (attach BAJETI-DESIGN-BRIEF.md)
> You are a senior product designer and front-end engineer. The attached brief is the source of truth for tokens, components, layout, conventions, data and product goals. Produce **Prototype A (Evolve)** as one self-contained HTML file with inline CSS and vanilla JS (no frameworks; ECharts only via a pinned CDN version if charts need it). Use the real tokens and `p-` class names; spacing multiples of 4 in `em`; light and dark themes with a toggle; iPhone 375px first, then 768px+. Cover the screens in the brief with clickable navigation between them, fake data from the data shapes only, and these states: default, empty, loading, error, values hidden. Mark new components with `/* NEW COMPONENT */`. When done list: (1) new tokens or classes, (2) what the backend must provide, (3) accessibility notes, (4) assumptions. Ask at most three clarifying questions first, only if something is truly ambiguous.
Then run the same prompt again with "Prototype B (Insight first)" and the B description above.
