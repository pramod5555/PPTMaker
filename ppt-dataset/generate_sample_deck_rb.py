"""
generate_sample_deck_rb.py — Roland Berger style sample deck.

Topic: "The Productivity Imperative: Technology Megatrends Reshaping European Industry — 2025"

Uses 2-pass converted Roland Berger HTML slides (200 DPI) as style references.
Output: pptmaker/sample_deck_rb.html
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

ROOT     = Path(__file__).parent.parent
HTML_DIR = ROOT / "html_slides"
OUT      = ROOT / "sample_deck_rb.html"

W, H = 1280, 720

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
)

SYSTEM_PROMPT = f"""You are a senior front-end developer creating pixel-perfect self-contained HTML/CSS presentation slides in the style of Roland Berger, the European management consulting firm.

Roland Berger slide characteristics you must honour:
  • Clean white backgrounds (#ffffff) for content slides
  • Very dark navy (#0a1628 or #060e1a) for cover slides
  • Primary blue accent: #1c78b0 (rules, kickers, bars, badges)
  • Secondary dark blue: #1c5fa8 (large numbers, bold callouts)
  • Body text: #1c2a3a (near-black) and #3a4a5a (supporting)
  • Muted grey: #8a9099 or #6a7a8a (subtitles, footnotes, captions)
  • Thin 2px horizontal blue rule below every slide header
  • Uppercase kicker label in #1c78b0 below the rule, letter-spacing:2px
  • Bold assertion headline directly below the kicker
  • Source footnote at bottom-left: 10px, #9aa0a8

LAYOUT PRECISION — compute all vertical positions explicitly:
  • If element A starts at top:T and occupies height:H, element B must start at top:(T + H + gap).
  • Never guess. Calculate. No element may visually overlap another.
  • All child elements: position:absolute. Root: position:relative; overflow:hidden.

LAYER ARCHITECTURE (use z-index):
  z-index 0–5   : background fills, full-bleed colour bands
  z-index 10–15 : decorative panels and card backgrounds
  z-index 20+   : text and data content

TYPOGRAPHY PRECISION:
  • font-family: Arial, Helvetica, sans-serif (always)
  • Set font-weight explicitly (300/400/600/700/800)
  • Set line-height on every text block
  • Set letter-spacing on uppercase labels (0.08em–0.15em)
  • Set width on every text block to control wrapping

DATA VISUALISATION (inline SVG or CSS divs — NO <img>, NO <canvas>, NO <script>):
  • Horizontal bar: track div (height:22px, background:#e8edf2) + filled div (same height, background:#1c78b0 or gradient)
  • Vertical bar: flex row, align-items:flex-end, each bar is a div with explicit height
  • Line chart: inline <svg> with <polyline points="...">
  • Donut/ring: SVG circle with stroke-dasharray
  • 2×2 matrix: four absolutely-positioned quadrant divs with a crossing line
  • Table: <table> with border-collapse:collapse, explicit cell padding and widths

DECORATIVE ELEMENTS:
  • Coloured accent bar at top of column: width:40px, height:3px, background:#1c78b0
  • Vertical left-edge rule: width:4px, height:Xpx, background:#1c78b0
  • Card: background:#f5f8fb, border-top:3px solid #1c78b0 or border-left:3px solid #1c78b0
  • Numbered circle badge: border-radius:50%, background:#1c78b0, white text, explicit width=height

STRICT REQUIREMENTS:
1. Start with <!DOCTYPE html>
2. All CSS in <style> block in <head>
3. Root element: exactly {W}px × {H}px, position:relative, overflow:hidden
4. NO <script> · NO <img> · NO external URLs
5. System fonts only: Arial, Helvetica, 'Segoe UI', Georgia
6. Replicate EVERY element described in the brief — do not simplify
7. Output ONLY the complete HTML — no explanation, no markdown, no truncation
   Last line must be </html>"""


SLIDES = [
    {
        "ref": "roland_berger_european_pe_outlook_1_slide_001",
        "brief": """Cover slide. Dark navy full-bleed background.

BACKGROUND: position:absolute, top:0, left:0, width:1280px, height:720px,
  background: radial-gradient(ellipse at 70% 50%, #112244 0%, #060e1a 65%).

TOP-LEFT LABEL (position:absolute, top:38px, left:72px):
  Text: 'ROLAND BERGER | TECHNOLOGY PRACTICE'
  font-size:11px, font-weight:400, color:#4a6a9a, letter-spacing:2px, text-transform:uppercase.

LEFT CONTENT BLOCK:
  Thin blue rule: position:absolute, top:210px, left:72px, width:48px, height:2px, background:#1c78b0.
  Kicker (top:224px, left:72px): 'EUROPEAN INDUSTRY OUTLOOK 2025'
    font-size:11px, color:#1c78b0, letter-spacing:2.5px, text-transform:uppercase.
  Main headline (top:250px, left:72px, width:580px):
    Line 1: 'The Productivity'  font-size:64px, font-weight:300, color:#ffffff, line-height:1.05.
    Line 2: 'Imperative'        same style.
    Line 3 (top:382px): 'Technology Megatrends'  font-size:32px, font-weight:300, color:#7aacdc, line-height:1.1.
    Line 4 (top:422px): 'Reshaping European Industry' same style.
  Dividing rule (top:480px, left:72px): width:400px, height:1px, background:#1c3a60.
  Subtitle (top:496px, left:72px, width:520px):
    'How automation, AI, and platform convergence determine which firms lead the next decade.'
    font-size:14px, color:#6a8aaa, line-height:1.6, font-weight:300.

RIGHT ABSTRACT ILLUSTRATION (position:absolute, top:100px, left:720px, width:480px, height:520px):
  Use inline SVG to draw a network of interconnected nodes and arcs in teal/blue tones.
  SVG viewBox="0 0 480 520":
    — Draw 8 circles (r=6–12) at various positions: (60,80),(180,60),(320,100),(420,180),(380,320),(240,400),(100,360),(200,240)
      fill: #1c78b0 opacity 0.8, or #4a9fd4 opacity 0.5, alternating.
    — Connect them with lines: stroke:#1c5fa8, stroke-width:1, opacity:0.4.
    — Add 3 larger concentric arc pairs (stroke-only circles): r=80,120,160 centred at (240,260),
      stroke:#1c78b0, stroke-width:1, opacity:0.15, fill:none.

BOTTOM BAND (position:absolute, top:660px, left:0, width:1280px, height:60px):
  background:#0d1e38.
  Inside: 'Roland Berger GmbH · Sederanger 1, 80538 Munich · www.rolandberger.com'
  position:absolute, top:672px, left:72px, font-size:10px, color:#3a5a7a.""",
    },
    {
        "ref": "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_013",
        "brief": """Three-column content slide. White background.

BACKGROUND: #ffffff.

HEADER:
  Blue rule: position:absolute, top:44px, left:64px, width:1152px, height:2px, background:#1c78b0.
  Kicker (top:56px, left:64px): 'PRODUCTIVITY DRIVERS — EUROPEAN INDUSTRY'
    font-size:10px, color:#1c78b0, letter-spacing:2px, text-transform:uppercase, font-weight:400.
  Headline (top:74px, left:64px, width:1100px):
    'Three structural forces determine which industrial firms pull ahead — and which fall behind'
    font-size:25px, font-weight:700, color:#1c2a3a, line-height:1.2.
    (At 25px, line-height 1.2, width 1100px → wraps to 2 lines = 60px tall. Ends at top:134px.)

THREE COLUMNS (top:156px):
  Column widths: 340px each. Gaps: 24px.
  Column 1: left:64px.   Column 2: left:428px.   Column 3: left:792px.
  Each column height: 480px.

  COLUMN STRUCTURE (all positions relative to column top-left as absolute from slide):
  Blue accent bar: width:36px, height:3px, background:#1c78b0. (Col1: top:156px, left:64px. Col2: top:156px, left:428px. Col3: top:156px, left:792px.)
  Column number (top+16px from bar): font-size:11px, color:#1c78b0, letter-spacing:2px, text-transform:uppercase.
  Column subhead (top+36px from bar): font-size:18px, font-weight:700, color:#1c2a3a.
  Thin divider (top+68px from bar): width:340px, height:1px, background:#d0d8e0.
  Three bullet rows (top+84px, spacing 62px each):
    Bullet circle: width:6px, height:6px, border-radius:50%, background:#1c78b0, vertical-align at text centre.
    Bullet text: left:+18px from circle, font-size:13px, color:#3a4a5a, line-height:1.45, max-width:316px.

  COLUMN 1 — AUTOMATION & ROBOTICS (top:172px, left:64px):
    Subhead: 'Physical Automation'
    Bullet 1: 'Industrial robot density in Germany reaches 322 units per 10,000 workers — 3× the global average'
    Bullet 2: 'Collaborative robot (cobot) installations growing at 24% CAGR, enabling SME deployment'
    Bullet 3: 'Payback periods for welding and assembly automation now under 18 months at scale'

  COLUMN 2 — AI & COGNITIVE TOOLS (top:172px, left:428px):
    Subhead: 'Intelligent Operations'
    Bullet 1: 'Predictive maintenance reduces unplanned downtime by 35–55% across automotive OEMs'
    Bullet 2: 'Generative AI cuts engineering design iteration cycles from weeks to hours'
    Bullet 3: 'AI-assisted quality control achieves defect detection rates of 99.7% — versus 97.1% human'

  COLUMN 3 — PLATFORM CONVERGENCE (top:172px, left:792px):
    Subhead: 'Digital Ecosystems'
    Bullet 1: 'Industrial IoT platforms integrating OT and IT data reduce inventory carrying costs by 18%'
    Bullet 2: 'Digital twin adoption at 41% among top-quartile manufacturers; 9% among bottom quartile'
    Bullet 3: 'Platform-enabled supply chain orchestration cuts order-to-delivery time by 28%'

FOOTER (top:668px, left:64px):
  font-size:10px, color:#9aa0a8.
  'Sources: IFR World Robotics 2024; McKinsey Manufacturing Survey; Roland Berger analysis, 2025'.""",
    },
    {
        "ref": "roland_berger_trend_compendium_2050_technology_and_innovation_slide_010",
        "brief": """Two-column evidence slide with horizontal bar chart and insight cards. White background.

BACKGROUND: #ffffff.

HEADER:
  Blue rule: position:absolute, top:44px, left:64px, width:1152px, height:2px, background:#1c78b0.
  Headline (top:56px, left:64px, width:800px):
    'European manufacturers trail US and Asian peers on technology adoption across all key dimensions'
    font-size:22px, font-weight:700, color:#1c2a3a, line-height:1.25.
    (22px × 1.25 × ~2.5 lines at 800px = ~69px tall. Ends at top:125px.)
  Subtitle (top:138px, left:64px):
    'Technology adoption index score by region [0–100], 2025 Roland Berger survey (n=842 firms)'
    font-size:12px, color:#6a7a8a, font-weight:400.

LEFT PANEL — HORIZONTAL BAR CHART (5 rows, starting top:172px):
  Chart area: left:64px, width:580px.

  Row structure per technology dimension (row height = 80px):
  Row 1 — Automation (top:172px):
    Label: left:64px, top:172px, font-size:13px, font-weight:600, color:#1c2a3a. Text: 'Automation & Robotics'
    Track 1 (EU):  top:194px, left:64px, width:390px, height:16px, background:#e8edf2, border-radius:2px.
    Fill EU:       top:194px, left:64px, width:218px (~56%), height:16px, background:#1c5fa8, border-radius:2px.
    Label '56':    top:194px, left:290px, font-size:11px, color:#fff, font-weight:700, line-height:16px.
    Track 2 (US):  top:214px, left:64px, width:390px, height:16px, background:#e8edf2, border-radius:2px.
    Fill US:       top:214px, left:64px, width:296px (~76%), height:16px, background:#7ab8e8, border-radius:2px.
    Label '76':    top:214px, left:344px, font-size:11px, color:#fff, font-weight:700, line-height:16px.
    Track 3 (Asia): top:234px, left:64px, width:390px, height:16px, background:#e8edf2, border-radius:2px.
    Fill Asia:     top:234px, left:64px, width:316px (~81%), height:16px, background:#a8ccdf, border-radius:2px.
    Label '81':    top:234px, left:354px, font-size:11px, color:#1c2a3a, font-weight:700, line-height:16px.
  (Repeat pattern for rows 2–5 with top offsets +80px each):
  Row 2 (top:252px) — 'AI & Machine Learning': EU 48, US 72, Asia 69.
  Row 3 (top:332px) — 'Digital Twin / Simulation': EU 39, US 65, Asia 71.
  Row 4 (top:412px) — 'Cloud & Edge Computing': EU 62, US 84, Asia 77.
  Row 5 (top:492px) — 'Cybersecurity Maturity': EU 71, US 80, Asia 58.
  (Scale: 100 score = 390px wide. EU:#1c5fa8, US:#7ab8e8, Asia:#a8ccdf.)

  Legend (top:580px, left:64px):
    Three colour swatches (12×12px) + labels: '■ Europe' (color:#1c5fa8) · '■ United States' (#7ab8e8) · '■ Asia-Pacific' (#a8ccdf)
    font-size:11px, color:#4a5a6a, gap:24px between legend items.

  Axis line: top:572px, left:64px, width:390px, height:1px, background:#c0c8d0.
  Axis labels (top:577px): '0' left:64px · '25' left:161px · '50' left:258px · '75' left:355px · '100' left:444px.
  font-size:10px, color:#9aa0a8.

RIGHT PANEL — INSIGHT CARDS (left:720px):
  Header: top:172px, left:720px. 'KEY FINDINGS' font-size:11px, font-weight:700, color:#1c2a3a, letter-spacing:1.5px, text-transform:uppercase.
  Card 1 (top:196px, left:720px, width:496px, height:108px):
    background:#f5f8fb, border-left:3px solid #1c78b0, padding:16px 20px, box-sizing:border-box.
    Stat '–18pt': font-size:38px, font-weight:700, color:#c0392b, line-height:1.
    Label 'European technology adoption gap vs. US peers, widening since 2022': font-size:12px, color:#4a5a6a, top:+8px.
  Card 2 (top:316px, left:720px, width:496px, height:108px): same card style.
    Stat '2.4×': font-size:38px, font-weight:700, color:#1c5fa8.
    Label 'higher productivity growth at top-quartile adopters vs. industry median'.
  Card 3 (top:436px, left:720px, width:496px, height:108px): same card style.
    Stat '€340bn': font-size:38px, font-weight:700, color:#1c5fa8.
    Label 'annual output at risk if European firms do not close the adoption gap by 2030'.

FOOTER (top:668px, left:64px):
  font-size:10px, color:#9aa0a8.
  'Sources: Roland Berger Technology Adoption Survey 2025; World Economic Forum; Eurostat'.""",
    },
    {
        "ref": "roland_berger_european_pe_outlook_1_slide_002",
        "brief": """2×2 strategic matrix slide — "Four archetypes of industrial response". White background.

BACKGROUND: #ffffff.

HEADER:
  Blue rule: position:absolute, top:44px, left:64px, width:1152px, height:2px, background:#1c78b0.
  Kicker (top:56px, left:64px): 'STRATEGIC ARCHETYPES'
    font-size:10px, color:#1c78b0, letter-spacing:2px, text-transform:uppercase.
  Headline (top:74px, left:64px, width:900px):
    'European firms fall into four archetypes — only one is positioned to lead'
    font-size:25px, font-weight:700, color:#1c2a3a, line-height:1.2.

2×2 MATRIX (top:148px, left:64px, width:820px, height:500px):
  The matrix has two axes:
    Y-axis label (vertical, rotated): left:64px, top:320px.
      Use transform:rotate(-90deg). Text: 'SPEED OF ADOPTION →'. font-size:10px, color:#6a7a8a, letter-spacing:1.5px.
    X-axis label: top:650px, left:350px. Text: 'BREADTH OF TECHNOLOGY PORTFOLIO →'. Same style.

  Cross lines:
    Vertical centre: position:absolute, top:148px, left:484px, width:1px, height:500px, background:#d0d8e0.
    Horizontal centre: position:absolute, top:398px, left:84px, width:800px, height:1px, background:#d0d8e0.

  Four quadrant cards (each width:390px, height:244px, padding:24px, box-sizing:border-box):
    Q1 TOP-LEFT (top:148px, left:84px): background:#f5f8fb, border-top:3px solid #7ab8e8.
      Badge circle (width:32px, height:32px, border-radius:50%, background:#7ab8e8): text '2', color:#fff, font-size:14px, font-weight:700.
      Title (top:+44px): 'Fast Movers' font-size:17px, font-weight:700, color:#1c2a3a.
      Desc (top:+68px, width:340px): 'High adoption speed but narrow tech scope — risks missing platform convergence benefits.'
        font-size:13px, color:#4a5a6a, line-height:1.45.
      Share tag (bottom-right of card): '28% of firms' font-size:11px, color:#7ab8e8, font-weight:600.

    Q2 TOP-RIGHT (top:148px, left:490px): background:#e8f2fb, border-top:3px solid #1c5fa8.
      Badge circle (background:#1c5fa8): text '1', color:#fff.
      Title: 'Transformation Leaders' font-size:17px, font-weight:700, color:#1c2a3a.
      Desc: 'Broad technology portfolio adopted rapidly — capturing compounding productivity gains.'
        font-size:13px, color:#4a5a6a, line-height:1.45.
      Share tag: '14% of firms' color:#1c5fa8.

    Q3 BOTTOM-LEFT (top:404px, left:84px): background:#f9f9f9, border-top:3px solid #c0c8d0.
      Badge circle (background:#9aa0a8): text '4', color:#fff.
      Title: 'Laggards' font-size:17px, font-weight:700, color:#1c2a3a.
      Desc: 'Slow adoption, narrow scope — facing acute competitive exposure within 3–5 years.'
        font-size:13px, color:#4a5a6a, line-height:1.45.
      Share tag: '35% of firms' color:#9aa0a8.

    Q4 BOTTOM-RIGHT (top:404px, left:490px): background:#f5f8fb, border-top:3px solid #4a9fd4.
      Badge circle (background:#4a9fd4): text '3', color:#fff.
      Title: 'Deep Specialists' font-size:17px, font-weight:700, color:#1c2a3a.
      Desc: 'Broad portfolio, methodical pace — strong in their segment but vulnerable to agile disruptors.'
        font-size:13px, color:#4a5a6a, line-height:1.45.
      Share tag: '23% of firms' color:#4a9fd4.

RIGHT SIDEBAR CALLOUT (left:920px, top:148px, width:360px):
  Header: 'IMPLICATION' font-size:11px, font-weight:700, color:#1c2a3a, letter-spacing:1.5px, text-transform:uppercase.
  Text block (top:+24px, width:340px, font-size:13px, color:#3a4a5a, line-height:1.6):
    'Only 14% of European industrial firms are on a trajectory to close the productivity gap with US and Asian leaders by 2030.
     The remaining 86% face a compounding disadvantage as technology lock-in effects intensify.
     Strategic repositioning is most feasible in the next 18–24 months before platform dependencies solidify.'
  Bold highlight box (top:+120px, width:340px, background:#f5f8fb, border-left:3px solid #1c78b0, padding:12px 16px):
    Text: '"The window to move from archetype 4 to archetype 1 is closing faster than most leadership teams recognise."'
    font-size:12px, color:#1c2a3a, font-style:italic, line-height:1.5.

FOOTER (top:668px, left:64px):
  font-size:10px, color:#9aa0a8.
  'Sources: Roland Berger Industrial Technology Survey 2025; n=842 firms across DE, FR, IT, PL, SE, NL'.""",
    },
    {
        "ref": "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_013",
        "brief": """Five-row executive action plan slide. White background.

BACKGROUND: #ffffff.

HEADER:
  Blue rule: position:absolute, top:44px, left:64px, width:1152px, height:2px, background:#1c78b0.
  Kicker (top:56px, left:64px): 'LEADERSHIP IMPERATIVES'
    font-size:10px, color:#1c78b0, letter-spacing:2px, text-transform:uppercase, font-weight:400.
  Headline (top:74px, left:64px, width:1000px):
    'Five actions that separate transformation leaders from the rest — ranked by impact and urgency'
    font-size:25px, font-weight:700, color:#1c2a3a, line-height:1.2.
    (2 lines × 30px = 60px. Ends at top:134px.)

FIVE ACTION ROWS (starting top:152px, left:64px, width:1152px):
  Each row height:96px. Separator line between rows: height:1px, background:#e0e6ec.

  Row layout (all absolute from slide top, each row_top = 152 + (row_index × 97)):
    Number badge: width:36px, height:36px, border-radius:50%, background:#1c78b0, text-align:center, line-height:36px.
      font-size:16px, font-weight:700, color:#ffffff. left:64px, top: row_top + 28px.
    Action headline: left:116px, top: row_top + 24px. font-size:15px, font-weight:700, color:#1c2a3a.
    Action detail:   left:116px, top: row_top + 46px, width:820px. font-size:13px, color:#4a5a6a, line-height:1.4.
    Time badge: right-aligned at left:1040px, top: row_top + 32px.
      background:#eef3f8, border-radius:12px, padding:4px 12px. font-size:11px, color:#1c78b0, font-weight:600.

  ROW 1 (row_top:152px):
    Headline: 'Appoint a Chief Automation Officer and embed technology ownership at the board level'
    Detail:   '78% of firms that achieved top-quartile productivity growth had C-suite technology accountability established before programme launch.'
    Time badge: 'Immediate · 0–3 months'

  ROW 2 (row_top:249px):
    Headline: 'Launch a Technology Readiness Assessment across all manufacturing and logistics sites'
    Detail:   'Baseline your position on all five adoption dimensions. Without diagnostic clarity, investment prioritisation is guesswork.'
    Time badge: '0–6 months'

  ROW 3 (row_top:346px):
    Headline: 'Commit ≥3% of revenue to technology capex for three consecutive years — and hold the line'
    Detail:   'Compounding adoption effects require sustained investment. Firms that cut in year 2 lose disproportionately more than the saving.'
    Time badge: '6–18 months'

  ROW 4 (row_top:443px):
    Headline: 'Build digital talent through targeted acquisition, not solely reskilling'
    Detail:   'Reskilling timelines (18–36 months) exceed the competitive window. Hire AI/automation specialists externally while reskilling runs in parallel.'
    Time badge: '6–24 months'

  ROW 5 (row_top:540px):
    Headline: 'Join or anchor a platform ecosystem — do not attempt to build proprietary stacks alone'
    Detail:   'Industrial platform leaders in automotive and machinery recoup ecosystem investment 2.8× faster than solo stack builders.'
    Time badge: '12–36 months'

FOOTER (top:668px, left:64px):
  font-size:10px, color:#9aa0a8.
  'Roland Berger Technology Practice perspective · Based on 200+ industrial transformation programmes, 2020–2025'.""",
    },
]


def read_ref(slide_id: str) -> str:
    path = HTML_DIR / f"{slide_id}.html"
    if not path.exists():
        print(f"  WARN: reference slide not found: {slide_id}")
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def generate_slide(brief: str, ref_html: str, idx: int, total: int) -> str:
    print(f"  Generating slide {idx+1}/{total} ...", end=" ", flush=True)

    user_content = (
        f"Create a new {W}×{H}px HTML/CSS presentation slide.\n\n"
        f"SLIDE BRIEF — follow this exactly. Every element described must appear:\n{brief}\n\n"
        f"STYLE REFERENCE — this is a real Roland Berger slide from the dataset. "
        f"Inherit its colour palette, font conventions, spacing rhythm, and CSS patterns. "
        f"Do NOT copy its content — generate the new content from the brief above:\n\n"
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
<title>Roland Berger — The Productivity Imperative: Technology Megatrends 2025</title>
<style>
  body {{ margin:0; background:#0a0f1e; display:flex; flex-direction:column;
         align-items:center; justify-content:center; min-height:100vh;
         font-family:Arial,sans-serif; }}
  h1 {{ color:#8a9aaa; font-size:12px; font-weight:400; margin:16px 0 8px;
        letter-spacing:2px; text-transform:uppercase; }}
  .slide-card {{ text-align:center; }}
  .label {{ color:#4a6a8a; font-size:11px; margin-bottom:8px; letter-spacing:1px; }}
  iframe {{ display:block; border-radius:3px; box-shadow:0 12px 48px rgba(0,0,0,0.7); }}
  .nav {{ display:flex; gap:16px; margin-top:20px; align-items:center; }}
  button {{ background:#111828; border:1px solid #2a3a5a; color:#8a9aaa;
            padding:8px 28px; border-radius:3px; cursor:pointer; font-size:12px;
            letter-spacing:1px; text-transform:uppercase; }}
  button:hover {{ background:#1a2a4a; color:#aac0d8; }}
  .dots {{ display:flex; gap:8px; align-items:center; }}
  .dot {{ width:7px; height:7px; border-radius:50%; background:#2a3a5a; cursor:pointer; transition:background 0.2s; }}
  .dot.active {{ background:#1c78b0; }}
</style>
</head>
<body>
<h1>Roland Berger · The Productivity Imperative · European Industry 2025</h1>
{cards}
<div class="nav">
  <button onclick="move(-1)">&#8592; Prev</button>
  <div class="dots" id="dots"></div>
  <button onclick="move(1)">Next &#8594;</button>
</div>
<script>
  var cur=0, total={len(slides_html)};
  var dots=document.getElementById('dots');
  for(var i=0;i<total;i++){{
    var d=document.createElement('div');
    d.className='dot'+(i===0?' active':'');
    d.dataset.i=i;
    d.onclick=function(){{go(+this.dataset.i);}};
    dots.appendChild(d);
  }}
  function go(n){{
    document.getElementById('s'+cur).style.display='none';
    dots.children[cur].classList.remove('active');
    cur=(n+total)%total;
    document.getElementById('s'+cur).style.display='block';
    dots.children[cur].classList.add('active');
  }}
  function move(d){{go(cur+d);}}
  document.addEventListener('keydown',function(e){{
    if(e.key==='ArrowRight')move(1);
    if(e.key==='ArrowLeft')move(-1);
  }});
</script>
</body>
</html>"""


def main():
    print("Roland Berger Sample Deck — The Productivity Imperative: Technology Megatrends 2025")
    print(f"Output: {OUT}\n")

    slides_html = []
    for i, slide_def in enumerate(SLIDES):
        ref_html = read_ref(slide_def["ref"])
        html = generate_slide(slide_def["brief"], ref_html, i, len(SLIDES))
        slides_html.append(html)
        if i < len(SLIDES) - 1:
            time.sleep(1)

    deck = wrap_deck(slides_html)
    OUT.write_text(deck, encoding="utf-8")
    print(f"\nDone — {OUT}")


if __name__ == "__main__":
    main()
