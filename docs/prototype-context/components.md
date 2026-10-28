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
