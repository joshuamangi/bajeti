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
