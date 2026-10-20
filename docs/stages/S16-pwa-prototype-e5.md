# S16: E5 PWA and prototype context bundle (#114)

**Prompt:** P12  |  **Mode:** claude+human  |  **Depends on:** S13  |  **Suggested branch:** `feature/issue-114-pwa`

## Goal

Build the prototype context bundle from the real CSS and templates, generate prototypes in Claude on the web, port the approved one, and make the app an installable PWA.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `app/static/css`: palette.css, main.css, modal.css, toast.css
4. `app/templates`: base.html and dashboard.html
5. `app/static/js/main.js`

### Outputs of earlier stages this stage relies on

- S13 analytics design (a good first prototype screen)
- S15 design for any screens needing prototypes

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

Two steps: first have Claude Code build the context bundle from the repo, then use it to prompt a prototype tool.

```
Task: create a "prototype context bundle" in docs/prototype-context/ that lets a designer-model (Claude on the web or Claude Design) generate a faithful prototype of a new Bajeti screen without seeing the codebase.

Produce:
1. design-tokens.md: every token from app/static/css/palette.css (colours with HSL values, font family, type scale), spacing rules (multiples of 4, em units), radii, shadows, breakpoints, dark/light behaviour.
2. components.md: each existing component (buttons, inputs, cards, modals, toasts, table/card list, radio budget list, Quick Expense) with its class names, states and a minimal HTML+CSS snippet copied from the real code.
3. layout.md: base.html structure, dashboard.html section order, navigation, Font Awesome icon names in use.
4. conventions.md: naming (`p-` prefix, BEM-ish), accessibility expectations, hide-values toggle behaviour, mobile-first rules and iPhone safe-area needs.
5. screenshots/ README listing the exact screens I must capture (dashboard, modal, table view, mobile view) and the filenames to use. You cannot take screenshots; give me the list.
6. data-shapes.md: realistic fake JSON for the screen data (fake names and amounts only).

Keep the bundle under ~15k tokens total so it fits comfortably in one chat. Do not include secrets or real user data. At the end, list anything in the CSS that is inconsistent so I can decide whether to normalise it before the prototype.
```

Then the prototype prompt (paste in Claude on the web, with the bundle attached or pasted):

```
You are a senior product designer/front-end engineer prototyping a new screen for Bajeti, a personal budgeting web app. The attached bundle is the source of truth for design tokens, components, layout and conventions. Match the existing look and feel exactly: dark theme, Manrope font, Font Awesome 6.4 icons, `p-` class prefix, spacing in multiples of 4 using em units, tokens from palette.css only (no new colours unless you list them separately).

Screen to prototype: <name, e.g. "Analytics: month totals with drill-down">
User goal: <one sentence>
Data available: <paste the relevant fake JSON from data-shapes.md>
States to show: default, empty, loading, error, and the hide-values toggle on.
Target: iPhone width (375px) first, then desktop. Must be usable one-handed and respect safe-area insets.

Output: a single self-contained HTML file with inline CSS and vanilla JS (no frameworks; ECharts via a pinned CDN only if charts are needed), using the real class names from the bundle where they exist. Mark new components with a comment `/* NEW COMPONENT */`. After the code, list: (1) new CSS tokens or classes introduced, (2) what the backend must provide, (3) accessibility notes, (4) what you assumed. Ask up to three clarifying questions first only if something is genuinely ambiguous; otherwise proceed.
```

Then port it:

```
Task: port the approved prototype in <path> into the real app. Map every class to existing ones where possible; add new CSS only in the existing files following the conventions; no inline styles; make it a Jinja2 template extending base.html; wire the handler and API. Show me a diff summary of new CSS tokens/classes first and wait for approval.
```

PWA implementation prompt:

```
Task: make Bajeti an installable PWA on iPhone and desktop. Plan first.

Do: web app manifest (name, icons incl. maskable, theme/background colours from palette.css), service worker with a strict rule NEVER to cache authenticated responses or API calls (cache only static assets; version the cache), offline fallback page, iOS meta tags (apple-touch-icon, status-bar style, apple-mobile-web-app-capable), safe-area insets in CSS, an install hint for iOS (Add to Home Screen) since iOS has no install prompt. Serve the service worker from the root scope with correct headers; make sure it works behind the Cloudflare Tunnel.

Security: a logout must clear caches; confirm no personal data can be read from the cache after logout. Add a short test checklist (airplane mode, update flow, logout) and note iOS limitations (storage eviction, no background sync).
```

## Watch out for

- The service worker must never cache authenticated responses, or one user's data can be shown to another on a shared device.
- Keep the prototype bundle small. It is read by Claude on the web, which has a smaller context budget than a long session.
- Port with the existing class names and conventions; do not add a CSS framework.

## Your part (Claude cannot or should not do these)

1. Capture the screenshots Claude lists (dashboard, modal, table view, mobile view).
2. Run the prototype prompt in Claude on the web with the bundle, review and iterate, then approve before the port.
3. Test the PWA on your iPhone: airplane mode, update flow, logout clears caches.

## Done when

- docs/prototype-context/ under about 15k tokens, with a list of CSS inconsistencies.
- Approved prototype ported with existing class names and conventions.
- PWA works behind the Cloudflare Tunnel and never caches authenticated responses.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- docs/prototype-context/
- Ported screen
- PWA manifest, service worker and iOS tags

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Where screenshots are stored and which prototype was approved.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S17-payment-capture-e4.md`: E4 Payment capture (#113).
