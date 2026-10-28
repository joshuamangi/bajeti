# Bajeti: porting Prototype A ("Evolve") into the app

This guide tells Claude Code (in VS Code) how to rebuild Bajeti's UI to match **Prototype A** and add the new features shown in it: analytics, recurring expenses, payment capture, admin, and PWA support. Work through it **one stage at a time**.

- **Visual and behavioural spec:** `design/prototype-a/bajeti-prototype-a-evolve.html`, a single self-contained file. Open it in a browser and use the purple **CONTROLS** tab to see every state.
- **Design source of truth:** `BAJETI-DESIGN-BRIEF.md`, covering tokens, components, conventions and data shapes. Where this guide and the brief disagree, this guide wins, because it records decisions made after the brief.

---

## 1. How to set this up in the repo

1. Create `design/prototype-a/` and put three files in it:
   - `bajeti-prototype-a-evolve.html` (the prototype)
   - `PORT-GUIDE.md` (this file)
   - `BAJETI-DESIGN-BRIEF.md` (if it isn't already in the repo)
2. Add these lines to the repo's `CLAUDE.md`, so every session knows the rules:
   ```md
   ## UI redesign (Prototype A)
   - Spec: design/prototype-a/PORT-GUIDE.md and design/prototype-a/bajeti-prototype-a-evolve.html
   - The prototype is a reference, not code to paste. Keep Jinja + vanilla JS + esbuild; no frameworks.
   - Work one stage per branch. Plan first, then implement, then verify against the prototype at 375px and 1200px, light and dark.
   ```
3. Use one branch per stage, such as `ui/s16-1-tokens` and `ui/s16-2-shell`. Merge each stage before starting the next.
4. Start every stage in **plan mode** (Shift+Tab in Claude Code). Approve the plan, then let it implement.
5. Keep the prototype open in a browser next to the app. After each stage, compare them side by side at 375px wide (DevTools device toolbar, iPhone SE or 12/13 size) and at 1200px.

---

## 2. Ground rules for Claude Code

- **Never copy the prototype wholesale.** It's one file with fake data, a hash router and prototype-only controls. Port each piece into the right template, CSS file and JS module.
- **Do not port these prototype-only parts:**
  - `seed()`, `emptyData()` and the in-memory `S.data` (fake data)
  - `buildDev`, `syncDev` and every `.p-dev*` class (the CONTROLS panel)
  - `body.p-framed`, `.p-statusbar` and `#pScroll` framing (the iPhone frame)
  - the base64 `@font-face` blocks (use the existing self-hosted Manrope and Font Awesome 6.4)
  - the data-URI manifest
- **Stack stays the same:** server-rendered Jinja templates, vanilla ES modules bundled by esbuild, hand-written CSS per area. No CSS or JS framework. Charts are hand-built HTML/SVG, as in the prototype; ECharts is not needed.
- **Navigation:** each tab and screen is a real server URL (see §6). Sheets (modals), toasts, optimistic updates and Undo are progressive enhancement in JS that call JSON endpoints.
- **Tokens only:** no hard-coded colours. Spacing in multiples of 4, in `em`. Every class starts with `p-`. Mark new components with `/* NEW COMPONENT */`.
- **Money:** every amount gets the `sensitive` class and must be masked by the eye toggle. Use thousands separators and 0 or 2 decimals; category rows and the chart use whole numbers. The currency code is a separate small, muted `<span class="p-cur">KES</span>`.
- **Accessibility is part of done:**
  - 44px touch targets; 16px form text; `inputmode="decimal"` for amounts
  - visible focus; 4.5:1 contrast in both themes; status never shown by colour alone
  - sheets trap focus and close on Escape and backdrop tap
  - `prefers-reduced-motion` is respected; every chart has a table or list alternative
- **Security:** the service worker caches static files only. It never caches signed-in pages or API responses.
- **Fix the known CSS issues as you touch each area.** The brief's README lists 13 inconsistencies, including the `@import` chains, the duplicate hide-values logic and `window.onclick` modal handlers.

---

## 3. Where things live in the prototype

Open the HTML file and search for these names. The inlined CSS comes first, then the JS.

| Feature | Search for (JS) | Search for (CSS) |
|---|---|---|
| Tokens, light and dark | — | `:root{`, `:root.light,body.light` |
| Money formatting and masking | `function money`, `moneyText`, `plainMoney` | `.p-cur` |
| Category maths: available, used, status | `function catStats`, `statusText`, `budgetSummary` | — |
| Active budget scope | `scopeCats`, `scopeSavings`, `outWord`, `function scopeBar`, `setActiveBudget` | `.p-scope` |
| App shell, header, tab bar | `const APP=` (Prototype A), `renderRoute`, `updateChrome` | `.p-header`, `.p-tabbar`, `.p-tab-add-circle` |
| Home | `function homeA` | `.p-home`, `.p-title-card`, `.p-eye-toggle`, `.p-divider`, `.p-block` |
| Budget switcher | `function budgetSwitcher` | `.p-budget-switch`, `.p-switch-chip`, `.p-switch-radio` |
| Summary cards | `function summaryCards` | `.p-summary-card`, `.p-summary-cards` |
| Month bar with today marker | `function spendMeter` | `.p-meter`, `.p-today-mark`, `.p-pace` |
| Category bar chart | `function catBarList` | `.p-catbars`, `.p-catbar` |
| Categories table (768px+) | `function categoriesTable` | `.p-table`, `.p-table-wrap` |
| Due now cards | `function dueCard`, `dueStrip`, `dueNow` | `.p-due-list`, `.p-due-card` |
| Pending payments row | `function pendingRow` | `.p-pending-row` |
| Sheets (modals) | `openSheet`, `paintSheet`, `closeSheet`, `FOCUSABLE`, `confirmSheet` | `.p-modal`, `.p-modal-content`, `.p-sheet-grip` |
| Toast with Undo | `function toast` | `#pSnackBar`, `.p-toast-undo` |
| Add expense | `function openAddExpense`, `FORMS.pAddForm`, `recentCategories`, `catChip`, `quickExpense` | `.p-amount-field`, `.p-letters`, `.p-letter`, `.p-chips`, `.p-chip` |
| Category sheet | `function categorySheet`, `expList` | `.p-cat-sheet-top` |
| Budgets tab | `function budgetsA`, `budgetColumns`, `allocBar`, `transfersSection` | `.p-budget-*`, `.p-alloc-bar`, `.p-legend` |
| Allocations and targets sheet | `function budgetManage`, `targetItem`, `targetTotals`, `FORMS.pTargetForm` | `.p-target-*`, `.p-inline-row` |
| Transfers | `function openTransfer`, `FORMS.pTransferForm` | — |
| Analytics: Month | `function analyticsView`, `trendChart`, `breakdownRow` | `.p-stat-grid`, `.p-trend-*`, `.p-breakdown*` |
| Analytics: 6 months | `function trendsView`, `squeezeRows`, `catMonth`, `heatCell` | `.p-period`, `.p-insight*`, `.p-heat*`, `.p-two` |
| Analytics: Year | `function yearView` | `.p-year-*` |
| Analytics: category detail | `function analyticsCategory` | `.p-crumbs` |
| Recurring | `function recurringView`, `recRow`, `openRecurringForm`, `approveDue`, `skipDue` | `.p-rec-*` |
| Payment capture | `function parseMessage`, `suggestCategory`, `capturePayment`, `payCard`, `paymentsInner` | `.p-paste`, `.p-parse-preview`, `.p-pay-*`, `.p-swipeable` |
| Admin hub | `ADMIN_SECTIONS`, `adminHub`, `adminSection` and `admin*` renderers | `.p-admin-*`, `.p-kv`, `.p-log` |
| Account | `function accountView` | `.p-pref-row`, `.p-segmented`, `.p-switch` |
| Auth and offline shell | `loginView`, `registerView`, `forgotView`, `offlineView` | `.p-auth*` |
| Banners and install hint | `bannersHtml`, `installHtml`, `setOnline` | `.p-banner*`, `.p-install*` |
| Empty, loading, error states | `emptyBox`, `skeleton`, `errorState`, `featureOff` | `.p-empty`, `.p-skel*`, `.p-state-error` |
| More page | `function moreA` | `.p-list`, `.p-list-row` |

---

## 4. Design tokens: changes to `palette.css`

Add or adjust these tokens. The **dark set is `:root`** and the **light set is `body.light`** (light is the default), as today. Values marked *adjusted* keep their names; they were moved only to reach 4.5:1 text contrast.

| Token | Dark (`:root`) | Light (`body.light`) | Note |
|---|---|---|---|
| `--primary-ink` | `hsl(190 80% 70%)` | `hsl(190 90% 27%)` | **New.** Primary colour for text and filled buttons (5.3:1 on white). Keep `--primary` for fills and decoration. |
| `--highlight` | `hsl(180 25% 62%)` | `hsl(180 35% 28%)` | adjusted |
| `--border-muted` | `hsl(220 15% 18%)` | `hsl(220 25% 84%)` | adjusted, so bar tracks show |
| `--secondary` | unchanged | `hsl(40 85% 32%)` | adjusted |
| `--tertiary` | `hsl(280 45% 72%)` | `hsl(280 45% 45%)` | adjusted |
| `--success` | unchanged | `hsl(155 60% 28%)` | adjusted |
| `--warning` | unchanged | `hsl(36 90% 32%)` | adjusted |
| `--danger` | `hsl(4 70% 64%)` | `hsl(4 70% 42%)` | adjusted |
| `--info` | `hsl(210 70% 68%)` | `hsl(210 70% 40%)` | adjusted |
| `--text-muted` | unchanged | `hsl(220 10% 38%)` | adjusted |
| `--shadow-inset` | `inset 0 1px 3px hsla(0,0%,0%,.35)` | `inset 0 1px 3px hsla(220,25%,10%,.18)` | **New.** Engraved title pill |
| `--scrim` | `hsla(220,35%,5%,.6)` | `hsla(220,25%,10%,.45)` | **New.** Replaces `rgba(0,0,0,.5)` |
| `--tint` | `hsla(190,80%,70%,.14)` | `hsla(190,90%,35%,.1)` | **New.** Soft selected background |
| `--space-1`…`--space-6` | `.4em .8em 1.2em 1.6em 2em 2.4em` | same | **New** |
| `--r-bar --r --r-item --r-modal` | `.2em .4em .6em .75rem` | same | **New** names for radii already in use |
| `--tap` | `44px` | same | **New.** Minimum touch target |
| `--tabbar-h` | `4em` | same | **New** |
| `--safe-top/bottom/left/right` | `env(safe-area-inset-*, 0px)` | same | **New** |

There is one breakpoint, **768px**. The prototype uses a container query (`@container app`) only so the phone frame works; the app should use `@media (min-width: 768px)`.

---

## 5. Screen-by-screen behaviour spec

Write each item as an acceptance test. **"Active budget"** means the budget the user last selected. It is stored on the server per user, so it survives reloads and devices.

### 5.1 App shell

- **Header:** sticky and inverted (`--text` background), with the "Bajeti" logo (Manrope 500, 1.75rem). On the right: a refresh button whose label includes the last-updated time, and the eye toggle.
  - On Home, the header eye is hidden because the title card has its own.
  - On sub-pages, the left side shows a back arrow and the page title.
- **Tab bar** (bottom, fixed, safe-area padded): Home, Budgets, **Add** (a raised round button that opens the Add expense sheet), Analytics, More.
  - More shows a red badge with the number of due bills plus pending payments; its aria-label states the count.
  - At 768px and above the tab bar becomes a left rail.
- **Banners** go below the header: offline (amber edge), syncing (blue edge), and "A new version is ready · Reload" (primary edge).
- **Install hint:**
  - iOS Safari (not standalone): "Tap Share, then Add to Home Screen".
  - Android and desktop: an Install button that uses `beforeinstallprompt`.
  - It shows on Home only and stays dismissed once dismissed.
- **Toast:** sits above the tab bar. Undo toasts last 6 seconds; others 3.5. Status is shown by an icon plus words.
- **Sheets:**
  - bottom sheet on phones, centred dialog at 768px and above
  - grip, title pill (`.p-modal-limit-name`) and a 44px close button
  - focus trap, Escape and backdrop tap to close; focus returns to the button that opened it
  - replaces `generateModal`

### 5.2 Home (in this order)

1. **Title card:** "‹Month›'s Budget", "Welcome, ‹first› ‹last›", and the outlined square eye toggle (2px `--primary-ink` border), which masks every amount in the app.
2. **Security-question warning:** amber, dismissible, only shown if the question isn't set.
3. **Active** section, headed "Active" with an "All budgets" link:
   - **Budget switcher:** horizontally scrolling chips, all the same height. Each has a round radio dot, the name and the type (EXPENSE or SAVINGS).
   - **Summary cards:** "‹Name› Budget" with "‹n› unallocated" underneath, and "Total Balance" with "‹n› spent". For savings budgets: "Savings Budget" and "Total Saved" with "‹n› withdrawn".
   - **Month bar:**
     - "Spent this month" and a %, a 10px bar, and a 2px **today marker** at day ÷ days-in-month.
     - Foot: "‹used› of ‹allocated›" and "Today, day 27 of 31".
     - Pace in words: **On track**, **Ahead of the month** (used% > month% + 5) or **Over budget**.
     - Savings budgets show "Withdrawn this month" with no marker and no pace.
4. Thick grey **divider** (`.p-divider`, from the live app).
5. **Pending payments row**, only if any: "3 payments waiting for a category", linking to Payments.
6. **Due now**, only if any: full-width cards with name, amount, "Category · Frequency · date", a tag (clock icon plus "Due tomorrow", "Due in 5 days" or "2 days overdue"), and **Skip** / **Approve** buttons. "Manage" links to Recurring.
7. Divider (only if 5 or 6 rendered).
8. **Categories**, with a sliders icon button (opens Allocations & targets) and a "+ Category" button:
   - **Phone: category bar chart.** One slim row per category: name, % used, and status text ("4,050 left", "Fully used" or "450 over" with a warning icon), plus a 6px bar.
   - **Sorted most used first:** exceeded categories first, then % used, highest first.
   - Shows the top 8, then a "Show all N categories" toggle. Tapping a row opens the category sheet.
   - **768px and above:** the categories table instead, with columns Category, Available, Used, Balance, Status and actions (bolt Quick Expense, + Add, pencil, trash).
9. **Recent:** the last 5 expenses in the active budget, and a "See all" link to Analytics. At 768px and above, Targets and Recent move to a right-hand column.

### 5.3 Add expense sheet

Opened from the tab bar, a category row, or a table action.

1. **Budget switcher** (only if there's more than one budget). Switching here changes the active budget **app-wide** and **keeps the typed amount and note**.
2. **Amount first:** a large centred field with a small "KES" prefix, `inputmode="decimal"`, autofocused.
3. **Category**, listing **only the active budget's categories, A–Z**:
   - **Letter filter** (when there are 2 or more categories): an "All" button spanning two columns plus **only the letters categories start with**, each 44px.
     - Tapping a letter filters the list; tapping it again, or "All", clears the filter.
     - If exactly one category matches, it is **picked automatically** and a line says "Picked Rent".
   - **Recently used:** the 4 categories with the most recent expense dates. Shown only when no letter is active and the sheet wasn't opened from a category. A category picked here is also shown as picked in the A–Z list.
   - Each chip shows its name and status ("2,100 left", "450 over", "20,000 saved").
4. **Type: Withdrawal / Spend**, only when a savings category is picked; Withdrawal is the default.
5. Note and date (max today).
6. **Quick Expense**, which adds the category's full allocation, and the **Add expense** button.

Saving is optimistic: totals, bars and the chart update immediately. A toast says "Added KES 1,234.50 to Groceries · Undo". When offline, the expense is queued with a "Pending sync" chip (see Stage 12).

### 5.4 Category sheet

- Remaining or Saved amount (large), "% used" in status colour with the word "over" when exceeded, and "of ‹available›".
- Progress bar.
- Quick Expense and Add Expense buttons.
- Transfers this month: "From X +500" or "To Y −500".
- Expenses list with edit and delete (delete gives an Undo toast).
- Targets, if set.
- Footer buttons: Top up, Edit, Delete.

### 5.5 Budgets tab

> **Targets already exist in the app (stage S11) and win over the prototype.** The prototype's Targets card, list and sheet were drawn from the brief, before Targets shipped. When porting, keep the app's real behaviour:
> - `POST /api/targets` is an **upsert** (201 when new, 200 when updated); there is one Target per budget x category with short, mid and long amounts (Decimal, two decimals).
> - Progress is measured against the **category balance** (`target` on the category stats, from `services/target_progress.py`), not a separate saved total.
> - The dashboard already has a Targets section with per-term totals (0 when empty). Reuse its markup and styles, then restyle it to the prototype.

- Title row with a **"+ New budget"** button.
- Savings and Expense columns of radio budget items (the existing component) with "Total:" pills. Each item shows "amount · n categories · active", plus sliders, pencil and trash buttons.
- An allocations card for the active budget: a stacked allocation bar with a legend, then **+ Category** and **Manage** buttons underneath.
- A "Transfers in ‹Month›" card with a **Move money** button (from Unallocated or a category, to a category; validates the available amount).
- A Targets card.
- **Allocations & targets sheet** (`budgetManage`):
  - a 3-column summary: Budget, Allocated, Unallocated
  - an over-allocation warning
  - an inline add-category row
  - the allocations list with edit and delete
  - a targets form (category plus Short, Mid and Long) and the targets list with progress per term ("66.7% · 10,000 to go" or "Target reached")
- **Creating a budget** opens its allocations sheet straight away. The type can't change after creation. For the "Monthly" budget, only the amount is editable.

### 5.6 Active budget scope (applies everywhere)

The active budget drives Home, the Add expense categories, Analytics, the Recurring list and form, Due now, and the category choices in Payments.

- **Payments inbox stays global:** money left the account either way. Only the "file it under" choices follow the active budget, and the screen says **"File payments into"** above a switcher.
- **Budgets tab** always lists every budget.
- **Opening a category from another budget** switches the active budget to that category's budget.
- **Screens with a scope bar** ("Showing" plus switcher, `scopeBar`): Analytics, Recurring, Payments and the Add expense sheet.
- **Savings budgets count withdrawals** in place of spending. The wording changes to "Withdrawn" and "Left in budget", with no pace and no daily allowance.

### 5.7 Analytics

A period switch at the top: **Month | 6 months | Year**. These are sibling views with no back arrow between them.

**Month** (`/analytics/2026-10`):
- Previous and next month arrows (next is disabled for the current month).
- Three stats:
  - "Spent · ‹Budget›" with a note that only this budget's spending is counted
  - "Budgeted" with % used and left or over
  - "vs ‹previous month›": ±% in words with an arrow. Show **neutral "No data"** when the previous month has nothing.
- **Spending by month:** the last 6 months as tappable bars, a dashed budget line and a **Show as table** disclosure.
- **Budget vs actual:** one row per category with spent, a bar, "% of spending" and "% of allocation · over". Tapping a row drills down.
- **Biggest changes vs last month** (top 3) and Targets progress.

**6 months** (`/analytics/trends`), ending this month:
- **Squeezed categories:** categories whose spending exceeded the allocation in 2 or more of the last 6 months.
  - Sorted by months over, then top-ups, then average %.
  - Each shows a red tag "Over 4 of 6 months" and "Averages X against Y (Z%)".
  - It also shows "topped up n times with A" (or "never topped up") and "ended over k times" (spending still exceeded allocation + transfers in − transfers out).
  - **Tip:** if the average rounded up to 100 is above the allocation, show "Consider allocating about ‹that›"; otherwise "The average fits; the overruns are one-off months".
- **Room to spare:** categories with 4 or more active months and an average under 60%, plus how much they gave to other categories.
- **Month by month:** a real `<table>` (accessible as-is) with categories as rows and months as columns, each cell showing **% of allocation used**:
  - over 100%: red tint, bold, caret-up icon
  - 90–99%: amber tint
  - exactly 100%: neutral, because fixed bills landing on plan are not a warning
  - a purple "+" in the corner when topped up that month
  - no activity: a dashed "–"
  - a visually hidden text per cell, e.g. "112% used, over allocation, topped up 1 time"
  - a key below the table; tapping a category name opens its detail
- **Transfers:** "Topped up most" (count and total in) beside "Money moved from" (count and total out).

**Year** (`/analytics/year/2026`):
- Year arrows.
- Stats: total so far (whole numbers), monthly average (total ÷ months elapsed) and busiest month.
- **By category:** rows sorted by year total, each with share of the year %, a bar relative to the biggest category, and "Average X a month · allocation Y". Tapping a row opens its detail.

**Category detail** (`/analytics/2026-10/<category_id>`):
- A breadcrumb back to the month.
- Stats: this month (with ± vs last month), "2026 so far" with its monthly average, and "Last 6 months: Over n of m" (red when 2 or more) with its top-ups.
- A year chart from January to the current month (compact bars, value shown on the selected month only, budget line).
- The expenses list.

### 5.8 Recurring (More → Recurring)

- Scope bar, then a "New" button and "About X a month across n active items".
- The **Due now** cards. "Ask first" items appear when due within **5 days**; approving records the expense **on its due date** and advances `next_due`, with Undo; Skip advances without recording.
- The list:
  - each row: name, "amount · Frequency · Category", and "Next: date (Due in n days)" or "Paused"
  - a mode tag: **Ask first** (hand icon) or **Auto-add** (bolt icon)
  - Pause/Resume, Edit and Delete buttons
  - sorted with paused items last, then by due date
- **Form fields:** name, amount, category (active budget, A–Z), repeats (Weekly, Monthly, Yearly), next due, and mode as radio cards.

### 5.9 Payment capture (More → Payments)

- **Paste box:** "Paste a payment message", plus "Try a sample" and **Read message**. Parsing shows a 3-column preview (Amount, Payee, Reference) and adds the payment to the inbox.
- **Duplicates are rejected by reference:** "Already captured: reference X…".
- **Inbox cards** (scope bar "File payments into" above):
  - source icon (SMS or email) and received time; amount; payee; "Ref … · paid date"
  - an "Original message" disclosure, hidden while values are hidden
  - a category select labelled "Category in ‹Budget›" with a **Suggested** tag
  - "Remember ‹payee› for next time"
  - **Dismiss** and **Approve** buttons; swiping left also dismisses; both give an Undo toast
- **Parser rules** (port to Python and unit-test them):
  - amount: `Ksh|KES|KShs` plus number
  - reference: the leading 8–12 character alphanumeric code, or "Reference: X"
  - payee: the text after "paid to", "sent to" or "payment to"
  - date: `dd/mm/yy`
- **Category suggestion:** a remembered payee rule first, then keywords (grocer/supermarket → Groceries, pharm/clinic → Health, fuel/matatu → Transport, power/water/internet → Utilities, cinema/stream → Entertainment), limited to the active budget.

### 5.10 Admin (More → Admin; owner only)

> **Deferred.** The app has no owner or role concept, so Admin needs a new model and a separate decision. It is parked in `docs/backlog.md` ("Admin area"). Do not build it in the first pass; keep the More page free of an Admin link until then. Account (§5.11) and the existing registration setting are unaffected.

- A hub of cards defined by a **registry** (`ADMIN_SECTIONS`), so a new section is one entry and needs no redesign: icon, title, description, a live status tag and a link to its sub-page.
- A dashed "Room for more" placeholder card.
- **Sections:**
  - Users: add a member with a 24-hour invite link; reset access; remove with Undo
  - Registration: an open/closed switch that shows On/Off text, with a warning while open
  - Backups: last backup, status, size and last restore test (warn after 30 days), with "Record restore test" and "Back up now"
  - System health: app, database size, version, uptime, service worker and connection
  - Activity log: filters All, Money, Access and Admin
  - Feature switches: Analytics, Recurring, Payments and Targets; turning one off hides it for everyone and deletes nothing
  - Data export: CSV and JSON
- Members see an "Owner only" empty state.

### 5.11 Account (More → Account)

- Profile card: avatar initials, name, email and role tag.
- Security: security question (Set or Missing tag), change password, and "Log out everywhere" (the only confirm dialog; everything else uses Undo).
- Preferences: theme segmented control (Light/Dark), "Hide amounts when the app opens" switch, and currency (KES or None).
- App: Install Bajeti, Check for updates.
- A Log out button.

### 5.12 Auth and states

- **Auth pages:** login (with a show-password toggle), register (shows "Registration is closed" when closed), and forgot password in 2 steps (email, then security question with a new password).
- **Every list needs four states:** default, **empty** (icon, title, one sentence, primary action), **loading** (skeleton shimmer) and **error** ("Couldn't load X", Try again, error code and time).
- **Feature switched off:** show the "‹Feature› is switched off" empty state with a link for the owner.

---

## 6. Backend work implied

The repo is **FastAPI + SQLAlchemy + Alembic + SQLite**. The JSON API is `routers/` -> `services/` (classes of static methods) -> `data/db/models/models.py`, validated by `schema/`. The web layer is `app/routers/requests_router.py` -> `app/handlers/` -> `app/services/` (httpx calls to the API) -> Jinja templates. Every query is scoped by `user_id`, and every new endpoint needs a test that a second user gets 404. See the repo's `CLAUDE.md`.

### Model changes

| Change | Why |
|---|---|
| `user.active_budget_id` | Active budget scope that persists across devices |
| **Monthly allocation snapshot** (`category_id, month, amount`), written when a month starts and whenever an allocation changes | The 6-month and Year views must compare each month against **that month's** allocation. Without it, raising an allocation rewrites history. |
| `transfer.month` (or derive it from the date) and `transfer.note` | Top-up counts and totals per month |
| `expense.type` (`spend` or `withdrawal`; this already exists), `expense.client_id` (unique, for idempotent offline sync), `expense.ref` (payment reference) | Offline queue; duplicate-capture check |
| `deleted_at` on budget, category, expense, recurring and user | Undo instead of confirm dialogs (soft delete, purge later) |
| `recurring` (name, amount, category_id, every, next_due, mode `ask_first`/`auto`, paused) | Recurring expenses |
| `pending_payment` (source, received, raw, amount, payee, reference, suggested_category_id, status) and `payee_rule` (payee → category_id) | Payment capture |
| `activity_log` (at, kind `money`/`access`/`admin`, user_id, text, amount) | Admin activity log |
| `feature_flag` (key, enabled); `setting` (registration_open, currency); `user.hide_amounts_default`, `user.theme` | Admin and Account |

### Endpoints (JSON, used by the JS)

- **Budgets:**
  - `POST /api/active-budget {budget_id}`
  - budget and category create, read, update and delete, each delete returning an id usable by `POST /api/undo/<kind>/<id>`
- **Expenses and transfers:**
  - `POST /api/expenses {category_id, amount, date, note, type, client_id}`
  - `PATCH` and `DELETE /api/expenses/<id>`
  - `POST /api/quick-expense {category_id}`
  - `POST /api/transfers {from|"unallocated", to, amount, note}`
  - `PUT /api/categories/<id>/target {short, mid, long}`
- **Home:** `GET /api/home` returns the active budget summary, category stats (available, used, balance, pct, status), due now, the pending payments count and the 5 most recent expenses. It can be server-rendered on first load.
- **Analytics** (do the maths in Python and unit-test it; the prototype's `catMonth` and `squeezeRows` are the reference):
  - `GET /api/analytics/month?budget_id&month`
  - `GET /api/analytics/trends?budget_id&end=YYYY-MM&months=6` returns, per category and month: spent, allocated (from the snapshot), transfers in (count, total), transfers out (count, total) and active; plus the squeezed, room-to-spare and transfer rankings.
  - `GET /api/analytics/year?budget_id&year`
  - `GET /api/analytics/category/<id>?month`
- **Recurring:** create, read, update and delete; `POST /api/recurring/<id>/approve` and `/skip`; a scheduled job for `auto` items.
- **Payments:**
  - `POST /api/payments/capture {raw}` (server-side parse, 409 on a duplicate reference)
  - `POST /api/payments/<id>/approve {category_id, remember}`
  - `POST /api/payments/<id>/dismiss`
- **Admin:** users (invite, reset, remove), registration, backups (status, run, record restore test), system health, the activity log (filtered and paginated), feature flags and export.
- **Account:** set security question, change password, log out everywhere (revoke all sessions), preferences.

---

## 7. Stages

Do these in order. Each stage ends with the app working and deployable.

| # | Stage | Main output | Done when |
|---|---|---|---|
| 0 | **Survey and map** (no app code) | `design/prototype-a/PORT-MAP.md`: each prototype component → the existing template, CSS or JS file it replaces or the new file it needs; list of affected routes; risks | The map is reviewed and agreed |
| 1 | **Tokens and base CSS** | `palette.css` per §4; a shared utilities file (`p-negative`, `p-positive`, `d-none`, `p-visually-hidden`, `p-cur`); remove `@import` chains; one hide-values module | Both themes pass 4.5:1; no visual regressions on today's pages |
| 2 | **App shell** | Header, tab bar or rail, safe areas, `viewport-fit=cover`, banners container, toast with Undo, the **sheet** component (replacing `generateModal`), the More page, a theme toggle | Every existing page opens inside the new shell; sheets trap focus and close on Escape and backdrop tap |
| 3 | **Home** | §5.2 complete, with server-persisted active budget, month bar and category chart (table at 768px+); hide Due and Pending until their stages ship | Matches the prototype at 375px and 1200px in light and dark; eye masks all amounts |
| 4 | **Add expense and category sheet** | §5.3 and §5.4, with optimistic save and Undo | Add, Quick Expense, letter filter, Recent and savings withdrawal all work; totals update without reload |
| 5 | **Budgets tab** | §5.5, including the Allocations & targets sheet, transfers and targets | Every budget, category, target and transfer action works with Undo where safe |
| 6 | **Active budget scope** | §5.6 across all screens built so far | Switching budget anywhere updates every screen; payments stay global |
| 7 | **Analytics** | Allocation snapshot migration plus backfill (current allocations for past months); §5.7 Month, 6 months, Year and category detail; unit tests for the trends maths | Test fixtures reproduce the prototype's insights (Eating out over 5 of 6, and so on) |
| 8 | **Recurring** | Model, job, §5.8, and Due now on Home | Approve and Skip with Undo; auto items get added by the job |
| 9 | **Payment capture** | Parser with tests, §5.9, and the pending row on Home | Samples in the prototype (`SAMPLES`) parse correctly; duplicates are rejected |
| 10 | **Admin hub** (deferred, see backlog) | Registry-driven hub plus the §5.10 sections, owner-only | A new section can be added by registering one entry |
| 11 | **Account and auth** | §5.11 and §5.12 | Preferences persist; log out everywhere revokes sessions |
| 12 | **PWA** | `manifest.webmanifest`, icons, a service worker (static files cache-first, an offline shell page for failed navigations, never caching HTML or API), update banner (waiting worker plus `skipWaiting` on Reload), install hints; **offline expense queue** in IndexedDB keyed by `client_id`, flushed on `online` | Installable on Android and desktop; iOS hint shows in Safari; adding an expense offline shows "Pending sync" and clears when back online with no duplicates |
| 13 | **Accessibility and QA pass** | §8 checklist across every screen | All boxes ticked; Lighthouse PWA and accessibility scores reviewed |

---

### Mapping to the repo's S-stages

The repo tracks work in `docs/stages/IMPLEMENTATION.md` (S00 to S18), not in the numbers above. Use these labels in branches and handoffs:

| This guide | Repo stage | Note |
|---|---|---|
| 0 to 6, 11, 13 | **S16** (E5 PWA), split into sub-stages `S16-0` ... `S16-n` | UI port: survey, tokens, shell, home, add expense, budgets, scope, account, QA |
| 7 Analytics | **S13** (E2) | S16 is listed as depending on S13; agree with the owner whether the shell can come first |
| 8 Recurring | **S14** (E3) | |
| 9 Payment capture | **S17** (E4) | |
| 10 Admin | backlog, no stage yet | needs an owner/role model |
| 12 PWA | **S16** | |

One stage per branch, `feature/issue-N-short-name`, and nothing is marked `done` without the owner's confirmation.

---

## 8. Checklist (every stage, every screen touched)

- [ ] Matches the prototype at **375px** and **1200px**, in **light** and **dark**
- [ ] Eye toggle masks **every** amount, including inputs when not focused; screen readers hear "hidden amount"
- [ ] Touch targets of 44px or more; form text 16px; amounts use `inputmode="decimal"`
- [ ] Visible focus; tab order makes sense; sheets trap focus, close on Escape and backdrop tap, and return focus
- [ ] Status shown by words or icons as well as colour ("left", "over", "Fully used", caret icons)
- [ ] Text contrast 4.5:1 in both themes
- [ ] Empty, loading and error states exist for every list
- [ ] Destructive actions use Undo toasts; only "Log out everywhere" confirms
- [ ] `prefers-reduced-motion` respected
- [ ] No hard-coded colours; spacing in multiples of 4 (em); all classes `p-` prefixed; new components marked `/* NEW COMPONENT */`
- [ ] No hover-only behaviour
- [ ] No console errors; existing tests pass; new logic has tests

---

## 9. Decisions already made

These were settled while building the prototype; don't reopen them without asking.

- Quick Expense adds the category's **full allocation**.
- Due now covers **ask-first** items due within **5 days**; approving records the expense on the **due date**.
- Home order: Active → payments and due bills → Categories → Recent.
- The category chart is sorted **most used first** and shows the top 8, with "Show all".
- Category rows, the chart and year totals use **whole numbers**; detail views keep 2 decimals.
- The letter filter appears whenever the active budget has **2 or more** categories (owner decision 2026-10-28; the prototype used more than 8), and shows only letters in use. "Recently used" still appears only past 8.
- The **active budget** scopes everything except the payments inbox and the Budgets list.
- Savings budgets count **withdrawals**; expense budgets count **spend**.
- "Squeezed" means spent above allocation in **2 or more of 6** months. "Room to spare" means an average under **60%** with 4 or more active months. Amber means 90–99%; exactly 100% is neutral.
- Charts are plain HTML/SVG with a table or list alternative. ECharts is not needed.

**Owner decisions (2026-10-28), previously open:**
1. **Offline read-only view:** keep the last Home data in **IndexedDB on the device** and clear it on logout (and on "Log out everywhere"). The service worker still never caches HTML or API responses.
2. **Allocation snapshots:** **no backfill.** Analytics starts from the migration date; earlier months show "No data" rather than today's allocations.
3. **Auto recurring items:** no push or email. They **only appear in the activity log**. Until Admin exists, the log needs its own small table and a place to show it (decide in S14).

---

## 10. Prompts

### Kickoff (first session, plan mode)

```
Read design/prototype-a/PORT-GUIDE.md completely, then design/prototype-a/BAJETI-DESIGN-BRIEF.md.
Open design/prototype-a/bajeti-prototype-a-evolve.html and skim the sections listed in §3 of the guide.
Then survey this repo: templates, static/css, static/js, routes, models and tests.

Do Stage 0 only. Write design/prototype-a/PORT-MAP.md containing:
1. A table mapping every prototype component and screen in §3 and §5 to the existing file it replaces, or the new file it needs.
2. The routes and endpoints that exist today vs those §6 requires.
3. Model changes and migrations needed, in stage order.
4. Risks, unknowns, and anything in the guide that conflicts with the codebase.
Do not change application code. Ask me at most 3 questions if something is genuinely unclear.
```

### Each stage (plan mode first)

```
Implement Stage <N> (<name>) from design/prototype-a/PORT-GUIDE.md, using PORT-MAP.md.
First give me a plan: files to change or create, migrations, endpoints, tests, and how you'll verify. Wait for my OK.
Then implement it. Follow §2 (ground rules) and §5 (behaviour) exactly; the prototype file is the visual reference.
When done:
- run the tests and the app, check the screens at 375px and 1200px in light and dark against the prototype;
- go through the §8 checklist for every screen you touched and report each item;
- list anything you couldn't match and why;
- tell me exactly what to click to check it myself.
Do not start the next stage.
```

### Review a finished stage (fresh session)

```
Review the changes on this branch against design/prototype-a/PORT-GUIDE.md Stage <N>, §5 and the §8 checklist.
Compare against the prototype file. Report concrete mismatches (file:line, what differs, what the prototype does),
then accessibility problems, then code-quality issues (hard-coded colours, non-p- classes, duplicated logic, missing tests).
Don't fix anything yet; rank findings by severity.
```

### Fix from a screenshot

```
Here are two screenshots at 375px: the app (first) and the prototype (second), same screen and theme.
List every visible difference in spacing, size, weight, colour, order and copy, then fix them using tokens only.
Re-check at 1200px and in dark mode afterwards.
```

### Asking for changes to the prototype itself (not the app)

Use this in the chat where the prototype was made, before porting a new idea:

```
Update Prototype A: <what should change, from the user's point of view>.
Why: <the problem it solves>.
Scope: <screens affected>. Keep everything else as is.
Show me at 375px (and 1200px if layout changes), and tell me any decisions you had to make
so I can add them to §9 of the port guide.
```
