"""Golden Hour theme (Phase 6b): colour tokens, the page CSS and the shared Altair look.

The spec is docs/design/dashboard_concept.md. India blue and finalist orange are the only
data colours; both pass the dataviz palette validator on --tartan-900 and on the sheet colour.
The sunset gradient is UI chrome only and never appears inside a chart.
"""

from __future__ import annotations

import altair as alt

PAGE = "#120d14"
PANEL = "#1a131d"
SHEET = "#241a26"  # what a frosted sheet looks like over the page; charts are checked on it
INK = "#fbf3ea"
INK_2 = "#c9b8b0"
INK_3 = "#a08f95"
RULE = "rgba(251, 243, 234, 0.08)"
SUN_1, SUN_2, SUN_3 = "#ffb547", "#ff6b4a", "#e2407a"
INDIA = "#2a78d6"
FINALISTS = "#e0622f"
BRONZE = "#d9a066"
OK, WARN, DOWN = "#4fd1a5", "#ffb547", "#ff5d73"

DISPLAY = "Unbounded, 'Arial Black', sans-serif"
MONO = "'JetBrains Mono', ui-monospace, Consolas, monospace"
BODY = "Figtree, system-ui, sans-serif"

FONTS = ("@import url('https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700;800"
         "&family=JetBrains+Mono:wght@400;500;700&family=Figtree:wght@400;500;600;700"
         "&display=swap');")

TOKENS = f"""
:root {{
  --tartan-900: {PAGE}; --tartan-800: {PANEL};
  --sheet: rgba(42, 31, 44, 0.72); --sheet-hi: rgba(58, 43, 60, 0.86); --fold: #3b2c3e;
  --ink: {INK}; --ink-2: {INK_2}; --ink-3: {INK_3}; --rule: {RULE};
  --sun-1: {SUN_1}; --sun-2: {SUN_2}; --sun-3: {SUN_3};
  --sunset: linear-gradient(115deg, var(--sun-1) 0%, var(--sun-2) 48%, var(--sun-3) 100%);
  --india: {INDIA}; --finalists: {FINALISTS}; --bronze: {BRONZE};
  --ok: {OK}; --warn: {WARN}; --down: {DOWN};
  --display: {DISPLAY}; --mono: {MONO}; --body: {BODY};
  --ease: cubic-bezier(0.2, 0.8, 0.2, 1);
  --lift-1: 0 1px 0 rgba(255,255,255,0.06) inset, 0 18px 40px -18px rgba(0,0,0,0.65), 0 2px 6px rgba(0,0,0,0.35);
  --lift-2: 0 1px 0 rgba(255,255,255,0.08) inset, 0 26px 50px -20px rgba(0,0,0,0.7), 0 3px 8px rgba(0,0,0,0.4);
  --lift-3: 0 1px 0 rgba(255,255,255,0.08) inset, 0 40px 70px -24px rgba(0,0,0,0.8), 0 4px 12px rgba(0,0,0,0.45);
}}
"""

GRAIN = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' "
         "height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' "
         "numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' "
         "filter='url(%23n)' opacity='0.55'/></svg>\")")

