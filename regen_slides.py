"""
regen_slides.py — Regenerate specific slide(s) in an existing deck HTML file.

Usage:
    python regen_slides.py --slides 0,2 --deck ../full_deck_v2.html
"""
from __future__ import annotations

import argparse
import base64
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

ROOT     = Path(__file__).parent.parent
HTML_DIR = ROOT / "html_slides"
SLIDES_DIR = Path(__file__).parent / "slides"
W, H = 1280, 720

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
)

SYSTEM_PROMPT = f"""You are a senior consulting front-end developer producing high-fidelity HTML/CSS slides.

STRICT REQUIREMENTS:
1. Start with <!DOCTYPE html>
2. ALL CSS in a <style> block inside <head> — no external stylesheets
3. The slide root element must be exactly {W}px wide and {H}px tall with position:relative; overflow:hidden
4. Use absolute positioning for every child element — no flexbox/grid at top level
5. NO <script> tags
6. NO <img> tags — use CSS shapes, gradients, SVG inline, or Unicode for all visuals
7. NO external URLs anywhere
8. System fonts only (Arial, Helvetica, sans-serif or Georgia for serif)
9. Do NOT let any text or element overflow or overlap another — check all absolute positions carefully
10. Output ONLY the complete HTML document — no explanation, no markdown fences"""


