# Golden Hour: dashboard design concept (Phase 6b)

A design spec for the Gap to the Podium site. It replaces the flat night-meet page with an
asymmetric dashboard and a dedicated "Mission control" space for the About/Overview content.

**Status: built** in `site/app.py` and `site/ui/` (theme, parts, dashboard, mission,
diagnostics). Where the build differs from the text below:

- "Closest to bronze" has no season sparklines: `serving/` holds no season-by-season history,
  so the sheet shows each athlete's latest index and 2028 projection instead.
- The models race sits under the career curves (left column) so the 42-row event ladder on the
  right does not leave a gap; the ladder scrolls inside its sheet, and hovering a row shows the
  raw mark inline rather than in a floating card (a scroll area would clip it).
- The age-18 marker on the career chart is a dotted rule, not a sunset diamond, so the
  gradient stays out of charts as section 3.3 requires.
- The 2028 axis fits the ranges shown (always including 100) instead of a fixed 82-106.
- Mission control is a second view (`?view=mission`) rather than a bottom sheet on phones.

Every number shown below comes from the files in `serving/` as of 2026-10-15. The
real page reads them at run time and never hardcodes them.

---

## 1. Concept

**Golden hour at the stadium.** It is the last twenty minutes of light before an evening
final: the sky is going from saffron to plum, the floodlights are warming up and the
tartan glows. The night-meet design kept the finish line and chalk type. Golden Hour keeps
the finish line as the one recurring motif (bronze = 100 = the line every chart is
measured against) and adds warmth, depth and light around it.

Three ideas drive every decision:

1. **The light comes from the finish line.** Ambient glows sit behind whatever is
   closest to bronze. The more a thing matters, the more light it catches. Decoration is
   never random: the brightest glow on the page is always behind the headline gap.
2. **Paper on tartan.** Content sits on warm, slightly translucent "programme sheets"
   (the printed start lists at a meet) floating over a dark, textured track surface.
   Sheets have folded corners, soft lift shadows and no hairline borders.
3. **Scoreboard numbers.** Every metric is set in a monospaced face inside a pill, like
   a stadium results board. Words are for explaining; numbers always look like numbers.

### What this design refuses

| Generic pattern | Golden Hour instead |
| --- | --- |
| Grey page, white cards with 1 px grey borders | Plum-black tartan surface with a mesh glow; borderless frosted sheets |
| Uniform 3x3 grid of same-size cards | 12-column asymmetric grid: one hero, one tall rail, one split panel, one ribbon |
| One font in four sizes | Three faces with distinct jobs: geometric display, monospaced metrics, humanist body |
| Library-default charts with a legend box | Gradient strokes, direct labels, floating tooltip sheets, legend pills that toggle |
| Accent colour everywhere | The signature gradient appears in exactly four places (section 3.3) |

---

## 2. Layout

### 2.1 Desktop (1280 px and up)

```
┌──────┬──────────────────────────────────────────────────────────────────────┐
│      │  HEADER STRIP   Gap to the podium        [Dashboard|Mission] ● live │
│ DOCK ├───────────────────────────────────────────────┬──────────────────────┤
│      │                                               │  CLOSEST TO BRONZE   │
│  ◉   │  HERO: the gap                                │  (folded sheet)      │
│  ◇   │  4.86 points  [95%: 2.97–6.75]                │  Neeraj Chopra  JT   │
│  △   │  finish-line track, glowing                   │  100.37 ▲            │
│  ▢   │                     (8 cols)                  ├──────────────────────┤
│ ──── │  ◖72 India athletes◗ ◖305 finalists◗  pills   │  STAT STACK (4 cols) │
│  ⓘ   │                                               │  1.96  82%  11       │
│      ├───────────────────────────────┬───────────────┴──────────────────────┤
│  ●   │  CAREER CURVES  (7 cols)      │  EVENT LADDER  (5 cols, tall)        │
│ api  │  gradient lines, tooltip      │  42 events ranked by gap             │
│      │  sheet, legend pills          │  bronze line down the middle         │
│      ├───────────────────────────────┴──────────────────────────────────────┤
│      │  MODELS RIBBON (12 cols, short)  5 contenders as racing lanes        │
│      ├──────────────────────────────────────────────────────────────────────┤
│      │  2028 CONSTELLATION (12 cols)  projections + 80% ranges, filters     │
└──────┴──────────────────────────────────────────────────────────────────────┘
```

