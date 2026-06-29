"""
generate_sample_deck_rb_data.py — Data-intensive Roland Berger style slides.

4 slides, each built around a real chart with fully pre-computed SVG coordinates:
  1. Scatter / bubble chart — European firm positioning (adoption vs. productivity)
  2. Stacked bar chart + line overlay — 5-year investment trends by technology type
  3. Heat map matrix — Technology maturity by country × dimension (6×5 grid)
  4. Multi-donut dashboard — Investment allocation by region with KPI cards

Output: pptmaker/sample_deck_rb_data.html
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

ROOT     = Path(__file__).parent.parent
HTML_DIR = ROOT / "html_slides"
OUT      = ROOT / "sample_deck_rb_data.html"

W, H = 1280, 720

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
)

SYSTEM_PROMPT = f"""You are a senior front-end developer creating pixel-perfect Roland Berger style HTML/CSS presentation slides.

Roland Berger visual identity:
  • White backgrounds (#ffffff) for all content slides
  • Primary blue: #1c78b0 (rules, kickers, bars, axis labels, card borders)
  • Dark blue: #1c5fa8 (large KPI numbers, filled bars, bubble fills)
  • Medium blue: #4a9fd4 (secondary bars, medium-intensity fills)
  • Light blue: #7ab8e8 (tertiary fills, light chart elements)
  • Near-black body: #1c2a3a · Supporting grey: #4a5a6a · Muted: #6a7a8a · Footnote: #9aa0a8
  • 2px horizontal blue rule at top of every content slide (left:64px, width:1152px, background:#1c78b0)
  • Uppercase kicker below rule: 10px, letter-spacing:2px, color:#1c78b0
  • Bold assertion headline below kicker: 22–26px, font-weight:700, color:#1c2a3a
  • Source footnote bottom-left: 10px, color:#9aa0a8

SVG CHARTS — you will receive exact pre-computed coordinates. Use them as given.
  • Inline SVG is allowed. No <canvas>, no <script>, no <img>.
  • Every <text> element needs font-family:Arial,Helvetica,sans-serif and explicit font-size.
  • Use text-anchor="middle" for centred labels, "end" for right-aligned.
  • Axis lines: stroke:#c0c8d0, stroke-width:1.
  • Grid lines: stroke:#e0e8f0, stroke-width:1, stroke-dasharray:4,3.
  • Chart background: no fill (transparent) — slide background shows through.

STRICT REQUIREMENTS:
1.  <!DOCTYPE html> at top
2.  All CSS in <style> in <head>
3.  Root: exactly {W}px × {H}px, position:relative, overflow:hidden
4.  NO <script> · NO <img> · NO external URLs
5.  System fonts only: Arial, Helvetica, 'Segoe UI'
6.  Implement EVERY chart element described — do not omit bars, bubbles, grid lines, or labels
7.  Output ONLY the complete HTML — no explanation, no markdown
8.  Last line must be </html>. Never truncate."""


# Pre-computed SVG coordinates are embedded directly in each brief.
SLIDES = [

    # ──────────────────────────────────────────────────────────────────────────
    # SLIDE 1: SCATTER / BUBBLE CHART
    # ──────────────────────────────────────────────────────────────────────────
    {
        "ref": "roland_berger_trend_compendium_2050_technology_and_innovation_slide_010",
        "brief": """Scatter/bubble chart slide. White background #ffffff. Font: Arial.

HEADER (position:absolute):
  Blue rule: top:44px, left:64px, width:1152px, height:2px, background:#1c78b0.
  Kicker: top:56px, left:64px. Text: 'TECHNOLOGY ADOPTION vs. PRODUCTIVITY GROWTH — EUROPEAN FIRMS 2025'
    font-size:10px, color:#1c78b0, letter-spacing:2px, text-transform:uppercase.
  Headline: top:74px, left:64px, width:1060px.
    Text: 'Leaders combine broad adoption with high productivity returns — the centre of gravity is shifting right'
    font-size:24px, font-weight:700, color:#1c2a3a, line-height:1.2.

SVG CHART (position:absolute, top:142px, left:64px, width:1152px, height:534px):
  Use: <svg xmlns="http://www.w3.org/2000/svg" width="1152" height="534" style="position:absolute;top:142px;left:64px">

  CHART AREA: data maps to pixel range x:[90,1140] y:[20,490]. Axes at x=90 (Y-axis) and y=490 (X-axis).

  GRID LINES (stroke:#e0e8f0, stroke-width:1, stroke-dasharray:4,3):
    Horizontal: y=380 y=270 y=160 y=50 — each from x=90 to x=1140.
    Vertical:   x=294 x=499 x=703 x=908 — each from y=20 to y=490.

  AXES (stroke:#c0c8d0, stroke-width:1.5):
    X-axis: line x1=90 y1=490 x2=1140 y2=490.
    Y-axis: line x1=90 y1=20  x2=90  y2=490.

  X-AXIS TICKS AND LABELS (font-size:11, fill:#6a7a8a, text-anchor:middle, y=505):
    0→x=90, 20→x=294, 40→x=499, 60→x=703, 80→x=908, 100→x=1112.
    Tick marks: line y1=490 y2=496 at each x above, stroke:#9aa0a8.
  X-AXIS TITLE (font-size:12, fill:#4a5a6a, text-anchor:middle, x=615, y=528):
    'Technology Adoption Index [0–100]'

  Y-AXIS TICKS AND LABELS (font-size:11, fill:#6a7a8a, text-anchor:end, x=82):
    0%→y=490, 10%→y=380, 20%→y=270, 30%→y=160, 40%→y=50.
    Tick marks: line x1=84 x2=90 at each y above, stroke:#9aa0a8.
  Y-AXIS TITLE (font-size:12, fill:#4a5a6a, text-anchor:middle):
    <text transform="rotate(-90)" x="-255" y="22">Productivity Growth 3-yr CAGR [%]</text>

  QUADRANT DIVIDERS (stroke:#1c78b0, stroke-width:1, stroke-dasharray:6,4, opacity:0.4):
    Vertical at x=703: line x1=703 y1=20  x2=703 y2=490.
    Horizontal at y=270: line x1=90  y1=270 x2=1140 y2=270.

  QUADRANT LABELS (font-size:11, font-weight:600, opacity:0.55):
    'TRANSFORMATION LEADERS' fill:#1c5fa8 at x=870 y=44 text-anchor:middle.
    'EFFICIENT LAGGARDS'     fill:#6a7a8a at x=290 y=244 text-anchor:middle.
    'TECHNOLOGISTS'          fill:#4a9fd4 at x=870 y=430 text-anchor:middle.
    'DIGITAL STRAGGLERS'     fill:#c0392b at x=290 y=460 text-anchor:middle.

  BUBBLES — each is a <circle> with fill, stroke:#fff, stroke-width:1.5, opacity:0.85.
  Then a <text> label near each bubble (font-size:10, fill:#1c2a3a, font-weight:600).

  Bubble data (cx, cy, r, fill, label, label-dx, label-dy):
    Siemens:       cx=826 cy=119 r=22 fill=#1c5fa8  label="Siemens"       dx=28  dy=-4
    Airbus:        cx=887 cy=97  r=24 fill=#1c5fa8  label="Airbus"        dx=30  dy=-4
    Philips:       cx=846 cy=141 r=16 fill=#1c5fa8  label="Philips"       dx=22  dy=14
    ABB:           cx=785 cy=152 r=18 fill=#1c5fa8  label="ABB"           dx=24  dy=4
    Bosch:         cx=754 cy=196 r=20 fill=#1c78b0  label="Bosch"         dx=26  dy=4
    Volkswagen:    cx=652 cy=229 r=25 fill=#4a9fd4  label="VW Group"      dx=-30 dy=-14
    BASF:          cx=550 cy=262 r=16 fill=#4a9fd4  label="BASF"          dx=-22 dy=4
    Renault:       cx=519 cy=317 r=18 fill=#7ab8e8  label="Renault"       dx=-24 dy=4
    Stellantis:    cx=489 cy=339 r=20 fill=#7ab8e8  label="Stellantis"    dx=-28 dy=4
    Thyssenkrupp:  cx=478 cy=350 r=15 fill=#b8d0e8  label="ThyssenKrupp" dx=22  dy=14
    US Average:    cx=928 cy=53  r=30 fill=#e8813a  stroke=#e8813a label="US Avg" dx=36 dy=4
    Asia Average:  cx=897 cy=86  r=28 fill=#2e8b57  stroke=#2e8b57 label="Asia Avg" dx=34 dy=4

  For each bubble use: <circle cx=".." cy=".." r=".." fill=".." stroke="#fff" stroke-width="1.5" opacity="0.88"/>
  Then: <text x="{cx+dx}" y="{cy+dy}" font-size="10" font-family="Arial" fill="#1c2a3a" font-weight="600">{label}</text>

  LEGEND (bottom-right of SVG, around x=1000, y=480):
    Three rows, each: a circle (r=6) + label text.
    Row 1: circle cx=1000 cy=480 r=6 fill=#1c5fa8 · text x=1012 y=484 'European leaders'  fill=#1c2a3a font-size:11
    Row 2: circle cx=1000 cy=496 r=6 fill=#7ab8e8 · text x=1012 y=500 'EU mid-tier'        fill=#1c2a3a font-size:11
    Row 3: circle cx=1000 cy=512 r=6 fill=#e8813a · text x=1012 y=516 'Regional average'   fill=#1c2a3a font-size:11
    Note: bubble size represents relative revenue scale.
    text x=1000 y=530 font-size:9 fill:#9aa0a8 'Bubble size = relative revenue'

FOOTNOTE (position:absolute, top:686px, left:64px):
  font-size:10px, color:#9aa0a8.
  'Sources: Roland Berger Technology Adoption Survey 2025; company annual reports; n=127 firms'""",
    },

    # ──────────────────────────────────────────────────────────────────────────
    # SLIDE 2: STACKED BAR CHART + LINE OVERLAY
    # ──────────────────────────────────────────────────────────────────────────
    {
        "ref": "roland_berger_trend_compendium_2050_technology_and_innovation_slide_010",
        "brief": """Stacked bar chart with total-line overlay. White background #ffffff.

HEADER:
  Blue rule: top:44px, left:64px, width:1152px, height:2px, background:#1c78b0.
  Kicker: top:56px, left:64px. 'EUROPEAN INDUSTRIAL TECHNOLOGY INVESTMENT 2020–2024'
    font-size:10px, color:#1c78b0, letter-spacing:2px, text-transform:uppercase.
  Headline: top:74px, left:64px, width:900px.
    'Software & AI has overtaken automation hardware as the largest investment category — total spend up 115%'
    font-size:23px, font-weight:700, color:#1c2a3a, line-height:1.2.

RIGHT KPI PANEL (position:absolute, top:74px, left:980px, width:272px):
  Three stat rows, each separated by a 1px #e0e6ec line:
  Row 1 (top:74px):  '€206bn' font-size:30px, font-weight:700, color:#1c5fa8.
                     'Total EU tech investment 2024' font-size:12px, color:#4a5a6a, top:+36px.
  Row 2 (top:148px): '+115%'  font-size:30px, font-weight:700, color:#2a8a4a.
                     'Growth vs. 2020 baseline'       font-size:12px, color:#4a5a6a.
  Row 3 (top:222px): '+21%'   font-size:30px, font-weight:700, color:#1c78b0.
                     '5-year investment CAGR'          font-size:12px, color:#4a5a6a.

SVG CHART (position:absolute, top:152px, left:64px, width:900px, height:510px):
  <svg xmlns="http://www.w3.org/2000/svg" width="900" height="510" style="position:absolute;top:152px;left:64px">

  GRID LINES (stroke:#e0e8f0, stroke-width:1, stroke-dasharray:4,3):
    Horizontal at y=348, y=245, y=143, y=40 — each x1=60 x2=870.

  AXES:
    X-axis: line x1=60 y1=450 x2=870 y2=450 stroke=#c0c8d0 stroke-width=1.5.
    Y-axis: line x1=60 y1=20  x2=60  y2=450 stroke=#c0c8d0 stroke-width=1.5.

  Y-AXIS LABELS (text-anchor:end, x=52, font-size:11, fill:#6a7a8a):
    y=450→'0', y=348→'50', y=245→'100', y=143→'150', y=40→'200'.
  Y-AXIS TITLE: <text transform="rotate(-90)" x="-225" y="16" font-size:11 fill:#4a5a6a text-anchor:middle>Investment (€bn)</text>

  X-AXIS LABELS (text-anchor:middle, y=466, font-size:12, fill:#1c2a3a, font-weight:600):
    x=162→'2020', x=314→'2021', x=466→'2022', x=618→'2023', x=770→'2024'.

  5 STACKED BARS — each bar is 4 stacked <rect> elements, rendered bottom-up.
  Colors: Automation=#1c5fa8 · Software/AI=#1c78b0 · Cloud=#4a9fd4 · Training=#7ab8e8

  Bar 2020 (x=112, w=100):
    Automation: rect x=112 y=364 w=100 h=86  fill=#1c5fa8
    Software/AI: rect x=112 y=307 w=100 h=57  fill=#1c78b0
    Cloud:       rect x=112 y=270 w=100 h=37  fill=#4a9fd4
    Training:    rect x=112 y=254 w=100 h=16  fill=#7ab8e8
    Total label: text x=162 y=244 '€96bn' font-size=11 fill=#1c2a3a text-anchor=middle font-weight=700

  Bar 2021 (x=264, w=100):
    Automation: rect x=264 y=352 w=100 h=98  fill=#1c5fa8
    Software/AI: rect x=264 y=280 w=100 h=72  fill=#1c78b0
    Cloud:       rect x=264 y=231 w=100 h=49  fill=#4a9fd4
    Training:    rect x=264 y=211 w=100 h=20  fill=#7ab8e8
    Total label: text x=314 y=201 '€117bn' font-size=11 fill=#1c2a3a text-anchor=middle font-weight=700

  Bar 2022 (x=416, w=100):
    Automation: rect x=416 y=344 w=100 h=106 fill=#1c5fa8
    Software/AI: rect x=416 y=246 w=100 h=98  fill=#1c78b0
    Cloud:       rect x=416 y=183 w=100 h=63  fill=#4a9fd4
    Training:    rect x=416 y=156 w=100 h=27  fill=#7ab8e8
    Total label: text x=466 y=146 '€144bn' font-size=11 fill=#1c2a3a text-anchor=middle font-weight=700

  Bar 2023 (x=568, w=100):
    Automation: rect x=568 y=335 w=100 h=115 fill=#1c5fa8
    Software/AI: rect x=568 y=208 w=100 h=127 fill=#1c78b0
    Cloud:       rect x=568 y=130 w=100 h=78  fill=#4a9fd4
    Training:    rect x=568 y=97  w=100 h=33  fill=#7ab8e8
    Total label: text x=618 y=87  '€172bn' font-size=11 fill=#1c2a3a text-anchor=middle font-weight=700

  Bar 2024 (x=720, w=100):
    Automation: rect x=720 y=325 w=100 h=125 fill=#1c5fa8
    Software/AI: rect x=720 y=163 w=100 h=162 fill=#1c78b0
    Cloud:       rect x=720 y=67  w=100 h=96  fill=#4a9fd4
    Training:    rect x=720 y=28  w=100 h=39  fill=#7ab8e8
    Total label: text x=770 y=18  '€206bn' font-size=11 fill=#1c2a3a text-anchor=middle font-weight=700

  TOTAL LINE OVERLAY (connecting tops of each stacked bar):
    Polyline: points="162,254 314,211 466,156 618,97 770,28"
    stroke=#1c2a3a stroke-width=2 fill=none stroke-dasharray=none.
    Add dots at each point: circle r=4 fill=#1c2a3a at each coordinate.

  CAGR ANNOTATION (arrow label near the line):
    Line from (162,250) to (770,24): skip this, just add a text label.
    text x=466 y=96 '+21% CAGR' font-size=12 fill=#1c2a3a font-weight=700 text-anchor=middle.
    Small upward arrow using SVG path: M 420,96 L 412,88 M 420,96 L 428,88 stroke=#1c2a3a stroke-width=1.5 fill=none.

  LEGEND (bottom of chart SVG, y=492):
    Four legend items, each: rect (12×12) + text label.
    Item 1: rect x=60  y=478 w=12 h=12 fill=#1c5fa8 · text x=78  y=489 'Automation Hardware'  font-size=11
    Item 2: rect x=230 y=478 w=12 h=12 fill=#1c78b0 · text x=248 y=489 'Software & AI'         font-size=11
    Item 3: rect x=360 y=478 w=12 h=12 fill=#4a9fd4 · text x=378 y=489 'Cloud & Infrastructure' font-size=11
    Item 4: rect x=530 y=478 w=12 h=12 fill=#7ab8e8 · text x=548 y=489 'Training & Change Mgmt' font-size=11
    All text: fill=#4a5a6a, font-size=11, font-family=Arial.

FOOTNOTE (position:absolute, top:676px, left:64px):
  font-size:10px, color:#9aa0a8.
  'Sources: Eurostat ICT Investment Statistics; IDC European Technology Tracker; Roland Berger analysis'""",
    },

    # ──────────────────────────────────────────────────────────────────────────
    # SLIDE 3: HEAT MAP MATRIX
    # ──────────────────────────────────────────────────────────────────────────
    {
        "ref": "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_013",
        "brief": """Technology maturity heat map. White background #ffffff.

HEADER:
  Blue rule: top:44px, left:64px, width:1152px, height:2px, background:#1c78b0.
  Kicker: top:56px, left:64px. 'TECHNOLOGY MATURITY INDEX — EUROPE BY COUNTRY AND DIMENSION [0–100]'
    font-size:10px, color:#1c78b0, letter-spacing:2px, text-transform:uppercase.
  Headline: top:74px, left:64px, width:900px.
    'Sweden and Germany lead — Poland and Italy face a compounding technology maturity deficit across all five dimensions'
    font-size:23px, font-weight:700, color:#1c2a3a, line-height:1.2.
    (2 lines × ~28px = 56px tall. Ends at top:130px.)

COLUMN HEADERS (position:absolute, top:134px):
  5 technology headers, each 172px wide, centred in column.
  font-size:11px, font-weight:700, color:#1c2a3a, text-align:center, text-transform:uppercase, letter-spacing:0.5px.
  Col 1 'AUTOMATION': left:200px,  width:172px.
  Col 2 'AI / ML':    left:372px,  width:172px.
  Col 3 'DIGITAL TWIN': left:544px, width:172px.
  Col 4 'CLOUD':      left:716px,  width:172px.
  Col 5 'CYBERSEC':   left:888px,  width:172px.
  6th header 'INDEX': left:1082px, width:134px. color:#1c78b0.

ROW LABELS (position:absolute for each, left:64px, width:130px, font-size:13px, font-weight:600, color:#1c2a3a):
  Each row is 76px tall. Row tops: 148, 224, 300, 376, 452, 528.
  Row 1 label: 'Sweden'       top:148px (vertical-centre in row = top:178px, line-height:76px).
  Row 2 label: 'Germany'      top:224px.
  Row 3 label: 'Netherlands'  top:300px.
  Row 4 label: 'France'       top:376px.
  Row 5 label: 'Italy'        top:452px.
  Row 6 label: 'Poland'       top:528px.
  (For each label: position:absolute, left:64px, top:[row_top]px, width:130px, height:76px,
   display:flex, align-items:center. font-size:13px, font-weight:600, color:#1c2a3a.)

HEAT MAP CELLS — 30 cells (6 rows × 5 cols) + 6 index cells.
Each cell: position:absolute, width:172px (index col: 134px), height:76px.
Cell content: score number centred, font-size:20px, font-weight:700.
White text if score ≥ 65; dark (#1c2a3a) if score < 65.

Color scale:
  score < 35:  background:#eaf3fb (very light)
  35–50:       background:#b8d8f0 (light blue)
  50–65:       background:#7ab8e8 (medium blue)
  65–75:       background:#4a9fd4 (medium-dark)
  75–85:       background:#1c78b0 (dark blue)
  85+:         background:#1c5fa8 (darkest blue)

Cell positions — left = 200 + (col_index × 172). top = 148 + (row_index × 76).
Col indices: 0=Automation, 1=AI, 2=Digital Twin, 3=Cloud, 4=Cybersec.
Index col (6th): left=1082.

ROW 0 — SWEDEN (top:148):
  Auto=82:  left:200  bg:#1c5fa8 text:white
  AI=70:    left:372  bg:#4a9fd4 text:white
  DT=65:    left:544  bg:#4a9fd4 text:white
  Cloud=78: left:716  bg:#1c78b0 text:white
  Cyber=80: left:888  bg:#1c5fa8 text:white
  Index=75: left:1082 bg:#1c78b0 text:white  font-size:18px (avg of 5)

ROW 1 — GERMANY (top:224):
  Auto=78:  left:200  bg:#1c78b0 text:white
  AI=62:    left:372  bg:#7ab8e8 text:#1c2a3a
  DT=54:    left:544  bg:#7ab8e8 text:#1c2a3a
  Cloud=71: left:716  bg:#4a9fd4 text:white
  Cyber=75: left:888  bg:#1c78b0 text:white
  Index=68: left:1082 bg:#4a9fd4 text:white

ROW 2 — NETHERLANDS (top:300):
  Auto=71:  left:200  bg:#4a9fd4 text:white
  AI=64:    left:372  bg:#7ab8e8 text:#1c2a3a
  DT=58:    left:544  bg:#7ab8e8 text:#1c2a3a
  Cloud=74: left:716  bg:#4a9fd4 text:white
  Cyber=72: left:888  bg:#4a9fd4 text:white
  Index=68: left:1082 bg:#4a9fd4 text:white

ROW 3 — FRANCE (top:376):
  Auto=65:  left:200  bg:#4a9fd4 text:white
  AI=55:    left:372  bg:#7ab8e8 text:#1c2a3a
  DT=48:    left:544  bg:#b8d8f0 text:#1c2a3a
  Cloud=68: left:716  bg:#4a9fd4 text:white
  Cyber=70: left:888  bg:#4a9fd4 text:white
  Index=61: left:1082 bg:#7ab8e8 text:#1c2a3a

ROW 4 — ITALY (top:452):
  Auto=52:  left:200  bg:#7ab8e8 text:#1c2a3a
  AI=41:    left:372  bg:#b8d8f0 text:#1c2a3a
  DT=38:    left:544  bg:#b8d8f0 text:#1c2a3a
  Cloud=58: left:716  bg:#7ab8e8 text:#1c2a3a
  Cyber=62: left:888  bg:#7ab8e8 text:#1c2a3a
  Index=50: left:1082 bg:#7ab8e8 text:#1c2a3a

ROW 5 — POLAND (top:528):
  Auto=45:  left:200  bg:#b8d8f0 text:#1c2a3a
  AI=35:    left:372  bg:#b8d8f0 text:#1c2a3a
  DT=30:    left:544  bg:#eaf3fb text:#1c2a3a
  Cloud=52: left:716  bg:#7ab8e8 text:#1c2a3a
  Cyber=48: left:888  bg:#b8d8f0 text:#1c2a3a
  Index=42: left:1082 bg:#b8d8f0 text:#1c2a3a

GRID LINES between cells (1px, #d0d8e4):
  Horizontal rules at top:224, top:300, top:376, top:452, top:528, top:604 (width:1152px, left:64px)
  Vertical rule at left:200 (height:456px, top:148px, width:1px, background:#d0d8e4)
  Vertical rule at left:372 same dimensions.
  Vertical rule at left:544, left:716, left:888, left:1060, left:1082.

COLOUR SCALE LEGEND (position:absolute, top:616px, left:200px):
  5 coloured blocks (each 80px wide × 18px tall) + labels below.
  Block 1: left:200  bg:#eaf3fb label:'<35'
  Block 2: left:280  bg:#b8d8f0 label:'35–50'
  Block 3: left:360  bg:#7ab8e8 label:'50–65'
  Block 4: left:440  bg:#4a9fd4 label:'65–75'
  Block 5: left:520  bg:#1c78b0 label:'75–85'
  Block 6: left:600  bg:#1c5fa8 label:'85+'
  Text labels below each block (top:638px): font-size:10px, color:#6a7a8a, text-align:center.
  Legend title at left:64px top:617px: 'Index score:' font-size:10px, color:#6a7a8a.

FOOTNOTE (top:668px, left:64px):
  font-size:10px, color:#9aa0a8.
  'Sources: Roland Berger Technology Adoption Survey 2025; n=842 firms across DE, FR, IT, PL, SE, NL · Index: unweighted average across five dimensions'""",
    },

    # ──────────────────────────────────────────────────────────────────────────
    # SLIDE 4: MULTI-DONUT DASHBOARD
    # ──────────────────────────────────────────────────────────────────────────
    {
        "ref": "roland_berger_european_pe_outlook_1_slide_002",
        "brief": """Four-donut dashboard showing technology investment allocation by region. White background #ffffff.

HEADER:
  Blue rule: top:44px, left:64px, width:1152px, height:2px, background:#1c78b0.
  Kicker: top:56px, left:64px. 'TECHNOLOGY INVESTMENT ALLOCATION BY REGION — 2024'
    font-size:10px, color:#1c78b0, letter-spacing:2px, text-transform:uppercase.
  Headline: top:74px, left:64px, width:1000px.
    'Software and AI dominates UK and Nordic investment — German firms still over-index on hardware'
    font-size:23px, font-weight:700, color:#1c2a3a, line-height:1.2.

4 DONUT PANELS arranged in a 2×2 grid (top-left, top-right, bottom-left, bottom-right):
  Panel dimensions: 280px wide, 260px tall.
  Positions: TL(top:152px, left:64px) · TR(top:152px, left:704px) · BL(top:428px, left:64px) · BR(top:428px, left:704px)

For each panel, the structure is:
  Region label: top:0 of panel, font-size:14px, font-weight:700, color:#1c2a3a, text-align:center.
  Donut chart (SVG centred in panel): below label at y:+24px within panel.
  Total investment label (centred inside donut hole): font-size:18px, font-weight:700, color:#1c5fa8.
  Legend: below donut at y:+196px of panel, 4 rows of colour swatch + % + label.

DONUT CONSTRUCTION:
  SVG: 180×180px, donut centred at (90,90), r=70, stroke-width=28.
  Inner circle (white hole): circle cx=90 cy=90 r=56 fill=white.
  Circumference C = 2π×70 = 439.82px.

  Each segment: <circle cx=90 cy=90 r=70 fill=none stroke=COLOR stroke-width=28
    stroke-dasharray="SHARE_PX REST_PX" stroke-dashoffset=OFFSET
    transform="rotate(-90 90 90)">
  Offset = -(cumulative_previous × C / 100) — but since C is the circumference,
  offset = -cumulative_degrees_in_px where each % = 439.82/100 = 4.398px per %.

PANEL 1 — GERMANY (TL: top:152px, left:64px):
  Total: €58bn. Region label: 'Germany — €58bn'
  Segments:
    Automation 38% → 167.1px; offset=0.        stroke=#1c5fa8
    Software/AI 26% → 114.4px; offset=-167.1.  stroke=#1c78b0
    Cloud 22% → 96.8px; offset=-281.5.         stroke=#4a9fd4
    Training 14% → 61.6px; offset=-378.3.      stroke=#7ab8e8
  Centre text: '€58bn'
  Legend: Automation 38% · Software/AI 26% · Cloud 22% · Training 14%

PANEL 2 — FRANCE (TR: top:152px, left:704px):
  Total: €31bn. Region label: 'France — €31bn'
  Segments:
    Automation 28% → 123.1px; offset=0.        stroke=#1c5fa8
    Software/AI 34% → 149.5px; offset=-123.1.  stroke=#1c78b0
    Cloud 25% → 109.9px; offset=-272.6.        stroke=#4a9fd4
    Training 13% → 57.2px; offset=-382.5.      stroke=#7ab8e8
  Centre text: '€31bn'
  Legend: Automation 28% · Software/AI 34% · Cloud 25% · Training 13%

PANEL 3 — UNITED KINGDOM (BL: top:428px, left:64px):
  Total: €44bn. Region label: 'United Kingdom — €44bn'
  Segments:
    Automation 22% → 96.8px; offset=0.         stroke=#1c5fa8
    Software/AI 42% → 184.7px; offset=-96.8.   stroke=#1c78b0
    Cloud 27% → 118.7px; offset=-281.5.        stroke=#4a9fd4
    Training 9%  → 39.6px; offset=-400.2.      stroke=#7ab8e8
  Centre text: '€44bn'
  Legend: Automation 22% · Software/AI 42% · Cloud 27% · Training 9%

PANEL 4 — NORDICS (BR: top:428px, left:704px):
  Total: €27bn. Region label: 'Nordics — €27bn'
  Segments:
    Automation 26% → 114.4px; offset=0.        stroke=#1c5fa8
    Software/AI 38% → 167.1px; offset=-114.4.  stroke=#1c78b0
    Cloud 24% → 105.6px; offset=-281.5.        stroke=#4a9fd4
    Training 12% → 52.8px; offset=-387.1.      stroke=#7ab8e8
  Centre text: '€27bn'
  Legend: Nordics 26%/38%/24%/12%

CENTRE PANEL (between the 4 donuts, left:360px, top:152px, width:328px, height:536px):
  This is the analytical summary column.
  Header: 'KEY TAKEAWAYS' top:152px, left:360px. font-size:11px, font-weight:700, color:#1c2a3a, letter-spacing:1.5px, text-transform:uppercase.
  Three insight cards stacked vertically (top:178px, left:360px, width:308px):

  Card 1 (top:178px, height:148px, background:#f5f8fb, border-left:3px solid #1c78b0, padding:16px 18px):
    Stat '+16pp' font-size:34px, font-weight:700, color:#1c5fa8.
    Label 'higher Software/AI share in UK vs. Germany — the widest inter-country gap in the study.'
    font-size:12px, color:#4a5a6a, line-height:1.5, margin-top:8px.

  Card 2 (top:334px, same style):
    Stat '€160bn' font-size:34px, font-weight:700, color:#1c5fa8.
    Label 'total investment across four regions — Germany alone accounts for 36% of the pool.'

  Card 3 (top:490px, same style, height:124px):
    Stat '2026' font-size:34px, font-weight:700, color:#c0392b.
    Label 'year by which Software/AI is projected to account for >40% of investment in all four regions.'

LEGEND SHARED (bottom of slide, top:668px, left:64px):
  Four swatches + labels in one row:
  swatch(12×12 #1c5fa8) 'Automation Hardware' · swatch(#1c78b0) 'Software & AI' · swatch(#4a9fd4) 'Cloud & Infra' · swatch(#7ab8e8) 'Training'
  Each swatch gap: 28px. font-size:10px, color:#4a5a6a. All inline.

FOOTNOTE (top:686px, left:64px):
  font-size:10px, color:#9aa0a8.
  'Sources: IDC European IT Spending Guide 2024; Eurostat; Roland Berger regional office analysis'""",
    },
]


def read_ref(slide_id: str) -> str:
    path = HTML_DIR / f"{slide_id}.html"
    if not path.exists():
        print(f"  WARN: reference not found: {slide_id}")
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def generate_slide(brief: str, ref_html: str, idx: int, total: int) -> str:
    print(f"  Generating slide {idx+1}/{total} ...", end=" ", flush=True)

    user_content = (
        f"Create a data-intensive {W}×{H}px HTML/CSS presentation slide.\n\n"
        f"SLIDE BRIEF — implement every chart element with the exact coordinates and dimensions given:\n{brief}\n\n"
        f"STYLE REFERENCE — use this real Roland Berger slide for colour palette, typography, and spacing conventions. "
        f"Do NOT copy its content — generate new content from the brief:\n\n"
        f"{ref_html}"
    )

    resp = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ],
        max_completion_tokens=16384,
    )

    raw = resp.choices[0].message.content or ""
    m = re.search(r"```(?:html)?\s*(<!DOCTYPE.*?</html>)\s*```", raw, re.DOTALL | re.IGNORECASE)
    if m:
        html = m.group(1).strip()
    else:
        m = re.search(r"(<!DOCTYPE.*?</html>)", raw, re.DOTALL | re.IGNORECASE)
        html = m.group(1).strip() if m else raw.strip()

    truncated = "</html>" not in html.lower()
    print("OK" + (" [TRUNCATED]" if truncated else ""))
    return html


def wrap_deck(slides_html: list[str]) -> str:
    cards = ""
    for i, html in enumerate(slides_html):
        encoded = (html
                   .replace("&", "&amp;")
                   .replace("<", "&#60;")
                   .replace(">", "&#62;")
                   .replace('"', "&quot;"))
        cards += f"""
    <div class="slide-card" id="s{i}" style="display:{'block' if i==0 else 'none'}">
      <div class="label">Slide {i+1} of {len(slides_html)}</div>
      <iframe srcdoc="{encoded}" width="{W}" height="{H}" scrolling="no" frameborder="0"></iframe>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Roland Berger — Data Intensive Slides</title>
<style>
  body {{ margin:0; background:#0a0f1e; display:flex; flex-direction:column;
         align-items:center; justify-content:center; min-height:100vh; font-family:Arial,sans-serif; }}
  h1 {{ color:#8a9aaa; font-size:12px; font-weight:400; margin:16px 0 8px; letter-spacing:2px; text-transform:uppercase; }}
  .slide-card {{ text-align:center; }}
  .label {{ color:#4a6a8a; font-size:11px; margin-bottom:8px; letter-spacing:1px; }}
  iframe {{ display:block; border-radius:3px; box-shadow:0 12px 48px rgba(0,0,0,0.7); }}
  .nav {{ display:flex; gap:16px; margin-top:20px; align-items:center; }}
  button {{ background:#111828; border:1px solid #2a3a5a; color:#8a9aaa; padding:8px 28px;
            border-radius:3px; cursor:pointer; font-size:12px; letter-spacing:1px; text-transform:uppercase; }}
  button:hover {{ background:#1a2a4a; color:#aac0d8; }}
  .dots {{ display:flex; gap:8px; align-items:center; }}
  .dot {{ width:7px; height:7px; border-radius:50%; background:#2a3a5a; cursor:pointer; }}
  .dot.active {{ background:#1c78b0; }}
</style>
</head>
<body>
<h1>Roland Berger · Data-Intensive Analysis Slides</h1>
{cards}
<div class="nav">
  <button onclick="move(-1)">&#8592; Prev</button>
  <div class="dots" id="dots"></div>
  <button onclick="move(1)">Next &#8594;</button>
</div>
<script>
  var cur=0,total={len(slides_html)};
  var dots=document.getElementById('dots');
  for(var i=0;i<total;i++){{
    var d=document.createElement('div');d.className='dot'+(i===0?' active':'');
    d.dataset.i=i;d.onclick=function(){{go(+this.dataset.i);}};dots.appendChild(d);
  }}
  function go(n){{
    document.getElementById('s'+cur).style.display='none';dots.children[cur].classList.remove('active');
    cur=(n+total)%total;
    document.getElementById('s'+cur).style.display='block';dots.children[cur].classList.add('active');
  }}
  function move(d){{go(cur+d);}}
  document.addEventListener('keydown',function(e){{
    if(e.key==='ArrowRight')move(1);if(e.key==='ArrowLeft')move(-1);
  }});
</script>
</body>
</html>"""


def main():
    print("Generating Roland Berger data-intensive deck (4 slides)")
    print(f"Output: {OUT}\n")

    slides_html = []
    for i, slide_def in enumerate(SLIDES):
        ref_html = read_ref(slide_def["ref"])
        html = generate_slide(slide_def["brief"], ref_html, i, len(SLIDES))
        slides_html.append(html)
        if i < len(SLIDES) - 1:
            time.sleep(1)

    OUT.write_text(wrap_deck(slides_html), encoding="utf-8")
    print(f"\nDone — {OUT}")


if __name__ == "__main__":
    main()