SLIDE_SPECS = {
    # ── Cover ────────────────────────────────────────────────────────────────────
    0: {
        "ref_keys": [
            "bain_global_pe_report_2023_slide_001",
            "bain_china_luxury_2011_slide_001",
            "roland_berger_trend_compendium_2050_technology_and_innovation_slide_001",
        ],
        # PNG-only refs (portrait L.E.K. slides — no HTML but strong visual style)
        "png_only": [
            "lek_womens-health-200b-opportunity-pharma-has-left-table_slide_001",
            "lek_overcoming-biopharma-growth-gap_slide_001",
        ],
        "brief": """Premium consulting cover slide. 1280x720px.
Topic: 'Digital Megatrends 2025&#x2013;2030: Five Forces Reshaping Industry'

VISUAL CONCEPT: Bold asymmetric split layout with dramatic typographic weight contrast.
Left 55% = content zone on deep charcoal #111827.
Right 45% = abstract data-visualization art on #0c1525 (slightly darker).

RIGHT PANEL — SVG inline abstract art (no img tags):
  Use inline <svg> positioned absolute (right:0, top:0, width:576px, height:720px).
  Draw an interconnected node graph / neural network:
  - 12-15 circles (r=3-8px) scattered across the SVG at varied positions
  - Lines connecting nodes, stroke:#1c78b0 at 20-35% opacity, stroke-width:1
  - 3-4 larger "hub" nodes (r=10-14px), fill:#1c78b0 at 30% opacity
  - 2-3 pulsing rings: concentric circles around hub nodes, stroke:#1c78b0 at 8-12% opacity, r increasing
  - Subtle radial gradient behind the graph: radial-gradient from #0d2040 to #0c1525
  This creates a sophisticated network topology map.

LEFT PANEL — all absolute positions within the 1280x720 slide:
  — Thin vertical accent bar: left:0, top:0, width:4px, height:720px, background:linear-gradient(180deg,#1c78b0,#0d4f7c)
  — Year badge (top:44px, left:56px): '2025 EDITION' font-size:10px, letter-spacing:3.5px,
    color:#1c78b0, text-transform:uppercase, font-weight:600
  — Thin rule (top:64px, left:56px): width:48px, height:1.5px, background:#1c78b0
  — FIRM label (top:44px, right:60px, position absolute): 'STRATEGIC INSIGHTS' font-size:10px,
    letter-spacing:2px, color:#374151, text-transform:uppercase

  — Main title block (top:160px, left:56px, width:580px):
    Line 1: 'Digital Megatrends' font-size:52px font-weight:800 color:#ffffff line-height:1.1
    Line 2: '2025&#x2013;2030:' font-size:52px font-weight:300 color:#93c5fd line-height:1.1
    Line 3: 'Five Forces' font-size:52px font-weight:800 color:#ffffff line-height:1.1
    Line 4: 'Reshaping Industry' font-size:52px font-weight:300 color:#ffffff line-height:1.1
    Weight alternation (800/300) creates visual rhythm. Use separate <div>s for each line.
    Ensure last line ends no lower than top:430px.

  — Divider line (top:450px, left:56px): width:200px, height:1px, background:#1c3a5e

  — Subtitle (top:468px, left:56px, width:560px):
    'A strategic analysis of five transformative forces redefining competitive advantage'
    font-size:14px, color:#6b7280, line-height:1.7, font-weight:400

  — Three stat pills (top:540px):
    Each pill: height:28px, border:1px solid #1c3a5e, border-radius:4px, padding:0 12px
    line-height:28px, font-size:11px, color:#9ca3af, display inline-block via absolute pos
    Pill 1 (left:56px): '5 Strategic Forces'
    Pill 2 (left:190px): '2025&#x2013;2030 Horizon'
    Pill 3 (left:340px): 'Executive Briefing'

  — Bottom-left (top:672px, left:56px): 'Prepared for Executive Leadership &bull; Confidential'
    font-size:10px, color:#374151, letter-spacing:0.3px
  — Slide number (top:672px, right:56px): '1' font-size:10px, color:#1c3a5e

NO overlapping elements. Verify all top positions are non-overlapping before outputting.""",
    },

    # ── Executive Summary ────────────────────────────────────────────────────────
    2: {
        "ref_keys": [
            "bain_global_pe_report_2023_slide_003",
            "bain_global_pe_report_2023_slide_005",
            "bain_china_luxury_2011_slide_003",
            "roland_berger_trend_compendium_2050_technology_and_innovation_slide_013",
        ],
        "png_only": [
            "lek_overcoming-biopharma-growth-gap_slide_003",
            "lek_us-warehouse-automations-next-act-broadening-automation-opportunity_slide_002",
        ],
        "brief": """Premium consulting executive summary slide. 1280x720px. White background #ffffff.

LAYOUT CONCEPT: Two-zone layout. Left zone = 5 key findings as numbered rows (clean list).
Right zone = 2 large data callout cards stacked vertically, visually bold.

HEADER (absolute positions):
  — Top accent rule: top:0, left:0, width:1280px, height:3px, background:linear-gradient(90deg,#1c78b0 0%,#93c5fd 40%,transparent 100%)
  — Kicker (top:20px, left:56px): 'EXECUTIVE SUMMARY' font-size:10px letter-spacing:3px color:#1c78b0 text-transform:uppercase font-weight:700
  — Headline (top:38px, left:56px, width:1000px):
    'Five findings that will reshape strategy in the next 18 months'
    font-size:26px font-weight:700 color:#111827 line-height:1.25
  — Separator line (top:92px, left:56px): width:1168px, height:1px, background:#e5e7eb

LEFT ZONE — five findings (left:56px, width:650px, starting top:108px):
  Each row height:96px. Row background alternates: odd=#fafafa, even=#ffffff.
  Row structure (absolute):
    — Number circle: 28px diameter, background:#1c78b0, border-radius:50%
      font-size:12px font-weight:700 color:#fff text-align:center line-height:28px
      position: left:56px, vertically centred in row
    — Finding title: left:100px, font-size:13px font-weight:700 color:#111827 width:580px
    — Supporting stat: left:100px, font-size:11px color:#6b7280 width:580px (6px below title)
    — Bottom separator: 1px solid #e5e7eb at row bottom

  Row 1 (top:108px): 'AI adoption has crossed the inflection point &mdash; 74% of enterprises report production deployments'
    Stat: 'Average enterprise AI ROI now exceeds initial investment within 14 months, down from 26 months in 2023.'
  Row 2 (top:204px): 'The green premium is collapsing: sustainable capex now delivers equivalent or better returns'
    Stat: 'Renewable LCOE has fallen 89% since 2010; 68% of CFOs rank ESG capex as core to value creation.'
  Row 3 (top:300px): 'Cloud-native architecture is the single greatest predictor of digital revenue growth'
    Stat: 'Cloud-native firms grow digital revenue 3.1&times; faster; migration backlog worth $2.4tn in latent value.'
  Row 4 (top:396px): 'Talent scarcity is outpacing automation &mdash; a structural gap, not a cyclical one'
    Stat: 'By 2030, 40% of current job roles will be substantially transformed; reskilling investment lags by 2.8&times;.'
  Row 5 (top:492px): 'M&amp;A is the fastest path to capability &mdash; organic build timelines have doubled since 2020'
    Stat: 'Time-to-capability via M&amp;A: 9 months. Via organic build: 21 months. Multiples rising but justified.'
  Bottom rule (top:588px, left:56px): width:650px height:1px background:#e5e7eb

RIGHT ZONE — 2 bold data cards (left:756px, width:468px):
  Card 1 (top:108px, height:224px): background:#f0f7ff, border-left:4px solid #1c78b0, border-radius:0 4px 4px 0
    — Label (top:124px, left:776px): 'PRIORITY SIGNAL' font-size:9px letter-spacing:2px color:#1c78b0 font-weight:700 text-transform:uppercase
    — Big stat (top:144px, left:776px): '74%' font-size:72px font-weight:800 color:#111827 line-height:1
    — Unit label (top:224px, left:776px): 'of enterprises now have AI in production' font-size:13px color:#374151 width:400px line-height:1.4
    — Trend (top:270px, left:776px): '&#x25B2; up from 37% in 2022' font-size:11px color:#059669 font-weight:600

  Card 2 (top:348px, height:224px): background:#f0fdf4, border-left:4px solid #059669, border-radius:0 4px 4px 0
    — Label (top:364px, left:776px): 'INVESTMENT SIGNAL' font-size:9px letter-spacing:2px color:#059669 font-weight:700 text-transform:uppercase
    — Big stat (top:384px, left:776px): '$1.8tn' font-size:60px font-weight:800 color:#111827 line-height:1
    — Unit label (top:456px, left:776px): 'clean energy investment in 2024 &mdash; first year exceeding fossil capex' font-size:13px color:#374151 width:400px line-height:1.4
    — Trend (top:504px, left:776px): '&#x25B2; +34% year-on-year' font-size:11px color:#059669 font-weight:600

FOOTER (top:616px, left:56px, width:1168px):
  — Top rule: 1px solid #e5e7eb
  — Source text (top:628px, left:56px): 'Sources: McKinsey Global Institute; Roland Berger Executive Survey; Accenture; World Economic Forum, 2025'
    font-size:9px color:#9ca3af letter-spacing:0.2px
  — Slide number (top:628px, right:56px): '3' font-size:9px color:#9ca3af

Ensure NO elements overlap. All absolute positions must be consistent with the layout described.""",
    },
}


