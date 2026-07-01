"""
generate_deck_v4.py — "The AI-Ready Enterprise: Building Competitive Advantage
in the Intelligence Economy"

Improvements over v3:
  - Smart reference selection by layout_type from dataset.json (no hardcoding)
  - Anti-overlap rule baked into system prompt
  - Palette lock enforced in every brief
  - New chart types: grouped bar, dot-plot, Gantt-style timeline
  - Leaner 12-slide structure (tighter, more impactful)
  - EY slides included as references

Usage:
    python generate_deck_v4.py
    python generate_deck_v4.py --out ../full_deck_v4.html
"""
from __future__ import annotations

import argparse, base64, json, os, re, time
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

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
)

SYSTEM = f"""You are a senior front-end developer at Bain & Company producing pixel-perfect HTML/CSS slides.

ABSOLUTE RULES (violations will break the slide):
1. Output ONLY complete HTML starting with <!DOCTYPE html>. No markdown, no explanation.
2. Root element: exactly {W}px wide, {H}px tall, position:relative, overflow:hidden.
3. Every child element: position:absolute. No flexbox/grid at top level.
4. No <script>, no <img>, no external URLs. System fonts only (Arial, Helvetica, sans-serif).
5. Charts: inline SVG using <rect><line><circle><path> only.

ANTI-OVERLAP RULE (critical — apply before setting any top value):
  Estimate headline width = char_count x font_size x 0.55
  If this exceeds container width, reduce font_size until it fits on ONE line.
  Then: subtitle_top = headline_top + font_size x 1.3 + 10px minimum gap.
  For a 90-char headline: 16px fits in 960px (90x16x0.55=792), 17px fits (90x17x0.55=842).
  Never use font-size above 18px for headlines longer than 75 characters.

{PALETTE}"""


# ── Smart reference selector ──────────────────────────────────────────────────

_dataset: list[dict] | None = None

def _load_dataset() -> list[dict]:
    global _dataset
    if _dataset is None:
        with open(DATASET) as f:
            _dataset = json.load(f)["slides"]
    return _dataset

def best_refs(layout_types: list[str], n: int = 3,
              exclude_sources: list[str] | None = None) -> list[str]:
    """Pick top-n slides by visual_polish matching any of the given layout_types."""
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
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return base64.standard_b64encode(f.read()).decode()