- **Dock**: 76 px wide, fixed, floats 16 px off the left edge with its own shadow
  (it is not glued to the viewport edge).
- **Content column**: max 1240 px, 28 px gutters, 12 columns.
- **Vertical rhythm**: 8 px base. Sheets are separated by 24 px, sections by 56 px.
- **Asymmetry**: the hero takes 8 columns, but the right rail is split 5 : 3 in height,
  so no two adjacent sheets share both a width and a height.

### 2.2 Tablet (768–1279 px)

The dock collapses into a horizontal floating bar pinned to the bottom centre. The hero
takes the full width. The right rail becomes a horizontal scroll strip of the "Closest to
bronze" sheet plus three stat pills. Curves and the ladder stack.

### 2.3 Phone (under 768 px)

Single column with 16 px side gutters. The hero number is 96 px. The finish-line track
switches to a vertical orientation (lanes run top to bottom) so labels stay at 14 px
instead of shrinking with the viewBox, which fixes the known phone limit of the current
design. The ladder shows the 12 closest events with a "Show all 42" pill. No horizontal
page scroll anywhere.

---

## 3. Visual system

### 3.1 Colour tokens

```css
:root {
  /* Surfaces: warm plum-blacks, never neutral grey */
  --tartan-900: #120d14;   /* page */
  --tartan-800: #1a131d;   /* dock, header strip */
  --sheet:      rgba(42, 31, 44, 0.72);  /* frosted programme sheet */
  --sheet-hi:   rgba(58, 43, 60, 0.82);  /* hovered / focused sheet */
  --fold:       #3b2c3e;   /* underside of the folded corner */

  /* Ink */
  --ink:        #fbf3ea;   /* primary text, warm off-white */
  --ink-2:      #c9b8b0;   /* secondary text */
  --ink-3:      #8a7a80;   /* captions, axis labels */
  --rule:       rgba(251, 243, 234, 0.08);  /* the only "line" allowed: inside sheets */

  /* Signature: golden-hour gradient. UI focus only, never data. */
  --sun-1: #ffb547;  /* saffron */
  --sun-2: #ff6b4a;  /* coral */
  --sun-3: #e2407a;  /* dusk magenta */
  --sunset: linear-gradient(115deg, var(--sun-1) 0%, var(--sun-2) 48%, var(--sun-3) 100%);

  /* Data: unchanged from Phase 6a, both already pass the palette validator on dark */
  --india:     #2a78d6;
  --finalists: #e0622f;
  --bronze:    #d9a066;  /* the finish line itself */

  /* Status */
  --ok:   #4fd1a5;
  --warn: #ffb547;
  --down: #ff5d73;
}
```

**Why the data colours do not change.** India blue and finalist orange were validated
for contrast on a dark surface in Phase 6a. The new page surface is darker and warmer but
at the same lightness band, so they still pass. Re-run the palette validator before
shipping anyway. The signature gradient is deliberately kept off the data: if India's line
were coral it would compete with the finalists and with the UI accents. The rule is
**gradient = "look here", blue/orange = "this is who"**.

Finalist orange and coral `--sun-2` are close. They never touch: coral appears only in UI
chrome (active states, the hero glow, the primary button), never inside a chart.

### 3.2 Background: tartan, mesh and grain

Three stacked layers on `body`, from bottom to top:

1. **Base**: `--tartan-900`.
2. **Mesh glow**: three large blurred radial gradients, fixed to the viewport:
   - saffron at 18% opacity, 900 px, top-right (the low sun);
   - magenta at 12% opacity, 700 px, bottom-left;
   - India blue at 8% opacity, 600 px, centred behind the hero (it picks up the India lane).
   They drift by up to 40 px over 40 s (`@keyframes` on `background-position`), and stop
   when `prefers-reduced-motion` is set.
3. **Tartan grain**: an inline SVG `feTurbulence` noise at 4% opacity with
   `mix-blend-mode: overlay`. It gives the surface the rubbery texture of a track and stops
   the gradients from banding.

Optional fourth layer, hero only: eight faint lane lines (1 px, `--rule`) running
diagonally behind the hero at 12°, fading out to the right.

### 3.3 Where the signature gradient is allowed

