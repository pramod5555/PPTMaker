"""
generate_deck_v3.py — Chart-heavy, Bain-style consulting deck.

Topic: "Strategic Priorities 2025-2030: Five Forces Defining the Next Decade"
Design: Bain & Company visual language — clean, data-forward, red accent, strong typography.
Output: pptmaker/full_deck_v3.html

Usage:
    python generate_deck_v3.py
    python generate_deck_v3.py --out ../full_deck_v3.html
"""
from __future__ import annotations

import argparse
import base64
import os
import re
import sys
import time
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

SYSTEM_PROMPT = f"""You are a senior consulting front-end developer at Bain & Company producing high-fidelity HTML/CSS slides.

STRICT REQUIREMENTS:
1. Start with <!DOCTYPE html>
2. ALL CSS in a <style> block inside <head>
3. Slide root element: exactly {W}px wide, {H}px tall, position:relative, overflow:hidden
4. Absolute positioning for EVERY child — no flexbox/grid at top level
5. NO <script> tags
6. NO <img> tags — use CSS shapes, SVG inline, Unicode for ALL visuals including charts
7. NO external URLs
8. System fonts only: Arial, Helvetica, sans-serif
9. Charts MUST use inline SVG with real data — bars, lines, dots rendered as SVG <rect>, <line>, <circle>, <path>
10. Do NOT let any element overflow or overlap another
11. Output ONLY the complete HTML — no explanation, no markdown"""

# ── References (Bain-first) ───────────────────────────────────────────────────
REFS = {
    # Bain PE Report 2023 — full chart slides
    "bain_chart_a":  "bain_global_pe_report_2023_slide_007",
    "bain_chart_b":  "bain_global_pe_report_2023_slide_010",
    "bain_chart_c":  "bain_global_pe_report_2023_slide_011",
    "bain_chart_d":  "bain_global_pe_report_2023_slide_012",
    "bain_chart_e":  "bain_global_pe_report_2023_slide_013",
    "bain_two_col":  "bain_global_pe_report_2023_slide_006",
    "bain_two_col2": "bain_global_pe_report_2023_slide_008",
    "bain_two_col3": "bain_global_pe_report_2023_slide_014",
    "bain_cover":    "bain_global_pe_report_2023_slide_001",
    "bain_exec":     "bain_global_pe_report_2023_slide_003",
    "bain_exec2":    "bain_global_pe_report_2023_slide_005",
    "bain_diag":     "bain_syracuse_innovation_2014_slide_004",
    "bain_mixed":    "bain_syracuse_innovation_2014_slide_008",
    "bain_mixed2":   "bain_syracuse_innovation_2014_slide_012",
    "bain_china_data": "bain_china_luxury_2011_slide_005",
    "bain_china_bar":  "bain_china_luxury_2011_slide_008",
    # Roland Berger section dividers
    "rb_section":    "roland_berger_trend_compendium_2050_technology_and_innovation_slide_005",
    "rb_section2":   "roland_berger_trend_compendium_2050_technology_and_innovation_slide_006",
    # Accenture / Deloitte for variety
    "ac_kpi":        "accenture_tech-vision-2025_slide_015",
    "de_table":      "deloitte_from-exits-to-ecosystems_html_slide_010",
}

# L.E.K. PNG-only refs (portrait but strong typographic style)
LEK_PNG_REFS = [
    "lek_overcoming-biopharma-growth-gap_slide_003",
    "lek_us-warehouse-automations-next-act-broadening-automation-opportunity_slide_002",
]


def _b64(sid: str) -> str | None:
    p = SLIDES_DIR / f"{sid}.png"
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def collect(keys: list[str]) -> list[dict]:
    out = []
    for k in keys:
        sid = REFS.get(k, "")
        if not sid:
            continue
        p = HTML_DIR / f"{sid}.html"
        if not p.exists():
            continue
        out.append({"sid": sid, "html": p.read_text(encoding="utf-8", errors="ignore"), "b64": _b64(sid)})
        if len(out) >= 3:
            break
    return out


def collect_png(sids: list[str]) -> list[dict]:
    return [{"sid": s, "b64": _b64(s)} for s in sids if _b64(s)]


def generate_slide(brief: str, refs: list[dict], png_refs: list[dict], idx: int, total: int) -> str:
    print(f"  [{idx+1}/{total}] {len(refs)} refs + {len(png_refs)} PNG ... ", end="", flush=True)
    content: list[dict] = []

    for i, r in enumerate(refs):
        if r.get("b64"):
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{r['b64']}"}})
        content.append({"type": "text", "text": (
            f"STYLE REF {i+1}/{len(refs)+len(png_refs)} (id:{r['sid']}) — "
            f"adopt this slide's exact color tokens, font sizing, chart style, spacing rhythm.\n"
            f"HTML:\n{r['html'][:5500]}\n"
        )})

    for j, r in enumerate(png_refs):
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{r['b64']}"}})
        content.append({"type": "text", "text": f"VISUAL INSPIRATION {len(refs)+j+1} (L.E.K. style — typographic precision, white space discipline).\n"})

    content.append({"type": "text", "text": (
        f"Create a brand-new {W}x{H}px consulting slide.\n"
        f"Design language: Bain & Company — bold data, clean white space, red accent #C41230, "
        f"sharp typographic hierarchy, every chart rendered as inline SVG with real numbers.\n"
        f"Do NOT copy reference content. Generate fresh content per the brief.\n\n"
        f"BRIEF:\n{brief}"
    )})

    resp = client.chat.completions.create(
        model="gpt-5.4",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}],
        max_completion_tokens=8192,
    )
    html = resp.choices[0].message.content or ""
    m = re.search(r"(<!DOCTYPE.*?</html>)", html, re.DOTALL | re.IGNORECASE)
    html = m.group(1).strip() if m else html
    print("OK")
    return html


