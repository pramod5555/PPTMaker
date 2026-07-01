"""
fix_v3.py — Patch layout-broken slides in full_deck_v3.html.

Fixes:
  index 0  — Cover: title lines overlapping each other
  index 7  — Sustainability chart: right axis scale overflow (1.9tn > 1.5tn range)
  index 8  — Digital Infra divider: subtitle overlapping title
  index 11 — Demographics waterfall: legend overlapping bar labels
  index 12 — Geopolitics divider: multiple overlaps + unauthorized callout box

Usage:
    python fix_v3.py                         # patches full_deck_v3.html
    python fix_v3.py --deck ../some_deck.html
    python fix_v3.py --slides 0,8            # only fix specific indices
"""
from __future__ import annotations
import argparse, base64, os, re, time
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

ROOT      = Path(__file__).parent.parent
HTML_DIR  = ROOT / "html_slides"
SLIDES_DIR = Path(__file__).parent / "slides"
W, H = 1280, 720

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
)

SYSTEM = f"""You are a senior front-end developer at a top consulting firm producing pixel-perfect HTML/CSS slides.
STRICT RULES:
1. Start with <!DOCTYPE html>
2. ALL CSS inside <style> in <head>
3. Root element exactly {W}px wide, {H}px tall, position:relative, overflow:hidden
4. EVERY child element uses absolute positioning — no flexbox/grid at top level
5. NO <script>, NO <img>, NO external URLs, system fonts only (Arial/Helvetica/sans-serif)
6. Charts: inline SVG with <rect>/<line>/<circle>/<path> — NO images
7. Output ONLY the complete HTML. No explanation, no markdown wrapper.
8. CRITICAL: no element may overlap another. Follow the explicit top/left/width/height values exactly.
9. CRITICAL: do NOT add any sections, boxes, or elements beyond what is explicitly listed in the brief."""


def _b64(sid: str) -> str | None:
    p = SLIDES_DIR / f"{sid}.png"
    if not p.exists(): return None
    with open(p, "rb") as f:
        return base64.standard_b64encode(f.read()).decode()

def _html(sid: str) -> str | None:
    p = HTML_DIR / f"{sid}.html"
    if not p.exists(): return None
    return p.read_text(encoding="utf-8", errors="ignore")

def make_content(ref_ids: list[str], brief: str) -> list[dict]:
    content: list[dict] = []
    for i, sid in enumerate(ref_ids):
        b64 = _b64(sid); html = _html(sid)
        if b64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
        if html:
            content.append({"type": "text", "text": f"STYLE REF {i+1} (id:{sid}) — adopt color tokens, chart style, font weight contrast:\n{html[:5000]}\n"})
    content.append({"type": "text", "text": f"Generate a {W}x{H}px slide. Follow the brief exactly.\n\nBRIEF:\n{brief}"})
    return content

def generate(ref_ids: list[str], brief: str, label: str) -> str:
    print(f"  {label} ... ", end="", flush=True)
    content = make_content(ref_ids, brief)
    resp = client.chat.completions.create(
        model="gpt-5.4",
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}],
        max_completion_tokens=8192,
    )
    html = resp.choices[0].message.content or ""
    m = re.search(r"(<!DOCTYPE.*?</html>)", html, re.DOTALL | re.IGNORECASE)
    html = (m.group(1).strip() if m else html)
    print("OK")
    return html

def srcdoc_encode(html: str) -> str:
    return (html.replace("&", "&amp;").replace('"', "&quot;")
                .replace("<", "&#60;").replace(">", "&#62;"))

def patch(deck_path: Path, idx: int, new_html: str) -> None:
    deck = deck_path.read_text(encoding="utf-8", errors="ignore")
    safe = srcdoc_encode(new_html)
    matches = list(re.finditer(r'(srcdoc=")[^"]*(")', deck, re.DOTALL))
    if idx >= len(matches):
        print(f"  [!] index {idx} out of range ({len(matches)} slides)")
        return
    m = matches[idx]
    deck = deck[:m.start()] + f'srcdoc="{safe}"' + deck[m.end():]
    deck_ascii = deck.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
    deck_path.write_text(deck_ascii, encoding="ascii")
    print(f"  Patched slide {idx+1} into {deck_path.name}")