Exactly four places. Anything else uses flat tokens.

1. The glow behind the hero number.
2. The active indicator in the dock and the header toggle.
3. The fill of the primary call to action ("Open the API").
4. The 2px top edge of the "Closest to bronze" sheet.

### 3.4 Typography

| Role | Face | Weight | Size (desktop / phone) | Notes |
| --- | --- | --- | --- | --- |
| Display (hero, section titles) | **Unbounded** | 700–800 | 64 / 40 px | Wide geometric forms; tracking −2% |
| Hero number | **Unbounded** | 800 | 168 / 96 px | `font-feature-settings: "tnum"` |
| Metrics, pills, axis ticks | **JetBrains Mono** | 500–700 | 13–40 px | Tabular, slashed zero |
| Body, labels, notes | **Figtree** | 400–600 | 16 / 15 px | Line height 1.55, max 66ch |
| Overlines | Figtree | 600 | 13 px | Sentence case, `--ink-3`, no letter-spaced capitals |

Load from Google Fonts with `display=swap`. Fallbacks: `Arial Black` for Unbounded,
`ui-monospace, Consolas` for JetBrains Mono, `system-ui` for Figtree.

Hierarchy rule: never two Unbounded elements next to each other at similar sizes. A section
title in Unbounded sits above body copy in Figtree, and the metric next to it is in mono.
Each block mixes faces, so the page never reads as "the same font, bigger".

### 3.5 Depth and material

**Programme sheet** (the card replacement):

```css
.sheet {
  background: var(--sheet);
  backdrop-filter: blur(18px) saturate(140%);
  border-radius: 22px 22px 22px 6px;  /* one tight corner, so they don't read as stock cards */
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.06) inset,  /* top lip catches the light */
    0 18px 40px -18px rgba(0, 0, 0, 0.65),    /* lift */
    0 2px 6px rgba(0, 0, 0, 0.35);            /* contact */
  border: none;
}
```

**Folded corner** (used on two sheets only: "Closest to bronze" and the mission statement):
a 28 px triangle at top-right drawn with `clip-path` on the sheet plus a pseudo-element in
`--fold` with a small diagonal gradient, so the corner looks peeled back and shows the
sheet's underside. On hover the fold opens from 28 px to 36 px over 220 ms.

**Elevation scale**

| Level | Use | Shadow lift | Blur |
| --- | --- | --- | --- |
| 0 | Page | none | — |
| 1 | Sheets at rest | 18 px | 18 px |
| 2 | Hovered sheet, dock | 26 px | 22 px |
| 3 | Tooltip sheet, drawer, modal | 40 px | 28 px |

**Back-glow**: hero elements get a `::before` blob behind them, filled with `--sunset`,
`filter: blur(60px)` and 35% opacity. It is the only place glows sit directly behind
content.

### 3.6 Iconography

A custom set of 14 line icons on a 24 px grid with a 1.75 px stroke and rounded joins,
drawn from athletics: a starting block (dashboard), a lane pair (events), a rising curve
with a spike (careers), a stopwatch with three hands (models), a laurel half-ring (2028),
a programme sheet (about), a radio mast (API status). Stored as inline SVG symbols in one
`<svg><defs>` block so they inherit `currentColor`. No icon font.

### 3.7 Motion

- Standard ease: `cubic-bezier(0.2, 0.8, 0.2, 1)`. Durations: 140 ms (press), 220 ms
  (hover), 420 ms (enter).
- Sheets enter with an 8 px rise plus a fade, staggered 40 ms in reading order, once only.
- The hero number counts up from 0 to 4.86 in 900 ms, and the finish-line dots roll
  into place after it.
- Everything above is disabled under `prefers-reduced-motion: reduce`; the page renders
  in its final state.

---

## 4. Components

Each component lists its content, its states, and a build note.

### 4.1 Floating dock (navigation)

**Structure** (top to bottom, grouped with 20 px gaps and a 24 px `--rule` divider
between groups):

- *Explore*: Dashboard, Events, Careers, Models, 2028.
- *Context*: Mission control (the About space).
- *Utilities*: API docs (external), GitHub (external).
- *Status*, pinned to the bottom: API status light plus data age.

**States**

