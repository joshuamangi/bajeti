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
