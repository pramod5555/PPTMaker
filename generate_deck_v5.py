"""
generate_deck_v5.py — "Private Capital in Transition: The New Rules of Value Creation 2025"

Changes from v4:
  - GENERATION_CONSTRAINTS embedded in system prompt (12 layout rules)
  - Different content domain (Private Equity / Capital) to test quality persistence
  - Explicit constraint reminders injected into every chart brief
  - Auto-runs validate_slides.py on output after generation

Usage:
    python generate_deck_v5.py
    python generate_deck_v5.py --out ../full_deck_v5.html
"""
from __future__ import annotations

import argparse, base64, json, os, re, subprocess, sys, time
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

ROOT       = Path(__file__).parent.parent
HTML_DIR   = ROOT / "html_slides"
SLIDES_DIR = Path(__file__).parent / "slides"
DATASET    = Path(__file__).parent / "dataset.json"
W, H = 1280, 720

PALETTE = (
    "PALETTE LOCK — use ONLY these exact values: "
    "dark-bg:#0A0A0A  light-bg:#FFFFFF  accent:#C41230  "
    "accent-dark:#8B0000  text-primary:#1A1A1A  text-secondary:#555555  "
    "text-muted:#888888  rule:#E8E8E8  card-bg:#FAFAFA  "
    "green:#1B7A3E  blue:#0D4D8C  orange:#B35C00  purple:#5C2D91"
)

# ── Constraint rules derived from all v4 layout bugs ─────────────────────────
LAYOUT_RULES = """
LAYOUT RULES — MANDATORY — VIOLATIONS WILL BREAK THE SLIDE:

L1. SUBTITLE Z-INDEX: .sub { z-index:1; } — always, every slide.
    Chart divs come after .sub in DOM order and paint over it without z-index.

L2. CHART CLEARANCE: chart-wrap/chart/col div top >= sub.top + sub_height + 10px.
    If sub is at top:86px with font-size:12px (height ~15px): chart must be top:112px min.
    If sub is at top:103px: chart must be top:128px min.
    NEVER place a chart div at the same top as the subtitle.

L3. POSITION:ABSOLUTE ON NESTED ELEMENTS: .slide > div { position:absolute } does NOT
    cascade to grandchildren. Any child of a panel/row/column that uses left: or top:
    MUST have position:absolute declared explicitly.
    Required on: .num-badge, .enabler-text, .row > div, .big, .small, icon divs.

L4. MULTI-COLUMN LEFT POSITIONS: set left: via inline style on EACH column div.
    CSS class left: applies to ALL instances — every column would stack at the same x.
    Right: <div class="col" style="left:64px">  <div class="col" style="left:440px">

L5. SVG HORIZONTAL GRID LINES: x1 = label column width (NOT 0).
    If labels are 180px wide: <line x1="180" y1="N" x2="1152" y2="N">
    Lines at x1=0 cut through row labels on the left side.

L6. SVG VERTICAL GRID LINES: y1 = header row total height (NOT 0).
    If phase+quarter header = 50px: <line x1="N" y1="50" x2="N" y2="520">
    Lines at y1=0 create visible separators inside header boxes.

L7. HEADER RECT STROKE: phase/section header rects must have NO stroke.
    Any stroke on a header rect creates visible divider lines inside the header.
    Right: <rect x="180" y="0" width="240" height="30" fill="#FAFAFA"/>
    Wrong: <rect ... stroke="#C41230"/>  or  stroke="#E8E8E8"/>

L8. VALUE LABEL COLOR VS BAR: a text label with fill=X over a rect with fill=X is invisible.
    For labels at or overlapping a colored bar: use fill="#FFFFFF" (white inside bar)
    OR position the label PAST bar end with text-anchor="start" at x = barEnd + 2.
    NEVER use text-anchor="end" with same fill color as the bar.

L9. SVG BOTTOM BUDGET:
    lastDataRow_cy = (computed from data spacing)
    legend_cy      = lastDataRow_cy + 30   (min 30px gap)
    axisTicks_y    = legend_cy + 20
    axisTitle_y    = axisTicks_y + 14
    svgHeight      = axisTitle_y + 14      (14px buffer — never less)
    Chart div height = svgHeight.

L10. ANNOTATION BOX BOUNDS: rect x + width must not exceed SVG viewBox width.
     Position callout boxes to the left of the tallest bar, not overlapping the right edge.

L11. POSITION:ABSOLUTE required before left/top work.
     left: and top: are silently ignored on static (non-positioned) elements.

L12. HEADLINE OVERFLOW: estimate headline width = char_count x font_size x 0.55.
     If > container_width, reduce font_size. Max 18px for headlines > 75 chars.
"""

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
)

SYSTEM = f"""You are a senior front-end developer at Bain & Company producing pixel-perfect HTML/CSS slides.

ABSOLUTE RULES (violations will break the slide):
1. Output ONLY complete HTML starting with <!DOCTYPE html>. No markdown, no explanation.
2. Root element: exactly {W}px wide, {H}px tall, position:relative, overflow:hidden.
3. Every direct child element: position:absolute. No flexbox/grid at top level.
4. No <script>, no <img>, no external URLs. System fonts only (Arial, Helvetica, sans-serif).
5. Charts: inline SVG using <rect><line><circle><path> only.

{LAYOUT_RULES}

{PALETTE}"""

# Short reminder injected at the top of every chart slide brief
CHART_REMINDER = """CONSTRAINT REMINDER (enforce before writing any CSS or SVG):
- .sub {{ z-index:1; }} — required
- chart div top >= sub.top + 30px minimum
- SVG horizontal grid lines: x1=labelWidth not 0
- SVG vertical grid lines: y1=headerHeight not 0
- Header rects: fill only, no stroke
- Value labels: white fill if over colored bar; else start-anchor past bar end
- SVG height = lastContent + 44px minimum buffer at bottom
"""


# ── Reference selector (same as v4) ──────────────────────────────────────────
_dataset: list[dict] | None = None

def _load_dataset() -> list[dict]:
    global _dataset
    if _dataset is None:
        with open(DATASET) as f:
            _dataset = json.load(f)["slides"]
    return _dataset