| State | Treatment |
| --- | --- |
| Rest | Icon in `--ink-3`, no background |
| Hover | Icon `--ink`; a label pill slides out to the right (Figtree 14 px on `--sheet-hi`, level 2) |
| Active | 40 px rounded square filled with `--sunset` at 22% opacity, icon `--ink`, and a 4 px sunset bar on the dock's left edge |
| Focus (keyboard) | 2 px `--sun-1` ring, 3 px offset |
| External link | A small arrow glyph at the icon's top-right |

**Status light**: a 10 px dot. `--ok` with a slow 2.4 s pulse ring when `/health` answers
in under 1.5 s; `--warn`, without a pulse, when it is slow (Render free-tier cold start);
`--down` when it fails. Under the dot, in JetBrains Mono 11 px: `data 1d` (age of
`generated_at`).

*Build*: `st.sidebar` restyled with CSS, plus `st.navigation`/`st.page_link` for real
page routing. The health check is a cached `requests.get(".../health", timeout=1.5)`
with `@st.cache_data(ttl=60)` so the page never blocks on a sleeping API.

### 4.2 Header strip

Left: wordmark "Gap to the podium" in Unbounded 22 px. Centre: nothing (breathing room).
Right: a two-way **pill toggle** `Dashboard | Mission control`, then a mono badge
`build 837c43d`.

**Pill toggle states**: the track is `--tartan-800` with an inset shadow. The selected
segment is a raised pill with a sunset fill at 90%, `--tartan-900` text and level 1
shadow; it slides between segments over 220 ms. The unselected label is `--ink-2`, and
`--ink` on hover.

*Build*: `st.segmented_control` with CSS targeting its button group, or a small HTML
component if the slide animation matters.

### 4.3 Hero: the gap (8 columns)

- Overline: "Measured at age 18, against the average 2024 Olympic finalist".
- Hero number: **4.86** in Unbounded 168 px, with "points" in Figtree 22 px baseline-aligned
  beside it. The sunset back-glow sits behind it.
- Confidence pill: `95%  2.97 – 6.75` in mono inside a frosted pill.
- **Finish-line track** (kept from Phase 6a, upgraded): two lanes in the tartan colour with
  a subtle inner shadow so they look recessed. Finalists' dot at 89.25, India's dot at 84.39
  (both read from `curves.csv` at age 18). The bronze line is `--bronze`, 3 px wide, and gives off its own 24 px glow.
  Between the two dots there is a bracket labelled `4.86` in mono. Dots have a soft
  same-colour halo.
- Floating pills overlapping the bottom edge of the hero by 50% (they break the sheet
  edge on purpose): `72 India athletes`, `305 finalists`, `42 events`. Each pill has a
  stacked avatar badge on its left: three 22 px circles with initials, overlapped by
  8 px, in the group's data colour.

**States**: the hero does not respond to hover (it is a statement). Clicking the bracket
opens the Careers view at age 18.

*Build*: one `st.markdown(..., unsafe_allow_html=True)` block with inline SVG, as in the
current `finish_line_svg`. The count-up is a CSS `@property --n` animation, so no
JavaScript is needed.

### 4.4 Closest to bronze (4 columns, top of right rail)

The folded-corner sheet with the 2px sunset top edge.

- Overline: "Closest to bronze right now".
- Athlete: Neeraj Chopra, in Unbounded 28 px. Event chip: `Javelin, men` in a pill.
- Big mono metric: `100.37` with a delta chip `+0.37 over bronze` in `--ok`.
- Below a `--rule`: the next two, smaller (Gulveer Singh, 5000 m: `100.20`), each with
  a 60 px sparkline of their season indices in their data colour.
- The footer link "All 11 athletes whose 2028 range reaches bronze" jumps to the 2028 view
  with the filter on.

**States**: hover lifts the sheet to level 2 and opens the fold. Focus uses the standard
ring.

### 4.5 Stat stack (4 columns, bottom of right rail)

Three stat pills stacked vertically, each a different width (100%, 82%, 64%,
right-aligned), so they read as a cascade and not a grid:

| Pill | Value | Label | Accent |
| --- | --- | --- | --- |
| Model error | `1.96 pts` | Typical error on unseen seasons | thin India-blue left cap |
| Range coverage | `82%` | Target 80%; a ring gauge fills to 82 with a tick at 80 | `--ok`, because it beats the target |
| Medal-range athletes | `11` | 2028 ranges that reach bronze | `--bronze` cap |

