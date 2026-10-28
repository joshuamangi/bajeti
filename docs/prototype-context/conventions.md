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