def best_refs(layout_types: list[str], n: int = 3,
              exclude_sources: list[str] | None = None) -> list[str]:
    ds = _load_dataset()
    exclude = set(exclude_sources or [])
    candidates = [
        s for s in ds
        if s["label"].get("layout_type") in layout_types
        and s["label"].get("estimated_quality_score", 0) >= 4
        and s["label"].get("source_company", "") not in exclude
        and (HTML_DIR / f"{s['slide_id']}.html").exists()
    ]
    candidates.sort(key=lambda s: s["label"].get("visual_polish", 0), reverse=True)
    return [s["slide_id"] for s in candidates[:n]]

def _b64(sid: str) -> str | None:
    p = SLIDES_DIR / f"{sid}.png"
    if not p.exists(): return None
    with open(p, "rb") as f:
        return base64.standard_b64encode(f.read()).decode()

def collect(sids: list[str]) -> list[dict]:
    out = []
    for sid in sids:
        p = HTML_DIR / f"{sid}.html"
        if not p.exists(): continue
        out.append({"sid": sid,
                    "html": p.read_text(encoding="utf-8", errors="ignore"),
                    "b64":  _b64(sid)})
    return out

def generate(refs: list[dict], brief: str, label: str) -> str:
    print(f"  {label} ({len(refs)} refs) ... ", end="", flush=True)
    content: list[dict] = []
    for i, r in enumerate(refs):
        if r.get("b64"):
            content.append({"type": "image_url",
                             "image_url": {"url": f"data:image/png;base64,{r['b64']}"}})
        content.append({"type": "text", "text":
            f"STYLE REF {i+1}/{len(refs)} (id:{r['sid']}) — adopt color tokens, "
            f"spacing rhythm, chart treatment:\n{r['html'][:5000]}\n"})
    content.append({"type": "text", "text":
        f"Generate a {W}x{H}px slide. {PALETTE}\n\nBRIEF:\n{brief}"})

    resp = client.chat.completions.create(
        model="gpt-5.4",
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user",   "content": content}],
        max_completion_tokens=8192,
    )
    html = resp.choices[0].message.content or ""
    m = re.search(r"(<!DOCTYPE.*?</html>)", html, re.DOTALL | re.IGNORECASE)
    html = m.group(1).strip() if m else html
    print("OK")
    return html