Pill anatomy: 64 px tall, radius 32 px, `--sheet` fill, value in mono 28 px on the left,
label in Figtree 14 px `--ink-2` on the right. Hover shows a tooltip sheet with how the
number is computed.

### 4.6 Career curves (7 columns, split panel)

A custom chart, not a library default.

- **Lines**: India and finalists, 3.5 px, monotone interpolation, with a **single-hue
  gradient stroke** running along the age axis: from the data colour at 55% opacity
  at age 16 to 100% at age 30. It encodes "careers build up" without changing the colour.
- **Area between the lines**: filled with a vertical India-to-finalist gradient at 10%
  opacity. This *is* the gap, made visible.
- **Bronze line**: 2 px dashed `--bronze` at 100 with a mono label `bronze 100` at the
  right end.
- **Direct labels** at line ends replace the legend box.
- **Legend pills** above the chart: `● India` and `● Finalists`. Clicking one dims the
  other line to 15%; clicking it again restores it. Active pill: data-colour fill at 18%
  with a matching 1.5 px ring. Inactive: `--ink-3` text with no fill.
- **Scrubber and tooltip sheet**: hovering anywhere draws a vertical 1 px `--ink-3` rule at
  the nearest age, with a level 3 frosted sheet floating 12 px above the cursor:
  ```
  Age 22
  ● Finalists   96.8
  ● India       91.2
  Gap           5.5 pts
  ```
  Values are mono, and the gap row is bold.
- **Age-18 marker**: a small sunset diamond on the x axis at 18, linking back to the hero.

*Build*: Altair can do all of it. Use `alt.Gradient` for strokes and the band fill, a
`selection_point(bind="legend")`-style parameter driven by the pills, and a
`nearest` hover selection for the scrubber. The tooltip sheet is Vega's tooltip themed
through `vega-tooltip` CSS (`#vg-tooltip-element`), which Streamlit exposes.

### 4.7 Event ladder (5 columns, tall)

All 42 events as a ranked "ladder" with the bronze line running vertically down the
middle of the sheet.

- One row per event, 30 px tall. On the left: event name in Figtree plus the athlete in
  `--ink-3`. On the right: a horizontal bar from the bronze line. Bars ahead of bronze go
  left and glow `--ok`; bars behind go right in India blue, with their length set by the gap
  percentage. The value sits at the bar's end in mono.
- **Tactical events** (5000 m, 10,000 m, steeple, marathon, walks) do not show a gap bar.
  They show a **world-rank chip** instead (`#12`, `#38`), because the gap is not meaningful
  there. A small stopwatch icon marks them, and a footnote explains.
- Events with no Indian mark show a muted "No mark yet" row at the bottom.
- **Filter pills** at the top: `All`, `Ahead of bronze` (2, plus 2 tactical), `Within 3%`, `Tactical`. The
  selected pill gets a sunset ring.

**States**: hovering a row raises it to `--sheet-hi`, shows the raw mark (`90.23 m`)
and dims the other rows to 60%.

### 4.8 Models ribbon (12 columns, short)

The backtest shown as a 200 m finish: five contenders as horizontal lanes, each with a
runner dot positioned by MAE. **Lower error = further right = closer to the finish.**

- Gradient boosting wins at `1.96`. Its dot is India blue with a sunset glow, and the
  lane label carries a `best` pill.
- Others (`2.34` age trend, `2.39` mixed model, `2.62` last season, `2.96` fixed curve)
  are `--ink-3` dots.
- On the right edge, a mono mini-table toggled by a pill switch: `MAE | RMSE | Bias |
  by horizon`. "By horizon" turns each lane into four small dots (1–4 seasons ahead), so
  you can see the error grow as the horizon gets longer.

### 4.9 2028 constellation (12 columns)

The projections as a range plot styled like a star chart.

- Each athlete-event is a row: the 80% range is a soft capsule (data colour at 30%), the
  projection a bright 10 px dot with a halo. If the range crosses 100, the capsule gets a
  `--bronze` inner edge where it passes the line.
- **Hollow dots** for athletes beyond the trained ages (the model is extrapolating), with
  a "beyond trained ages" pill in the legend.
