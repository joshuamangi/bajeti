# Prototype context bundle

Purpose: let Claude on the web (Design) generate faithful prototypes of a redesigned Bajeti without seeing the code. Nothing in here is secret: only public CSS/HTML facts, fake data and a product brief.

## How to use
1. Capture the screenshots listed below into `screenshots/` (Claude Code cannot take screenshots).
2. Attach **`BAJETI-DESIGN-BRIEF.md`** (all text files combined, roughly 5-6k tokens) plus the screenshots to a new chat in Claude on the web.
3. Paste the prompt at the end of `product-brief.md` for Prototype A, review, iterate; then again for Prototype B.
4. Bring the chosen HTML file back to the repo; the port and the PWA come next (stage S16).
Rebuild the combined file after editing any part: `cat design-tokens.md components.md layout.md conventions.md data-shapes.md product-brief.md > BAJETI-DESIGN-BRIEF.md`.

## Screenshots to capture (iPhone width 375px unless noted, light theme, fake or test data)
| File | Screen |
|---|---|
| `01-dashboard-mobile.png` | Dashboard, top of page |
| `02-dashboard-mobile-scrolled.png` | Budgets list and category tiles |
| `03-budget-modal-mobile.png` | Budget modal showing allocations and the Targets section |
| `04-category-modal-mobile.png` | A category detail modal |
| `05-add-expense-modal-mobile.png` | Add expense |
| `06-side-nav-mobile.png` | Burger drawer open |
| `07-dashboard-desktop.png` | Desktop width, with the categories table |
| `08-values-hidden-mobile.png` | Dashboard with the eye toggle on |
| `09-login-mobile.png` | Login page |
Use the browser's device toolbar and mask any real amounts or names before saving.

## CSS inconsistencies found (decide whether to normalise before the port)
1. **Theme naming:** the HSL `:root` set is dark, `body.light` is light, and the page hard-codes `light`; earlier notes calling the app "dark theme" are wrong.
2. **Spacing is not all multiples of 4:** values such as 0.1em, 0.2em, 0.3em, 0.6em, 1.1em and rem/px mixes (1.5rem modal padding, 6px bars, 28px/32px controls, 0.9em text).
3. **Heavy inline styles in dashboard.html:** the same input, select and button styles are repeated on every form instead of using classes.
4. **Four overlapping button systems:** `p-btn-*`, `p-icon-btn-*`, `p-actions-btns-*`, `p-modal-btn-*`.
5. **Dead or broken rules:** `.p- .p-category-transfers-list` (main.css) never matches; `.p-container` and `.main` look unused; `#pSnackBar` repeats `box-shadow` and `.show`.
6. **Utility classes in the wrong file:** `p-negative`, `p-positive`, `d-none` live in `home.css` but are used everywhere.
7. **Unprefixed names:** `tableView`, `categoriesTable`, `table-responsive`, `compact-mode`, `modal-open`.
8. **Hide-values logic exists twice** (`home.js` and `bajeti.js`).
9. **Duplicate attributes:** some alert divs carry two `class` attributes, so the second is ignored.
10. **`@import` chains:** modal.css and toast.css import main.css (which imports palette.css) while base.html also loads each file.
11. **Modal opening** replaces `window.onclick` on every open (handlers pile up); modals have no focus trap or Escape handling.
12. **Only one breakpoint (768px)** and no safe-area handling yet.
13. `--tertiary` has no OKLCH override while the others do.