def wrap_deck(slides: list[str], topic: str) -> str:
    n = len(slides)
    cards = ""
    for i, html in enumerate(slides):
        safe = (html.replace("&","&amp;").replace('"',"&quot;")
                    .replace("<","&#60;").replace(">","&#62;"))
        vis = "block" if i == 0 else "none"
        cards += (f'\n  <div class="slide-card" id="s{i}" style="display:{vis}">'
                  f'\n    <div class="label">Slide {i+1} / {n}</div>'
                  f'\n    <iframe srcdoc="{safe}" width="{W}" height="{H}" '
                  f'scrolling="no" frameborder="0"></iframe>\n  </div>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{topic}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0D0D0D;display:flex;flex-direction:column;align-items:center;
       padding:24px;font-family:Arial,sans-serif}}
  .deck-title{{color:#555;font-size:11px;letter-spacing:3px;text-transform:uppercase;
               margin-bottom:20px}}
  .slide-card{{position:relative;margin-bottom:48px}}
  .label{{position:absolute;bottom:-26px;left:0;right:0;text-align:center;
          color:#444;font-size:11px;letter-spacing:1px}}
  iframe{{display:block;border:none;box-shadow:0 12px 48px rgba(0,0,0,0.7)}}
  .nav{{display:flex;align-items:center;gap:24px;margin-top:8px}}
  .nav button{{background:#1A1A1A;border:1px solid #333;color:#CCC;
               padding:10px 32px;cursor:pointer;font-size:13px;border-radius:2px}}
  .nav button:hover{{background:#C41230;border-color:#C41230;color:#FFF}}
  .dots{{display:flex;gap:8px}}
  .dot{{width:8px;height:8px;border-radius:50%;background:#333;cursor:pointer;
        transition:background .15s}}
  .dot.active{{background:#C41230}}
</style>
</head>
<body>
<div class="deck-title">{topic}</div>
{cards}
<div class="nav">
  <button onclick="go(-1)">&#8592; Prev</button>
  <div class="dots" id="dots"></div>
  <button onclick="go(1)">Next &#8594;</button>
</div>
<script>
var cur=0,n={n};
var dots=document.getElementById('dots');
for(var i=0;i<n;i++){{var d=document.createElement('div');
  d.className='dot'+(i==0?' active':'');d.dataset.i=i;
  d.onclick=function(){{show(+this.dataset.i)}};dots.appendChild(d);}}
function show(i){{document.getElementById('s'+cur).style.display='none';
  dots.children[cur].classList.remove('active');cur=i;
  document.getElementById('s'+cur).style.display='block';
  dots.children[cur].classList.add('active');}}
function go(d){{show((cur+d+n)%n)}}
document.addEventListener('keydown',function(e){{
  if(e.key=='ArrowRight'||e.key==' ')go(1);
  if(e.key=='ArrowLeft')go(-1);}});
</script>
</body>
</html>"""


# ── Slide specifications ──────────────────────────────────────────────────────

def build_slides() -> list[dict]:
    r_cover   = best_refs(["cover"],                    n=2)
    r_exec    = best_refs(["exec_summary"],             n=3)
    r_chart   = best_refs(["full_chart"],               n=3)
    r_two_col = best_refs(["two_col_chart"],            n=3)
    r_mixed   = best_refs(["mixed_layout"],             n=3)
    r_section = best_refs(["section_divider","cover"],  n=2, exclude_sources=["EY"])
    r_diag    = best_refs(["diagram","three_col_text"], n=2)

    print("\nReference selection:")
    for lbl, refs in [("cover",r_cover),("exec",r_exec),("chart",r_chart),
                      ("two_col",r_two_col),("mixed",r_mixed),
                      ("section",r_section),("diag",r_diag)]:
        print(f"  {lbl}: {refs}")
    print()

    return [

        # ── 1. COVER ─────────────────────────────────────────────────────────
        {
            "refs": r_cover,
            "label": "01 Cover",
            "brief": """Cover slide. 1280x720px.

LAYOUT: Left 56% white zone. Right 44% dark #0A0A0A.
Vertical divider: left:717px top:0 width:1px height:720px background:#E8E8E8.

LEFT ZONE (white #FFFFFF):
  A: top:0 left:0 width:717px height:720px background:#FFFFFF
  B: top:0 left:0 width:5px height:720px background:#C41230
  C: top:48px left:72px 'PRIVATE CAPITAL IN TRANSITION' font-size:9px letter-spacing:4px color:#C41230 font-weight:700
  D: top:68px left:72px width:40px height:1px background:#C41230
  E: top:84px left:72px — title in 3 separate divs:
     'Private Capital' font-size:56px font-weight:800 color:#1A1A1A line-height:64px
     'in Transition' font-size:56px font-weight:300 color:#C41230 line-height:64px
     'Value Creation 2025' font-size:40px font-weight:800 color:#1A1A1A line-height:52px
     (ends at top:84+180=264px)
  F: top:284px left:72px width:540px font-size:13px color:#555 line-height:1.7
     'The new rules of private equity performance — as AI, rate cycles,
     and operational complexity reshape how value is created and captured'
  G: top:348px left:72px width:580px height:1px background:#E8E8E8
  H: top:366px left:72px — three stat pills inline-block padding:6px 16px border:1px solid #E8E8E8
     border-radius:2px margin-right:10px font-size:9px color:#888 letter-spacing:1px white-space:nowrap
     Pills: '$5.8tn AUM Tracked' | 'CEO & CFO Survey n=620' | 'Confidential 2025'
  I: top:686px left:72px font-size:9px color:#CCCCCC 'Prepared for LP Advisory Board'
  J: top:686px left:600px font-size:9px color:#CCCCCC '1'

RIGHT ZONE (dark, left:717px width:563px background:#0A0A0A):
  K: Inline SVG top:0 left:717px width:563px height:720px:
     - 5 horizontal lines y:140,220,300,380,460 x1=40+(i*10) x2=x1+60+(i*40) stroke:#C41230 opacity:0.2 stroke-width:1.5
     - 3 white circles r:90,60,40 at cx:420,cy:200 | cx:320,cy:480 | cx:480,cy:540 fill:none stroke:white opacity:0.04
     - 4x4 dot grid r:2 fill:white opacity:0.10 start x:80 y:80 spacing:56px
     - SVG text '$5.8tn' x:300 y:220 font-size:72px font-weight:800 fill:white opacity:0.04
     - '%' x:400 y:195 font-size:36px fill:#C41230 opacity:0.12

NOTHING ELSE.""",
        },

        # ── 2. AGENDA ─────────────────────────────────────────────────────────
        {
            "refs": r_mixed,
            "label": "02 Agenda",
            "brief": """Agenda slide. 1280x720px. Background #FFFFFF.

HEADER:
  A: top:0 width:1280px height:3px background:linear-gradient(90deg,#C41230,transparent)
  B: top:16px left:64px 'AGENDA' font-size:9px letter-spacing:4px color:#C41230 font-weight:700
  C: top:34px left:64px 'From market context to value creation playbook — four chapters' font-size:20px font-weight:700 color:#1A1A1A
  D: top:68px left:64px width:1152px height:1px background:#E8E8E8

TIMELINE (top:96px):
  Horizontal line top:120px left:120px width:1040px height:2px background:#E8E8E8
  4 nodes at x:184,464,744,1024 — circle 24x24px border:2px solid #C41230 border-radius:50%
  Node 1 background:#C41230. Others #FFFFFF.

4 CHAPTER CARDS (top:148px width:240px height:476px):
  Left edges: 64,344,624,904. border-left:3px solid (color) padding-left:20px.

  Card 1 (left:64 color:#C41230):
    'CHAPTER 1' 9px letter-spacing:3px color:#C41230
    'Market' 22px 800 #1A1A1A / 'Environment' 22px 300 #C41230
    'Rate cycles, geopolitics, and sector rotation reshaping deal flow and hold periods'
    '$4.6tn' 44px 800 #C41230
    'dry powder waiting to deploy — highest in private equity history'

  Card 2 (left:344 color:#0D4D8C):
    'CHAPTER 2' / 'Capital' 800 / 'Allocation' 300 blue
    'Where the best GPs are deploying capital across sectors, geographies, and strategies'
    '23%' 44px 800 #0D4D8C
    'IRR premium for top-quartile GPs vs. median — the performance gap is widening'

  Card 3 (left:624 color:#1B7A3E):
    'CHAPTER 3' / 'Value' 800 / 'Creation' 300 green
    'AI-enabled operational improvement as the primary lever replacing financial engineering'
    '3.8x' 44px 800 #1B7A3E
    'EBITDA multiple expansion achievable through AI-first operating model'

  Card 4 (left:904 color:#B35C00):
    'CHAPTER 4' / 'Exit' 800 / 'Readiness' 300 orange
    'LP expectations, ESG mandates, and IPO window timing for optimal realisation'
    '18mo' 44px 800 #B35C00
    'average preparation timeline for optimal exit — starting from year 3 of hold'

FOOTER: top:672px left:64px 'Private Capital in Transition | 2025' 9px #AAAAAA | '2' right
NOTHING ELSE.""",
        },

        # ── 3. EXEC SUMMARY ───────────────────────────────────────────────────
        {
            "refs": r_exec,
            "label": "03 Exec Summary",
            "brief": f"""{CHART_REMINDER}
Executive summary. 1280x720px. Background #FFFFFF.

HEADER:
  A: top:0 width:1280px height:3px background:#C41230
  B: top:16px left:64px 'EXECUTIVE SUMMARY' 9px letter-spacing:4px #C41230 700
  C: top:34px left:64px width:900px 'Six numbers that define private equity's inflection moment' 16px 700 #1A1A1A
  D: top:68px left:64px width:1152px height:1px background:#E8E8E8

6-KPI GRID (top:80px, 3 cols x 2 rows, each 280px wide 148px tall):
  Left col x:64, mid x:352, right x:640. Row 1 top:80, row 2 top:236.
  Each cell: border-bottom:1px solid #F0F0F0 border-right:1px solid #F0F0F0.

  (1,1) '$4.6tn' 44px 800 #C41230 / 'global PE/VC dry powder — capital waiting to deploy'
  (1,2) '23%' 44px 800 #1A1A1A / 'IRR premium for top-quartile GPs vs. median performers'
  (1,3) '3.8x' 44px 800 #1A1A1A / 'EBITDA multiple expansion from AI-first operating model'
  (2,1) '62%' 44px 800 #1B7A3E / 'of GPs now cite AI capability as primary value creation lever'
  (2,2) '14yr' 44px 800 #1A1A1A / 'median fund hold period — up from 5.6 years in 2019'
  (2,3) '$890bn' 44px 800 #B35C00 / 'in PE-backed companies requiring ESG compliance upgrade by 2027'

  Grid borders: vertical at left:632,920px top:80 height:296. Horizontal top:228 width:856.
  Bottom border top:376px.

KEY FINDINGS (top:392px left:64px):
  Label 'KEY FINDINGS' 9px letter-spacing:3px #C41230 700
  3 rows at top:412,450,488 — red bullet + bold label + normal text:
  Row 1: 'AI is the new operational alpha:' + ' GPs using AI see 3.8x EBITDA expansion vs. 1.6x for non-AI portfolios'
  Row 2: 'Hold periods are structurally longer:' + ' 14-year medians require new LP communication and liquidity frameworks'
  Row 3: 'ESG is now a valuation input:' + ' buyers applying 1.2–1.8x discount for non-compliant portfolios at exit'

RIGHT PANEL (top:80px left:956px width:260px height:560px background:#FAFAFA border:1px solid #E8E8E8):
  Title top:96px left:972px 'GP Performance Distribution' 11px 700 #1A1A1A
  Sub top:114px left:972px 'IRR by quartile, 2024 vintage' 9px #888

  SVG (top:130px left:972px width:228px height:380px viewBox="0 0 228 380"):
    CRITICAL — labels past bar end with text-anchor start, NOT end:
    5 horizontal bars for GP quartiles, each row height:56px gap:8px.
    Data (label, IRR%):
      'Top Decile'   34
      'Q1'          28
      'Median'      19
      'Q3'          11
      'Bottom Q'     4
    For each bar at y=i*56:
      Label: x:0 y:y+30 font-size:10px fill:#555
      Bar: x:80 y:y+18 height:16 width=IRR*2.8 fill:#C41230(top2) #1A1A1A(median) #888(rest) rx:2
      Value: x=80+IRR*2.8+4 y=y+30 font-size:9px 700 fill:#1A1A1A text-anchor:start
    Legend y:310: red sq 'Top Quartile' | grey sq 'Median & Below'

FOOTER: 'Sources: Preqin 2025; Bain Global PE Report; Cambridge Associates' | '3'
NOTHING ELSE.""",
        },

        # ── 4. DEAL ENVIRONMENT — Grouped bar chart ────────────────────────────
        {
            "refs": r_chart,
            "label": "04 Deal Environment",
            "brief": f"""{CHART_REMINDER}
Data slide: PE deal flow grouped bar chart. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 1 | MARKET ENVIRONMENT'.
  Headline (16px width:960px): 'Deal flow recovering — but sector rotation and hold-period extension reshape the landscape'
  Sub (top must be >= headline_bottom + 10px): 'Global PE deal count and value ($bn), 2021-2024 by sector'

GROUPED BAR CHART (SVG top:112px left:64px width:820px height:480px viewBox="0 0 820 480"):
  Background #FAFAFA. Plot x:80 y:20 to x:780 y:400.

  CRITICAL LAYOUT:
  - Horizontal grid lines: x1=80 NOT x1=0
  - Value labels: white fill inside dark bars; or text-anchor=start past bar end
  - svgHeight=480, last legend element at y=450, buffer=30px

  6 year-sector groups. Group width=100px. Starting x:90.
  Group positions: 90,200,310,420,530,640.
  Within each group: 3 bars (width:24 gap:4px) for Tech, Healthcare, Industrials.
  Colors: Tech=#1A1A1A, Healthcare=#C41230, Industrials=#0D4D8C.

  Y-axis: Deal value $bn, range 0-300. Scale: 300/380=0.79px per $bn.
  y(v) = 400 - v/300*380.
  Y gridlines at 0,75,150,225,300: x1:80 x2:780. Stroke:#F0F0F0.
  Y labels x:76 text-anchor:end font-size:9px fill:#888.

  Data per group (year, Tech, Healthcare, Industrials in $bn):
  2019: 210, 95, 140
  2020: 160, 120, 90
  2021: 280, 170, 210
  2022: 190, 140, 160
  2023: 140, 110, 120
  2024: 185, 155, 145

  For each group gx, for each bar b at gx+b*28:
    Bar: rx:2 height per value
    Growth label ABOVE bar: '+/-X%' font-size:8px fill:#1B7A3E or #C41230

  X labels at y:415 text-anchor:middle font-size:9px fill:#555.
  Legend at y:440 x:80: three colored squares + labels.
  Baseline y:400 stroke:#CCCCCC.

RIGHT PANEL (top:112px left:908px width:308px):
  3 stat cards (each 148px height):
  Card 1: '$4.6tn' 40px 800 #C41230 / 'global PE dry powder — 22% increase YoY despite tighter credit'
  Card 2: '14yr' 40px 800 #1A1A1A / 'median hold period — up 150% since 2019 as GPs wait for exit windows'
  Card 3: '62%' 40px 800 #1B7A3E / 'of 2024 deals in tech or healthcare — highest sector concentration ever'

FOOTER: 'Sources: Preqin Deal Analytics 2025; Bain Global PE Report; PitchBook' | '4'
NOTHING ELSE.""",
        },

        # ── 5. VALUE CREATION LEVERS — Dot-plot ──────────────────────────────
        {
            "refs": r_two_col,
            "label": "05 Value Creation Levers",
            "brief": f"""{CHART_REMINDER}
Data slide: dot-plot before/after EBITDA margin improvement by value creation lever. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 3 | VALUE CREATION'.
  Headline (16px width:960px): 'AI-enabled levers deliver 3x the margin improvement of traditional PE playbook'
  Sub: 'Average EBITDA margin improvement by intervention type, 2024 PE portfolio companies (n=312)'

DOT-PLOT SVG (top:112px left:64px width:780px height:550px viewBox="0 0 780 550"):
  Background #FAFAFA. Plot x:220 y:20 to x:740 y:468.

  CRITICAL LAYOUT:
  - Horizontal gridlines x1=220 (not x1=0) x2=740
  - Vertical gridlines y1=0 y2=468 (no header in this chart, y1=0 ok here)
  - legend cy = 468 + 30 = 498; tick labels y = 498+20=518; axis title y=532; svgHeight=550
  - .sub must have z-index:1; chart top:112 >= sub_bottom

  8 lever rows, y = 20 + i*56 for i=0..7.
  X-axis: 0% to 30% EBITDA improvement. 1%=17.3px. x(v)=220+v*17.3.
  Axis: baseline x:220 y:468 width:520.
  Ticks at 0,5,10,15,20,25,30%: x=220,306.5,393,479.5,566,652.5,739. Labels y:482.
  Vertical gridlines at those x: y1:20 y2:468 stroke:#F0F0F0.
  Axis title: x:480 y:496 text-anchor:middle font-size:10px fill:#555 'EBITDA margin improvement (pp)'

  Data (lever, before%, after%):
  'Pricing AI'             2   18
  'Procurement AI'         3   14
  'Sales Productivity'     2   12
  'Demand Forecasting'     1   10
  'Cost Structure Review'  4    9
  'Workforce Optimisation' 2    7
  'Working Capital'        3    6
  'Traditional OpEx Cut'   4    5

  Each row at y=20+i*56:
    Connector: x1=220+before*17.3 x2=220+after*17.3 y1=y y2=y stroke:#E8E8E8 stroke-width:2
    Before dot: cx=220+before*17.3 cy=y r:7 fill:#CCCCCC stroke:#888
    After dot: cx=220+after*17.3 cy=y r:9
      fill:#C41230 if i<4 (AI-enabled) else fill:#888888
    After label: x=220+after*17.3+14 y=y+4 font-size:10px 700 fill matches dot
    Role label: x:212 y=y+6 text-anchor:end font-size:11px fill:#1A1A1A

  Legend at cy=498: grey circle 'Before AI' | red circle 'After AI (top-4 levers)'
  Tick labels y=518. Axis title y=532. svgHeight=550.

  Dashed box rows 0-3 (AI-enabled): x:300 y:8 w:432 h:228 fill:none stroke:#C41230 stroke-dasharray:4
  Label 'AI-ENABLED LEVERS' x:304 y:24 font-size:8px fill:#C41230 font-weight:700

RIGHT PANEL (top:112px left:868px width:348px background:#FAFAFA border:1px solid #E8E8E8):
  Title 'Why AI levers outperform' font-size:11px 700 top:128px left:884px.

  3 insight blocks:
  Block 1 top:156px: red left border | '3.8x' 36px 800 #C41230
    'average EBITDA improvement from AI-first interventions vs. traditional cost cutting'
  Block 2 top:306px: dark border | '6mo' 36px 800 #1A1A1A
    'faster realisation vs. traditional levers — AI compresses the value creation timeline'
  Block 3 top:456px: orange border | '89%' 36px 800 #B35C00
    'of top-quartile GPs deployed at least one AI lever in their most recent portfolio company'

FOOTER: 'Sources: Bain GP Survey 2025; McKinsey PE Value Creation Study; Bain Portfolio Analytics' | '5'
NOTHING ELSE.""",
        },

        # ── 6. CAPITAL ALLOCATION — Quadrant scatter ──────────────────────────
        {
            "refs": r_chart,
            "label": "06 Capital Allocation",
            "brief": f"""{CHART_REMINDER}
Data slide: sector allocation scatter. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 2 | CAPITAL ALLOCATION'.
  Headline (16px width:960px): 'Best GPs overweight healthcare and tech-enabled services — financials and energy underweight'
  Sub: 'GP sector allocation vs. benchmark IRR premium, 2022-2024 vintages (n=480 funds)'

SCATTER CHART (SVG top:112px left:64px width:760px height:500px viewBox="0 0 760 500"):
  Background #FAFAFA. Plot x:80 y:20 to x:720 y:440.

  CRITICAL:
  - Grid lines: horizontal x1=80; no header row so vertical y1=0 is fine
  - svgHeight=500; axis title y=480; last element at y=460; buffer=20px ok
  - .sub z-index:1; chart top:112

  X-axis: Sector allocation % of AUM (0-30%). x(v)=80+v*21.3.
  Y-axis: IRR premium vs. benchmark (-10% to +30%). y(v)=440-(v+10)*11.
  Grid: vertical at 0,5,10,15,20,25,30%; horizontal at -10,0,10,20,30%.
  Stroke:#F0F0F0. Zero line y:440-(0+10)*11=330 stroke:#CCCCCC stroke-width:1.5.

  X label: 'Sector Allocation (% of AUM)' x:400 y:460 text-anchor:middle 10px #555.
  Y label: 'IRR Premium vs. Benchmark' x:20 y:230 font-size:10px fill:#555
    (SVG transform rotate for Y axis is NOT allowed — just place horizontally offset).

  10 BUBBLES (sector, allocation%, IRR_premium%, bubble_r, fill):
  'Healthcare IT'     22   28   20  #C41230
  'SaaS/Cloud'        18   24   18  #C41230
  'Medtech'           16   19   16  #1B7A3E
  'Industrials AI'    14   15   14  #0D4D8C
  'Business Svcs'     12   12   12  #1A1A1A
  'Consumer Tech'     10    8   11  #888888
  'Traditional Retail' 8   -2   14  #CCCCCC
  'Energy'             6   -4   12  #CCCCCC
  'Financial Svcs'     5    3   10  #555555
  'Real Estate'        4   -6   10  #CCCCCC

  cx=80+alloc*21.3 cy=440-(irr+10)*11 r=bubble_r.
  Labels: white text centered font-size:8px 700.
  Performance quadrant labels (font-size:10px italic):
    x:84 y:34: 'HIGH CONVICTION' fill:#1B7A3E
    x:84 y:340: 'BENCHMARK' fill:#888
    x:400 y:340: 'UNDERWEIGHT' fill:#C41230

RIGHT PANEL (top:112px left:848px width:368px background:#FAFAFA border:1px solid #E8E8E8):
  Title 'Allocation principles' 11px 700 top:128px.
  4 rows (each 88px) at top:156,244,332,420:
  '60%' 32px 800 #C41230 'of AUM in healthcare IT and SaaS/Cloud in top-decile funds'
  '2.3x' 32px 800 #1A1A1A 'IRR premium for high-conviction overweighting vs. diversified approach'
  '8yr' 32px 800 #0D4D8C 'minimum sector expertise before GPs achieve IRR premium in a new vertical'
  '$50M' 32px 800 #B35C00 'minimum check size for meaningful operational improvement at portfolio level'

FOOTER: 'Sources: Cambridge Associates 2025; Bain Sector Study; Preqin Fund Performance' | '6'
NOTHING ELSE.""",
        },

        # ── 7. OPERATING MODEL — 3-column ─────────────────────────────────────
        {
            "refs": r_diag,
            "label": "07 Operating Model",
            "brief": f"""{CHART_REMINDER}
Framework slide: PE operating model evolution. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 3 | OPERATING MODEL'.
  Headline (16px width:960px): 'Three operating model shifts separate top-quartile GPs from the rest'
  Sub: 'From financial engineering to AI-enabled operational alpha'

THREE COLUMN FRAMEWORK (top:106px):
  CRITICAL: each col must use inline style left. Do NOT use CSS class for column left positions.
  <div class="col" style="left:64px; top:106px; ...">
  <div class="col" style="left:440px; top:106px; ...">
  <div class="col" style="left:816px; top:106px; ...">
  Each col: width:360px height:504px border:1px solid #E8E8E8 border-radius:2px.

  COL 1 (left:64) — OLD MODEL:
    Top bar 4px #E8E8E8 (grey)
    Badge top:122px left:80px: 'OLD PLAYBOOK' 9px letter-spacing:3px #888
    Title top:140px left:80px: 'Financial engineering' 18px 700 #888
    4 bullets top:170,206,242,278: grey bullet + text:
      'Leverage optimisation as primary return driver'
      'Multiple expansion through market timing'
      'Cost cutting via headcount reduction'
      'Value held in acquisition premium'
    X icon SVG top:340px left:164px: red circle stroke:#C41230 r:32

  COL 2 (left:440) — NEW MODEL:
    Top bar 4px #C41230
    Badge: 'NEW PLAYBOOK' #C41230
    Title: 'Operational alpha' 18px 700 #1A1A1A
    4 bullets:
      'AI-enabled pricing and procurement'
      'AI COO embedded at portfolio company'
      'Talent reskilling over headcount cuts'
      'Value built through margin expansion'
    Checkmark SVG top:340px left:504px: green circle stroke:#1B7A3E

  COL 3 (left:816) — WHAT IT TAKES:
    Top bar 4px #1A1A1A
    Badge: 'REQUIREMENTS' #1A1A1A
    Title: 'Enablers' 18px 700
    4 enabler blocks with numbered red badges:
      '01 Data: Portfolio-wide data platform'
      '02 Talent: AI-skilled operating partners'
      '03 Tech: Cloud-native analytics stack'
      '04 Governance: AI ethics and risk board'
    Timeline: '18-36 month transformation' #888 10px

BOTTOM BAR (top:626px left:64px width:1152px height:48px background:#FAFAFA border:1px solid #E8E8E8):
  'KEY INSIGHT:' 10px 700 #C41230 left:80px
  'GPs with AI-first operating model achieve 3.8x EBITDA expansion vs. 1.6x for traditional playbook' 11px #1A1A1A left:180px

FOOTER: 'Sources: Bain GP Capability Study 2025; McKinsey PE Operations Survey' | '7'
NOTHING ELSE.""",
        },

        # ── 8. HOLD PERIOD TIMELINE — Gantt ───────────────────────────────────
        {
            "refs": r_mixed,
            "label": "08 Hold Period Roadmap",
            "brief": f"""{CHART_REMINDER}
Data slide: Gantt-style hold period roadmap. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 3 | VALUE CREATION TIMELINE'.
  Headline (16px width:960px): 'A 36-month value creation roadmap — from deal close to exit-ready'
  Sub: 'Phased workstream sequencing across operational, financial, and governance tracks'

GANTT SVG (top:112px left:64px width:1152px height:520px viewBox="0 0 1152 520"):
  Background #FAFAFA.

  HEADER ROW (y:0 height:30) — phase labels, fill only NO STROKE:
    Phase 1 'Foundation' x:180 w:240 fill:#F5F5F5  (NO stroke attribute)
    Phase 2 'Build' x:420 w:240 fill:#FFF0F0  (NO stroke)
    Phase 3 'Scale' x:660 w:240 fill:#F0F9F0  (NO stroke)
    Phase 4 'Exit Prep' x:900 w:230 fill:#C41230
    Text labels text-anchor:middle font-size:10px font-weight:700
      fill:#555 for phases 1-3, fill:#FFF for phase 4.

  QUARTER LABELS row y:30-50:
    'Q1'-'Q12' at x:210,300,...(every 90px) y:44 font-size:9px fill:#888 text-anchor:middle.

  VERTICAL GRID LINES — CRITICAL: y1=50 NOT y1=0:
    x values: 180,270,360,450,540,630,720,810,900,990,1080,1130.
    <line x1="N" y1="50" x2="N" y2="520" stroke="#F0F0F0"/>

  HORIZONTAL GRID LINES — CRITICAL: x1=180 NOT x1=0:
    At y: 94,110,154,170,214,230,274,290,334,350,394,410,454,470,514.
    <line x1="180" y1="N" x2="1152" y2="N" stroke="#F0F0F0"/>

  8 WORKSTREAM ROWS (y positions: 50,110,170,230,290,350,410,470):
    Row labels: x:172 text-anchor:end font-size:11px fill:#1A1A1A 600.
    Bars: rx:4. x=180+start_q*90 width=duration*90. height:28 centered in row.

    Workstream, start_q(0-based), duration_q, fill, label:
    'Deal Thesis Validation'  0  2  #C41230  'Thesis locked'
    'Management Assessment'   0  3  #0D4D8C  'Team aligned'
    'Data Platform Build'     1  4  #1B7A3E  'Data live'
    'AI Pilots (3 use cases)' 2  4  #888888  '3 pilots running'
    'Pricing Optimisation'    3  5  #C41230  'New pricing live'
    'AI Operating Partner'    2  8  #1A1A1A  'Full deployment'
    'ESG Compliance'          4  6  #B35C00  'ESG certified'
    'Exit Preparation'        9  3  #555555  'Exit ready'

    Milestone diamond at bar end: small rotated rect 8x8 fill:white stroke:barColor.
    Milestone label above: font-size:8px fill:#555.

FOOTER: 'Indicative timeline; depends on portfolio company readiness and market conditions' | '8'
NOTHING ELSE.""",
        },

        # ── 9. IRR vs RISK — Scatter ──────────────────────────────────────────
        {
            "refs": r_chart,
            "label": "09 IRR vs Risk",
            "brief": f"""{CHART_REMINDER}
Data slide: strategy IRR vs risk scatter. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 2 | STRATEGY SELECTION'.
  Headline (16px width:960px): 'AI-enabled strategies dominate the risk-adjusted return frontier in 2024'
  Sub: 'Strategy risk profile vs. net IRR, bubble = AUM deployed ($bn). 2024 vintage.'

SCATTER SVG (top:140px left:64px width:760px height:460px viewBox="0 0 760 460"):
  CRITICAL: chart top:140 >= sub_bottom (sub at top:115 + 15px = 130; 140 >= 130 OK).
  Background #FAFAFA. Plot x:80 y:20 to x:720 y:400.

  X-axis: Risk (1-10). x(r)=80+(r-1)*71.
  Y-axis: Net IRR % (0-40%). y(v)=400-v*9.5.
  Grid: verticals x1=80 y1=0 y2=400 at risk 1,3,5,7,9.
  Horizontals x1=80 x2=720 y1=y y2=y at IRR 0,10,20,30,40%. stroke:#F0F0F0.
  Axis labels font-size:9px fill:#888.
  X label: 'Strategy Risk Profile (1=Low, 10=High)' x:400 y:420 text-anchor:middle 10px #555.
  IRR label: 'Net IRR %' x:14 y:200 font-size:10px fill:#555.

  SWEET SPOT zone (x:152 y:115 w:215 h:190 fill:#F0F9F0 rx:4 opacity:0.7):
    'SUPERIOR RISK-ADJ.' x:158 y:131 9px fill:#1B7A3E 700.

  8 BUBBLES (name, risk, IRR, AUM_bn, fill):
  'AI Buyout'         2.5  34  8.2  #C41230
  'Healthcare AI'     3.0  29  5.4  #C41230
  'Tech Growth'       4.5  26  12.1 #1A1A1A
  'Infra AI'          2.0  22  6.8  #0D4D8C
  'Traditional Buyout' 5.5 18  22.4 #888888
  'Venture'           8.5  28  4.1  #B35C00
  'Distressed'        7.0  14  9.8  #555555
  'Real Assets'       3.5  12  18.2 #CCCCCC

  cx=80+(risk-1)*71 cy=400-IRR*9.5 r=sqrt(AUM)*3 capped:36.
  White labels font-size:8px 700 centered.
  Diagonal guideline x1:80 y1:400 x2:720 y2:20 stroke:#E8E8E8 stroke-dasharray:6.

RIGHT PANEL (top:140px left:848px width:368px height:460px background:#FAFAFA border:1px solid #E8E8E8):
  Title 'Selection criteria' 11px 700 top:156px left:864px.
  4 rows (each 88px) at top:184,272,360,448:
  '3:1' 32px 800 #1B7A3E 'minimum risk-adjusted return ratio for AI strategy allocation'
  '$8bn' 32px 800 #C41230 'minimum fund size to access proprietary AI deal flow at scale'
  '70%' 32px 800 #1A1A1A 'of top-quartile GPs concentrate 70%+ in 3 or fewer strategies'
  '24mo' 32px 800 #B35C00 'diligence cycle for large AI buyout — double the traditional timeline'

FOOTER: 'Sources: Cambridge Associates IRR Study 2025; Preqin Strategy Analysis; Bain PE Outlook' | '9'
NOTHING ELSE.""",
        },

        # ── 10. LP PRIORITIES — Ranked list ────────────────────────────────────
        {
            "refs": r_exec,
            "label": "10 LP Priorities",
            "brief": f"""{CHART_REMINDER}
Data slide: LP ranked priority list. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'LP AGENDA | PRIORITIZATION'.
  Headline (16px width:960px): 'Six priorities every LP must address before committing to next fund cycle'
  Sub: 'Ranked by urgency x impact, LP survey n=390 institutional investors, 2025'

LEFT RANKING LIST (top:86px left:64px width:700px):
  CRITICAL: .sub z-index:1; all row elements need position:absolute.
  6 rows each 88px. Separator 1px #EFEFEF at bottom.

  Each row structure (all position:absolute within row):
    Priority badge: 40x40 background:#1A1A1A(P1-P2) or #E8E8E8(P3-P6) border-radius:2px
      text: 'P1' 14px 800 white or #888
    Score circle: 36x36 border-radius:50% border:2px solid #C41230(top2) or #E8E8E8
      score number: 12px 700
    Title: 13px 700 #1A1A1A
    Description: 11px #555 line-height:1.5 width:480px
    Trend badge: right side, up arrow green or % change

  Row 1 (top:94px): P1 score:91 'Demand AI transparency and governance reporting'
    'Require quarterly AI deployment metrics and risk disclosure from portfolio GPs'
    Trend: '+34% urgency YoY' green

  Row 2 (top:182px): P2 score:87 'Standardise ESG measurement across GP relationships'
    'Uniform carbon, labour, and governance metrics — prerequisite for LP board approval'
    '+22% YoY' green

  Row 3 (top:270px): P3 score:79 'Review liquidity terms and secondary market access'
    '14-year median holds require structured liquidity solutions beyond traditional exit paths'
    '+18% YoY' green

  Row 4 (top:358px): P4 score:74 'Assess GP AI capability as core DD criterion'
    'AI operating capability now weighted equally with sector expertise in GP selection'
    '+41% YoY' green

  Row 5 (top:446px): P5 score:68 'Renegotiate fee structures for long hold periods'
    'Traditional 2-and-20 misaligns incentives when hold periods extend to 14+ years'
    '+12% YoY' green

  Row 6 (top:534px): P6 score:61 'Expand co-investment capabilities'
    'Direct co-invest access reduces fee drag and improves net IRR by 180-220bps'
    '-5% YoY (deprioritised as governance takes precedence)' color:#C41230

RIGHT PANEL (top:86px left:788px width:428px):
  Top SVG: urgency-impact grid 380x240px showing P1-P6 dots.
  Bottom: methodology note 10px #888 line-height:1.6
    'Urgency x Impact weighted survey (n=390 LPs).
    Bain LP Advisory Group proprietary framework. 2025.'

FOOTER: 'Sources: Bain LP Survey 2025; Preqin LP Sentiment; ILPA Principles' | '10'
NOTHING ELSE.""",
        },

        # ── 11. CASE STUDIES ──────────────────────────────────────────────────
        {
            "refs": r_two_col,
            "label": "11 Case Studies",
            "brief": """Two-column case study slide. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'EVIDENCE | CASE STUDIES'.
  Headline (16px width:960px): 'Two GP playbooks — healthcare buyout and industrial AI show the new value creation model'

TWO CASE STUDY CARDS (top:72px each width:560px gap:16px):
  Left x:64, right x:640. Each height:576px border:1px solid #E8E8E8 border-radius:2px.

  LEFT CARD — HEALTHCARE BUYOUT:
    Top accent 4px #C41230
    Tag 'MID-MARKET GP | $3.2bn FUND VI' 9px #888 letter-spacing:2px top:88px left:80px
    Title 'AI-Driven Medtech Platform' 18px 700 top:108px left:80px
    Rule top:136px: 40px width 2px #C41230
    Challenge top:152px: 'CHALLENGE: Portfolio company with fragmented EHR data across 14 hospitals;
      manual coding errors costing $28M annually; 340 FTE in revenue cycle management.'
    Approach top:232px: 'APPROACH'
      '&bull; NLP model for automated clinical coding across 2.4M annual encounters'
      '&bull; AI-powered prior authorisation reducing denial rate from 18% to 4%'
      '&bull; Predictive readmission model deployed across all 14 sites'
    Results top:360px: 'RESULTS (20 months)' color:#1B7A3E
    4 metrics 2x2:
      '$31M' coding error elimination | '94%' prior auth approval (vs 82%)
      '3.8x' EBITDA expansion | '180' FTE redeployed to patient care
      Each: 28px 800 #C41230, 9px #555 label

  RIGHT CARD — INDUSTRIAL AI:
    Top accent #0D4D8C
    Tag 'LARGE CAP GP | $8.1bn FUND IV'
    Title 'Precision Manufacturing AI'
    Rule: #0D4D8C
    Challenge: 'CHALLENGE: Tier-1 auto supplier with 12% defect rate; $180M warranty cost annually;
      48-hour production planning cycle across 6 plants in 4 countries.'
    Approach:
      '&bull; Computer vision quality inspection at 2,400 inspection points'
      '&bull; AI production scheduler reducing changeover time 67%'
      '&bull; Predictive maintenance cutting unplanned downtime 81%'
    Results: 'RESULTS (28 months)' color:#0D4D8C
      '0.8%' defect rate (vs 12%) | '$124M' warranty cost reduction
      '2.9x' EBITDA multiple expansion | '$340M' enterprise value added

FOOTER: 'Based on Bain portfolio company engagements. Names withheld. Results indicative.' | '11'
NOTHING ELSE.""",
        },

        # ── 12. CALL TO ACTION ─────────────────────────────────────────────────
        {
            "refs": r_exec,
            "label": "12 Call to Action",
            "brief": """Closing CTA slide. 1280x720px. Background #0A0A0A.

Left accent bar: left:0 top:0 width:5px height:720px background:#C41230.

HEADER (left:72px):
  'THE NEW RULES' top:48px 9px letter-spacing:5px #C41230 700
  Rule top:68px: 48px width 1px #C41230
  'Three imperatives for' top:84px font-size:52px font-weight:300 #FFFFFF line-height:60px
  'the AI-ready GP' top:144px font-size:52px font-weight:800 #FFFFFF line-height:60px
  Sub top:218px left:72px width:560px font-size:14px color:#888 line-height:1.65:
    'The window for differentiated AI-enabled returns is 24-36 months.
    Early movers will compound structural advantages that laggards cannot close.'

THREE ACTION CARDS (top:316px each width:340px height:252px):
  Positions: left:72,428,784. Each: border:1px solid #2A2A2A border-radius:2px background:#111111.

  Card 1 (accent #C41230 left:72):
    '01' top:330px left:88px 11px letter-spacing:3px #C41230 700
    'Operate' top:352px left:88px 22px 800 #FFFFFF
    'Deploy an AI operating partner to your top 3 portfolio companies within 90 days.'
    12px #777 top:386px left:88px width:296px line-height:1.6
    'TIMELINE: 90 days' top:524px left:88px 9px #C41230 letter-spacing:2px

  Card 2 (accent #1A1A1A left:428):
    '02' #FFFFFF | 'Assess' #FFFFFF
    'Commission AI capability gap analysis across all portfolio companies in current fund.'
    'TIMELINE: 60 days' #888

  Card 3 (accent #555555 left:784):
    '03' #888 | 'Report'
    'Establish AI performance KPIs in LP reporting from next quarter — lead the transparency standard.'
    'TIMELINE: Next quarter'

FOOTER top:688px:
  Left: 'Private Capital in Transition | Bain & Company | 2025' 9px #333
  Right: 'bain.com' 9px #333
NOTHING ELSE.""",
        },
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="../full_deck_v5.html")
    args = parser.parse_args()

    topic = "Private Capital in Transition: The New Rules of Value Creation 2025"
    out_path = (Path(__file__).parent / args.out).resolve()
    slide_specs = build_slides()
    total = len(slide_specs)

    print(f"Generating {total}-slide deck: {topic}")
    print(f"Output: {out_path}\n")

    slides_html: list[str] = []
    for i, spec in enumerate(slide_specs):
        refs = collect(spec["refs"])
        html = generate(refs, spec["brief"], spec["label"])
        slides_html.append(html)
        if i < total - 1:
            time.sleep(0.4)

    deck = wrap_deck(slides_html, topic)
    deck_ascii = deck.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
    out_path.write_text(deck_ascii, encoding="ascii")
    print(f"\nDone -> {out_path.name}")

    # Auto-validate
    print("\nRunning validator...")
    validator = Path(__file__).parent / "validate_slides.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(out_path)],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"VALIDATION ISSUES FOUND. Run with --fix to auto-repair safe issues:")
        print(f"  python validate_slides.py {out_path.name} --fix")
    else:
        print("All slides passed validation.")


if __name__ == "__main__":
    main()