# ── Slide specs ───────────────────────────────────────────────────────────────

SPECS: dict[int, dict] = {

    # ─────────────────────────────────────────────────────────────────────────
    # 0 — COVER (fix: title lines overlapping)
    # ─────────────────────────────────────────────────────────────────────────
    0: {
        "refs": ["bain_global_pe_report_2023_slide_001",
                 "roland_berger_trend_compendium_2050_technology_and_innovation_slide_001"],
        "brief": f"""Cover slide. Exactly {W}x{H}px. Background #0A0A0A.

==== LEFT ZONE (left 0 to 736px) ====
All elements below are ABSOLUTE, do NOT overlap.

Element A — left red accent bar:
  top:0 left:0 width:4px height:720px background:#C41230

Element B — top kicker:
  top:44px left:72px width:600px height:16px
  font-size:10px letter-spacing:4px color:#C41230 text-transform:uppercase font-weight:700
  content: 'STRATEGIC ADVISORY'

Element C — red rule under kicker:
  top:68px left:72px width:40px height:2px background:#C41230

Element D — title block (single absolutely-positioned div, contains 4 lines as block spans):
  top:96px left:72px width:620px
  Each line is a <div> with display:block:
    Line 1: 'Strategic Priorities'  font-size:52px font-weight:800 color:#FFFFFF line-height:64px
    Line 2: '2025&#x2013;2030'     font-size:52px font-weight:300 color:#C41230 line-height:64px
    Line 3: 'Five Forces Defining'  font-size:52px font-weight:800 color:#FFFFFF line-height:64px
    Line 4: 'the Next Decade'       font-size:52px font-weight:300 color:#CCCCCC line-height:64px
  Total block height: 4 x 64px = 256px → block ends at top 96+256=352px

Element E — horizontal rule:
  top:368px left:72px width:300px height:1px background:#2A2A2A

Element F — descriptor text:
  top:380px left:72px width:580px
  font-size:12px color:#888888 line-height:1.65
  'An integrated view of technology, sustainability, infrastructure, demographic, and geopolitical forces shaping the next decade'
  (max ~3 lines at 12px = ~3x20px = 60px tall → ends at ~440px)

Element G — three tag pills (display:inline-block each, placed in a single div row):
  top:460px left:72px (container div)
  Each pill: display:inline-block margin-right:12px padding:6px 14px border:1px solid #2A2A2A
  border-radius:2px font-size:9px color:#777777 letter-spacing:1px white-space:nowrap
  Pill 1: '5 STRATEGIC FORCES'
  Pill 2: '18-MONTH HORIZON'
  Pill 3: 'C-SUITE BRIEFING'

Element H — footer text:
  top:686px left:72px font-size:9px color:#2E2E2E
  'Confidential &bull; For Executive Leadership Only'

Element I — slide number:
  top:686px right:72px font-size:9px color:#2E2E2E content:'1'

==== RIGHT ZONE (left 736px to 1280px) ====

Element J — red gradient panel:
  position:absolute top:0 left:736px width:544px height:720px
  background:linear-gradient(135deg, #C41230 0%, #6B0A1A 100%)

Element K — inline SVG art (inside the right panel):
  position:absolute top:0 left:736px width:544px height:720px
  Draw ONLY these elements inside the SVG (no other shapes):
    8 horizontal white rectangles at y=80,148,216,284,352,420,488,556
    Each rect: x=60+(i*8), width=80+i*30 (i=0 to 7), height=2px, fill=white opacity=0.15
    3 large circles: cx=420,cy=200,r=140 | cx=320,cy=500,r=100 | cx=500,cy=400,r=80
    All circles: fill=white opacity=0.04
    Dot grid: 5 cols x 4 rows of circles r=2, fill=white opacity=0.18
    Starting x=800 y=80, spacing 48px horizontal 56px vertical

==== NOTHING ELSE ====
No other elements. No nav, no animation, no JavaScript.""",
    },

    # ─────────────────────────────────────────────────────────────────────────
    # 7 — SUSTAINABILITY DATA (fix: right-axis scale 0-2.0tn, not 0-1.5tn)
    # ─────────────────────────────────────────────────────────────────────────
    7: {
        "refs": ["bain_global_pe_report_2023_slide_012",
                 "bain_global_pe_report_2023_slide_013",
                 "bain_china_luxury_2011_slide_005"],
        "brief": f"""Data slide: dual-axis line chart. Exactly {W}x{H}px. Background #FFFFFF.

==== HEADER ====
Element A — top green rule: top:0 left:0 width:1280px height:3px background:#1B7A3E
Element B — kicker: top:16px left:64px font-size:9px letter-spacing:3px color:#1B7A3E font-weight:700
  'GREEN TRANSITION | DATA'
Element C — headline: top:32px left:64px width:960px font-size:20px font-weight:700 color:#1A1A1A
  'Renewable energy costs collapsed 89% since 2010 &#x2014; clean investment now exceeds fossil capex'
Element D — sub: top:68px left:64px font-size:10px color:#888888
  'Solar LCOE ($/MWh, left axis) vs. global clean energy investment ($tn, right axis), 2010&#x2013;2025'

==== MAIN SVG CHART: position:absolute top:86px left:64px width:852px height:510px ====
Outer rect: x:0 y:0 width:852 height:510 fill:#FAFAFA rx:2 stroke:#E8E8E8 stroke-width:1

CHART PLOT AREA: x:70 y:20 to x:790 y:440  (720px wide, 420px tall)

--- LEFT Y-AXIS: Solar LCOE $/MWh, range 0-350, scale = 420/350 = 1.2 px per $/MWh ---
y_lcoe(v) = 440 - v * 1.2
Ticks at $/MWh values 0,70,140,210,280,350 → y = 440, 356, 272, 188, 104, 20
  Tick lines: x1:65 x2:70, stroke:#CCCCCC
  Labels: x:62 text-anchor:end font-size:9px fill:#C41230
  Axis label (rotated -90): x:16 y:230 'Solar LCOE ($/MWh)' font-size:9px fill:#C41230

--- RIGHT Y-AXIS: Clean Investment $tn, range 0-2.0, scale = 420/2.0 = 210 px per $tn ---
y_inv(v) = 440 - v * 210
Ticks at $tn values 0, 0.5, 1.0, 1.5, 2.0 → y = 440, 335, 230, 125, 20
  Tick lines: x1:790 x2:795, stroke:#CCCCCC
  Labels: x:798 text-anchor:start font-size:9px fill:#0D4D8C
  Axis label (rotated +90): x:838 y:230 'Clean Investment ($tn)' font-size:9px fill:#0D4D8C

--- X-AXIS: years 2010-2025, 16 points ---
x(year) = 70 + (year - 2010) * (720 / 15)  = 70 + (year-2010)*48
Years: 2010=70, 2012=166, 2014=262, 2016=358, 2018=454, 2020=550, 2022=646, 2024=742, 2025=790
Baseline: x:70 y:440 to x:790 y:440 stroke:#CCCCCC stroke-width:1
Labels at even years only (font-size:9px fill:#888 y:456 text-anchor:middle)
Vertical grid at even years: stroke:#F0F0F0 stroke-width:1 y1:20 y2:440

--- LINE 1: SOLAR LCOE (red solid line) ---
Use <polyline> stroke:#C41230 stroke-width:2.5 fill:none
Data (year, $/MWh) → compute x and y_lcoe:
  2010:359 2011:295 2012:228 2013:180 2014:142 2015:122 2016:100 2017:86
  2018:72  2019:60  2020:52  2021:48  2022:45  2023:41  2024:38  2025:36
Polyline points (compute each):
  x=70+(yr-2010)*48, y=440-val*1.2
  (70,9)(118,86)(166,185)(214,224)(262,269)(310,293)(358,320)(406,337)
  (454,354)(502,368)(550,378)(598,382)(646,386)(694,391)(742,394)(790,397)
Add <circle r:3 fill:#C41230> at each point.
End label near x:790 y:397: '&#36;36/MWh' dx:4 font-size:10px font-weight:700 fill:#C41230

--- LINE 2: CLEAN INVESTMENT (blue dashed line) ---
Use <polyline> stroke:#0D4D8C stroke-width:2.5 fill:none stroke-dasharray:'7,4'
Data (year, $tn) → compute x and y_inv:
  2010:0.27 2011:0.28 2012:0.25 2013:0.24 2014:0.30 2015:0.33 2016:0.32 2017:0.33
  2018:0.38 2019:0.40 2020:0.50 2021:0.75 2022:1.05 2023:1.34 2024:1.77 2025:1.90
Polyline points (x same formula, y=440-val*210):
  (70,383)(118,381)(166,388)(214,390)(262,377)(310,371)(358,373)(406,371)
  (454,360)(502,356)(550,335)(598,283)(646,220)(694,159)(742,69)(790,41)
Add <circle r:3 fill:#0D4D8C> at each point.
End label near x:790 y:41: '&#36;1.9tn' dx:4 font-size:10px font-weight:700 fill:#0D4D8C

--- ANNOTATION BOX ---
rect x:340 y:100 width:190 height:64 fill:#FFF8F8 stroke:#C41230 stroke-width:1 rx:2
text x:350 y:122 'Cost crossover' font-size:11px font-weight:700 fill:#C41230
text x:350 y:140 'Renewables now cheaper' font-size:9px fill:#555
text x:350 y:154 'than fossil in 95% of markets' font-size:9px fill:#555

--- LEGEND ---
rect x:70 y:454 width:320 height:30 fill:white stroke:#E8E8E8 rx:2
rect x:82 y:464 w:14 h:3 fill:#C41230 — text x:100 y:471 'Solar LCOE (falling)' font-size:10px fill:#333
rect x:222 y:464 w:14 h:3 fill:#0D4D8C stroke-dasharray:4 — text x:240 y:471 'Clean Investment (rising)' font-size:10px fill:#333

==== RIGHT KPI PANEL: position:absolute top:86px left:940px width:276px ====
Panel: top:86px left:940px width:276px height:510px background:#FAFAFA border:1px solid #E8E8E8
Title: top:102px left:956px font-size:11px font-weight:700 color:#1A1A1A 'Key metrics'
Rule: top:122px left:956px width:244px height:1px background:#E8E8E8

4 stat cards stacked (each 106px tall starting top:130px):
Card 1 (top:130): left border 3px solid #1B7A3E background:#F5FAF7
  top:146px left:968px: '$1.8tn' font-size:38px font-weight:800 color:#1B7A3E
  top:194px left:968px width:220px: 'Global clean energy investment 2024 &#x2014; first year exceeding fossil capex' font-size:9px color:#555 line-height:1.5

Card 2 (top:240): left border 3px solid #1A1A1A background:#FFFFFF
  '89%' font-size:38px font-weight:800 color:#1A1A1A (top:256px)
  'Fall in solar LCOE since 2010; grid parity in 135 countries' (top:304px) font-size:9px color:#555

Card 3 (top:350): left border 3px solid #888888
  '68%' font-size:38px font-weight:800 (top:366px)
  'of CFOs rank ESG capex as core to long-term value creation' (top:414px) font-size:9px color:#555

Card 4 (top:460): left border 3px solid #888888
  '2030' font-size:38px font-weight:800 (top:476px)
  'Year all new energy investment expected to be renewable-first globally' (top:524px) font-size:9px color:#555

==== FOOTER ====
top:672px left:64px font-size:9px color:#AAAAAA: 'Sources: IRENA 2025; BloombergNEF; IEA World Energy Investment'
top:672px right:64px font-size:9px color:#AAAAAA: '8'

==== NOTHING ELSE ====""",
    },

    # ─────────────────────────────────────────────────────────────────────────
    # 8 — DIGITAL INFRA DIVIDER (fix: title at 64px on 2 lines + subtitle below)
    # ─────────────────────────────────────────────────────────────────────────
    8: {
        "refs": ["roland_berger_trend_compendium_2050_technology_and_innovation_slide_005",
                 "roland_berger_trend_compendium_2050_technology_and_innovation_slide_006"],
        "brief": f"""Dark chapter divider. Exactly {W}x{H}px. Background: #05080F.

==== ELEMENTS (all absolute, none overlap) ====

Element A — left accent bar:
  top:0 left:0 width:5px height:720px background:#0D4D8C

Element B — chapter label:
  top:260px left:80px width:400px height:16px
  font-size:10px letter-spacing:5px color:#0D4D8C text-transform:uppercase font-weight:700
  content: 'FORCE 03'

Element C — thin rule:
  top:282px left:80px width:48px height:1px background:#0D4D8C

Element D — title line 1 ('Digital'):
  top:300px left:80px width:700px height:72px
  font-size:68px font-weight:800 color:#FFFFFF line-height:72px white-space:nowrap overflow:hidden

Element E — title line 2 ('Infrastructure'):
  top:372px left:80px width:900px height:72px
  font-size:68px font-weight:800 color:#FFFFFF line-height:72px white-space:nowrap overflow:hidden

Element F — subtitle (below both title lines, minimum top = 372+72+24 = 468px):
  top:468px left:80px width:640px
  font-size:16px color:#777777 line-height:1.6
  'Cloud-native architecture is the new competitive moat &#x2014; not just an IT decision'

Element G — page range:
  top:686px right:80px font-size:10px color:#2D2D2D
  'Slides 9&#x2013;10'

Element H — right abstract SVG:
  position:absolute top:0 right:0 width:480px height:720px
  Draw inside SVG ONLY:
    Dot grid: 12 cols x 9 rows, spacing 36px, starting x:20 y:40
    Each dot: r:2 fill:#0D4D8C opacity:0.20
  That is all — no other shapes.

==== NOTHING ELSE. No callout boxes, no extra text. ====
""",
    },

    # ─────────────────────────────────────────────────────────────────────────
    # 11 — DEMOGRAPHICS WATERFALL (fix: legend overlap + label readability)
    # ─────────────────────────────────────────────────────────────────────────
    11: {
        "refs": ["bain_global_pe_report_2023_slide_007",
                 "bain_global_pe_report_2023_slide_011",
                 "bain_china_luxury_2011_slide_008"],
        "brief": f"""Data slide: workforce waterfall chart. Exactly {W}x{H}px. Background #FFFFFF.

==== HEADER ====
Element A — orange rule: top:0 left:0 width:1280px height:3px background:#B35C00
Element B — kicker: top:16px left:64px font-size:9px letter-spacing:3px color:#B35C00 font-weight:700 'DEMOGRAPHICS | DATA'
Element C — headline: top:32px left:64px width:960px font-size:20px font-weight:700 color:#1A1A1A
  'By 2030, automation and demographics create a 58M-person talent gap in advanced economies'
Element D — sub: top:66px left:64px font-size:10px color:#888888
  'Net workforce impact 2025&#x2013;2030 (millions of workers), G7 economies'

==== WATERFALL SVG: position:absolute top:82px left:64px width:868px height:536px ====
Outer background: x:0 y:0 width:868 height:536 fill:#FAFAFA rx:2 stroke:#E8E8E8

PLOT AREA: x:80 y:20 to x:820 y:420 (740px wide, 400px tall)

SCALE: 1 million workers = 3.0px. Baseline (zero net change) = y:330. Each positive bar rises above y:330; each negative falls below.

Bar data — 7 bars, each width:72px, gap:14px:
Starting x of bar 1 = 88. Each bar starts at: 88, 174, 260, 346, 432, 518, 604.

Bar 1 (+45M, NEW ENTRANTS) — green:
  bar top = 330 - 45*3 = 330-135 = 195. SVG rect: x:88 y:195 width:72 height:135 fill:#1B7A3E rx:1
  label '+45M': x:124 y:188 text-anchor:middle font-size:10px font-weight:700 fill:#1B7A3E

Bar 2 (+18M, RESKILLED) — green:
  bar top = 330 - 18*3 = 330-54 = 276. rect: x:174 y:276 width:72 height:54 fill:#1B7A3E rx:1
  label '+18M': x:210 y:269 text-anchor:middle font-size:10px font-weight:700 fill:#1B7A3E

Bar 3 (-38M, RETIREMENT) — red:
  bar bottom = 330 + 38*3 = 330+114 = 444... but plot area ends at y:420. Clamp to y:420.
  bar top = 330. rect: x:260 y:330 width:72 height:90 fill:#C41230 rx:1  (use 90px = 30M shown, label actual -38M)
  Actually: let scale = 400/(58+71+38+24+45+18+12) = 400/266 = 1.5px/M

  REVISED SCALE: Use 1.5px/M so all bars fit. Baseline y:330.
  Positive bars rise above y:330. Negative bars fall below y:330. Net span = 58M * 1.5 = 87px below.

  Bar heights:
  +45M: height = 45*1.5 = 68px. top = 330-68 = 262.
  +18M: height = 18*1.5 = 27px. top = 330-27 = 303.
  -38M: height = 38*1.5 = 57px. top = 330.
  -71M: height = 71*1.5 = 107px. top = 330.
  -24M: height = 24*1.5 = 36px. top = 330.
  +12M: height = 12*1.5 = 18px. top = 330-18 = 312.
  -58M (NET): height = 58*1.5 = 87px. top = 330.

Draw these SVG rects:
  Bar 1 (+45M): x:88  y:262 width:72 height:68  fill:#1B7A3E rx:1
  Bar 2 (+18M): x:174 y:303 width:72 height:27  fill:#1B7A3E rx:1
  Bar 3 (-38M): x:260 y:330 width:72 height:57  fill:#C41230 rx:1
  Bar 4 (-71M): x:346 y:330 width:72 height:107 fill:#C41230 rx:1
  Bar 5 (-24M): x:432 y:330 width:72 height:36  fill:#E8A0A0 stroke:#C41230 stroke-width:1 rx:1
  Bar 6 (+12M): x:518 y:312 width:72 height:18  fill:#1B7A3E rx:1
  Bar 7 (-58M): x:604 y:330 width:72 height:87  fill:#8B0000 rx:1

Value labels ABOVE each bar (for positive) or BELOW (for negative, at bar bottom + 4px):
  '+45M': x:124 y:254 (8px above bar top) text-anchor:middle font-size:11px font-weight:700 fill:#1B7A3E
  '+18M': x:210 y:295 text-anchor:middle font-size:11px font-weight:700 fill:#1B7A3E
  '-38M': x:296 y:395 text-anchor:middle font-size:11px font-weight:700 fill:#C41230
  '-71M': x:382 y:445 text-anchor:middle font-size:11px font-weight:700 fill:#C41230
  '-24M': x:468 y:374 text-anchor:middle font-size:11px font-weight:700 fill:#C41230
  '+12M': x:554 y:304 text-anchor:middle font-size:11px font-weight:700 fill:#1B7A3E
  '-58M': x:640 y:425 text-anchor:middle font-size:12px font-weight:800 fill:#8B0000

Baseline: x:80 y:330 width:740 stroke:#888888 stroke-width:1.5
Horizontal gridlines at y:262 (45M level) and y:417 (58M below): stroke:#F0F0F0 stroke-width:1

Category labels BELOW x-axis (y:450), each horizontally centered on bar x-center, NO rotation:
  x:124 'New Entrants' | x:210 'Reskilled' | x:296 'Retirement' | x:382 'Automation'
  x:468 'Skill Mismatch' | x:554 'Migration' | x:640 'Net Gap'
  All: font-size:9px fill:#555555 text-anchor:middle

LEGEND row at y:490 x:88 — three items inline:
  Rect x:88 y:484 w:14 h:10 fill:#1B7A3E — text x:106 y:493 'Workforce gain' font-size:10px fill:#333
  Rect x:230 y:484 w:14 h:10 fill:#C41230 — text x:248 y:493 'Workforce loss' font-size:10px fill:#333
  Rect x:372 y:484 w:14 h:10 fill:#8B0000 — text x:390 y:493 'Net talent gap' font-size:10px fill:#333

Ref line label at x:84 y:326 'Zero net change' font-size:8px fill:#888 text-anchor:end

==== RIGHT KPI PANEL: position:absolute top:82px left:956px width:260px height:536px ====
background:#FAFAFA border:1px solid #E8E8E8

3 stat cards stacked (each 164px):
Card 1 (top:98px): left border 3px solid #B35C00 background:#FFF8F0
  '58M' font-size:44px font-weight:800 color:#B35C00 (top:114px left:972px)
  'talent gap projected in G7 by 2030 &#x2014; widening at 8M per year' font-size:9px color:#555 width:212px (top:168px)

Card 2 (top:266px): left border 3px solid #1A1A1A
  '2.8&#xD7;' font-size:44px font-weight:800 color:#1A1A1A (top:282px)
  'reskilling investment shortfall vs. demand; corporate training lags' font-size:9px color:#555 (top:336px)

Card 3 (top:434px): left border 3px solid #888888
  '40%' font-size:44px font-weight:800 color:#1A1A1A (top:450px)
  'of current roles substantially transformed; 12% fully displaced by 2030' font-size:9px color:#555 (top:504px)

==== FOOTER ====
top:672px left:64px: 'Sources: WEF Future of Jobs 2025; McKinsey Global Institute; OECD' font-size:9px color:#AAAAAA
top:672px right:64px: '12' font-size:9px color:#AAAAAA

==== NOTHING ELSE ====""",
    },

    # ─────────────────────────────────────────────────────────────────────────
    # 12 — GEOPOLITICS DIVIDER (fix: simplify, prevent overlaps, no callout box)
    # ─────────────────────────────────────────────────────────────────────────
    12: {
        "refs": ["roland_berger_trend_compendium_2050_technology_and_innovation_slide_005",
                 "roland_berger_trend_compendium_2050_technology_and_innovation_slide_006"],
        "brief": f"""Dark chapter divider. Exactly {W}x{H}px. Background: #0A000F.

This slide has EXACTLY SEVEN elements listed below. Do NOT add anything else — no callout boxes, no extra text blocks, no icons, no additional sections.

Element 1 — left accent bar:
  position:absolute top:0 left:0 width:5px height:720px background:#5C2D91

Element 2 — chapter tag:
  position:absolute top:268px left:80px width:300px height:16px
  font-size:10px letter-spacing:5px color:#5C2D91 text-transform:uppercase font-weight:700
  content exactly: 'FORCE 05'

Element 3 — thin rule:
  position:absolute top:290px left:80px width:48px height:1px background:#5C2D91

Element 4 — title line 1 'Geopolitical Risk':
  position:absolute top:308px left:80px width:900px height:80px
  font-size:72px font-weight:800 color:#FFFFFF line-height:80px white-space:nowrap overflow:hidden

Element 5 — subtitle text (starts at top:308+80+32=420px minimum):
  position:absolute top:420px left:80px width:620px
  font-size:17px color:#777777 line-height:1.6
  content: 'Supply chain rewiring and regulatory divergence are reshaping competitive geography'

Element 6 — page range:
  position:absolute top:686px right:80px font-size:10px color:#2E2E2E
  content: 'Slides 13&#x2013;14'

Element 7 — right abstract SVG:
  position:absolute top:0 right:0 width:560px height:720px
  Draw ONLY a network graph: 9 nodes connected by lines.
  Node positions (cx, cy, r=8, fill=#5C2D91 opacity=0.7):
    (200,180) (320,140) (420,220) (480,360) (360,460)
    (240,440) (140,320) (380,280) (300,340)
  Lines between adjacent nodes (stroke:#5C2D91 opacity:0.25 stroke-width:1):
    Connect: 0-1, 1-2, 2-3, 3-4, 4-5, 5-6, 6-0, 7-1, 7-2, 7-8, 8-3, 8-4, 8-5
  That is all inside the SVG.

THAT IS ALL SEVEN ELEMENTS. NO MORE.""",
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck",   default="../full_deck_v3.html")
    parser.add_argument("--slides", default="0,7,8,11,12",
                        help="Comma-separated slide indices to fix")
    args = parser.parse_args()

    deck_path = (Path(__file__).parent / args.deck).resolve()
    if not deck_path.exists():
        print(f"[!] Deck not found: {deck_path}")
        return

    indices = [int(x.strip()) for x in args.slides.split(",")]
    print(f"Fixing slides {indices} in {deck_path.name}\n")

    for idx in indices:
        if idx not in SPECS:
            print(f"  [skip] no spec for index {idx}")
            continue
        spec = SPECS[idx]
        html = generate(spec["refs"], spec["brief"], f"slide {idx+1}")
        patch(deck_path, idx, html)
        if idx != indices[-1]:
            time.sleep(0.4)

    print("\nAll done.")


if __name__ == "__main__":
    main()
