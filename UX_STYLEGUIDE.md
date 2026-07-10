# UX Style Guide

The design language of the Search API Playground, written so other apps can adopt
the same look and feel. It documents **principles, tokens, and components** — copy
the values verbatim; they're the source of truth for this family of apps.

Aesthetic in one line: **calm, light, neutral-grey UI with a single dark-slate
accent; dense but breathable; raw data always one click away.**

---

## 1. Principles

1. **Raw-first, honest UI.** Always show the real underlying data (raw JSON, real
   HTTP status, real timings, real errors). Parsed/pretty views are a *rendering
   of* the raw data, shown alongside it — never instead of it. Never hide or
   silently truncate a payload; if you clip a preview, the full value is one click
   away.
2. **Progressive disclosure.** Show the few common controls up front; tuck the
   rest into a collapsed **Advanced options** group. Help text lives in a hover
   **ⓘ tooltip**, not always-on prose. Deep/large data starts collapsed.
3. **Schema/data-driven rendering.** Build forms and views from data, not
   hand-written markup, so nothing drifts. One generic renderer, no per-case code.
4. **Faithful feedback.** Every async action shows a clear loading state with a
   live elapsed timer; every result shows status + latency + cost when available;
   errors are surfaced verbatim.
5. **Self-documenting.** Any change to behaviour/structure updates the docs in the
   same commit.

---

## 2. Color tokens

Neutral greys carry the UI; one dark slate is the only "brand" accent; semantic
colors are used sparingly.

### Surfaces & text (light)
| Token | Hex | Use |
|---|---|---|
| Page background | `#fafafa` | app background |
| Card / panel | `#ffffff` | forms, panes, popovers |
| Band / subtle fill | `#f1f5f9` | inset bars, chips |
| Fill (pill/badge) | `#f0f1f3` / `#eceef1` | neutral pills, hot badges |
| Border (light) | `#e4e6e9` | card & divider borders |
| Border (medium) | `#d0d3d8` | inputs, controls |
| Text primary | `#1f2328` | headings, values |
| Text secondary | `#5a6270` | labels, body |
| Text muted | `#8c959f` | meta, hints |
| Text faint | `#9ca3af` | placeholders, uppercase labels |

### Accent & semantic
| Token | Hex | Use |
|---|---|---|
| Primary (slate) | `#3d434d` | primary buttons, active tab/toggle, selected pills |
| Primary hover | `#2c313a` | hover of the above |
| Success green | `#059669` on `#ecfdf5` | HTTP 2xx pill, copied confirmation |
| Error red | `#dc2626` on `#fef2f2` | error pill/text, invalid fields, required `*` |
| Cost amber | `#b0895a` on `#fdf4e7` | cost pill |
| Deprecated tan | `#b0895a` | "· deprecated" field marker |

### Dark surfaces (code / JSON tree)
| Token | Hex | Use |
|---|---|---|
| Dark background | `#1f2328` | raw JSON, JSON tree, code blocks |
| Dark text | `#e5e7eb` | body text on dark |
| JSON key | `#9cc3ff` | object keys |
| JSON string | `#9ece9e` | string values |
| JSON number | `#e0b978` | numbers |
| JSON boolean | `#c99bec` | true/false |
| JSON null / punctuation | `#8c959f` | null, `{ N keys }` hints |
| Link on dark | `#7fb0ff` | URL values |
| Scrollbar track / thumb (dark) | `#2a2f36` / `#5a636e` | styled scrollbars |

---

## 3. Typography

- **Body / UI:** `Outfit`, sans-serif.
- **Display heading (h1):** `Fraunces`, serif — used only for the app title.
- **Mono / code / field labels / paths:** `'SF Mono', 'Fira Code', 'Consolas', monospace`.

Scale: page title ~26px (Fraunces); section headings 14–16px/600; body 13px;
labels 12px/600 (mono); meta & help 11–12px; badges 10px. Line-height 1.45–1.65
for reading text. Use `font-variant-numeric: tabular-nums` for live counters.

---

## 4. Spacing, radius, motion

- **Radii:** inputs/buttons/cards `8px`; groups/popovers `10px`; badges `4–5px`;
  pills fully round `20px`; toggle track `999px`.
- **Gaps:** form field gap `12px 16px`; inline control gap `6–10px`; card padding
  `10–14px`.
- **Shadows:** popovers/floating only — `0 12px 36px rgba(0,0,0,.2)`. Flat
  elsewhere; separate with borders, not shadows.
- **Motion:** `.12s–.15s` ease for hovers, toggles, chevrons; spinners `.8s`
  linear; indeterminate bars `~1.1s` ease-in-out. Keep it subtle.

---

## 5. Components

### Tabs (folder bar)
Top-level nav. **About first, feature/entity tabs (alpha) in the middle, global
actions last.** Active tab = page background color raised above the bar border.

### Buttons
- **Primary:** slate `#3d434d` bg, white text, `8px` radius, 600 weight; hover
  `#2c313a`; disabled `#d0d3d8`.
- **Secondary/segmented:** white bg, `#d0d3d8` border, secondary text; active
  segment = slate bg + white text. Used for **Tree | Raw** toggles.

### Forms
- **Two-up grid:** short scalar fields (int/enum/bool/date/string) pair
  **two-per-row**; roomy fields (multi-line text, csv lists, JSON, groups) span
  the full row. Nested groups stack single-column.
- **Label:** 12px/600 mono, secondary color. Required → red `*`. Help → an **ⓘ**
  badge after the label (see Tooltips). Never put help in an always-on line.