def encode_png(slide_id: str) -> str | None:
    p = SLIDES_DIR / f"{slide_id}.png"
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def collect_refs(slide_ids: list[str]) -> list[dict]:
    refs = []
    for sid in slide_ids:
        p = HTML_DIR / f"{sid}.html"
        if not p.exists():
            continue
        refs.append({
            "sid":   sid,
            "html":  p.read_text(encoding="utf-8", errors="ignore"),
            "b64":   encode_png(sid),
            "type":  "full",
        })
    return refs


def collect_png_refs(slide_ids: list[str]) -> list[dict]:
    """PNG-only refs for portrait slides — no HTML, visual inspiration only."""
    refs = []
    for sid in slide_ids:
        b64 = encode_png(sid)
        if b64:
            refs.append({"sid": sid, "b64": b64, "type": "png_only"})
    return refs


def generate_slide(brief: str, refs: list[dict], png_refs: list[dict], label: str) -> str:
    total = len(refs) + len(png_refs)
    print(f"  Generating {label} ({len(refs)} full + {len(png_refs)} PNG refs) ...", end=" ", flush=True)

    content: list[dict] = []

    # Full refs first (HTML + PNG)
    for i, ref in enumerate(refs):
        if ref.get("b64"):
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{ref['b64']}"}})
        lbl = f"STYLE REFERENCE {i+1}/{total} (full — use color tokens, spacing, typography from this)"
        content.append({"type": "text", "text": f"{lbl} (id: {ref['sid']}):\nHTML source:\n{ref['html'][:5000]}\n"})

    # PNG-only refs (L.E.K. style — visual inspiration, no HTML)
    for j, ref in enumerate(png_refs):
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{ref['b64']}"}})
        lbl = f"VISUAL INSPIRATION {len(refs)+j+1}/{total} (L.E.K. Consulting — study the typography, white space, color restraint, and information hierarchy)"
        content.append({"type": "text", "text": f"{lbl} (id: {ref['sid']}): No HTML available — use this image purely for visual style inspiration.\n"})

    content.append({"type": "text", "text": (
        f"Generate a brand-new {W}x{H}px HTML/CSS presentation slide.\n"
        f"PRIMARY STYLE DIRECTION: Bain & Company's clean, data-forward design — bold typography, "
        f"restrained color palette, strong data callouts, generous white space.\n"
        f"SECONDARY INSPIRATION: L.E.K. Consulting's precise typographic hierarchy and clean layouts (see visual references above).\n"
        f"Do NOT copy content or layout structure — generate fresh content per the brief.\n\n"
        f"SLIDE BRIEF:\n{brief}"
    )})

    resp = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ],
        max_completion_tokens=8192,
    )

    html = resp.choices[0].message.content or ""
    m = re.search(r"(<!DOCTYPE.*?</html>)", html, re.DOTALL | re.IGNORECASE)
    if m:
        html = m.group(1).strip()
    print("OK")
    return html