STYLES = """
/* ---------- page: tartan, mesh glow, grain ---------- */
html, body, .stApp { background: var(--tartan-900) !important; }
.stApp { color: var(--ink); font-family: var(--body); }
.stApp::before { content: ""; position: fixed; inset: -80px; z-index: 0; pointer-events: none;
  background:
    radial-gradient(900px 700px at 88% 6%, rgba(255,181,71,0.18), transparent 60%),
    radial-gradient(700px 600px at 6% 96%, rgba(226,64,122,0.12), transparent 60%),
    radial-gradient(600px 500px at 42% 22%, rgba(42,120,214,0.08), transparent 60%);
  animation: drift 40s ease-in-out infinite alternate; }
.stApp::after { content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image: GRAIN; opacity: 0.05; mix-blend-mode: overlay; }
@keyframes drift { from { transform: translate3d(0,0,0); } to { transform: translate3d(-40px,24px,0); } }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stMainBlockContainer"], .block-container {
  position: relative; z-index: 1; max-width: 1320px; padding: 1.6rem 2rem 6rem 8.2rem !important; }
.stApp p, .stApp li, .stApp label { font-family: var(--body); }
.stApp .mono { font-family: var(--mono); }
.stApp h1, .stApp h2, .stApp h3 { font-family: var(--display); color: var(--ink); }
.stApp a { color: var(--ink); }
[data-testid="stElementContainer"]:has(> .stMarkdown .dock) { position: static; }

/* ---------- type ---------- */
.overline { font: 600 13px/1.3 var(--body); color: var(--ink-3); margin: 0 0 .55rem; }
.stApp .section-title { font: 700 clamp(1.2rem, 2.1vw, 1.55rem)/1.15 var(--display) !important; letter-spacing: -0.02em;
  color: var(--ink); margin: 0 0 .4rem; padding: 0; }
.note { color: var(--ink-2); font: 400 15px/1.55 var(--body); max-width: 66ch; margin: 0 0 1rem; }
.mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.anchor { position: relative; top: -24px; display: block; height: 0; }

/* ---------- sheets: plain HTML ones and keyed Streamlit containers ---------- */
.sheet, [class*="st-key-sheet"] {
  background: var(--sheet) !important; backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  border-radius: 22px 22px 22px 6px; box-shadow: var(--lift-1); border: none;
  transition: box-shadow 220ms var(--ease), background 220ms var(--ease), transform 220ms var(--ease);
  animation: rise 420ms var(--ease) both; }
.sheet { padding: 1.5rem 1.6rem; position: relative; }
[class*="st-key-sheet"] { padding: 1.5rem 1.6rem 1.1rem !important; gap: .6rem; }
.sheet.lift:hover, [class*="st-key-sheet"]:hover { box-shadow: var(--lift-2); }
.sheet.lift:hover { background: var(--sheet-hi); }
@keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .sheet, [class*="st-key-sheet"] { background: var(--tartan-800) !important; } }

/* folded corner */
.fold { clip-path: polygon(0 0, calc(100% - 28px) 0, 100% 28px, 100% 100%, 0 100%);
  transition: clip-path 220ms var(--ease); }
.fold::after { content: ""; position: absolute; top: 0; right: 0; width: 28px; height: 28px;
  background: linear-gradient(225deg, transparent 50%, var(--fold) 50%, #4a3a4d 100%);
  border-bottom-left-radius: 6px; box-shadow: -3px 3px 6px rgba(0,0,0,0.35);
  transition: width 220ms var(--ease), height 220ms var(--ease); }
.fold:hover { clip-path: polygon(0 0, calc(100% - 36px) 0, 100% 36px, 100% 100%, 0 100%); }
.fold:hover::after { width: 36px; height: 36px; }
.sun-edge::before { content: ""; position: absolute; left: 22px; right: 40px; top: 0; height: 2px;
  background: var(--sunset); border-radius: 2px; }

/* ---------- header ---------- */
.wordmark { display: flex; align-items: center; gap: .7rem; font: 700 1.25rem/1 var(--display);
  letter-spacing: -0.02em; color: var(--ink); padding-top: .35rem; }
.wordmark .sun { width: 22px; height: 22px; border-radius: 50%; background: var(--sunset);
  box-shadow: 0 0 22px rgba(255,107,74,0.55); }
.badge { display: inline-flex; align-items: center; gap: .45rem; font: 500 12px/1 var(--mono);
  color: var(--ink-2); background: var(--tartan-800); border-radius: 999px; padding: .5rem .8rem;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.5); text-decoration: none; white-space: nowrap; }
.badge:hover { color: var(--ink); }
.header-right { display: flex; justify-content: flex-end; align-items: center; gap: .6rem;
  padding-top: .15rem; flex-wrap: wrap; }

/* ---------- Streamlit widgets: pill toggles, pills, switch, inputs ---------- */
[data-testid="stButtonGroup"] { gap: .4rem; flex-wrap: wrap; }
[data-testid="stButtonGroup"] button {
  font: 600 13px/1 var(--body) !important; border-radius: 999px !important; border: none !important;
  min-height: 34px; padding: .45rem .95rem !important; transition: all 220ms var(--ease);
  background: var(--sheet) !important; color: var(--ink-2) !important; box-shadow: none !important; }
[data-testid="stButtonGroup"] button:hover { color: var(--ink) !important; background: var(--sheet-hi) !important; }
[data-testid="stButtonGroup"] button[data-selected="true"] {
  color: var(--ink) !important; background: rgba(255,107,74,0.14) !important;
  box-shadow: inset 0 0 0 1.5px var(--sun-2) !important; }
[data-testid="stButtonGroup"] button p { font: inherit !important; }
.st-key-view [data-testid="stButtonGroup"] { background: var(--tartan-800); border-radius: 999px;
  padding: 4px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.6); gap: 0; flex-wrap: nowrap; width: max-content; }
.st-key-view [data-testid="stButtonGroup"] button { background: transparent !important; }
.st-key-view [data-testid="stButtonGroup"] button[data-selected="true"] {
  background: var(--sunset) !important; color: var(--tartan-900) !important; box-shadow: var(--lift-1) !important; }
.st-key-legend [data-testid="stButtonGroup"] button[data-selected="true"]:nth-of-type(1) {
  background: rgba(42,120,214,0.2) !important; box-shadow: inset 0 0 0 1.5px var(--india) !important; }
.st-key-legend [data-testid="stButtonGroup"] button[data-selected="true"]:nth-of-type(2) {
  background: rgba(224,98,47,0.2) !important; box-shadow: inset 0 0 0 1.5px var(--finalists) !important; }
button:focus-visible, a:focus-visible, input:focus-visible {
  outline: 2px solid var(--sun-1) !important; outline-offset: 3px; }
[data-testid="stTextInput"] input, [data-baseweb="select"] > div {
  background: rgba(18,13,20,0.6) !important; border: none !important; border-radius: 14px !important;
  color: var(--ink) !important; font-family: var(--body) !important;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.6) !important; }
[data-testid="stTextInput"] input { caret-color: var(--sun-1); font-family: var(--mono) !important; }
[data-testid="stWidgetLabel"] p { color: var(--ink-3) !important; font: 600 13px/1.3 var(--body) !important; }
[data-testid="stCheckbox"] label span[role="checkbox"], [data-baseweb="checkbox"] > div:first-child { }
[data-testid="stToggle"] [data-baseweb="checkbox"] > div:first-child { background: var(--tartan-800) !important; }
[data-testid="stToggle"] input:checked + div, [data-testid="stToggle"] [aria-checked="true"] + div { background: var(--sunset) !important; }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }
[data-testid="stAlert"] { border-radius: 16px; }
[data-testid="stVegaLiteChart"] { background: transparent !important; }
#vg-tooltip-element { background: rgba(42,31,44,0.94) !important; color: var(--ink) !important; border: none !important;
  border-radius: 14px !important; padding: .7rem .9rem !important; box-shadow: var(--lift-3) !important;
  backdrop-filter: blur(20px); font: 500 13px/1.5 var(--mono) !important; }
#vg-tooltip-element td.key { color: var(--ink-3) !important; font-family: var(--body) !important; padding-right: .9rem !important; }
#vg-tooltip-element td.value { color: var(--ink) !important; text-align: right; }

/* ---------- dock ---------- */
.dock { position: fixed; left: 16px; top: 50%; transform: translateY(-50%); z-index: 999990;
  width: 76px; padding: 14px 0; display: flex; flex-direction: column; align-items: center; gap: 4px;
  background: rgba(26,19,29,0.88); backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
  border-radius: 26px; box-shadow: var(--lift-2); }
.dock .group { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.dock .divider { width: 24px; height: 1px; background: var(--rule); margin: 10px 0; }
.dock a { position: relative; display: grid; place-items: center; width: 46px; height: 46px;
  border-radius: 14px; color: var(--ink-3); text-decoration: none; transition: all 220ms var(--ease); }
.dock a svg { width: 22px; height: 22px; }
.dock a:hover { color: var(--ink); background: rgba(255,255,255,0.04); }
.dock a .label { position: absolute; left: 58px; top: 50%; transform: translate(-6px,-50%); opacity: 0;
  pointer-events: none; white-space: nowrap; font: 600 13px/1 var(--body); color: var(--ink);
  background: var(--sheet-hi); backdrop-filter: blur(14px); padding: .55rem .8rem; border-radius: 999px;
  box-shadow: var(--lift-2); transition: all 220ms var(--ease); }
.dock a:hover .label, .dock a:focus-visible .label { opacity: 1; transform: translate(0,-50%); }
.dock a.active { color: var(--ink); background: linear-gradient(115deg, rgba(255,181,71,0.22), rgba(226,64,122,0.22)); }
.dock a.active::before { content: ""; position: absolute; left: -15px; top: 10px; bottom: 10px; width: 4px;
  border-radius: 0 4px 4px 0; background: var(--sunset); }
.dock a .ext { position: absolute; top: 6px; right: 6px; width: 6px; height: 6px; border-top: 1.5px solid currentColor;
  border-right: 1.5px solid currentColor; opacity: .7; }
.dock .status { display: flex; flex-direction: column; align-items: center; gap: 6px; margin-top: 6px;
  font: 500 10.5px/1.2 var(--mono); color: var(--ink-3); text-align: center; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex: none; position: relative; }
.dot.ok { background: var(--ok); } .dot.warn { background: var(--warn); } .dot.down { background: var(--down); }
.dot.ok.pulse::after { content: ""; position: absolute; inset: -4px; border-radius: 50%;
  border: 2px solid var(--ok); animation: pulse 2.4s ease-out infinite; }
@keyframes pulse { from { transform: scale(.6); opacity: .9; } to { transform: scale(1.8); opacity: 0; } }

/* ---------- hero ---------- */
.hero { padding: 1.9rem 2rem 2.6rem; overflow: visible; margin-bottom: 1.6rem; }
.hero .lanes-bg { position: absolute; inset: 0; border-radius: inherit; overflow: hidden; pointer-events: none; }
.hero .lanes-bg::before { content: ""; position: absolute; inset: -40% -10%;
  background: repeating-linear-gradient(102deg, transparent 0 46px, rgba(251,243,234,0.035) 46px 47px);
  mask-image: linear-gradient(90deg, #000 0%, transparent 70%); -webkit-mask-image: linear-gradient(90deg, #000 0%, transparent 70%); }
.hero-row { display: flex; align-items: flex-end; gap: 1.4rem; flex-wrap: wrap; position: relative; }
.hero-num { position: relative; font: 800 clamp(5.5rem, 13vw, 10.5rem)/0.82 var(--display);
  letter-spacing: -0.04em; color: var(--ink); font-variant-numeric: tabular-nums; }
.hero-num::before { content: ""; position: absolute; inset: 8% -6% 0 -8%; z-index: -1; background: var(--sunset);
  filter: blur(60px); opacity: .38; border-radius: 50%; }
@property --a { syntax: '<integer>'; initial-value: 0; inherits: false; }
@property --b { syntax: '<integer>'; initial-value: 0; inherits: false; }
.count { counter-reset: a var(--a) b var(--b); animation: count 900ms var(--ease) both; }
.count::after { content: counter(a) "." counter(b, decimal-leading-zero); }
@keyframes count { from { --a: 0; --b: 0; } }
.sr { position: absolute !important; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.hero-unit { font: 600 1.35rem/1.2 var(--body); color: var(--ink); margin-bottom: .5rem; }
.hero-unit small { display: block; font: 400 15px/1.45 var(--body); color: var(--ink-2); max-width: 30ch; margin-top: .35rem; }
.ci { display: inline-flex; gap: .55rem; align-items: center; font: 500 13px/1 var(--mono); color: var(--ink);
  background: rgba(251,243,234,0.07); backdrop-filter: blur(10px); border-radius: 999px; padding: .5rem .85rem; margin-top: 1.1rem; }
.ci b { color: var(--ink-3); font-weight: 500; }

/* finish-line track (HTML so labels stay readable on phones) */
.track { position: relative; margin: 2.2rem 0 .4rem; padding: 0 0 1.6rem; }
.track .lane { position: relative; height: 18px; border-radius: 9px; margin: 2.1rem 0 0;
  background: linear-gradient(180deg, #120d14, #1d1520); box-shadow: inset 0 2px 4px rgba(0,0,0,0.7), 0 1px 0 rgba(255,255,255,0.04); }
.track .runner { position: absolute; top: 50%; width: 26px; height: 26px; margin: -13px 0 0 -13px; border-radius: 50%;
  box-shadow: 0 0 0 3px var(--tartan-900); animation: roll 900ms var(--ease) both 300ms; }
.track .runner.india { background: var(--india); box-shadow: 0 0 0 3px var(--tartan-900), 0 0 22px rgba(42,120,214,0.6); }
.track .runner.finalists { background: var(--finalists); box-shadow: 0 0 0 3px var(--tartan-900), 0 0 22px rgba(224,98,47,0.55); }
@keyframes roll { from { left: 0; opacity: 0; } }
.track .lane-label { position: absolute; left: 0; top: -1.75rem; font: 600 15px/1 var(--body); color: var(--ink); white-space: nowrap; }
.track .lane-label .mono { color: var(--ink-2); margin-left: .45rem; }
.track .finish { position: absolute; z-index: 2; top: .2rem; bottom: 1.3rem; width: 3px; margin-left: -1.5px; background: var(--bronze);
  border-radius: 2px; box-shadow: 0 0 24px rgba(217,160,102,0.7); }
.track .finish-label { position: absolute; top: -1.6rem; transform: translateX(-50%); font: 500 12px/1 var(--mono);
  color: var(--bronze); white-space: nowrap; }
.track .bracket { position: absolute; height: 0; border-top: 1.5px dashed var(--ink-3); }
.track .bracket span { position: absolute; left: 50%; top: -.75rem; transform: translateX(-50%); font: 700 12px/1 var(--mono);
  color: var(--ink); background: var(--tartan-800); padding: .3rem .5rem; border-radius: 999px; white-space: nowrap; }
.track .ticks { position: absolute; left: 0; right: 0; bottom: 0; height: 1rem; }
.track .ticks span { position: absolute; transform: translateX(-50%); font: 400 11px/1 var(--mono); color: var(--ink-3); }

.float-pills { position: absolute; left: 2rem; right: 2rem; bottom: 0; transform: translateY(50%);
  display: flex; gap: .6rem; flex-wrap: wrap; }
.fpill { display: inline-flex; align-items: center; gap: .6rem; padding: .45rem .9rem .45rem .5rem; border-radius: 999px;
  background: var(--sheet-hi); backdrop-filter: blur(14px); box-shadow: var(--lift-2); font: 500 13px/1 var(--body); color: var(--ink-2); }
.fpill b { font: 700 14px/1 var(--mono); color: var(--ink); }
.stack { display: inline-flex; }
.stack i { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; font: 700 9px/1 var(--mono);
  font-style: normal; color: var(--tartan-900); box-shadow: 0 0 0 2px #3a2b3c; margin-left: -8px; }
.stack i:first-child { margin-left: 0; }

/* ---------- right rail ---------- */
.closest .who { font: 700 1.55rem/1.1 var(--display); letter-spacing: -0.02em; margin: .2rem 0 .55rem; }
.chip { display: inline-block; font: 600 12px/1 var(--body); color: var(--ink-2); background: rgba(251,243,234,0.07);
  border-radius: 999px; padding: .4rem .65rem; }
.big-metric { display: flex; align-items: baseline; gap: .7rem; margin: .9rem 0 .2rem; flex-wrap: wrap; }
.big-metric .mono { font-size: 2.4rem; font-weight: 700; color: var(--ink); }
.delta { font: 600 12px/1 var(--mono); padding: .35rem .55rem; border-radius: 999px; }
.delta.up { color: var(--ok); background: rgba(79,209,165,0.12); }
.delta.down { color: var(--ink-2); background: rgba(251,243,234,0.06); }
.runner-up { display: flex; justify-content: space-between; gap: .8rem; padding: .7rem 0; border-top: 1px solid var(--rule); }
.runner-up .n { font: 600 14px/1.25 var(--body); } .runner-up .e { font: 400 13px/1.3 var(--body); color: var(--ink-3); }
.runner-up .v { font: 700 15px/1.25 var(--mono); text-align: right; } .runner-up .p { font: 400 12px/1.3 var(--mono); color: var(--ink-3); text-align: right; }
.rail-link { display: inline-block; margin-top: .6rem; font: 600 13px/1.4 var(--body); color: var(--sun-1) !important; text-decoration: none; }
.rail-link:hover { text-decoration: underline; }

.stat-stack { display: flex; flex-direction: column; align-items: flex-end; gap: .7rem; margin: 1.2rem 0 1.6rem; }
.spill { position: relative; display: flex; align-items: center; gap: .9rem; min-height: 64px; border-radius: 32px;
  padding: .55rem 1.2rem .55rem 1.4rem; background: var(--sheet); backdrop-filter: blur(18px); box-shadow: var(--lift-1);
  transition: box-shadow 220ms var(--ease); }
.spill:hover { box-shadow: var(--lift-2); }
.spill::before { content: ""; position: absolute; left: 0; top: 16px; bottom: 16px; width: 4px; border-radius: 0 4px 4px 0; background: var(--cap); }
.spill .v { font: 700 1.55rem/1 var(--mono); color: var(--ink); white-space: nowrap; }
.spill .l { font: 400 13px/1.3 var(--body); color: var(--ink-2); }
.ring { --p: 0; width: 38px; height: 38px; border-radius: 50%; flex: none; position: relative;
  background: conic-gradient(var(--ok) calc(var(--p) * 1%), rgba(251,243,234,0.08) 0); }
.ring::before { content: ""; position: absolute; inset: 6px; border-radius: 50%; background: #2a1f2c; }
.ring::after { content: ""; position: absolute; left: 50%; top: -2px; width: 2px; height: 10px; background: var(--ink);
  transform-origin: 50% 21px; transform: rotate(calc(var(--t) * 3.6deg)); }

/* hover cards (CSS only) */
.has-tip { position: relative; }
.tip { position: absolute; z-index: 50; left: 50%; bottom: calc(100% + 10px); transform: translate(-50%, 4px); opacity: 0;
  pointer-events: none; min-width: 210px; padding: .8rem .95rem; border-radius: 14px; background: rgba(42,31,44,0.94);
  backdrop-filter: blur(20px); box-shadow: var(--lift-3); font: 400 13px/1.45 var(--body); color: var(--ink-2);
  transition: all 220ms var(--ease); text-align: left; }
.tip b { color: var(--ink); font-weight: 600; } .tip .mono { color: var(--ink); }
.has-tip:hover .tip, .has-tip:focus-within .tip { opacity: 1; transform: translate(-50%, 0); }

/* ---------- event ladder ---------- */
.ladder-scroll { max-height: 1010px; overflow-y: auto; margin-top: .4rem; padding-right: 4px;
  mask-image: linear-gradient(#000 calc(100% - 48px), transparent); -webkit-mask-image: linear-gradient(#000 calc(100% - 48px), transparent);
  scrollbar-width: thin; scrollbar-color: #4a3a4d transparent; }
.ladder { padding-bottom: 40px; }
.lrow .mk { display: none; font-family: var(--mono); color: var(--ink); margin-left: .5rem; }
.lrow:hover .mk, .lrow:focus .mk { display: inline; }
.lrow { display: grid; grid-template-columns: minmax(0, 44%) 1fr; align-items: center; gap: .8rem; padding: .32rem .5rem;
  border-radius: 10px; transition: background 220ms var(--ease), opacity 220ms var(--ease); }
.ladder:hover .lrow { opacity: .6; } .ladder .lrow:hover { opacity: 1; background: var(--sheet-hi); }
.lrow .ev { font: 600 14px/1.2 var(--body); color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lrow .ath { font: 400 12px/1.25 var(--body); color: var(--ink-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lbar { position: relative; height: 22px; }
.lbar .line { position: absolute; top: -6px; bottom: -6px; width: 2px; margin-left: -1px; background: var(--bronze); opacity: .85; }
.lbar .bar { position: absolute; top: 6px; height: 10px; border-radius: 3px; }
.lbar .bar.behind { background: var(--india); border-radius: 0 4px 4px 0; }
.lbar .bar.ahead { background: var(--ok); border-radius: 4px 0 0 4px; box-shadow: 0 0 14px rgba(79,209,165,0.5); }
.lbar .val { position: absolute; top: 3px; font: 600 12px/16px var(--mono); color: var(--ink-2); white-space: nowrap; }
.rank { display: inline-flex; align-items: center; gap: .4rem; font: 700 12px/1 var(--mono); color: var(--ink);
  background: rgba(251,243,234,0.07); border-radius: 999px; padding: .35rem .6rem; }
.rank svg { width: 13px; height: 13px; color: var(--ink-3); }
.lrow.none .ev { color: var(--ink-3); font-weight: 500; }
.muted { font: 400 12px/1 var(--body); color: var(--ink-3); }
.ladder-head { display: grid; grid-template-columns: minmax(0, 44%) 1fr; gap: .8rem; padding: 0 .5rem .3rem;
  font: 500 11px/1 var(--mono); color: var(--ink-3); }
.ladder-head .scale { position: relative; height: 12px; }
.ladder-head .scale span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
.foot { font: 400 12.5px/1.5 var(--body); color: var(--ink-3); margin-top: .8rem; }

/* ---------- models race ---------- */
.race { margin-top: .5rem; }
.race-lane { display: grid; grid-template-columns: 190px 1fr; align-items: center; gap: 1rem; padding: .45rem 0; }
.race-lane .name { font: 600 14px/1.2 var(--body); color: var(--ink-2); display: flex; align-items: center; gap: .5rem; }
.race-lane.best .name { color: var(--ink); }
.best-pill { font: 700 10.5px/1 var(--mono); color: var(--tartan-900); background: var(--sunset); padding: .3rem .45rem; border-radius: 999px; }
.race-track { position: relative; height: 16px; border-radius: 8px; background: linear-gradient(180deg, #120d14, #1d1520);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.7); }
.race-dot { position: absolute; top: 50%; width: 18px; height: 18px; margin: -9px 0 0 -9px; border-radius: 50%;
  background: #6f6168; box-shadow: 0 0 0 3px var(--tartan-900); }
.race-dot.best { background: var(--india); box-shadow: 0 0 0 3px var(--tartan-900), 0 0 0 6px rgba(255,107,74,0.25), 0 0 26px rgba(255,107,74,0.55); }
.race-dot.small { width: 12px; height: 12px; margin: -6px 0 0 -6px; }
.race-dot .v { position: absolute; left: calc(100% + 8px); top: 50%; transform: translateY(-50%); font: 700 11.5px/1 var(--mono); color: var(--ink); white-space: nowrap; }
.race-dot.small .v { left: 50%; top: auto; bottom: calc(100% + 3px); transform: translateX(-50%); font-size: 10px; color: var(--ink-3); }
.race-axis { display: grid; grid-template-columns: 190px 1fr; gap: 1rem; font: 400 11px/1 var(--mono); color: var(--ink-3); margin: .4rem 0 .9rem; }
.race-axis .scale { position: relative; height: 12px; }
.race-axis .scale span { position: absolute; transform: translateX(-50%); }
.stApp table.mtable, .stApp .mtable th, .stApp .mtable td { border: none !important; background: transparent !important; }
.mtable { width: 100%; border-collapse: collapse; font: 400 13px/1.3 var(--mono); color: var(--ink-2); }
.mtable th { font: 600 12px/1.3 var(--body); color: var(--ink-3); text-align: right; padding: .45rem .4rem; }
.stApp .mtable td { text-align: right; padding: .5rem .4rem; border-top: 1px solid var(--rule) !important; }
.mtable th:first-child, .mtable td:first-child { text-align: left; font-family: var(--body); }
.mtable tr.best td { color: var(--ink); font-weight: 700; }

/* ---------- 2028 constellation ---------- */
.stars { margin-top: .6rem; }
.srow { display: grid; grid-template-columns: minmax(0, 260px) 1fr; gap: 1rem; align-items: center; padding: .28rem .5rem; border-radius: 10px; }
.srow:hover { background: var(--sheet-hi); }
.srow .who { font: 600 14px/1.2 var(--body); color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.srow .ev { font: 400 12px/1.2 var(--body); color: var(--ink-3); }
.sky { position: relative; height: 24px; }
.sky .line { position: absolute; top: -6px; bottom: -6px; width: 2px; margin-left: -1px; background: var(--bronze); box-shadow: 0 0 14px rgba(217,160,102,0.55); }
.sky .cap { position: absolute; top: 6px; height: 12px; border-radius: 6px; background: rgba(42,120,214,0.32); }
.sky .cap.reach { box-shadow: inset 0 0 0 1px rgba(217,160,102,0.0); }
.sky .cap .over { position: absolute; top: 0; bottom: 0; right: 0; border-radius: 0 6px 6px 0; background: rgba(217,160,102,0.78); }
.sky .star { position: absolute; top: 50%; width: 10px; height: 10px; margin: -5px 0 0 -5px; border-radius: 50%; background: var(--india);
  box-shadow: 0 0 0 2px var(--tartan-900), 0 0 12px rgba(120,170,255,0.75); }
.sky .star.hollow { background: var(--tartan-900); box-shadow: 0 0 0 2px var(--india), 0 0 12px rgba(120,170,255,0.5); }
.sky .tip { left: var(--x); }
.legend-row { display: flex; gap: .55rem; flex-wrap: wrap; margin: .2rem 0 .4rem; }
.lpill { display: inline-flex; align-items: center; gap: .45rem; font: 500 12.5px/1 var(--body); color: var(--ink-2);
  background: rgba(251,243,234,0.06); border-radius: 999px; padding: .4rem .7rem; }
.lpill i { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.empty { text-align: center; padding: 2rem 1rem; color: var(--ink-3); font: 400 14px/1.5 var(--body); }
.empty .lane-art { width: 160px; height: 14px; margin: 0 auto 1rem; border-radius: 7px; background: linear-gradient(180deg, #120d14, #1d1520);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.7); }

/* ---------- Mission control ---------- */
.mission-statement { font: 700 clamp(1.7rem, 3.4vw, 2.6rem)/1.08 var(--display); letter-spacing: -0.03em; color: var(--ink); margin: .2rem 0 1rem; max-width: 18ch; }
.hl { background: linear-gradient(transparent 62%, rgba(255,107,74,0.42) 62%, rgba(255,107,74,0.42) 90%, transparent 90%); }
.diag-row { display: grid; grid-template-columns: 14px 1fr auto; align-items: center; gap: .8rem; padding: .78rem 0; border-top: 1px solid var(--rule); }
.diag-row:first-of-type { border-top: none; }
.diag-row .k { font: 600 14px/1.25 var(--body); color: var(--ink); } .diag-row .d { font: 400 12.5px/1.35 var(--body); color: var(--ink-3); }
.diag-row .v { font: 600 13px/1.2 var(--mono); color: var(--ink); text-align: right; white-space: nowrap; }
.ticket div, .ticket span { font-family: var(--mono); }
.ticket { position: relative; padding: 1.3rem 1.4rem 1.3rem 2rem; font: 400 13px/1.9 var(--mono); color: var(--ink-2);
  -webkit-mask: radial-gradient(circle 5px at 0 12px, transparent 98%, #000) 0 0 / 100% 24px repeat-y;
  mask: radial-gradient(circle 5px at 0 12px, transparent 98%, #000) 0 0 / 100% 24px repeat-y; }
.ticket .k { display: inline-block; width: 4.8em; color: var(--ink-3); } .ticket .v { color: var(--ink); }
.ticket a { color: var(--sun-1) !important; text-decoration: none; }
.pipeline { position: relative; display: flex; justify-content: space-between; gap: .4rem; margin: 1.6rem 0 .6rem; }
.pipeline::before { content: ""; position: absolute; left: 20px; right: 20px; top: 19px; height: 2px; background: var(--rule); }
.pipeline .done-line { position: absolute; left: 20px; top: 19px; height: 2px; background: var(--sunset); border-radius: 2px; }
.phase { position: relative; display: flex; flex-direction: column; align-items: center; gap: .55rem; flex: 1; min-width: 0; }
.phase .chip-n { width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; font: 700 14px/1 var(--mono); }
.phase.done .chip-n { background: #3a2b3c; color: var(--ink); box-shadow: var(--lift-1); }
.phase.next .chip-n { background: var(--tartan-900); color: var(--ink); box-shadow: 0 0 0 2px var(--sun-2); animation: ring 2.4s ease-in-out infinite; }
.phase.planned .chip-n { background: var(--tartan-900); color: var(--ink-3); box-shadow: inset 0 0 0 1.5px var(--rule), 0 0 0 1.5px rgba(251,243,234,0.15); }
@keyframes ring { 50% { box-shadow: 0 0 0 2px var(--sun-2), 0 0 0 8px rgba(255,107,74,0.12); } }
.phase .what { font: 500 11.5px/1.3 var(--body); color: var(--ink-3); text-align: center; max-width: 11ch; }
.phase .tip { bottom: calc(100% + 6px); }
.people { display: flex; gap: 1.1rem; align-items: center; flex-wrap: wrap; }
.avatar { width: 72px; height: 72px; border-radius: 50%; display: grid; place-items: center; font: 800 1.35rem/1 var(--display);
  color: var(--ink); background: radial-gradient(circle at 30% 25%, #4a3a4d, #2a1f2c); position: relative; flex: none; }
.avatar::before { content: ""; position: absolute; inset: -3px; border-radius: 50%; padding: 3px; background: var(--sunset);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude; }
.person .n { font: 700 1.15rem/1.2 var(--display); letter-spacing: -0.02em; color: var(--ink); }
.person .links { display: flex; gap: .5rem; margin-top: .55rem; flex-wrap: wrap; }
.astack { display: flex; margin-top: 1.2rem; }
.astack .a { width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; font: 700 12px/1 var(--mono); color: var(--ink);
  background: #3a2b3c; box-shadow: 0 0 0 3px #2a1f2c; margin-left: -10px; transition: margin 220ms var(--ease); position: relative; }
.astack .a:first-child { margin-left: 0; }
.astack:hover .a { margin-left: 6px; } .astack:hover .a:first-child { margin-left: 0; }
.astack .a .tip { min-width: 0; white-space: nowrap; }
.formula { font: 500 14px/1.6 var(--mono); color: var(--ink); background: rgba(18,13,20,0.55); border-radius: 12px; padding: .9rem 1rem;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.6); margin: .4rem 0 1rem; }
.btn { display: inline-flex; align-items: center; gap: .5rem; font: 700 14px/1 var(--body); color: var(--tartan-900) !important;
  background: var(--sunset); border-radius: 999px; padding: .75rem 1.15rem; text-decoration: none !important; box-shadow: var(--lift-1);
  transition: transform 140ms var(--ease), filter 220ms var(--ease); }
.btn:hover { filter: brightness(1.04); transform: translateY(-1px); } .btn:active { transform: scale(.98); }
.st-key-recheck button { border-radius: 999px !important; border: none !important; background: var(--sheet-hi) !important;
  color: var(--ink) !important; font: 600 13px/1 var(--body) !important; }

/* ---------- spacing between Streamlit rows ---------- */
.gap-s { height: .4rem; } .gap-l { height: 2.4rem; }

/* ---------- tablet and phone ---------- */
@media (max-width: 1100px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: 1.2rem 1.25rem 7.5rem !important; }
  .dock { top: auto; bottom: 14px; left: 50%; transform: translateX(-50%); width: auto; max-width: calc(100vw - 24px);
    flex-direction: row; padding: 6px 10px; border-radius: 22px; overflow-x: auto; }
  .dock .group { flex-direction: row; } .dock .divider { width: 1px; height: 24px; margin: 0 6px; }
  .dock a .label { display: none; } .dock a.active::before { left: 10px; right: 10px; top: auto; bottom: -6px; width: auto; height: 3px; border-radius: 3px 3px 0 0; }
  .dock .status { flex-direction: row; margin: 0 6px 0 4px; }
  .dock a.utility { display: none; }
}
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: .8rem 1rem 7.5rem !important; }
  .hero { padding: 1.4rem 1.2rem 3.6rem; }
  .float-pills { left: 1.2rem; right: 1.2rem; }
  .race-lane, .race-axis { grid-template-columns: 1fr; gap: .4rem; } .race-axis > div:first-child { display: none; }
  .srow { grid-template-columns: 1fr; gap: .25rem; }
  .lrow, .ladder-head { grid-template-columns: minmax(0, 40%) 1fr; }
  .ladder-scroll { max-height: none; mask-image: none; -webkit-mask-image: none; }
  .pipeline { overflow-x: auto; justify-content: flex-start; } .phase { min-width: 76px; }
  .header-right { justify-content: flex-start; }
  .track .bracket span { display: none; }
  .dock .status span.age { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
"""

CSS = f"<style>{FONTS}{TOKENS}{STYLES.replace('GRAIN', GRAIN)}</style>"


def style(chart: alt.TopLevelMixin) -> alt.TopLevelMixin:
    """Every Altair chart: transparent on the sheet, recessive axes, the page's type."""
    return (
        chart.configure(background="transparent", font=BODY)
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=INK_3, titleColor=INK_3, gridColor="#2f2532", domainColor="#3a2e3c",
                        tickColor="#3a2e3c", labelFont=MONO, titleFont=BODY, labelFontSize=11,
                        titleFontSize=12, titleFontWeight=500, titlePadding=10)
    )  # fmt: skip