- **Selector + description, no redundancy:** the switcher dropdown shows the
  primary identifier (e.g. `POST /contents`); directly below it show only the
  **human description** as subtext. Don't repeat the identifier as a separate
  heading — the dropdown already displays the current selection.
- **Inputs:** white bg, `#d0d3d8` border, `8px` radius; focus border `#8c959f`.
- **Booleans = toggle switch,** not a bare checkbox. Track `34×18`, off `#d0d3d8`
  → on `#3d434d`, white knob, `.15s` slide.
- **Enum = select** with a leading "— unset —" option (unset ≠ a value).
- **Advanced options:** params flagged advanced fold into a collapsed group at the
  form's end with a count badge and a chevron (CSS triangle, rotates on toggle).
- **Validation:** highlight the offending field(s) in red on submit; focus the
  first; never fire a request known to 400.

### Pills / badges (status chips)
Small rounded chips in a summary bar. `HTTP 200` (green) / non-2xx (red),
`NNN ms` latency, result count, `$` cost (amber), a muted request-id. A pill that
holds richer detail is **clickable** — add a trailing `›` affordance, `cursor:
pointer`, and open a popover (see below). The latency pill carries a `title`
explaining it's full round-trip.

### Content badges (on result cards)
Each structured field a result carries (highlights/summary/entities/…) renders as
a **clickable pill** that opens the field's full value in a popover. Only make
object/array/structured values into pills — bare scalars stay in the raw view to
avoid noise.

### Tooltips (ⓘ)
Help lives behind a small circled-**i** badge next to a label. On hover/click it
shows a dark floating bubble (max-width ~280px) appended to `<body>` (so nothing
clips it), positioned by the trigger and clamped to the viewport. Dismiss on
mouse-out / outside-click / Esc. `cursor: pointer`, never `help` (that renders the
"?" cursor and reads as broken).

### Popover (click-to-drill)
For viewing a field's full content or a breakdown. A white card appended to
`<body>`: header (title + × close), scrollable body (`max-height: min(52vh,
440px)`), shadow. Content by type: **string → wrapped text; array of strings →
list; object/array → the JSON tree**. Close on × / outside-click / Esc. Prefer
this over hover tooltips for anything long or interactive.

### JSON tree (interactive) + raw text
The canonical way to show a response object. A **Tree | Raw** segmented toggle
(default Tree) + a **Copy** button (flashes green "Copied!"). Tree: click any
object/array to expand/collapse; collapsed nodes show a `{ N keys }` / `[ N items
]` hint; deep nodes auto-collapse (depth ≥ ~1) so big payloads stay scannable;
URL values render as links; keys/values color-coded (see dark tokens). Raw: the
wrapped `JSON.stringify(…, 2)`. Both live in a collapsed "Response object"
disclosure right under the summary bar, so it's clear parsed views derive from it.

### Loading state
Never a bare spinner or a shimmer alone. Show: a **spinner** + a **label naming
the operation** ("Querying <provider> · <endpoint>…") + a **live elapsed-seconds
counter** ("5.9s · waiting for the server…") + an **indeterminate bar**. The timer
is what reassures users during slow (30s–3min) calls. Each concurrent pane gets
its own.

### Result cards
Favicon + linked title, a meta line (host · date · author), the content badges
row, then a snippet (summary/highlights/description/excerpt, clipped ~240 chars).
Cap the visible list (~12) with a "+N more — see the raw response" note rather
than rendering thousands.

### Scrollbars
Style them so they're **always visible** (don't rely on macOS overlay
scrollbars): `::-webkit-scrollbar` width ~12px with a rounded thumb, plus Firefox
`scrollbar-width: thin; scrollbar-color`. Dark thumb on dark surfaces, grey on
light.

### Empty & error states
Empty: a muted centered line ("Build a request and hit **Send**…"). Error: red
text with the verbatim message; for HTTP errors show the raw error body, never a
generic "something went wrong."

---

## 6. Interaction rules

- **One hover affordance per meaning:** ⓘ = help (tooltip); `›` = drillable
  (popover); chevron = expand/collapse.
- **Everything dismissible** (popovers/tooltips) closes on outside-click + Esc.
- **Copy** actions confirm inline for ~1.2s (green "Copied!"), then revert.
- **Async never blocks silently** — loading state up immediately, cleared only
  when the real result (or error) replaces it.
- **Faithful timing/labels:** if a number could be misread (round-trip vs
  server-side), say which via a tooltip.

---

## 7. Quick token reference (CSS custom-property starter)

```css
:root {
  --bg:#fafafa; --card:#fff; --band:#f1f5f9; --fill:#f0f1f3;
  --border:#e4e6e9; --border-mid:#d0d3d8;
  --text:#1f2328; --text-2:#5a6270; --muted:#8c959f; --faint:#9ca3af;
  --primary:#3d434d; --primary-hover:#2c313a;
  --green:#059669; --green-bg:#ecfdf5; --red:#dc2626; --red-bg:#fef2f2;
  --cost:#b0895a; --cost-bg:#fdf4e7;
  --dark:#1f2328; --dark-text:#e5e7eb;
  --jt-key:#9cc3ff; --jt-str:#9ece9e; --jt-num:#e0b978; --jt-bool:#c99bec; --jt-null:#8c959f;
  --radius:8px; --radius-lg:10px; --pill:20px;
  --font-body:'Outfit',sans-serif; --font-display:'Fraunces',serif;
  --font-mono:'SF Mono','Fira Code','Consolas',monospace;
}
```

Reference implementation: `app/index.html` (tokens/CSS) and `app/playground.js`
(the generic renderer, tree/popover/loading components).