- The bronze line runs vertically with its glow.
- Filters as a pill row: event select, name search (a frosted input with a mono cursor),
  and the toggle `Range reaches bronze` as a real switch: 44x24 track, sunset fill when on,
  the knob slides with a 140 ms ease and a small press-squash.
- Below: the full table in `st.dataframe`, themed to match (header in Figtree 600 on
  `--tartan-800`, no grid lines, zebra at 3%).

---

## 5. Mission control (the About / Overview space)

A full-screen view reached from the header toggle or the dock. On phones it is a
bottom sheet that rises to 92% height. It has its own composition, so it does not feel
like a text page bolted on.

```
┌───────────────────────────────────────────────────────────────────────────┐
│  MISSION (folded sheet, 7 cols)              │  LIVE DIAGNOSTICS (5 cols) │
│  "Find the gap early, so it can be closed."  │  ● API         ok   210 ms │
│  3 sentence background                       │  ● Results     1 day old   │
│                                              │  ● Consistency  all checks │
│                                              │  ● Coverage    82% ≥ 80%   │
├───────────────────────┬──────────────────────┴────────────────────────────┤
│ BUILD (4 cols)        │  THE PIPELINE (8 cols)                            │
│ site  837c43d         │  Olympedia → BigQuery/dbt → models → API → site   │
│ api   v1.0.0          │  phase chips 0–7, done/next/planned               │
│ data  2026-10-15      │                                                   │
├───────────────────────┴──────────────────┬────────────────────────────────┤
│ PEOPLE (6 cols)                          │ SOURCES & METHOD (6 cols)      │
│ profile cards, stacked avatars           │ data licences, index formula   │
└──────────────────────────────────────────┴────────────────────────────────┘
```

### 5.1 Mission sheet

Folded corner. An overline "Why this exists", then a statement in Unbounded 40 px:
**"Find the gap early, so it can be closed."** Below it, three sentences in Figtree from
the README: India's athletes improve at the same rate and peak at the same age as Olympic
finalists, but start further behind, so the gap already exists by 18; that points to
junior development. A sunset underline (6 px, 40% opacity, offset under the baseline)
marks the phrase "by age 18".

### 5.2 Live diagnostics

A frosted sheet with four rows. Each row: status dot, label, value in mono, and a small
right-aligned sparkline or gauge.

| Row | Source | Green when | Amber when | Red when |
| --- | --- | --- | --- | --- |
| API | `GET /health`, timed | < 1.5 s | 1.5–8 s (cold start) | error or timeout |
| Results age | `findings.generated_at` | < 14 days | 14–60 days | > 60 days |
| Consistency | `site_data.check_findings` | no problems | — | any problem; each listed |
| Range coverage | `findings.projection_range_coverage_80` | within ±5 pts of 80% | ±5–10 | beyond ±10 |

A "Re-check" pill button at the bottom clears the cache and reruns the checks. While it
runs, the dots show a 1.2 s shimmer.

### 5.3 Build card

A monospaced "ticket" with a perforated left edge (radial-gradient dots on a mask):

```
SITE    837c43d   Phase 6a: night-meet design
API     v1.0.0    gaptopodium.onrender.com
DATA    2026-10-15 18:13 UTC
MODEL   gradient boosting  ·  MAE 1.96
```

The commit comes from `git rev-parse --short HEAD` at startup (or the
`STREAMLIT_COMMIT` env var on Community Cloud); the API version from `/openapi.json`.
Clicking the commit opens it on GitHub.

### 5.4 Pipeline strip

Eight phase chips on a curved track line (an SVG path, `--rule` with a sunset section up
to the current phase). Done = solid chip with a check, next = pulsing sunset ring,
planned = outline. Hovering a chip shows a tooltip sheet with that phase's one-line summary
from the README roadmap.

### 5.5 People

Profile cards built from `git shortlog`, so they stay true without manual edits:

- **Rohith Jagan**, project lead: a large 72 px monogram avatar with a sunset ring, role
  pill, and links to GitHub and the API.
- **Contributors**: a row of stacked 36 px avatars overlapped by 10 px, plus a `+n` chip
  when there are more than five. Hovering fans the stack out over 220 ms and shows names.
- **Data credits**: Olympedia, Wikipedia (CC BY-SA 4.0), World Athletics, shown as text
  chips, not logos.

### 5.6 Sources and method