def wrap_deck(slides_html: list[str], topic: str) -> str:
    n = len(slides_html)
    cards = ""
    for i, html in enumerate(slides_html):
        safe = (html.replace("&", "&amp;").replace('"', "&quot;")
                    .replace("<", "&#60;").replace(">", "&#62;"))
        vis = "block" if i == 0 else "none"
        cards += (
            f'\n    <div class="slide-card" id="s{i}" style="display:{vis}">'
            f'\n      <div class="label">Slide {i+1} / {n}</div>'
            f'\n      <iframe srcdoc="{safe}" width="{W}" height="{H}" scrolling="no" frameborder="0"></iframe>'
            f'\n    </div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{topic}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #111; display: flex; flex-direction: column; align-items: center;
         justify-content: flex-start; min-height: 100vh; padding: 20px; font-family: Arial, sans-serif; }}
  .deck-title {{ color: #888; font-size: 13px; letter-spacing: 2px; text-transform: uppercase;
                 margin-bottom: 16px; }}
  .slide-card {{ position: relative; }}
  .label {{ position: absolute; bottom: -28px; left: 0; right: 0; text-align: center;
            color: #555; font-size: 12px; letter-spacing: 1px; }}
  iframe {{ display: block; border: none; box-shadow: 0 8px 40px rgba(0,0,0,0.6); }}
  .nav {{ display: flex; align-items: center; gap: 20px; margin-top: 48px; }}
  .nav button {{ background: #222; border: 1px solid #444; color: #ccc; padding: 10px 28px;
                 cursor: pointer; font-size: 14px; letter-spacing: 1px; border-radius: 2px; }}
  .nav button:hover {{ background: #C41230; border-color: #C41230; color: #fff; }}
  .dots {{ display: flex; gap: 8px; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #444; cursor: pointer;
          transition: background 0.2s; }}
  .dot.active {{ background: #C41230; }}
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
  var cur=0, n={n};
  var dots=document.getElementById('dots');
  for(var i=0;i<n;i++){{var d=document.createElement('div');d.className='dot'+(i==0?' active':'');d.dataset.i=i;d.onclick=function(){{show(+this.dataset.i)}};dots.appendChild(d);}}
  function show(i){{document.getElementById('s'+cur).style.display='none';dots.children[cur].classList.remove('active');cur=i;document.getElementById('s'+cur).style.display='block';dots.children[cur].classList.add('active');}}
  function go(d){{show((cur+d+n)%n);}}
  document.addEventListener('keydown',function(e){{if(e.key=='ArrowRight'||e.key==' ')go(1);if(e.key=='ArrowLeft')go(-1);}});
</script>
</body>
</html>"""


def build_slides() -> list[dict]:
    return [
        # ─────────────────────────────────────────────────────────────────────
        # 1. COVER
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["bain_cover", "rb_section"],
            "png":  LEK_PNG_REFS[:1],
            "brief": """Premium consulting cover. 1280x720px. Dark background.

VISUAL CONCEPT: Split layout. Left 58% = content zone, background #0A0A0A.
Right 42% = bold abstract. Background: linear-gradient(135deg, #C41230 0%, #7B0D1E 100%).
Vertical divider: left:742px top:0 width:1px height:720px background:rgba(255,255,255,0.08).

RIGHT PANEL (absolute, clipped to right 538px):
  Inline SVG (position:absolute, right:0, top:0, width:538px, height:720px):
    - 8-10 horizontal white rectangles at varied y positions, widths 60-300px, height 2-4px,
      opacity 0.12-0.25, representing data bars
    - 3 large white circles, r=80-160, opacity 0.04, at different positions
    - Small red dot grid: 5x4 grid of dots, r=2, fill:white, opacity:0.15, spaced 40px apart
  This creates a minimal data-art feel against the red gradient.

LEFT PANEL (all absolute):
  — Kicker top:52px left:72px: 'STRATEGIC ADVISORY' font-size:10px letter-spacing:4px
    color:#C41230 text-transform:uppercase font-weight:700
  — Rule top:72px left:72px: width:40px height:2px background:#C41230
  — Title line 1 top:120px left:72px width:600px:
    'Strategic Priorities' font-size:58px font-weight:800 color:#FFFFFF line-height:1.05
  — Title line 2 top:182px left:72px:
    '2025&#x2013;2030' font-size:58px font-weight:300 color:#C41230 line-height:1.05
  — Title line 3 top:244px left:72px width:580px:
    'Five Forces Defining' font-size:58px font-weight:800 color:#FFFFFF line-height:1.05
  — Title line 4 top:306px left:72px:
    'the Next Decade' font-size:58px font-weight:300 color:#CCCCCC line-height:1.05
  — Divider rule top:388px left:72px: width:320px height:1px background:#2A2A2A
  — Descriptor top:404px left:72px width:580px:
    'An integrated view of technology, sustainability, infrastructure, demographic, and geopolitical forces'
    font-size:13px color:#888888 line-height:1.7
  — Three stat pills (top:476px, each 28px height, border:1px solid #2A2A2A border-radius:2px):
    Pill 1 left:72px: '5 Strategic Forces' font-size:10px color:#888 letter-spacing:1px
    Pill 2 left:216px: '18-Month Horizon' font-size:10px color:#888
    Pill 3 left:354px: 'C-Suite Briefing' font-size:10px color:#888
  — Footer left: top:672px left:72px: 'Confidential &bull; For Executive Leadership'
    font-size:10px color:#333333
  — Footer right: top:672px right:72px: '1' font-size:10px color:#333333
NO overlapping elements.""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 2. AGENDA — Card Grid
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["bain_exec", "bain_mixed"],
            "png":  LEK_PNG_REFS,
            "brief": """Consulting agenda slide. 1280x720px. White background #FFFFFF.

CONCEPT: 5 chapter cards in a horizontal row. Each card is visually self-contained with
a bold chapter number, title, one teaser stat, and a colored top border.

HEADER (absolute):
  — Top accent line: top:0 left:0 width:1280px height:3px
    background:linear-gradient(90deg,#C41230 0%,#F5A0A0 30%,transparent 100%)
  — Kicker top:18px left:64px: 'AGENDA' font-size:9px letter-spacing:4px
    color:#C41230 text-transform:uppercase font-weight:700
  — Headline top:36px left:64px: 'Five forces examined across five chapters'
    font-size:22px font-weight:700 color:#1A1A1A
  — Sub-rule top:74px left:64px: width:1152px height:1px background:#E8E8E8

FIVE CHAPTER CARDS (top:88px, each width:224px, height:564px):
  Card layout: position absolute, top:88px.
  Left edges: 64, 304, 544, 784, 1024 px.
  Between cards: 1px solid #E8E8E8 dividers.

  Each card structure (positions relative to card's left edge, absolute in slide):
    — Colored top accent: width:224px height:4px top:88px (card left)
    — Chapter number: top:110px font-size:56px font-weight:800 letter-spacing:-2px
    — Chapter label: top:178px font-size:9px letter-spacing:3px text-transform:uppercase font-weight:600
    — Thin rule: top:200px width:32px height:1px
    — Chapter title: top:218px font-size:16px font-weight:700 color:#1A1A1A width:196px
    — Description: top:254px font-size:11px color:#6B6B6B line-height:1.6 width:196px
    — Stat number: top:360px font-size:38px font-weight:800
    — Stat label: top:404px font-size:10px color:#6B6B6B width:196px line-height:1.4
    — Page range: top:618px font-size:10px color:#AAAAAA

  Card 1 (left:64px): color:#C41230, number:'01', label:'AI &amp; AUTOMATION',
    title:'Artificial Intelligence at Scale', desc:'From experimentation to enterprise deployment — the shift that separates winners',
    stat:'74%', stat-label:'of enterprises now report AI in production vs. 37% in 2022', pages:'Slides 4&#x2013;6'

  Card 2 (left:304px): color:#1B7A3E, number:'02', label:'SUSTAINABILITY',
    title:'Green Transition &amp; Energy', desc:'LCOE parity is here — the green premium has collapsed across markets',
    stat:'89%', stat-label:'fall in solar LCOE since 2010; cost crossover with fossil fuels reached', pages:'Slides 7&#x2013;8'

  Card 3 (left:544px): color:#0D4D8C, number:'03', label:'DIGITAL INFRA',
    title:'Cloud &amp; Connectivity', desc:'Cloud-native architecture is the new competitive moat — not just an IT choice',
    stat:'3.1&#xD7;', stat-label:'faster digital revenue growth for cloud-native vs. legacy firms', pages:'Slides 9&#x2013;10'

  Card 4 (left:784px): color:#B35C00, number:'04', label:'DEMOGRAPHICS',
    title:'Workforce Transformation', desc:'Talent scarcity is structural — demographics and automation collide',
    stat:'40%', stat-label:'of current roles substantially changed by 2030; reskilling gap widening', pages:'Slides 11&#x2013;12'

  Card 5 (left:1024px): color:#5C2D91, number:'05', label:'GEOPOLITICS',
    title:'Geostrategic Risk &amp; Opportunity', desc:'Supply chain rewiring and regulatory divergence reshape competitive advantage',
    stat:'62%', stat-label:'of CEOs cite geopolitical risk as top strategic variable for 2025&#x2013;2027', pages:'Slides 13&#x2013;14'

FOOTER (top:672px left:64px): 'Strategic Priorities 2025&#x2013;2030' font-size:9px color:#AAAAAA
Slide number: top:672px right:64px '2' font-size:9px color:#AAAAAA
NO elements may overlap.""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 3. EXECUTIVE SUMMARY — Findings + Inline Bar Chart
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["bain_exec", "bain_exec2", "bain_two_col"],
            "png":  LEK_PNG_REFS,
            "brief": """Executive summary slide. 1280x720px. White background.

LAYOUT: Left zone (findings list, left:64px width:620px) + Right zone (data chart, left:724px width:492px).

HEADER:
  — Top red rule: top:0 width:1280px height:3px background:linear-gradient(90deg,#C41230,transparent)
  — Kicker top:18px left:64px: 'EXECUTIVE SUMMARY' 9px letter-spacing:4px color:#C41230 font-weight:700
  — Headline top:36px left:64px width:1152px: 'Five findings that demand executive action now'
    font-size:24px font-weight:700 color:#1A1A1A
  — Rule top:76px left:64px: width:1152px height:1px background:#E8E8E8

LEFT — FIVE NUMBERED FINDINGS (top:90px):
  Each row: height:98px. Rows at top: 90, 188, 286, 384, 482.
  Row structure:
    — Left red bar: width:3px height:78px, vertically centered in row, background:#C41230
    — Number: left:84px, font-size:11px font-weight:700 color:#C41230 (top of row +16px)
    — Finding headline: left:100px font-size:13px font-weight:700 color:#1A1A1A width:560px (top+16px)
    — Evidence: left:100px font-size:11px color:#555555 width:560px line-height:1.5 (top+34px)
    — Bottom separator: 1px #EFEFEF at row bottom

  Row 1: 'AI crossed the enterprise inflection point' / 'Average ROI payback now 14 months — down from 26 months in 2023. Deployment outpacing regulation.'
  Row 2: 'The green premium is gone — sustainable capex now wins on returns' / 'LCOE fell 89% since 2010. 68% of CFOs rank ESG capex as core to long-term value creation.'
  Row 3: 'Cloud-native architecture is the #1 predictor of digital revenue' / '3.1&#xD7; faster growth vs. legacy. $2.4tn in latent migration backlog value unrealised by 2025.'
  Row 4: 'Talent scarcity is structural — 40% of roles transformed by 2030' / 'Reskilling investment lags demand by 2.8&#xD7;. Automation creates net displacement in 6 of 11 major sectors.'
  Row 5: 'M&amp;A beats organic build — time-to-capability doubled' / 'Via M&amp;A: 9 months. Via organic build: 21 months and rising. Multiples elevated but strategically justified.'

  Bottom rule: top:582px left:64px width:620px height:1px background:#E8E8E8

RIGHT — INLINE SVG BAR CHART (top:90px left:724px):
  Title: top:90px left:724px: 'CEO Strategic Priority Ranking, 2025' font-size:12px font-weight:700 color:#1A1A1A
  Sub: top:108px left:724px: '% citing as top-3 priority (n=1,240 global CEOs)' font-size:10px color:#888888

  Inline SVG chart (position:absolute top:128px left:724px width:480px height:420px):
    5 horizontal bars, each row height:72px, bars from left:120px.
    Max value = 74%, full bar width = 320px. Scale: 1% = 3.24px.

    Row 1 (y:20): label 'AI &amp; Automation' font-size:11px fill:#1A1A1A at x:0 y:36
      Bar: x:120 y:22 height:28px width:240px (74%) fill:#C41230 rx:2
      Value text: x:368 y:40: '74%' font-size:12px font-weight:700 fill:#C41230

    Row 2 (y:92): label 'Talent &amp; Skills' font-size:11px at x:0 y:108
      Bar: x:120 y:94 height:28px width:213px (66%) fill:#1A1A1A rx:2
      Value: x:341 y:112: '66%' font-size:12px font-weight:700 fill:#1A1A1A

    Row 3 (y:164): label 'Digital Infra' font-size:11px at x:0 y:180
      Bar: x:120 y:166 height:28px width:185px (57%) fill:#888888 rx:2
      Value: x:313 y:184: '57%' font-size:12px fill:#888888

    Row 4 (y:236): label 'Sustainability' font-size:11px at x:0 y:252
      Bar: x:120 y:238 height:28px width:165px (51%) fill:#888888 rx:2
      Value: x:293 y:256: '51%' font-size:12px fill:#888888

    Row 5 (y:308): label 'Geopolitics' font-size:11px at x:0 y:324
      Bar: x:120 y:310 height:28px width:139px (43%) fill:#888888 rx:2
      Value: x:267 y:328: '43%' font-size:12px fill:#888888

    Baseline: x:120 y:355 width:360 stroke:#E8E8E8 stroke-width:1

  YoY change note: top:560px left:724px: '&#x25B2; All priorities increased vs. 2023 survey'
    font-size:10px color:#1B7A3E font-weight:600

FOOTER top:672px: source left:64px 9px color:#AAAAAA 'Sources: Bain CEO Survey 2025; McKinsey Global Institute; Accenture'
Slide number right:64px '3' font-size:9px color:#AAAAAA""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 4. AI CHAPTER DIVIDER
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["rb_section", "rb_section2"],
            "png":  [],
            "brief": """Dark chapter divider. 1280x720px. Background #0A0A0A.
Left accent bar: left:0 top:0 width:5px height:720px background:#C41230.

LAYOUT (all absolute):
  — Chapter tag top:280px left:80px: 'FORCE 01' font-size:10px letter-spacing:5px
    color:#C41230 text-transform:uppercase font-weight:700
  — Thin rule top:300px left:80px: width:48px height:1px background:#C41230
  — Chapter title top:320px left:80px width:680px: 'AI &amp; Automation'
    font-size:72px font-weight:800 color:#FFFFFF line-height:1.0
  — Subtitle top:412px left:80px width:640px:
    'From experimentation to enterprise deployment&#x2014;the inflection point is here'
    font-size:17px color:#888888 line-height:1.55
  — Right abstract: inline SVG absolute right:0 top:0 width:480px height:720px
    Draw: overlapping translucent red rectangles (fill:#C41230 opacity 0.04-0.10),
    6-8 rects at varied sizes and positions, suggesting data bars/columns.
    Add 3 horizontal white lines (stroke:white opacity:0.05 stroke-width:1).
  — Page range top:672px right:80px: 'Slides 4&#x2013;6'
    font-size:10px color:#333333
NO overlap.""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 5. AI DATA — Horizontal Stacked Bar Chart
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["bain_chart_a", "bain_chart_b", "bain_two_col2"],
            "png":  [],
            "brief": """Data slide: AI adoption stacked bar chart. 1280x720px. White background #FFFFFF.

HEADER:
  — Red rule top:0 width:1280px height:3px background:#C41230
  — Kicker top:18px left:64px: 'AI &amp; AUTOMATION | DATA' 9px letter-spacing:3px color:#C41230
  — Headline top:36px left:64px width:1000px: 'AI adoption is uneven&#x2014;Financial Services and Tech lead; Industrial lags by 3 years'
    font-size:21px font-weight:700 color:#1A1A1A
  — Sub top:72px left:64px: '% of firms at each AI adoption stage by industry (n=3,800 global enterprises, 2025)'
    font-size:10px color:#888888

CHART (inline SVG, position:absolute top:96px left:64px width:860px height:520px):
  Background rect: x:0 y:0 width:860 height:520 fill:#FAFAFA rx:2

  Legend (y:14): Three squares + labels:
    Square 1: x:140 y:8 width:12 height:12 fill:#1A1A1A — 'Scaled (>50% functions)'
    Square 2: x:310 y:8 width:12 height:12 fill:#C41230 — 'In Production'
    Square 3: x:430 y:8 width:12 height:12 fill:#E8E8E8 stroke:#CCCCCC — 'Piloting'
    Labels: font-size:10px fill:#555

  Axis label (x:40 y:45 font-size:10px fill:#888 text-anchor:middle transform:rotate(-90,40,45)): 'Industry'

  7 horizontal stacked bars, y positions: 50,115,180,245,310,375,440. Each bar height:44px.
  Industry labels right-aligned at x:130, y = bar_y+27, font-size:11px fill:#1A1A1A.
  Max total = 100%, full bar width = 680px (x:140 to x:820).

  Bar data (Scaled % | Production % | Piloting %):
  FS (Financial Services):    32|41|20 → Scaled:x:140 w:218 | Prod:x:358 w:279 | Pilot:x:637 w:136
  Tech:                       28|44|21 → Scaled:x:140 w:190 | Prod:x:330 w:299 | Pilot:x:629 w:143
  Retail/CPG:                 18|38|28 → Scaled:x:140 w:122 | Prod:x:262 w:259 | Pilot:x:521 w:190
  Healthcare:                 14|33|32 → Scaled:x:140 w:095 | Prod:x:235 w:224 | Pilot:x:459 w:218
  Mfg/Industrial:             10|29|34 → Scaled:x:140 w:068 | Prod:x:208 w:197 | Pilot:x:405 w:231
  Energy/Utilities:            8|26|35 → Scaled:x:140 w:054 | Prod:x:194 w:177 | Pilot:x:371 w:238
  Public Sector:               4|19|38 → Scaled:x:140 w:027 | Prod:x:167 w:129 | Pilot:x:296 w:258

  Colors: Scaled=#1A1A1A, Production=#C41230, Piloting=#E8E8E8 (with stroke:#D0D0D0)
  Value labels inside each segment if wide enough: font-size:9px fill:white for dark, fill:#888 for light.
  Segment % text: show Scaled % inside Scaled bar (white, centered), Prod % inside Prod bar (white, centered)

  Baseline: x:140 y:496 width:680 stroke:#CCCCCC stroke-width:1
  X-axis ticks at 0%/25%/50%/75%/100%: x:140,310,480,650,820 y:498 stroke:#CCCCCC h:6
  X-axis labels: font-size:9px fill:#888 at those x positions y:512

RIGHT CALLOUT PANEL (top:96px left:948px width:272px):
  Panel background: top:96px left:948px width:272px height:520px background:#FAFAFA border:1px solid #E8E8E8
  Title top:112px left:964px: 'Key takeaways' font-size:11px font-weight:700 color:#1A1A1A

  3 callout blocks stacked (top:140,240,360):
    Each: left red rule (3px wide), bold stat, label text

  Block 1 top:140px left:964px:
    Stat: '&#x25B2;2x' font-size:28px font-weight:800 color:#C41230
    Label: 'Scaled deployments doubled in FS since 2022' font-size:10px color:#555 width:228px

  Block 2 top:260px left:964px:
    Stat: '3yr' font-size:28px font-weight:800 color:#1A1A1A
    Label: 'Gap between Tech leaders and Industrial laggards' font-size:10px color:#555 width:228px

  Block 3 top:380px left:964px:
    Stat: '61%' font-size:28px font-weight:800 color:#1A1A1A
    Label: 'Still only piloting — window to scale is closing fast' font-size:10px color:#555 width:228px

FOOTER top:672px left:64px: 'Sources: Bain AI Adoption Survey 2025; McKinsey State of AI' font-size:9px color:#AAAAAA
Slide number: top:672px right:64px '5' font-size:9px color:#AAAAAA""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 6. AI FRAMEWORK — Maturity Ladder with Mini Charts
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["bain_two_col", "bain_chart_c", "bain_diag"],
            "png":  [],
            "brief": """Framework slide: AI maturity ladder with mini donut indicators. 1280x720px. White.

HEADER:
  — Red rule top:0 width:1280px height:3px
  — Kicker top:18px left:64px: 'AI &amp; AUTOMATION | FRAMEWORK' 9px color:#C41230
  — Headline top:36px left:64px: 'Three layers of AI maturity define the gap between leaders and laggards'
    font-size:21px font-weight:700 color:#1A1A1A
  — Rule top:76px left:64px: width:1152px height:1px background:#E8E8E8

THREE COLUMN CARDS (top:88px left:64px, each width:360px, height:500px, gap:16px):
  Card positions: left:64, 440, 816.
  Each card: border:1px solid #E8E8E8 border-radius:2px padding implied by absolute positions.
  Card 1 background:#FAFAFA, Cards 2+3 background:#FFFFFF.

  CARD 1 — TASK AUTOMATION (left:64px):
    — Top red bar: top:88px left:64px width:360px height:4px background:#E8E8E8
    — Layer badge top:104px left:80px: 'LAYER 01' font-size:9px letter-spacing:3px color:#C41230 font-weight:700
    — Rule top:122px left:80px: width:32px height:1px background:#C41230
    — Title top:136px left:80px: 'Task Automation' font-size:18px font-weight:700 color:#1A1A1A
    — Bullets top:166px left:80px width:312px font-size:11px color:#444 line-height:1.7:
      '&bull; RPA and GenAI eliminate repetitive manual work'
      '&bull; 35&#x2013;45% cost reduction in targeted processes'
      '&bull; Risk: shallow implementation without process redesign'
    — Mini inline SVG donut top:320px left:80px width:80px height:80px:
      Background circle: cx:40 cy:40 r:32 fill:none stroke:#E8E8E8 stroke-width:10
      Progress arc for 61%: cx:40 cy:40 r:32 fill:none stroke:#C41230 stroke-width:10
        stroke-dasharray:'122.5 200' stroke-linecap:round transform:rotate(-90,40,40)
      Center text: x:40 y:44 text-anchor:middle font-size:14px font-weight:800 fill:#1A1A1A: '61%'
    — Mini label top:408px left:80px: '61% of firms at this layer' font-size:10px color:#888
    — Bottom note top:444px left:80px width:312px font-size:10px color:#888:
      'Entry-level AI maturity. Foundation for deeper deployment.'

  CARD 2 — DECISION INTELLIGENCE (left:440px):
    — Top bar: top:88px left:440px width:360px height:4px background:#C41230
    — Badge top:104px left:456px: 'LAYER 02' color:#C41230
    — Rule top:122px left:456px width:32px height:1px background:#C41230
    — Title top:136px left:456px: 'Decision Intelligence' font-size:18px font-weight:700
    — Bullets top:166px left:456px width:312px:
      '&bull; AI-augmented decisions in credit, procurement, pricing'
      '&bull; 1.8&#x2013;2.4&#xD7; better decision velocity vs. manual'
      '&bull; Requires clean data architecture &#x2014; 67% cite data quality as blocker'
    — Mini donut top:320px left:456px: 27% progress arc
      stroke-dasharray:'54 200' stroke:#1A1A1A
      Center: '27%'
    — Label top:408px left:456px: '27% of firms at this layer'
    — Note top:444px left:456px: 'The differentiation layer. Moat-building territory.'

  CARD 3 — AUTONOMOUS OPERATIONS (left:816px):
    — Top bar: top:88px left:816px width:360px height:4px background:#1A1A1A
    — Badge top:104px left:832px: 'LAYER 03' color:#1A1A1A
    — Rule top:122px left:832px
    — Title top:136px left:832px: 'Autonomous Operations' font-size:18px font-weight:700
    — Bullets top:166px left:832px width:312px:
      '&bull; End-to-end orchestration: supply chains, pricing, allocation'
      '&bull; Only 12% reached this layer &#x2014; but they capture disproportionate margin'
      '&bull; Organizational transformation is the binding constraint, not technology'
    — Mini donut top:320px left:832px: 12% progress
      stroke-dasharray:'24 200' stroke:#888888
      Center: '12%'
    — Label top:408px left:832px: '12% of firms at this layer'
    — Note top:444px left:832px: 'The leadership frontier. Requires CEO-level commitment.'

FOOTER top:672px: Sources left:64px '9px #AAAAAA' | Slide '6' right:64px""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 7. SUSTAINABILITY CHAPTER DIVIDER
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["rb_section", "rb_section2"],
            "png":  [],
            "brief": """Dark chapter divider. 1280x720px. Background #050F05.
Left accent: left:0 top:0 width:5px height:720px background:#1B7A3E.

LAYOUT:
  — Chapter tag top:280px left:80px: 'FORCE 02' letter-spacing:5px color:#1B7A3E
  — Rule top:300px left:80px: width:48px height:1px background:#1B7A3E
  — Title top:320px left:80px width:680px: 'Green Transition'
    font-size:72px font-weight:800 color:#FFFFFF
  — Sub top:412px left:80px width:640px:
    'The green premium has collapsed&#x2014;sustainable investment now delivers superior returns'
    font-size:17px color:#888888 line-height:1.55
  — Right SVG (width:480px height:720px right:0 top:0):
    Abstract: overlapping green rectangles (fill:#1B7A3E opacity 0.04-0.08),
    3 upward-trending line segments (stroke:#1B7A3E opacity:0.15 stroke-width:2)
  — Page range top:672px right:80px: 'Slides 7&#x2013;8' font-size:10px color:#333333""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 8. SUSTAINABILITY DATA — Dual-Axis Line Chart
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["bain_chart_d", "bain_china_data", "bain_two_col3"],
            "png":  [],
            "brief": """Data slide: dual-axis SVG line chart. 1280x720px. White.

HEADER:
  — Green rule top:0 width:1280px height:3px background:#1B7A3E
  — Kicker top:18px left:64px: 'GREEN TRANSITION | DATA' color:#1B7A3E 9px
  — Headline top:36px left:64px width:960px:
    'Renewable energy costs collapsed 89% since 2010&#x2014;clean investment now exceeds fossil capex'
    font-size:21px font-weight:700 color:#1A1A1A
  — Sub top:72px left:64px: 'LCOE ($/MWh) vs. global clean energy investment ($tn), 2010&#x2013;2025'
    font-size:10px color:#888888

MAIN SVG CHART (position:absolute top:92px left:64px width:840px height:490px):
  Chart area: x:60 y:20 width:740 height:400 (data plot area).
  Outer rect: x:0 y:0 width:840 height:490 fill:#FAFAFA rx:2

  LEFT Y-AXIS — LCOE $/MWh (left side):
    Label: x:14 y:220 transform:rotate(-90,14,220) font-size:10px fill:#C41230: 'Solar LCOE ($/MWh)'
    Ticks at y: 20(350), 100(280), 180(210), 260(140), 340(70), 420(0):
      Lines x:55 to x:60, stroke:#E8E8E8
      Labels x:50 text-anchor:end font-size:9px fill:#C41230: '350','280','210','140','70','0'

  RIGHT Y-AXIS — Investment $tn:
    Label: x:826 y:220 transform:rotate(90,826,220) font-size:10px fill:#0D4D8C: 'Clean Energy Investment ($tn)'
    Ticks at same y positions: values '0','0.3','0.6','0.9','1.2','1.5' text-anchor:start x:806 fill:#0D4D8C

  X-AXIS years 2010-2025 at x: 60,111,162,213,264,315,366,417,468,519,570,621,672,723,774,800
    Labels at y:435: '2010','2011',...'2025' font-size:9px fill:#888 (show every 2 years)
    Baseline: x:60 y:420 width:740 stroke:#E8E8E8 stroke-width:1
    Vertical grid lines at each label: stroke:#F0F0F0 stroke-width:1

  LINE 1 — SOLAR LCOE (red, declining):
    Data points (year, $/MWh) mapped to SVG coordinates.
    Year→x: 2010=60, each year +51px. $/MWh→y: 0=420, 350=20 (scale: 1.14px per $/MWh).
    Values: 2010:359, 2011:295, 2012:228, 2013:180, 2014:142, 2015:122, 2016:100,
            2017:86, 2018:72, 2019:60, 2020:52, 2021:48, 2022:45, 2023:41, 2024:38, 2025:36
    Compute SVG y = 420 - (value * 1.14). Draw <polyline points="..." fill:none stroke:#C41230 stroke-width:2.5>
    Add dots at each year: <circle r:3 fill:#C41230>
    End label: '&#36;36/MWh' near last point fill:#C41230 font-size:10px font-weight:700

  LINE 2 — CLEAN INVESTMENT (blue, rising):
    Scale: $tn→y: 0=420, 1.5=20 (scale: 267px per tn).
    Values: 2010:0.27, 2011:0.28, 2012:0.25, 2013:0.24, 2014:0.30, 2015:0.33,
            2016:0.32, 2017:0.33, 2018:0.38, 2019:0.40, 2020:0.50, 2021:0.75,
            2022:1.05, 2023:1.34, 2024:1.77, 2025:1.90
    Compute y = 420 - (value * 267). Draw <polyline stroke:#0D4D8C stroke-width:2.5 stroke-dasharray:'6,3'>
    Add dots: <circle r:3 fill:#0D4D8C>
    End label: '&#36;1.9tn' fill:#0D4D8C font-size:10px font-weight:700

  Legend box (x:80 y:450 width:340 height:28 fill:white stroke:#E8E8E8 rx:2):
    Red square x:92 y:460 w:10 h:10 + 'Solar LCOE' fill:#1A1A1A font-size:10px
    Blue dashed square x:220 y:460 + 'Clean Investment' fill:#1A1A1A font-size:10px

  Annotation box: x:320 y:120 width:180 height:56 fill:#FFF5F5 stroke:#C41230 rx:2
    Text line 1: x:330 y:142 '&#x22CE; Cost crossover' font-size:11px fill:#C41230 font-weight:700
    Text line 2: x:330 y:160 'Renewables cheaper than' font-size:10px fill:#555
    Text line 3: x:330 y:174 'fossil fuels in 95% of markets' font-size:10px fill:#555
    Arrow line: from x:308 y:148 to x:420 y:380 stroke:#C41230 stroke-width:1 stroke-dasharray:3

RIGHT STAT PANEL (top:92px left:928px width:288px):
  4 KPI cards stacked (height:116px each, gap:4px):

  Card 1 top:92px: background:#F5FAF7 border-left:3px solid #1B7A3E
    Big stat: '$1.8tn' font-size:42px font-weight:800 color:#1B7A3E
    Label: 'Global clean energy investment 2024&#x2014;first year exceeding fossil capex'
    font-size:10px color:#555 width:248px

  Card 2 top:212px: background:#FFFFFF border-left:3px solid #1B7A3E
    Big stat: '89%' font-size:42px font-weight:800 color:#1A1A1A
    Label: 'Fall in solar LCOE since 2010. Grid parity reached in 135 countries.'

  Card 3 top:332px: background:#FFFFFF border-left:3px solid #888888
    Big stat: '68%' font-size:42px font-weight:800 color:#1A1A1A
    Label: 'of CFOs now rank ESG capex as core to long-term value creation'

  Card 4 top:452px: background:#FFFFFF border-left:3px solid #888888
    Big stat: '2030' font-size:42px font-weight:800 color:#1A1A1A
    Label: 'Year all new energy investment expected to be renewable-first globally'

FOOTER top:672px: 'Sources: IRENA 2025; BloombergNEF; IEA World Energy Investment' left:64px 9px #AAAAAA
Slide number: '8' right:64px""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 9. DIGITAL INFRA CHAPTER DIVIDER
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["rb_section", "rb_section2"],
            "png":  [],
            "brief": """Dark chapter divider. 1280x720px. Background #05080F.
Left accent: left:0 top:0 width:5px height:720px background:#0D4D8C.
  — Chapter tag top:280px left:80px: 'FORCE 03' color:#0D4D8C letter-spacing:5px
  — Rule top:300px left:80px width:48px height:1px background:#0D4D8C
  — Title top:320px left:80px width:680px: 'Digital Infrastructure'
    font-size:72px font-weight:800 color:#FFFFFF
  — Sub top:412px left:80px width:640px:
    'Cloud-native architecture is the new competitive moat&#x2014;not just an IT decision'
    font-size:17px color:#888888 line-height:1.55
  — Right SVG abstract: grid of dots (r:2 fill:#0D4D8C opacity:0.15) in 12x8 pattern, spacing 40px, starting x:760 y:40
  — Page range: 'Slides 9&#x2013;10' top:672px right:80px color:#333333""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 10. DIGITAL INFRA — Bubble Chart (Cloud Maturity vs Revenue Growth)
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["bain_chart_e", "bain_chart_b", "ac_kpi"],
            "png":  [],
            "brief": """Data slide: bubble chart. 1280x720px. White.

HEADER:
  — Blue rule top:0 width:1280px height:3px background:#0D4D8C
  — Kicker top:18px left:64px: 'DIGITAL INFRASTRUCTURE | DATA' color:#0D4D8C
  — Headline top:36px left:64px width:960px:
    'Cloud-native firms grow digital revenue 3.1&#xD7; faster&#x2014;the infrastructure gap is widening'
    font-size:21px font-weight:700 color:#1A1A1A
  — Sub top:72px left:64px: 'Cloud maturity score (0&#x2013;100) vs. digital revenue CAGR (%), bubble = market cap ($bn). 2024 data.'
    font-size:10px color:#888888

MAIN SVG BUBBLE CHART (position:absolute top:92px left:64px width:820px height:490px):
  Chart area: x:60 y:20 to x:780 y:440.
  Background: fill:#FAFAFA rx:2.

  X-AXIS — Cloud Maturity Score 0-100:
    Baseline: x:60 y:440 width:720 stroke:#CCCCCC
    Ticks and labels at x: 60(0), 204(20), 348(40), 492(60), 636(80), 780(100)
    Labels font-size:9px fill:#888 y:456
    Axis label: x:420 y:478 text-anchor:middle font-size:10px fill:#888: 'Cloud Maturity Score (0&#x2013;100)'
    Grid verticals: stroke:#F0F0F0 stroke-width:1 from y:20 to y:440

  Y-AXIS — Digital Revenue CAGR %:
    Labels at y: 440(0%), 368(5%), 296(10%), 224(15%), 152(20%), 80(25%), 20(30%)
    Scale: 1% = 14.4px above baseline y:440.
    Axis label rotated: 'Digital Revenue CAGR (%)' x:18 y:230 rotate(-90)
    Grid horizontals: stroke:#F0F0F0

  QUADRANT DIVIDERS (at x:420, y:230 — midpoints):
    Vertical: x:420 y:20 to y:440 stroke:#E0E0E0 stroke-width:1 stroke-dasharray:4
    Horizontal: y:230 x:60 to x:780 stroke:#E0E0E0 stroke-width:1 stroke-dasharray:4
    Quadrant labels (font-size:9px fill:#CCCCCC italic):
      Top-right (x:490 y:36): 'LEADERS'
      Top-left (x:70 y:36): 'OVER-PERFORMERS'
      Bottom-right (x:490 y:432): 'INFRASTRUCTURE UPGRADERS'
      Bottom-left (x:70 y:432): 'LAGGARDS'

  BUBBLES (cx, cy, r, fill):
    Amazon:   cx:752 cy:44  r:32 fill:#0D4D8C opacity:0.8  — label:'Amazon'   CAGR 28% maturity 97
    Microsoft:cx:724 cy:80  r:28 fill:#0D4D8C opacity:0.7  — label:'Microsoft' CAGR 25%
    Shopify:  cx:676 cy:116 r:18 fill:#0D4D8C opacity:0.7  — label:'Shopify'  CAGR 22%
    Salesforce:cx:636 cy:152 r:20 fill:#0D4D8C opacity:0.65 — label:'Salesforce' CAGR 19%
    JPMorgan: cx:540 cy:210 r:24 fill:#888888 opacity:0.7  — label:'JPMorgan' CAGR 13%
    Walmart:  cx:492 cy:254 r:26 fill:#888888 opacity:0.65 — label:'Walmart'  CAGR 10%
    GM:       cx:276 cy:340 r:20 fill:#CCCCCC opacity:0.8  stroke:#888 — label:'GM'  CAGR 4%
    Ford:     cx:204 cy:368 r:18 fill:#CCCCCC opacity:0.8  stroke:#888 — label:'Ford' CAGR 2%

    Each bubble: add a white text label centered (font-size:9px font-weight:700 fill:white for dark, fill:#555 for light)

  NOTE box (x:88 y:60 width:200 height:48 fill:white stroke:#E8E8E8 rx:2):
    'Gap is widening: cloud leaders now capture 3.1&#xD7; more digital revenue growth than laggards'
    font-size:9px fill:#555 line-height:1.5

RIGHT CALLOUT PANEL (top:92px left:908px width:308px):
  Panel: background:#FAFAFA border:1px solid #E8E8E8
  Title: top:108px left:924px: 'Infrastructure gap metrics' font-size:11px font-weight:700

  3 stat blocks:
  Block 1 top:140px left:924px:
    Stat: '3.1&#xD7;' font-size:36px font-weight:800 color:#0D4D8C
    Label: 'Revenue growth advantage of cloud-native vs legacy'
  Block 2 top:270px left:924px:
    Stat: '$2.4tn' font-size:36px font-weight:800 color:#1A1A1A
    Label: 'Latent value in cloud migration backlog unrealised by 2025'
  Block 3 top:390px left:924px:
    Stat: '87%' font-size:36px font-weight:800 color:#1A1A1A
    Label: 'of new enterprise apps are cloud-native by design in 2025, vs 56% in 2021'

FOOTER: 'Sources: Gartner; Accenture Technology Vision 2025; company reports' 9px #AAAAAA | Slide '10'""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 11. DEMOGRAPHICS CHAPTER DIVIDER
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["rb_section", "rb_section2"],
            "png":  [],
            "brief": """Dark chapter divider. Background #0F0A00.
Left accent: background:#B35C00.
  — 'FORCE 04' color:#B35C00
  — 'Demographic Shifts &amp; Workforce' font-size:64px font-weight:800 color:#FFFFFF
  — Sub: 'Talent scarcity, aging populations, and automation are reshaping the global labour market'
    color:#888888
  — Right SVG: ascending bar chart silhouette in orange tones (opacity 0.06-0.10)
  — 'Slides 11&#x2013;12' right:80px""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 12. DEMOGRAPHICS — Waterfall Chart
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["bain_chart_a", "bain_china_bar", "bain_mixed2"],
            "png":  [],
            "brief": """Data slide: workforce waterfall chart. 1280x720px. White.

HEADER:
  — Orange rule top:0 width:1280px height:3px background:#B35C00
  — Kicker top:18px left:64px: 'DEMOGRAPHICS | DATA' color:#B35C00
  — Headline top:36px left:64px width:960px:
    'By 2030, automation and demographics create a 58M-person talent gap in advanced economies'
    font-size:21px font-weight:700 color:#1A1A1A
  — Sub top:72px left:64px: 'Net workforce impact 2025&#x2013;2030 (millions of workers), G7 economies'
    font-size:10px color:#888888

WATERFALL CHART (inline SVG position:absolute top:92px left:64px width:860px height:480px):
  Background fill:#FAFAFA rx:2. Chart area x:120 y:20 width:680 height:380.

  BARS (waterfall style — each bar starts where previous ended):
  Baseline y=400. Scale: 1M workers = 2.8px.

  Bar data (label, value, type):
  'Starting workforce' +820M: x:140 y:400-820*2.8=...

  Use simplified waterfall with 7 bars, relative changes:
  Starting: baseline bar showing current 820M workers (just a label, not a bar — use as reference)

  Show 6 change bars + final result:
  Bar 1: 'New entrants' +45M → green bar height:126px at x:140 rising from y:274 to y:400
  Bar 2: 'Reskilled workers' +18M → green height:50px at x:232
  Bar 3: 'Retirement wave' -38M → orange/red bar falling at x:324
  Bar 4: 'Automation displacement' -71M → red falling at x:416
  Bar 5: 'Skill mismatch loss' -24M → light red at x:508
  Bar 6: 'Migration inflow' +12M → green at x:600
  Final: 'Net Gap' -58M → deep red bar at x:692

  Color scheme: positive = #1B7A3E (gain), negative = #C41230 (loss), net = #8B0000
  Each bar width:72px with 12px gap.
  Connecting lines between bars (stroke:#CCCCCC stroke-width:1 stroke-dasharray:3).
  Bar labels above each bar: value in millions ('+45M', '-38M') font-size:10px font-weight:700.
  Category labels below x:640 at y:420, rotated -40deg, font-size:10px fill:#555.
  Baseline reference line y:274 (820M level) across chart: stroke:#CCCCCC stroke-dasharray:4.

  X-axis: y:400 x:120 width:680 stroke:#CCCCCC stroke-width:1.5

  Legend (x:140 y:444): Green sq 'New workforce' | Red sq 'Workforce loss' | Dark red 'Net talent gap'
  font-size:10px fill:#555.

RIGHT PANEL (top:92px left:948px width:268px):
  Panel background:#FAFAFA border:1px solid #E8E8E8.

  3 stat cards:
  Card 1 top:112px left:964px:
    '58M' font-size:44px font-weight:800 color:#B35C00
    'talent gap projected in G7 by 2030 — widening at 8M/year' font-size:10px color:#555

  Card 2 top:254px left:964px:
    '2.8&#xD7;' font-size:44px font-weight:800 color:#1A1A1A
    'reskilling investment shortfall vs. demand — corporate training budgets not keeping pace'

  Card 3 top:394px left:964px:
    '40%' font-size:44px font-weight:800 color:#1A1A1A
    'of current roles substantially transformed; 12% fully displaced by AI by 2030'

FOOTER: 'Sources: WEF Future of Jobs 2025; McKinsey Global Institute; OECD' | Slide '12'""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 13. GEOPOLITICS CHAPTER DIVIDER
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["rb_section", "rb_section2"],
            "png":  [],
            "brief": """Dark chapter divider. Background #0A000F.
Left accent: background:#5C2D91.
  — 'FORCE 05' color:#5C2D91
  — 'Geopolitical Risk' font-size:72px font-weight:800 color:#FFFFFF
  — Sub: 'Supply chain rewiring and regulatory divergence are reshaping competitive geography'
    color:#888888
  — Right SVG abstract: network graph nodes in purple tones
  — 'Slides 13&#x2013;14' right:80px""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 14. GEOPOLITICS — Risk Matrix Heat Map
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["bain_chart_c", "bain_chart_d", "de_table"],
            "png":  [],
            "brief": """Data slide: geopolitical risk matrix. 1280x720px. White.

HEADER:
  — Purple rule top:0 width:1280px height:3px background:#5C2D91
  — Kicker top:18px left:64px: 'GEOPOLITICS | RISK MATRIX' color:#5C2D91
  — Headline top:36px left:64px width:960px:
    '62% of CEOs rank geopolitical risk as top strategic variable&#x2014;five vectors demand boardroom attention'
    font-size:21px font-weight:700 color:#1A1A1A
  — Sub top:72px left:64px: 'Probability of escalation vs. strategic business impact (2025&#x2013;2027 horizon)'
    font-size:10px color:#888888

RISK MATRIX SVG (position:absolute top:92px left:64px width:680px height:510px):
  Background: fill:#FAFAFA rx:2. Plot area: x:80 y:30 to x:640 y:450.

  AXES:
  X-axis — Strategic Impact (Low to High, left to right):
    Line: x:80 y:450 width:560 stroke:#CCCCCC
    Labels: x:80(Low), x:360(Medium), x:640(High) y:468 font-size:10px fill:#888 text-anchor:middle
    Title: x:360 y:488 text-anchor:middle font-size:10px fill:#555: 'Strategic Business Impact'

  Y-axis — Probability:
    Line: x:80 y:30 to y:450 stroke:#CCCCCC
    Labels: y:450(Low), y:240(Medium), y:30(High) x:72 text-anchor:end font-size:10px fill:#888
    Title rotated: x:20 y:240 rotate(-90): 'Probability of Escalation' font-size:10px fill:#555

  BACKGROUND HEAT MAP (4 quadrants, colored):
    Bottom-left (low prob, low impact): fill:#F5F5F5 x:80 y:240 width:280 height:210
    Top-left (high prob, low impact): fill:#FFF8E1 x:80 y:30 width:280 height:210
    Bottom-right (low prob, high impact): fill:#FFF3F0 x:360 y:240 width:280 height:210
    TOP-RIGHT (high prob, high impact) = CRITICAL: fill:#FFE5E5 x:360 y:30 width:280 height:210

  Quadrant labels (font-size:10px fill:#CCCCCC font-style:italic):
    'Monitor': x:180 y:446
    'Prepare': x:460 y:446
    'Track': x:180 y:44
    'CRITICAL': x:460 y:44 fill:#C41230 font-weight:700

  Grid lines: dashed at x:360 (vertical) and y:240 (horizontal) stroke:#CCCCCC stroke-dasharray:4

  5 RISK BUBBLES (cx, cy, r, label):
  Each bubble: circle with fill, white text label, small text below for risk name.

  R1 'US-China Tech Decoupling': cx:580 cy:80 r:38 fill:#C41230 opacity:0.85
    Impact:High Prob:High — label inside: 'US-China' font-size:9px fill:white

  R2 'European Regulatory Divergence': cx:440 cy:180 r:28 fill:#C41230 opacity:0.70
    label: 'EU Regs' font-size:9px fill:white

  R3 'Supply Chain Fragmentation': cx:520 cy:130 r:32 fill:#C41230 opacity:0.75
    label: 'Supply Chain' font-size:9px fill:white

  R4 'Energy Geopolitics': cx:240 cy:120 r:24 fill:#B35C00 opacity:0.75
    label: 'Energy' fill:white

  R5 'Currency/Trade Policy': cx:160 cy:300 r:20 fill:#888888 opacity:0.75
    label: 'Trade' fill:white

  Arrow from R1 toward R3 and R2 suggesting interconnection: stroke:#C41230 opacity:0.3 stroke-width:1

RIGHT INSIGHT PANEL (top:92px left:760px width:456px):
  Panel background:#FAFAFA border:1px solid #E8E8E8.
  Title: top:108px left:776px: '5 risks requiring board-level response' font-size:11px font-weight:700

  5 risk rows (each 76px height, starting top:136px):
  Each row: left colored tag (4px wide, full row height), risk name bold, brief descriptor, probability badge.

  Row 1 top:136px: color:#C41230
    Name: 'US&#x2013;China Technology Decoupling' font-size:12px font-weight:700
    Desc: 'Semiconductor, AI, and data localization forced&#x2014;supply chain bifurcation accelerating'
    Badge: 'HIGH RISK' font-size:8px color:#C41230 border:1px solid #C41230 padding:2px 6px

  Row 2 top:212px: color:#C41230
    Name: 'Supply Chain Fragmentation'
    Desc: 'Friend-shoring and nearshoring add 8&#x2013;15% to operational costs across sectors'
    Badge: 'HIGH RISK'

  Row 3 top:288px: color:#C41230
    Name: 'European Regulatory Divergence'
    Desc: 'AI Act, CSRD, and data sovereignty rules create compliance complexity for global firms'
    Badge: 'ELEVATED'

  Row 4 top:364px: color:#B35C00
    Name: 'Energy Geopolitics'
    Desc: 'Transition energy supply chains (lithium, cobalt, rare earths) concentrated in 3 nations'
    Badge: 'ELEVATED' color:#B35C00

  Row 5 top:440px: color:#888888
    Name: 'Currency and Trade Policy Volatility'
    Desc: 'Tariff regimes in flux; FX exposure rising for firms with >30% international revenue'
    Badge: 'MONITOR'

FOOTER: 'Sources: WEF Global Risks 2025; Bain Geopolitical Risk Monitor; CEO surveys' | Slide '14'""",
        },

        # ─────────────────────────────────────────────────────────────────────
        # 15. RECOMMENDATIONS — Priority Action Cards with Timeline
        # ─────────────────────────────────────────────────────────────────────
        {
            "refs": ["bain_exec", "bain_mixed", "bain_exec2"],
            "png":  LEK_PNG_REFS,
            "brief": """Recommendations slide. 1280x720px. White.

HEADER:
  — Red rule top:0 width:1280px height:3px background:#C41230
  — Kicker top:18px left:64px: 'STRATEGIC RECOMMENDATIONS' 9px letter-spacing:3px color:#C41230
  — Headline top:36px left:64px: 'Five priority actions for executive leadership'
    font-size:22px font-weight:700 color:#1A1A1A
  — Rule top:76px left:64px: width:1152px height:1px background:#E8E8E8

TIMELINE HEADER (top:84px):
  Three horizon labels aligned to right of slide (absolute):
  'NOW&#x2013;12M' at right:820px top:84px font-size:9px letter-spacing:2px color:#888888
  '12&#x2013;24M' at right:520px top:84px font-size:9px letter-spacing:2px color:#888888
  '24&#x2013;36M' at right:236px top:84px font-size:9px letter-spacing:2px color:#888888
  Vertical guide lines (1px dashed #E8E8E8) from y:100 to y:630 at those right-edge positions.

FIVE ACTION ROWS (top:100px, each height:100px):
  Rows at top: 100, 200, 300, 400, 500.
  Each row: bottom border 1px #EFEFEF.

  Row structure:
    — Priority badge: left:64px, centered vertically, 32x32px, background:#1A1A1A border-radius:2px
      text:'P1'/'P2' etc, font-size:11px font-weight:800 color:white text-align:center line-height:32px
    — Action title: left:112px font-size:13px font-weight:700 color:#1A1A1A (top+16px in row)
    — Action description: left:112px font-size:11px color:#555555 width:520px (top+36px)
    — Expected outcome: left:112px font-size:10px color:#1B7A3E font-weight:600 (top+58px)
    — Timeline bar: absolute right side, height:16px, vertically centred in row
      bar indicating which horizons are active (filled vs outline)
      NOW segment: right:820px, '12M' right:520px, '36M' right:220px
      Active segments filled #1A1A1A, inactive #E8E8E8, border-radius:2px

  P1 (top:100): badge background:#C41230 text:'P1'
    Title: 'Scale AI from pilots to enterprise-wide production'
    Desc: 'Appoint AI COO. Define 3 priority use cases per business unit. Set 18-month ROI targets.'
    Outcome: '&#x25B2; Expected: 15&#x2013;25% productivity gain in scaled functions'
    Timeline: active NOW+12M (left 2 segments filled)

  P2 (top:200): badge #C41230 text:'P2'
    Title: 'Accelerate cloud migration with clear business ROI mandate'
    Desc: 'Audit application portfolio. Retire legacy systems blocking cloud-native deployment.'
    Outcome: '&#x25B2; Expected: 3.1&#xD7; digital revenue acceleration vs. on-premise competitors'
    Timeline: active all 3 segments

  P3 (top:300): badge #1A1A1A text:'P3'
    Title: 'Lock in green transition investments before 2026 regulatory reset'
    Desc: 'Accelerate renewable energy PPAs. ESG capex integration into capital allocation framework.'
    Outcome: '&#x25B2; Expected: ESG premium elimination + cost parity with fossil in core markets'
    Timeline: active NOW+12M

  P4 (top:400): badge #1A1A1A text:'P4'
    Title: 'Launch reskilling at scale — talent scarcity is structural, not cyclical'
    Desc: 'Build internal AI academy. Partner with universities. Set 40% workforce reskilling target by 2027.'
    Outcome: '&#x25B2; Expected: Reduce talent gap exposure by 60% vs. peers'
    Timeline: active all 3 (long-term program)

  P5 (top:500): badge #888888 text:'P5'
    Title: 'Map geopolitical exposure and stress-test supply chains'
    Desc: 'Identify top-10 single-source vulnerabilities. Model friend-shoring cost vs. risk tradeoff.'
    Outcome: '&#x25B2; Expected: Reduce critical supply chain concentration from 3 to &lt;1 region'
    Timeline: active NOW+12M

FOOTER (top:624px):
  Rule top:624px left:64px width:1152px height:1px background:#E8E8E8
  Left: 'Strategic Priorities 2025&#x2013;2030 | Confidential' font-size:9px color:#AAAAAA
  Right: 'Slide 15 / 15' font-size:9px color:#AAAAAA
NO overlaps. Ensure timeline bars do not overlap text.""",
        },
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="../full_deck_v3.html")
    args = parser.parse_args()

    topic = "Strategic Priorities 2025&#x2013;2030: Five Forces Defining the Next Decade"
    out_path = (Path(__file__).parent / args.out).resolve()

    slide_specs = build_slides()
    total = len(slide_specs)
    print(f"Generating {total}-slide deck: {topic.replace('&#x2013;', '-')}")
    print(f"Output: {out_path}\n")

    slides_html: list[str] = []
    for i, spec in enumerate(slide_specs):
        refs     = collect(spec["refs"])
        png_refs = collect_png(spec["png"])
        html     = generate_slide(spec["brief"], refs, png_refs, i, total)
        slides_html.append(html)
        if i < total - 1:
            time.sleep(0.5)

    deck = wrap_deck(slides_html, topic)
    deck_ascii = deck.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
    out_path.write_text(deck_ascii, encoding="ascii")
    print(f"\nDone -> {out_path.name}")


if __name__ == "__main__":
    main()