def collect(sids: list[str]) -> list[dict]:
    out = []
    for sid in sids:
        p = HTML_DIR / f"{sid}.html"
        if not p.exists():
            continue
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

    # Pre-select references by layout type
    r_cover   = best_refs(["cover"],                    n=2)
    r_exec    = best_refs(["exec_summary"],             n=3)
    r_chart   = best_refs(["full_chart"],               n=3)
    r_two_col = best_refs(["two_col_chart"],            n=3)
    r_mixed   = best_refs(["mixed_layout"],             n=3)
    r_section = best_refs(["section_divider","cover"],  n=2, exclude_sources=["EY"])
    r_diag    = best_refs(["diagram","three_col_text"], n=2)

    print("\nReference selection:")
    for label, refs in [("cover",r_cover),("exec",r_exec),("chart",r_chart),
                        ("two_col",r_two_col),("mixed",r_mixed),
                        ("section",r_section),("diag",r_diag)]:
        print(f"  {label}: {refs}")
    print()

    return [

        # ── 1. COVER ──────────────────────────────────────────────────────────
        {
            "refs": r_cover,
            "label": "01 Cover",
            "brief": """Cover slide. 1280x720px.

LAYOUT: Left 56% white content zone. Right 44% = dark panel #0A0A0A.
Vertical divider: left:717px top:0 width:1px height:720px background:#E8E8E8.

LEFT ZONE (all absolute, on white background #FFFFFF):
  A: top:0 left:0 width:717px height:720px background:#FFFFFF (base)
  B: top:0 left:0 width:5px height:720px background:#C41230 (left accent)
  C: top:48px left:72px — 'THE AI-READY ENTERPRISE' font-size:9px letter-spacing:4px
     color:#C41230 font-weight:700 text-transform:uppercase
  D: top:68px left:72px width:40px height:1px background:#C41230
  E: top:84px left:72px width:580px — title block, 3 lines as separate divs:
     Line 1: 'The AI-Ready' font-size:56px font-weight:800 color:#1A1A1A line-height:64px
     Line 2: 'Enterprise' font-size:56px font-weight:300 color:#C41230 line-height:64px
     Line 3: 'Blueprint' font-size:56px font-weight:800 color:#1A1A1A line-height:64px
     (block ends at top:84+192=276px)
  F: top:296px left:72px width:540px font-size:13px color:#555 line-height:1.7
     'A C-suite framework for deploying AI at enterprise scale — from readiness
     assessment to competitive advantage'
     (2 lines at 13px = ~36px, ends at 332px)
  G: top:356px left:72px width:580px height:1px background:#E8E8E8
  H: top:374px left:72px — three stat pills, display:inline-block each,
     padding:6px 16px border:1px solid #E8E8E8 border-radius:2px margin-right:10px
     font-size:9px color:#888 letter-spacing:1px white-space:nowrap
     Pills: '12 Strategic Imperatives' | 'CEO-Level' | 'Confidential 2025'
  I: top:686px left:72px font-size:9px color:#CCCCCC
     'Prepared for Executive Leadership'
  J: top:686px left:600px font-size:9px color:#CCCCCC '1'

RIGHT ZONE (dark #0A0A0A, left:717px width:563px):
  K: top:0 left:717px width:563px height:720px background:#0A0A0A
  L: Inline SVG top:0 left:717px width:563px height:720px:
     Draw ONLY:
     - 6 horizontal red lines at y:120,200,280,360,440,520
       each: x1=60+(i*12) x2=x1+(80+i*30) stroke:#C41230 opacity:0.25 stroke-width:1.5
     - 3 white circles r:100,70,45 at cx:460,cy:240 | cx:380,cy:480 | cx:500,cy:560
       fill:none stroke:white opacity:0.04 stroke-width:1
     - 5x4 dot grid r:2 fill:white opacity:0.12 starting x:80 y:80 spacing:52px horizontal 60px vertical
     - Two large text numbers (SVG text): '74' x:340 y:200 font-size:96px font-weight:800
       fill:white opacity:0.04
       '%' x:420 y:180 font-size:48px fill:#C41230 opacity:0.15

NOTHING ELSE.""",
        },

        # ── 2. AGENDA — Horizontal timeline cards ──────────────────────────────
        {
            "refs": r_mixed,
            "label": "02 Agenda",
            "brief": """Agenda slide. 1280x720px. Background #FFFFFF.

DESIGN: Horizontal timeline with 4 chapter cards. A continuous horizontal line
connects numbered nodes above each card.

HEADER:
  A: top:0 width:1280px height:3px background:linear-gradient(90deg,#C41230,transparent)
  B: top:16px left:64px 'AGENDA' font-size:9px letter-spacing:4px color:#C41230 font-weight:700
  C: top:34px left:64px 'From assessment to advantage — four chapters' font-size:20px font-weight:700 color:#1A1A1A
  D: top:68px left:64px width:1152px height:1px background:#E8E8E8

TIMELINE BAR (top:96px):
  Horizontal line: top:120px left:120px width:1040px height:2px background:#E8E8E8
  4 nodes at x: 184, 464, 744, 1024 — each:
    Circle top:108px: width:24px height:24px border-radius:50% border:2px solid #C41230
    background (node 1 only):#C41230; others:#FFFFFF
    Number inside: font-size:11px font-weight:700 color:#C41230 (or white for filled)
    Text-align:center line-height:20px

4 CHAPTER CARDS (top:148px, each width:240px height:476px):
  Left edges: 64, 344, 624, 904.
  Each card: border-left:3px solid (chapter color) padding-left:20px

  Card 1 (left:64, color:#C41230):
    top:156px left:84px 'CHAPTER 1' font-size:9px letter-spacing:3px color:#C41230 font-weight:700
    top:178px left:84px 'AI Readiness' font-size:22px font-weight:800 color:#1A1A1A
    top:212px left:84px 'Assessment' font-size:22px font-weight:300 color:#C41230
    top:248px left:84px width:210px font-size:11px color:#555 line-height:1.65
      'Evaluate your AI maturity across five dimensions: data, talent,
      technology, process, and governance'
    top:380px left:84px '38%' font-size:44px font-weight:800 color:#C41230
    top:432px left:84px width:210px font-size:10px color:#888
      'of enterprises score "developing" or below on AI readiness — the baseline most face'

  Card 2 (left:344, color:#0D4D8C):
    'CHAPTER 2' color:#0D4D8C
    'Investment' font-size:22px font-weight:800
    'Architecture' font-size:22px font-weight:300 color:#0D4D8C
    'Allocate AI investment across the right functions — build, buy, and partner decisions'
    '$4.1tn' font-size:44px font-weight:800 color:#0D4D8C
    'total enterprise AI investment expected globally by 2027'

  Card 3 (left:624, color:#1B7A3E):
    'CHAPTER 3' color:#1B7A3E
    'Operating' font-size:22px font-weight:800
    'Model Shift' font-size:22px font-weight:300 color:#1B7A3E
    'Redesign workflows and org structure around AI-augmented decision making'
    '2.4x' font-size:44px font-weight:800 color:#1B7A3E
    'productivity gain for firms that redesign operating model vs. overlay AI on existing processes'

  Card 4 (left:904, color:#B35C00):
    'CHAPTER 4' color:#B35C00
    'Governance' font-size:22px font-weight:800
    '& Risk' font-size:22px font-weight:300 color:#B35C00
    'Establish AI governance, risk frameworks, and responsible deployment standards'
    '61%' font-size:44px font-weight:800 color:#B35C00
    'of boards lack a formal AI governance framework — the critical gap for 2025'

FOOTER: top:672px left:64px 'The AI-Ready Enterprise Blueprint | 2025' font-size:9px color:#AAAAAA
FOOTER: top:672px right:64px '2' font-size:9px color:#AAAAAA
NOTHING ELSE.""",
        },

        # ── 3. EXEC SUMMARY — 6-KPI grid + bar chart ─────────────────────────
        {
            "refs": r_exec,
            "label": "03 Exec Summary",
            "brief": """Executive summary. 1280x720px. Background #FFFFFF.

HEADER:
  A: top:0 width:1280px height:3px background:#C41230
  B: top:16px left:64px 'EXECUTIVE SUMMARY' font-size:9px letter-spacing:4px color:#C41230 font-weight:700
  C: top:34px left:64px width:900px 'Six numbers that define the AI imperative — and the cost of delay'
     font-size:16px font-weight:700 color:#1A1A1A
  D: top:68px left:64px width:1152px height:1px background:#E8E8E8

6-KPI GRID (top:80px, 3 cols x 2 rows, each cell 280px wide 148px tall):
  Left column x:64, middle x:352, right x:640. Row 1 top:80, row 2 top:236.
  Each cell: border-bottom:1px solid #F0F0F0 border-right:1px solid #F0F0F0 padding implied.

  Cell (1,1) top:88px left:72px: '74%' 44px 800 #C41230 / 'of enterprises now run AI in production (up from 37% in 2022)' 10px #555
  Cell (1,2) top:88px left:360px: '14mo' 44px 800 #1A1A1A / 'average AI payback period — down from 26 months in 2023'
  Cell (1,3) top:88px left:648px: '$2.6tn' 44px 800 #1A1A1A / 'latent value in AI deployments not yet at enterprise scale'
  Cell (2,1) top:244px left:72px: '3.1x' 44px 800 #1B7A3E / 'revenue growth differential: AI leaders vs. AI followers'
  Cell (2,2) top:244px left:360px: '40%' 44px 800 #1A1A1A / 'of roles substantially transformed by AI by 2028'
  Cell (2,3) top:244px left:648px: '61%' 44px 800 #B35C00 / 'of boards have no formal AI governance framework'

  Grid border lines:
    Vertical at left:632px top:80px height:296px 1px #F0F0F0
    Vertical at left:920px top:80px height:296px 1px #F0F0F0
    Horizontal at top:228px left:64px width:856px 1px #F0F0F0
  Bottom border: top:376px left:64px width:856px height:1px background:#E8E8E8

KEY FINDINGS (top:392px left:64px):
  Label: 'KEY FINDINGS' font-size:9px letter-spacing:3px color:#C41230 font-weight:700
  3 finding rows at top: 412, 450, 488. Each row:
    Red bullet left:64px width:6px height:6px background:#C41230 border-radius:50% (centered vertically)
    Text left:84px font-size:12px color:#1A1A1A font-weight:600 (first 30 chars)
    continuation font-weight:400 color:#555 (rest of sentence)

  Row 1: 'Scale gap is the top risk:' + ' 74% have deployed AI but only 12% have reached enterprise scale'
  Row 2: 'Governance lags deployment:' + ' boards approve AI budgets but 61% have no oversight framework'
  Row 3: 'Operating model is the binding constraint:' + ' technology is available; org change is not'

RIGHT PANEL (top:80px left:956px width:260px height:560px):
  background:#FAFAFA border:1px solid #E8E8E8
  Title top:96px left:972px 'CEO Priority Shift' font-size:11px font-weight:700 color:#1A1A1A
  Sub top:114px left:972px '% citing as #1 strategic priority' font-size:9px color:#888

  Inline SVG (top:130px left:972px width:228px height:380px):
    5 horizontal bars, each height:48px gap:8px.
    Bar data (label, 2023%, 2025%):
      'AI & Data'      32 74
      'Talent'         41 66
      'Digital Infra'  28 57
      'Sustainability' 35 51
      'Geopolitics'    29 43

    For each bar row at y=i*56:
      Label: x:0 y:y+30 font-size:10px fill:#555
      2023 bar: x:80 y:y+14 height:14 fill:#E8E8E8 width=val*1.8
      2025 bar: x:80 y:y+30 height:14 fill:#C41230 (first) or #1A1A1A (rest) width=val*1.8
      Values: after each bar font-size:9px font-weight:700

    Legend at y:300: red sq 'FY2025' | grey sq 'FY2023'

FOOTER: top:672px 'Sources: Bain CEO Survey 2025; McKinsey State of AI; Accenture' left:64px 9px #AAAAAA | '3' right:64px
NOTHING ELSE.""",
        },

        # ── 4. AI READINESS — Quadrant scatter ────────────────────────────────
        {
            "refs": r_chart,
            "label": "04 Readiness Matrix",
            "brief": """Data slide: AI readiness 2x2 quadrant scatter. 1280x720px. White.

HEADER:
  Red rule top:0. Kicker: 'CHAPTER 1 | AI READINESS' color:#C41230.
  Headline (top:34px left:64px width:960px font-size:16px font-weight:700):
  'Most enterprises are stuck in the "Capable but Constrained" quadrant — only 12% are Scaled'
  Sub (top:64px): 'AI readiness vs. deployment scale, 2025 (n=2,400 global enterprises)'

QUADRANT CHART (SVG top:80px left:64px width:720px height:576px):
  Background #FAFAFA. Plot area x:80 y:24 to x:680 y:504.

  X-axis: 'AI Readiness Score (Technology + Data + Talent)' 0-100
    Baseline y:504. Ticks at x:80,230,380,530,680 labels:'0','25','50','75','100'
  Y-axis: 'Deployment Scale (% functions with AI in production)' 0-100%
    Left line x:80. Ticks at y:504,429,354,279,204,129,54 labels:'0%','10%','20%','30%','40%','50%','60%'

  Midlines (at x:380, y:279) — dashed #CCCCCC:
    Vertical: x:380 y1:24 y2:504
    Horizontal: y:279 x1:80 x2:680

  QUADRANT LABELS (font-size:10px italic fill:#CCCCCC):
    Bottom-left (x:90 y:490): 'NOT READY'
    Bottom-right (x:390 y:490): 'CAPABLE BUT CONSTRAINED'
    Top-left (x:90 y:38): 'FAST MOVERS'
    Top-right (x:390 y:38): 'AI LEADERS' fill:#C41230 font-weight:700

  QUADRANT BACKGROUNDS:
    Bottom-left: x:80 y:279 w:300 h:225 fill:#FAFAFA
    Bottom-right: x:380 y:279 w:300 h:225 fill:#FFF8F5
    Top-left: x:80 y:24 w:300 h:255 fill:#F5FAF7
    Top-right: x:380 y:24 w:300 h:255 fill:#FFF0F0

  BUBBLES (cx, cy=y for that scale, r=bubble_size, fill):
    Scale: readiness_score->x = 80+score*6, deployment%->y = 504-pct*4.5

    'AI Leaders' cluster (top-right):
      cx:650 cy:42  r:24 fill:#C41230 opacity:0.8 label:'Amazon'
      cx:620 cy:80  r:20 fill:#C41230 opacity:0.7 label:'Google'
      cx:590 cy:120 r:18 fill:#C41230 opacity:0.65 label:'Microsoft'

    'Capable but Constrained' cluster (bottom-right):
      cx:530 cy:340 r:32 fill:#1A1A1A opacity:0.6 label:'JP Morgan'
      cx:480 cy:370 r:28 fill:#555555 opacity:0.55 label:'Walmart'
      cx:440 cy:400 r:24 fill:#888888 opacity:0.5 label:'Siemens'

    'Fast Movers' (top-left):
      cx:240 cy:140 r:18 fill:#1B7A3E opacity:0.7 label:'Shopify'
      cx:200 cy:180 r:14 fill:#1B7A3E opacity:0.6 label:'Grab'

    'Not Ready' (bottom-left):
      cx:160 cy:430 r:20 fill:#CCCCCC stroke:#888 opacity:0.8 label:'Avg. Gov.'
      cx:200 cy:400 r:16 fill:#CCCCCC stroke:#888 label:'SMB avg.'

    Each bubble: white label text centered, font-size:8px font-weight:700

  SCALE NOTE: x:84 y:516 'Bubble size = annual AI investment ($M)' font-size:8px fill:#888

RIGHT PANEL (top:80px left:808px width:408px):
  Panel background:#FAFAFA border:1px solid #E8E8E8.
  Title top:96px: 'Readiness breakdown by dimension' font-size:11px font-weight:700

  5 dimension bars (each 76px row, top:120px left:824px):
    'Data Infrastructure'  score:42/100  fill:#C41230
    'AI Talent & Skills'   score:38/100  fill:#C41230
    'Technology Stack'     score:58/100  fill:#1A1A1A
    'Process Automation'   score:51/100  fill:#1A1A1A
    'Governance & Risk'    score:29/100  fill:#B35C00

    Each bar: label left, score bar (max width 280px), score label right
    Bar widths = score * 2.8

  Benchmark line at x=50*2.8=140 (score 50) dashed red vertical across all bars.
  Label 'Industry avg.' at top of benchmark line font-size:8px fill:#C41230

FOOTER: 'Sources: Bain AI Readiness Index 2025; MIT CISR; McKinsey' | '4'
NOTHING ELSE.""",
        },

        # ── 5. INVESTMENT DATA — Grouped bar chart ────────────────────────────
        {
            "refs": r_chart,
            "label": "05 Investment Grouped Bars",
            "brief": """Data slide: grouped bar chart. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 2 | INVESTMENT ARCHITECTURE'.
  Headline (font-size:16px max, width:960px): 'AI investment doubled in two years — but distribution across functions reveals misalignment with value'
  Sub: 'Annual enterprise AI investment by function ($bn), 2022 vs 2025 (n=1,800 global firms)'

GROUPED BAR CHART (SVG top:86px left:64px width:820px height:510px):
  Background #FAFAFA. Plot x:90 y:20 to x:790 y:440.

  8 function groups, each group width=86px, gap=9px between groups.
  Starting x: 90. Group x positions: 90, 185, 280, 375, 470, 565, 660, 755.
  Within each group: 2 bars (2022=width:36px, 2025=width:36px, gap:8px).
  Colors: 2022=#CCCCCC, 2025=#C41230 (first 3 functions showing growth) or #1A1A1A.

  Y-axis: $bn, range 0-180. Scale: 180/420=0.43px per $bn. y = 440 - value/180*420.
  Gridlines at $bn 0,45,90,135,180: y=440,345,251,156,62. Stroke:#F0F0F0.
  Y labels: x:86 text-anchor:end font-size:9px fill:#888.

  Data (function, 2022_bn, 2025_bn):
  'Customer\nExp.'    28  78
  'Operations'        45  122
  'R&D/Product'       18  67
  'Risk/Fraud'        52  89
  'HR/Talent'         8   29
  'Finance'           14  38
  'Supply Chain'      31  74
  'IT/Infra'          62  158

  For each group at gx:
    2022 bar: x=gx y=440-val22/180*420 w:36 h=val22/180*420 fill:#CCCCCC rx:2
    2025 bar: x=gx+44 y=440-val25/180*420 w:36 h=val25/180*420
      fill:#C41230 if val25-val22>50 else #1A1A1A rx:2
    Growth badge above 2025 bar: '+{growth}%' font-size:8px fill:#1B7A3E font-weight:700
    Function label at y:458 x=gx+40 text-anchor:middle font-size:9px fill:#555

  Baseline y:440 stroke:#CCCCCC.

  LEGEND at y:470: grey sq '2022' | red sq '2025 (projected)'

  ANNOTATION box at x:484 y:40 w:200 h:48 fill:#FFF5F5 stroke:#C41230 rx:2:
    'IT/Infra leads at $158bn' font-size:10px font-weight:700 fill:#C41230
    'but Operations shows biggest ROI per $bn invested' font-size:9px fill:#555

RIGHT PANEL (top:86px left:908px width:308px):
  3 stat cards (each 152px):
  Card 1: '$640bn' 40px 800 #C41230 / 'total enterprise AI spend 2025 — up from $258bn in 2022'
  Card 2: '2.5x' 40px 800 #1A1A1A / 'Operations ROI per $bn is 2.5x IT Infrastructure — yet IT still receives 25% of budget'
  Card 3: '$1.6bn' 40px 800 #1A1A1A / 'average spend at which AI investment turns self-funding through cost reduction'

FOOTER: 'Sources: Gartner IT Spending 2025; Bain AI Investment Survey; IDC' | '5'
NOTHING ELSE.""",
        },

        # ── 6. PRODUCTIVITY — Dot-plot (before/after) ─────────────────────────
        {
            "refs": r_two_col,
            "label": "06 Productivity Dot-Plot",
            "brief": """Data slide: dot-plot showing before/after AI productivity by role. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 2 | PRODUCTIVITY IMPACT'.
  Headline (font-size:16px width:960px): 'AI augmentation delivers uneven productivity gains — white-collar knowledge work leads by 2x'
  Sub: 'Estimated productivity improvement per role type with AI augmentation, 2025 (% time saved on core tasks)'

DOT-PLOT CHART (SVG top:86px left:64px width:780px height:520px):
  Background #FAFAFA. Plot area x:220 y:20 to x:740 y:480.
  9 role rows, evenly spaced: y = 20 + i*56 for i=0..8.

  X-axis: 0% to 60% improvement. Scale: 60%=520px. 1%=8.67px. x(v) = 220 + v*8.67.
  Baseline x:220 y:490 width:520 stroke:#CCCCCC.
  Ticks at 0,15,30,45,60%: x=220,350,480,610,740. Labels y:504 font-size:9px fill:#888.
  Vertical gridlines at those x positions: y1:20 y2:480 stroke:#F0F0F0.
  Axis label: 'Productivity improvement (% time saved)' x:480 y:518 text-anchor:middle font-size:10px fill:#555.

  9 ROLE ROWS (label left, connector line, before dot, after dot):
    Role labels: x:212 text-anchor:end font-size:11px fill:#1A1A1A (role name), y=row_y+6.

    Data (role, before%, after%):
    'Legal Analysis'      5  52
    'Financial Analyst'   4  48
    'Software Dev.'       6  44
    'Marketing Writer'    3  40
    'HR/Recruiting'       4  36
    'Customer Support'    8  34
    'Supply Chain Ops'    6  28
    'Manufacturing'       4  18
    'Physical Labour'     2   8

    For each row at y=20+i*56:
      Connector line: x1=220+before*8.67 y1=y x2=220+after*8.67 y2=y
        stroke:#E8E8E8 stroke-width:2
      Before dot: cx=220+before*8.67 cy=y r:7 fill:#CCCCCC stroke:#888 stroke-width:1
      After dot: cx=220+after*8.67 cy=y r:9
        fill:#C41230 if i<3 else fill:#1A1A1A if i<6 else fill:#888888
      After value label: x=220+after*8.67+14 y=y+4 font-size:10px font-weight:700
        fill matches dot color content='{after}%'

  LEGEND at y:490 x:220: grey dot 'Without AI' | red dot 'With AI augmentation'

  ANNOTATION bracket (SVG path) highlighting top 3 rows:
    Dashed box around rows 0-2: x:470 y:8 w:264 h:172 fill:none stroke:#C41230 stroke-dasharray:4
    Label 'KNOWLEDGE WORK LEADERS' x:474 y:24 font-size:8px fill:#C41230 font-weight:700

RIGHT CALLOUT PANEL (top:86px left:868px width:348px):
  Panel background:#FAFAFA border:1px solid #E8E8E8.
  Title: 'Why the gap is structural' font-size:11px font-weight:700 top:102px left:884px.

  3 insight blocks (each 140px):
  Block 1 top:130px:
    Red 3px left border.
    '48%' font-size:36px font-weight:800 color:#C41230
    'average productivity lift for knowledge roles — driven by reasoning and drafting automation'
    font-size:10px color:#555 line-height:1.5

  Block 2 top:280px:
    Dark border.
    '13%' font-size:36px font-weight:800 color:#1A1A1A
    'average for operational roles — still meaningful but ceiling capped by physical constraints'

  Block 3 top:430px:
    Grey border.
    '3.7x' font-size:36px font-weight:800 color:#B35C00
    'gap between highest and lowest impacted role types — largest productivity divergence on record'

FOOTER: 'Sources: Stanford HAI 2025; MIT Work of the Future; Bain People Productivity Survey' | '6'
NOTHING ELSE.""",
        },

        # ── 7. OPERATING MODEL — Framework 3-column ──────────────────────────
        {
            "refs": r_diag,
            "label": "07 Operating Model",
            "brief": """Framework slide: AI operating model. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 3 | OPERATING MODEL SHIFT'.
  Headline (font-size:16px width:960px): 'Three operating model shifts separate AI leaders from followers'
  Sub: 'From project-based AI overlay to enterprise AI fabric'

THREE COLUMN FRAMEWORK (top:86px, each column 360px, gap:16px):
  Left column x:64, center x:440, right x:816.
  Each column: border:1px solid #E8E8E8 border-radius:2px height:504px background:#FFFFFF.

  COLUMN 1 — FROM OVERLAY TO FABRIC (left:64):
    Top bar (full width, 4px): background:#E8E8E8 (grey = old model)
    State badge top:102px left:80px: 'OLD MODEL' font-size:9px letter-spacing:3px color:#888
    Title top:120px left:80px: 'AI as overlay' font-size:18px font-weight:700 color:#888
    4 bullet rows at top: 150,186,222,258 — each has grey bullet + text:
      '&bull; Siloed pilots in individual business units'
      '&bull; AI team as central IT function'
      '&bull; Process unchanged; AI bolted on'
      '&bull; Value locked in proof-of-concept'
    Large X icon (SVG) top:320px left:164px: red circle with X, r:32 fill:#FFF0F0 stroke:#C41230
      Line 1: x1:148 y1:304 x2:180 y2:336 | Line 2: x1:180 y1:304 x2:148 y2:336
      stroke:#C41230 stroke-width:3

  COLUMN 2 — NEW MODEL (center x:440):
    Top bar: background:#C41230
    Badge: 'NEW MODEL' color:#C41230
    Title: 'AI as fabric' font-size:18px font-weight:700 color:#1A1A1A
    4 bullets:
      '&bull; Enterprise-wide AI platform and standards'
      '&bull; AI COO role with P&amp;L accountability'
      '&bull; Processes redesigned around AI decisions'
      '&bull; Value captured at enterprise scale'
    Checkmark circle top:320px left:504px: green fill:#E8F5ED stroke:#1B7A3E
      Checkmark path stroke:#1B7A3E stroke-width:3

  COLUMN 3 — WHAT IT TAKES (right x:816):
    Top bar: background:#1A1A1A
    Badge: 'REQUIREMENTS' color:#1A1A1A
    Title: 'Enablers' font-size:18px font-weight:700
    4 enabler blocks (each with numbered red badge):
      '01 Data: Unified data fabric across BUs'
      '02 Talent: 10-20% workforce reskilled by 2026'
      '03 Tech: Cloud-native ML ops pipeline'
      '04 Governance: Board-level AI risk committee'
    Timeline at bottom: '12-24 month transformation horizon' color:#888 font-size:10px

  ARROW connecting column 1 to column 2: SVG path at top:300px
    Curved arrow from x:424 y:300 to x:440 y:300 stroke:#C41230 stroke-width:2
    Arrowhead at end

BOTTOM BAR (top:606px left:64px width:1152px height:48px background:#FAFAFA border:1px solid #E8E8E8):
  'KEY INSIGHT:' font-size:10px font-weight:700 color:#C41230 left:80px centered vertically
  'Firms treating AI as fabric — not overlay — capture 3.1x more value at half the time-to-scale' font-size:11px color:#1A1A1A left:180px

FOOTER: 'Sources: Bain AI Transformation Study 2025; MIT CISR AI Operating Model' | '7'
NOTHING ELSE.""",
        },

        # ── 8. GOVERNANCE — Gantt-style implementation timeline ───────────────
        {
            "refs": r_mixed,
            "label": "08 Implementation Timeline",
            "brief": """Data slide: Gantt-style implementation timeline. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 4 | GOVERNANCE & RISK'.
  Headline (font-size:16px width:960px): 'A 24-month AI governance roadmap — from foundation to enterprise-wide deployment'
  Sub: 'Phased implementation across governance, technology, talent, and risk dimensions'

TIMELINE CHART (SVG top:86px left:64px width:1152px height:520px):
  Background #FAFAFA.

  HEADER ROW (phase labels) at y:0 height:30:
    Phase 1 'Foundation' x:180 w:240 fill:#F5F5F5 stroke:#E8E8E8
    Phase 2 'Scale' x:420 w:240 fill:#FFF5F5 stroke:#C41230 stroke-width:1
    Phase 3 'Optimize' x:660 w:240 fill:#FFF0F0 stroke:#C41230 stroke-width:1
    Phase 4 'Lead' x:900 w:230 fill:#C41230
    Phase labels: text-anchor:middle font-size:10px font-weight:700 fill:#555 (or white for phase 4)
    Month labels at y:30: 'Q1' 'Q2' 'Q3' 'Q4' 'Q5' 'Q6' 'Q7' 'Q8' at x:210,270,...

  Month grid lines x:180 to x:1130, 8 columns of 120px, y:0 to y:520. Stroke:#F0F0F0.

  8 WORKSTREAM ROWS (y positions: 50,110,170,230,290,350,410,470 each h:44px):
    Row labels: x:172 text-anchor:end font-size:11px fill:#1A1A1A font-weight:600.
    Bars: rounded rects rx:4 starting at x=180+start_month*120, width=duration*120.

    Workstream, start_month, duration, fill_color, milestone_label:
    'AI Strategy Board'       0  8  #C41230   'Strategy approved'
    'Data Platform'           0  5  #0D4D8C   'Data fabric live'
    'AI COO Role'             1  2  #1A1A1A   'COO appointed'
    'Pilot Programs (3)'      1  4  #888888   '3 pilots running'
    'Risk Framework'          2  3  #B35C00   'Policy ratified'
    'Talent Reskilling'       2  6  #1B7A3E   '20% reskilled'
    'Enterprise Rollout'      5  3  #C41230   'Scale complete'
    'Governance Review'       7  1  #555555   'Annual audit'

    Each bar: height:28px vertically centered in row.
    Milestone diamond at bar end: small SVG diamond (4pt star or rotated rect) fill:white stroke:(bar_color) w:10 h:10.
    Milestone label above diamond: font-size:8px fill:#555.

  Phase 2-4 bars highlighted with slightly darker opacity to show progression.

RIGHT LEGEND (x:1140 y:50 width:8px markers + labels):
  color legend for workstreams: red=Strategy | blue=Technology | black=Leadership | etc.

FOOTER: 'Indicative timeline; actual depends on organizational readiness' | '8'
NOTHING ELSE.""",
        },

        # ── 9. RISK vs REWARD — Scatter ───────────────────────────────────────
        {
            "refs": r_chart,
            "label": "09 Risk vs Reward",
            "brief": """Data slide: AI investment risk vs. reward scatter. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'CHAPTER 4 | RISK MANAGEMENT'.
  Headline (font-size:16px width:960px): 'Not all AI bets are equal — portfolio positioning determines enterprise returns'
  Sub: 'AI initiative risk level vs. expected ROI multiple, bubble = investment size ($M). 2025 enterprise portfolio.'

SCATTER CHART (SVG top:86px left:64px width:760px height:520px):
  Background #FAFAFA. Plot x:80 y:20 to x:720 y:460.

  X-axis: Risk Level (Low to High), 1-10. Scale: (720-80)/9=71px per unit.
  Y-axis: Expected ROI (1x-8x). Scale: (460-20)/7=63px per unit.
  x(r) = 80 + (risk-1)*71. y(roi) = 460 - (roi-1)*63.

  Grid: vertical at risk 1,3,5,7,9 and horizontal at roi 1,2,4,6,8.
    Stroke:#F0F0F0. Axis labels font-size:9px fill:#888.
  X label: 'Implementation Risk' x:400 y:478 text-anchor:middle font-size:10px fill:#555.
  Y label rotated: 'Expected ROI Multiple' x:20 y:240 font-size:10px fill:#555.

  SWEET SPOT ZONE (x:220 y:83 w:220 h:252 fill:#F0F9F0 rx:4 opacity:0.8):
    Label 'SWEET SPOT' x:226 y:100 font-size:9px fill:#1B7A3E font-weight:700.

  HIGH-RISK ZONE (x:500 y:20 w:220 h:200 fill:#FFF5F5 rx:4 opacity:0.6):
    Label 'HIGH RISK' x:506 y:36 font-size:9px fill:#C41230 font-weight:700.

  10 BUBBLES (name, risk, roi, size_M, color):
    'Customer AI'     3.0  6.2  80   #1B7A3E  (sweet spot)
    'Fraud Detection' 2.5  5.8  120  #1B7A3E
    'Supply Chain AI' 3.5  4.8  95   #0D4D8C
    'HR Automation'   2.0  3.2  40   #888888
    'GenAI Copilot'   4.5  5.5  200  #1A1A1A
    'AI R&D Platform' 6.5  7.2  350  #C41230
    'Autonomous Ops'  8.0  6.8  500  #C41230  (high risk)
    'AI M&A Target'   7.5  4.2  800  #B35C00
    'LLM Foundation'  9.0  3.5  1200 #8B0000
    'Analytics Dash'  1.5  2.0  25   #CCCCCC

    cx=x(risk) cy=y(roi) r=sqrt(size_M)*1.8 capped at 40. Fill=color opacity:0.75.
    Labels: white font-size:8px font-weight:700 centered.

  DIAGONAL GUIDELINE x1:80 y1:460 x2:720 y2:20 stroke:#E8E8E8 stroke-dasharray:6 stroke-width:1.

RIGHT INSIGHTS (top:86px left:848px width:368px):
  Panel #FAFAFA border:#E8E8E8.
  Title: 'Portfolio principles' font-size:11px font-weight:700 top:102px.

  4 principle rows (each 104px):
  Row 1: '60/30/10' font-size:36px font-weight:800 color:#1B7A3E
    'target split: 60% sweet-spot, 30% adjacency, 10% bold bets'
  Row 2: '18mo' font-size:36px font-weight:800 color:#1A1A1A
    'max payback horizon for sweet-spot plays before re-evaluation'
  Row 3: '$5M' font-size:36px font-weight:800 color:#B35C00
    'minimum viable pilot size to generate statistically valid ROI signal'
  Row 4: '3:1' font-size:36px font-weight:800 color:#C41230
    'minimum ROI threshold for scaling from pilot to production'

FOOTER: 'Sources: Bain AI ROI Tracker 2025; BCG AI Portfolio Study; internal benchmarks' | '9'
NOTHING ELSE.""",
        },

        # ── 10. BOARD PRIORITIES — Action ranking ────────────────────────────
        {
            "refs": r_exec,
            "label": "10 Board Priorities",
            "brief": """Data slide: ranked priority list with trend bars. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'BOARD AGENDA | PRIORITIZATION'.
  Headline (font-size:16px width:960px): 'Six AI imperatives every board must address before year-end 2025'
  Sub: 'Ranked by urgency x impact score, with YoY trend vs. 2024 board survey (n=840 public company boards)'

LEFT RANKING LIST (top:86px left:64px width:700px):
  6 rows, each 88px tall. Separator: 1px #EFEFEF at row bottom.

  Each row structure:
    Priority badge: 40x40px background:#1A1A1A (P1-P2) or #E8E8E8 (P3-P6) border-radius:2px
      text: 'P1' font-size:14px font-weight:800 color:white (or #888 for lower)
    Score circle: 36x36px border-radius:50% border:2px solid #C41230 (top 2) or #E8E8E8
      Score number inside: font-size:12px font-weight:700 color:#C41230 or #888
    Title: font-size:13px font-weight:700 color:#1A1A1A
    Description: font-size:11px color:#555 line-height:1.5 width:480px
    Trend badge: right side — up-arrow green or down-arrow red with % change

  Row 1 (top:94px): P1, score:94, 'Establish AI Governance Framework'
    'Formal board-level AI oversight with clear accountability and risk thresholds'
    Trend: '+28% urgency YoY' color:#1B7A3E

  Row 2 (top:182px): P2, score:89, 'Define AI Investment Allocation Policy'
    'Portfolio-level AI spend with expected returns tied to strategic objectives'
    Trend: '+19% YoY' color:#1B7A3E

  Row 3 (top:270px): P3, score:82, 'Mandate AI Readiness Assessment'
    'Baseline measurement across all business units — prerequisite for scaling'
    Trend: '+15% YoY' color:#1B7A3E

  Row 4 (top:358px): P4, score:76, 'Appoint Chief AI Officer (or equivalent)'
    'Executive-level AI ownership with P&L accountability and board access'
    Trend: '+32% YoY' color:#1B7A3E

  Row 5 (top:446px): P5, score:71, 'Commission Workforce Reskilling Program'
    '20% of workforce requiring upskilling by 2026 — board must fund and mandate'
    Trend: '+8% YoY' color:#1B7A3E

  Row 6 (top:534px): P6, score:65, 'Review AI Vendor and Partnership Strategy'
    'Build vs. buy vs. partner — strategic alignment to competitive roadmap'
    Trend: '-3% YoY (de-prioritised as governance takes over)' color:#C41230

RIGHT PANEL (top:86px left:788px width:428px):
  Top half: urgency vs. impact scatter mini-chart (inline SVG, 380x240px)
    Simple 3x3 grid of colored cells showing priority distribution.
    Red fill for high urgency+impact, grey for low.
    6 labeled dots for P1-P6.

  Bottom half: source + methodology note (font-size:10px color:#888).
    'Urgency x Impact scored 0-100 based on weighted survey responses.
    YoY trend vs. 2024 board AI readiness survey. Bain & Company proprietary.'

FOOTER: 'Sources: Bain Board AI Survey 2025; WEF Corporate Governance Report; NACD AI Guidance' | '10'
NOTHING ELSE.""",
        },

        # ── 11. CASE STUDIES — Two comparison cards ──────────────────────────
        {
            "refs": r_two_col,
            "label": "11 Case Studies",
            "brief": """Two-column case study slide. 1280x720px. White.

HEADER:
  Red rule. Kicker: 'EVIDENCE | CASE STUDIES'.
  Headline (font-size:16px width:960px): 'Two paths to AI leadership — financial services and retail show the blueprint in action'

TWO CASE STUDY CARDS (top:72px, each width:560px, gap:16px):
  Left card x:64, right card x:640.
  Each card: height:576px border:1px solid #E8E8E8 border-radius:2px background:#FFFFFF.

  LEFT CARD — FINANCIAL SERVICES:
    Top accent: width:560px height:4px background:#C41230
    Company type tag top:88px left:80px: 'GLOBAL BANK | $2.1tn AUM' font-size:9px color:#888 letter-spacing:2px
    Title top:108px left:80px: 'AI-Powered Credit Decisioning' font-size:18px font-weight:700 color:#1A1A1A
    Rule top:136px left:80px: width:40px height:2px background:#C41230
    Challenge top:152px left:80px width:480px font-size:11px color:#555 line-height:1.6:
      'CHALLENGE: Credit approval taking 4-7 days; 23% false-positive rejection rate losing
      $340M in annual fee revenue; manual underwriting team of 820 people.'
    Approach top:232px: label 'APPROACH' 9px letter-spacing:2px color:#C41230 + 3 brief points font-size:11px
      '&bull; ML model trained on 8 years of credit outcomes'
      '&bull; Real-time decisioning integrated into mobile banking app'
      '&bull; Human-in-loop for edge cases above $500K threshold'
    Results top:360px: label 'RESULTS (18 months)' color:#1B7A3E
    4 result metrics in 2x2 grid:
      '91min' avg decision time (vs 5 days) | '8%' false positive rate (vs 23%)
      '$420M' additional fee revenue | '340' headcount redeployed to advisory
      Each: metric font-size:28px font-weight:800 color:#C41230, label font-size:9px color:#555

  RIGHT CARD — RETAIL:
    Top accent: background:#0D4D8C
    Tag: 'GLOBAL RETAILER | 4,200 STORES'
    Title: 'Supply Chain AI Orchestration' font-size:18px font-weight:700
    Rule: background:#0D4D8C
    Challenge: 'CHALLENGE: $2.1bn in annual waste from overstock/stockout; 34-person demand
      forecasting team; 72-hour replenishment cycle across 140 DCs.'
    Approach: 'APPROACH'
      '&bull; AI demand forecasting across all 4,200 SKU-location combinations'
      '&bull; Automated replenishment with supplier API integration'
      '&bull; Edge AI at distribution centres for real-time allocation'
    Results: 'RESULTS (24 months)' color:#0D4D8C
      '$1.4bn' waste reduction | '94%' forecast accuracy (vs 71%)
      '8hr' replenishment cycle | '31%' working capital freed

FOOTER: 'Case studies based on Bain client engagements; names withheld. Indicative of achievable outcomes.' | '11'
NOTHING ELSE.""",
        },

        # ── 12. CALL TO ACTION ───────────────────────────────────────────────
        {
            "refs": r_exec,
            "label": "12 Call to Action",
            "brief": """Closing call-to-action slide. 1280x720px.

LAYOUT: Dark background #0A0A0A. Left accent bar 4px #C41230.

HEADER (left zone top:48px left:72px):
  'THE IMPERATIVE' font-size:9px letter-spacing:5px color:#C41230 font-weight:700
  Rule top:68px: width:48px height:1px background:#C41230
  'Three actions for' font-size:52px font-weight:300 color:#FFFFFF top:84px line-height:60px
  'the AI-ready board' font-size:52px font-weight:800 color:#FFFFFF top:144px line-height:60px
  Sub top:218px left:72px width:560px font-size:14px color:#888 line-height:1.65:
    'The window for deliberate, structured AI transformation is 18-24 months. After that,
    the gap between leaders and followers becomes structural and self-reinforcing.'

THREE ACTION CARDS (top:316px, each width:340px height:252px):
  Card positions: left:72, 428, 784.
  Each: border:1px solid #2A2A2A border-radius:2px background:#111111.
  Card top accent: width:340px height:3px.

  Card 1 (accent #C41230 left:72):
    '01' top:330px left:88px font-size:11px letter-spacing:3px color:#C41230 font-weight:700
    'Assess' top:352px left:88px font-size:22px font-weight:800 color:#FFFFFF
    'Commission an enterprise AI readiness assessment across all five dimensions within 60 days.'
    font-size:12px color:#777 top:386px left:88px width:296px line-height:1.6
    'TIMELINE: 60 days' top:524px left:88px font-size:9px color:#C41230 letter-spacing:2px

  Card 2 (accent #1A1A1A left:428):
    '02' color:#FFFFFF
    'Govern' color:#FFFFFF
    'Establish board-level AI governance committee with external expertise by Q3 2025.'
    'TIMELINE: 90 days' color:#888

  Card 3 (accent #555555 left:784):
    '03' color:#888
    'Scale'
    'Move top-performing AI pilot to enterprise scale with dedicated funding and AI COO ownership.'
    'TIMELINE: 12 months'

FOOTER (top:688px):
  Left: 'The AI-Ready Enterprise Blueprint | Bain & Company | 2025' font-size:9px color:#333
  Right: 'bain.com' font-size:9px color:#333

NOTHING ELSE.""",
        },
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="../full_deck_v4.html")
    args = parser.parse_args()

    topic = "The AI-Ready Enterprise: Building Competitive Advantage in the Intelligence Economy"
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


if __name__ == "__main__":
    main()