The index formula set as a small typeset block in mono:
`index = mark as a % of the event's bronze level` (higher is always better, 100 = bronze), with a link to the
method section in the README, plus a short note that every figure is a model estimate
and not a medal forecast.

---

## 6. Interaction states (summary)

| Element | Rest | Hover | Active / selected | Focus | Disabled |
| --- | --- | --- | --- | --- | --- |
| Sheet | level 1 | level 2, `--sheet-hi` | — | 2 px `--sun-1` ring | — |
| Pill toggle | inset track | label to `--ink` | raised sunset pill | ring | 40% opacity |
| Filter pill | `--ink-2` text, `--sheet` | `--ink` | sunset 1.5 px ring + 14% fill | ring | 40% |
| Legend pill | data colour fill 18% | brighten to 26% | toggled off: `--ink-3`, no fill | ring | — |
| Switch | `--tartan-800` track | knob grows 1 px | sunset track, knob right | ring | 40% |
| Primary button | sunset fill, `--tartan-900` text | +4% brightness, lift 1 px | press: scale 0.98, 140 ms | ring | grey fill |
| Dock item | `--ink-3` | label pill slides out | sunset tile + edge bar | ring | — |
| Status dot | colour per state | tooltip with detail | — | — | — |

Empty states: a filter with no results shows a quiet programme-sheet illustration
(an empty lane) and a one-line reason, with a pill to clear the filter.
Loading: sheets show a warm shimmer (`--sheet` to `--sheet-hi`, 1.2 s) in their final
shape, so nothing jumps when data arrives.

---

## 7. Accessibility

- Body text on `--sheet` over the darkest part of the page has at least 7:1 contrast;
  `--ink-3` captions at least 4.5:1. Check against the worst case: the sheet over the
  saffron glow.
- Colour never carries meaning alone: ahead/behind bronze also has direction and a sign,
  status dots have text, hollow vs solid dots have a legend pill.
- Every SVG chart has `role="img"` and an `aria-label` that states the key numbers, as
  the current finish-line graphic does.
- All glows and drift stop under `prefers-reduced-motion`; `backdrop-filter` falls back to
  a solid `--tartan-800` sheet when unsupported.
- Keyboard: dock, toggles and pills are reachable in reading order with visible rings.

---

## 8. Building it in Streamlit

| Part | Approach | Risk |
| --- | --- | --- |
| Tokens, background, sheets, type | One CSS block injected with `st.markdown` (as now) | Low. Streamlit class names change between versions, so target `data-testid` attributes |
| Dock | Restyled `st.sidebar` plus `st.navigation` multipage | Medium: sidebar width and collapse button need CSS overrides |
| Asymmetric grid | `st.columns([8, 4])`, `[7, 5]`, nested `st.container` | Low |
| Hero, ladder, constellation, ribbon, pipeline | Inline SVG strings built in Python | Low. The finish-line SVG already proves the pattern |
| Career curves | Altair with gradients and selections | Low–medium |
| Mission control | A second page, or `st.dialog` for the phone sheet | Low |
| Live diagnostics | `requests` + `st.cache_data(ttl=60)` | Low. Must time out fast because of Render cold starts |
| Hover-only effects inside SVG | CSS `:hover` on SVG groups | Low. Streamlit sanitises `<script>` but keeps `<style>` |
| Drift and count-up animations | Pure CSS | Low |

Suggested file layout:

```
site/
  app.py              # entry: st.navigation over the two pages
  pages/dashboard.py
  pages/mission.py
  theme.py            # tokens, CSS, fonts, Altair config
  svg.py              # hero track, ladder, ribbon, constellation, pipeline
  diagnostics.py      # health ping, freshness, build info
```

Every number stays in `src/site_data.py`, which is already tested offline. The new
modules only draw.

## 9. Order of work

1. `theme.py`: tokens, background layers, sheet class, fonts. Re-run the palette validator.
2. Dashboard skeleton with the asymmetric grid and placeholder sheets; check at 1440,
   1024, 390 px.
3. Hero and "Closest to bronze", then the stat stack.
4. Career curves (Altair) and event ladder (SVG).
5. Models ribbon and 2028 constellation.
6. Mission control: mission, diagnostics, build, pipeline, people.
7. Motion, reduced-motion, keyboard pass, and AppTest checks for both pages.