def srcdoc_encode(html: str) -> str:
    return (html
            .replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&#60;")
            .replace(">", "&#62;"))


def patch_deck(deck_path: Path, slide_index: int, new_html: str) -> None:
    """Replace the srcdoc of the Nth iframe in the deck file."""
    deck = deck_path.read_text(encoding="utf-8")
    safe = srcdoc_encode(new_html)

    pattern = re.compile(r'(srcdoc=")[^"]*(")', re.DOTALL)
    matches = list(pattern.finditer(deck))
    if slide_index >= len(matches):
        print(f"  ERROR: deck has only {len(matches)} slides, cannot patch index {slide_index}")
        return

    m = matches[slide_index]
    deck = deck[:m.start()] + f'srcdoc="{safe}"' + deck[m.end():]

    # Write as ASCII with xmlcharrefreplace to avoid mojibake
    deck_ascii = deck.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
    deck_path.write_text(deck_ascii, encoding="ascii")
    print(f"  Patched slide {slide_index + 1} into {deck_path.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slides", default="0,2", help="Comma-separated 0-based slide indices to regenerate")
    parser.add_argument("--deck", default="../full_deck_v2.html")
    args = parser.parse_args()

    deck_path = (Path(__file__).parent / args.deck).resolve()
    indices = [int(x.strip()) for x in args.slides.split(",")]

    print(f"Regenerating slides {indices} in {deck_path.name}")

    for idx in indices:
        if idx not in SLIDE_SPECS:
            print(f"  No spec defined for slide index {idx}, skipping")
            continue
        spec = SLIDE_SPECS[idx]
        refs     = collect_refs(spec["ref_keys"])
        png_refs = collect_png_refs(spec.get("png_only", []))
        html = generate_slide(spec["brief"], refs, png_refs, f"slide {idx + 1}")
        patch_deck(deck_path, idx, html)

    print("Done.")


if __name__ == "__main__":
    main()
