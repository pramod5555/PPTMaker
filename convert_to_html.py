"""
convert_to_html.py — Convert slide PNGs to HTML/CSS using Azure OpenAI (gpt-5.4).

Reads pending slides from dataset.json, sends each PNG to gpt-5.4 with vision,
and saves the generated HTML to html_slides/{slide_id}.html.

Usage
-----
    # Convert next 10 pending slides
    python convert_to_html.py --limit 10

    # Convert a specific slide
    python convert_to_html.py --slide accenture_Accenture-Banking-Top-10-Trends-2024_slide_001

    # High-quality 2-pass mode (generate + self-review): recommended for complex slides
    python convert_to_html.py --source "Roland Berger,Deloitte" --overwrite --passes 2

    # Dry-run: show what would be converted
    python convert_to_html.py --limit 5 --dry-run

    # Re-convert already-done slides (overwrite)
    python convert_to_html.py --limit 5 --overwrite

    # Re-convert slides whose HTML is truncated (missing </html>)
    python convert_to_html.py --truncated

    # Tip: re-render source PDFs at higher DPI before re-converting for best quality:
    #   python convert_pymupdf.py --pdf <file>.pdf --dpi 200
    #   python convert_to_html.py --source "Roland Berger" --overwrite --passes 2
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import os
from openai import AzureOpenAI
from PIL import Image

load_dotenv()

ROOT       = Path(__file__).parent.parent
DATASET    = Path(__file__).parent / "dataset.json"
SLIDES_DIR = Path(__file__).parent / "slides"
HTML_DIR   = ROOT / "html_slides"
HTML_DIR.mkdir(exist_ok=True)

VIEWPORT_W, VIEWPORT_H = 1280, 720

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — production-grade instructions for complex consulting slides
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are a senior front-end developer who specialises in pixel-perfect replication of consulting firm presentation slides as self-contained HTML/CSS documents.

Your goal: produce HTML that is visually indistinguishable from the original slide at first glance. Do not simplify. Do not omit elements because they seem complex. Every visible element in the screenshot must appear in your output.

══════════════════════════════════════════════════════════════════
COORDINATE SCALING — NON-NEGOTIABLE
══════════════════════════════════════════════════════════════════
The PNG is rendered from a source larger than {VIEWPORT_W}×{VIEWPORT_H}px.
The user message provides exact source dimensions and pre-computed scale factors.
Apply them to EVERY numeric CSS value without exception:
  left, top, width, height, font-size, border-radius,
  padding, margin, border-width, gap, line-height (when in px),
  transform: translate(), SVG coordinates (cx, cy, r, x, y, width, height).

Vertical stacking rule — calculate, never guess:
  If element A starts at top:T and has height:H, element B directly below it
  must start at top:(T + H + gap_px). Compute this explicitly for every stack.

Hard limits: left/width ≤ {VIEWPORT_W}px · top/height ≤ {VIEWPORT_H}px.

══════════════════════════════════════════════════════════════════
LAYER ARCHITECTURE — USE z-index FOR COMPLEX SLIDES
══════════════════════════════════════════════════════════════════
  z-index 0–5   : background fills, full-bleed color bands, gradient washes
  z-index 10–15 : decorative geometry (diagonal shapes, coloured panels)
  z-index 20–25 : card and panel backgrounds (white/light boxes)
  z-index 30–40 : primary content (text blocks, charts, tables)
  z-index 50+   : overlaid labels, callout badges, page numbers, logos

All elements: position:absolute. Root: position:relative; overflow:hidden.
Never use CSS grid or flexbox on the root — only on interior containers.

══════════════════════════════════════════════════════════════════
DECORATIVE ELEMENTS — replicate all structural chrome
══════════════════════════════════════════════════════════════════
Coloured header/footer bands  → position:absolute div, full-width, background-color, z-index:5
Vertical left-edge accent bar → position:absolute div, width:4–8px, height:100%, left:0, background
Diagonal/angled background    → CSS clip-path:polygon(...) on a positioned div
Gradient wash                 → background:linear-gradient(direction, #color1, #color2)
Card with shadow              → background:#fff; border-radius:4px; box-shadow:2px 4px 12px rgba(0,0,0,.10)
Dotted/dashed rule            → border-top:1px dashed #ccc (or solid)
Thin separator line           → height:1px or width:1px div with background-color
Circle badge / KPI callout    → border-radius:50% div, explicit width=height, centered text
Number superscript footnote   → position:absolute, font-size:10px, top:Xpx

══════════════════════════════════════════════════════════════════
TYPOGRAPHY PRECISION
══════════════════════════════════════════════════════════════════
Font weights: 300 light · 400 regular · 500 medium · 600 semibold · 700 bold · 800 extrabold
Always set:
  font-weight  — match exactly; never default to 400 for bold text
  line-height  — set explicitly (e.g. 1.2, 1.35, 1.5, or in px)
  letter-spacing — uppercase kickers/labels: 0.05em–0.15em
  text-transform — UPPERCASE for kicker lines, category tags, axis labels
  width        — set on every text block so line-wrapping matches the original

Consulting headline pattern (replicate when present):
  • Thin uppercase kicker (12–14px, letter-spacing:0.1em, muted colour) — e.g. "MARKET OUTLOOK"
  • Bold assertion headline (22–36px, dark colour, width constrained) — the "so what"
  • Thin body text (13–15px, line-height:1.5) below with 8–12px gap

══════════════════════════════════════════════════════════════════
DATA VISUALISATION — approximate every chart with CSS/SVG
══════════════════════════════════════════════════════════════════
Inline SVG is allowed and encouraged for any chart shape. No <canvas>, no <script>.

Vertical bar chart:
  Outer container: position:absolute, display:flex, align-items:flex-end, gap:Xpx
  Each bar: div with explicit width and height (height = value/max × chart_height px)
  Labels below: positioned div under each bar

Horizontal bar chart:
  Each row: label div (fixed width) + bar div (height:Xpx, width:Y%, background-color)

Line / area chart:
  Use inline <svg> with <polyline points="x1,y1 x2,y2 ..."> or <path d="M...L...">
  Compute SVG coordinates directly from data values scaled to chart px dimensions

Pie / donut chart:
  SVG <circle> stroke-dasharray technique:
  circumference = 2π×r; stroke-dasharray = "share×circ rest×circ"

Scatter plot:
  SVG <circle cx="..." cy="..." r="4" fill="..."> for each point, axes as <line> elements

Progress ring / KPI circle:
  SVG circle with stroke-dasharray, stroke-dashoffset for partial fill

Data table:
  HTML <table> with border-collapse:collapse, explicit cell widths and padding
  Alternate row shading via background-color on <tr>

Sparkline:
  Small inline <svg> with a <polyline>, no axes needed

Annotation / callout arrow:
  CSS border trick or SVG <path> with marker-end arrowhead

When exact data values are not visible: estimate proportions from the image and use them.

══════════════════════════════════════════════════════════════════
ICONS AND ILLUSTRATIONS — CSS/Unicode/SVG only
══════════════════════════════════════════════════════════════════
Arrows          → Unicode ↑ ↓ → ← ▲ ▼ ▶ ◀ or SVG path
Checkmarks      → ✓ ✗ in correct colour
Bullets/dots    → • ◆ ● ○ ◯
Circular icon   → border-radius:50% div + background + centred Unicode or letter
Abstract shape  → border-radius combinations, e.g. border-radius:60% 40% 30% 70%/60% 30% 70% 40%
Number badge    → 40×40px circle div, bold number, high-contrast text
Person icon     → circle (head) + rounded rectangle (body), stacked divs

══════════════════════════════════════════════════════════════════
COLUMN LAYOUT RULES
══════════════════════════════════════════════════════════════════
Three-column layout:
  Each column ≈ {VIEWPORT_W//3 - 20}px wide; left offsets ≈ 60, {VIEWPORT_W//3 + 40}, {2*VIEWPORT_W//3 + 20}px

Two-column layout (content + chart):
  Left column ≈ 55% width; right column ≈ 40% width; gap ≈ 5%

Cards in a row:
  Equal-width divs, border:1px solid #e0e0e0, border-radius:4px, padding inside

══════════════════════════════════════════════════════════════════
STRICT REQUIREMENTS — all ten must be met
══════════════════════════════════════════════════════════════════
1.  Start with <!DOCTYPE html>
2.  All CSS inside a <style> block in <head> — no external stylesheets
3.  Root element: exactly {VIEWPORT_W}px × {VIEWPORT_H}px
4.  Root element: position:relative; overflow:hidden;
5.  All direct children of root: position:absolute
6.  NO <script> tags
7.  NO <img> tags — recreate visually with CSS / SVG / Unicode
8.  NO external URLs in src, href, url(), or @import
9.  System fonts only: Arial, Helvetica, 'Segoe UI', Georgia, 'Times New Roman', monospace
10. Output ONLY the complete HTML document — no explanation, no markdown fences, no truncation
    The final line must be </html>. Never stop mid-output."""


# ─────────────────────────────────────────────────────────────────────────────
# REVIEW PROMPT — pass 2: compare against original and fix discrepancies
# ─────────────────────────────────────────────────────────────────────────────
REVIEW_SYSTEM = """You are a meticulous QA engineer reviewing HTML slide replications against their original screenshots.
Your job is to compare the HTML rendering against the original image and produce a corrected, complete HTML document.
Output ONLY the corrected complete HTML document — no explanation, no markdown fences. The final line must be </html>."""

REVIEW_USER_TEMPLATE = """The HTML below was generated to replicate the presentation slide shown in the image above.

Compare the HTML against the original slide carefully. Check every element:
  • Elements that are missing entirely from the HTML
  • Elements that overlap text they should not overlap (check vertical stacking math)
  • Wrong colours compared to the original (background, text, accent)
  • Text that is cut off or overflows outside the {w}×{h}px boundary
  • Font sizes, weights, or letter-spacing that don't match
  • Charts or data visualisations that are absent, wrong shape, or wrong proportions
  • Decorative structure (coloured bands, vertical rules, card borders) that is missing
  • Elements positioned too high or too low relative to the original

Fix all issues you find. Preserve everything that is already correct.
Output the complete corrected HTML document — do not truncate.

Current HTML:
{html}"""


def build_user_prompt(slide: dict, src_w: int, src_h: int) -> str:
    lbl     = slide.get("label", {})
    palette = lbl.get("color_palette", {})

    x_scale = VIEWPORT_W / src_w
    y_scale = VIEWPORT_H / src_h

    layout  = lbl.get("layout_type", "unknown")
    chart   = lbl.get("chart_type", "none")
    company = lbl.get("source_company", "unknown")
    columns = lbl.get("column_count", 1)
    icons   = lbl.get("has_icons_illustrations", False)
    callouts= lbl.get("has_data_callouts", False)
    purpose = lbl.get("slide_purpose", "unknown")
    density = lbl.get("text_density", "medium")
    bg      = palette.get("background", "#FFFFFF")
    accent  = palette.get("primary_accent", "#000000")

    layout_hint = layout
    if columns > 1:
        layout_hint += f", {columns} columns"
    if chart and chart not in ("none", "unknown"):
        layout_hint += f", {chart} chart"

    extra = []
    if icons:
        extra.append("Slide contains icons or illustrations — replicate with CSS shapes / Unicode.")
    if callouts:
        extra.append("Slide contains data callout boxes or KPI numbers — include them prominently.")
    if company in ("Roland Berger", "BCG", "McKinsey", "Bain"):
        extra.append(
            f"This is a {company} slide. Replicate their precise corporate style: "
            "structured layout, exact colour bands, crisp typography, complete chart detail."
        )

    meta_lines = [
        f"Source image size : {src_w}×{src_h}px",
        f"Output viewport   : {VIEWPORT_W}×{VIEWPORT_H}px",
        f"X scale factor    : {x_scale:.4f}  — multiply every observed x-position and width by this",
        f"Y scale factor    : {y_scale:.4f}  — multiply every observed y-position, height, font-size by this",
        f"Layout            : {layout_hint}",
        f"Slide purpose     : {purpose}",
        f"Text density      : {density}",
        f"Source company    : {company}",
        f"Background colour : {bg}",
        f"Primary accent    : {accent}",
    ]
    if extra:
        meta_lines.append("Notes             : " + " | ".join(extra))

    return (
        "Convert this presentation slide screenshot into a complete, pixel-faithful HTML/CSS document.\n\n"
        "SCALING: every CSS pixel value must be derived from the scale factors below — do not eyeball.\n"
        "COMPLETENESS: replicate every visible element including decorative chrome, charts, and icons.\n"
        "STACKING: compute vertical positions explicitly — never let text blocks overlap.\n\n"
        "Metadata:\n"
        + "\n".join(meta_lines)
        + "\n\nThe screenshot is the ground truth. Match it exactly, scaled to the output viewport."
    )


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def extract_html(raw: str) -> str:
    match = re.search(r"```(?:html)?\s*(<!DOCTYPE.*?</html>)\s*```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"(<!DOCTYPE.*?</html>)", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw.strip()


def validate(html: str) -> list[str]:
    lower = html.lower()
    issues = []
    if "<!doctype html>" not in lower:
        issues.append("missing DOCTYPE")
    if "<style" not in lower:
        issues.append("missing <style>")
    if f"{VIEWPORT_W}px" not in html:
        issues.append(f"missing {VIEWPORT_W}px width")
    if f"{VIEWPORT_H}px" not in html:
        issues.append(f"missing {VIEWPORT_H}px height")
    if "position:relative" not in lower.replace(" ", ""):
        issues.append("missing position:relative on root")
    if "overflow:hidden" not in lower.replace(" ", ""):
        issues.append("missing overflow:hidden")
    if "<script" in lower:
        issues.append("contains <script>")
    if "<img" in lower:
        issues.append("contains <img>")
    functional_url = re.search(
        r'(?:src|href)\s*=\s*["\']https?://'
        r'|url\s*\(\s*["\']?https?://'
        r'|@import\s+["\']https?://',
        lower
    )
    if functional_url:
        issues.append("contains external URL")
    return issues


def convert_slide(client: AzureOpenAI, slide: dict, passes: int = 1, dry_run: bool = False) -> bool:
    slide_id = slide["slide_id"]
    img_path = SLIDES_DIR / f"{slide_id}.png"

    if not img_path.exists():
        print(f"  SKIP  {slide_id} — PNG not found")
        return False

    if dry_run:
        print(f"  DRY   {slide_id}")
        return True

    with Image.open(img_path) as img:
        src_w, src_h = img.size

    pass_label = f" [2-pass]" if passes >= 2 else ""
    print(f"  Converting {slide_id} ({src_w}x{src_h} -> {VIEWPORT_W}x{VIEWPORT_H}){pass_label} ...", end=" ", flush=True)

    b64 = encode_image(img_path)

    # ── Pass 1: initial generation ────────────────────────────────────────────
    response = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text",      "text": build_user_prompt(slide, src_w, src_h)},
                ],
            },
        ],
        max_completion_tokens=8192,
    )

    raw  = response.choices[0].message.content or ""
    html = extract_html(raw)

    # ── Pass 2: self-review and correction ────────────────────────────────────
    if passes >= 2 and "</html>" in html.lower():
        print("p1-OK ", end="", flush=True)
        review_user = REVIEW_USER_TEMPLATE.format(w=VIEWPORT_W, h=VIEWPORT_H, html=html)
        review_resp = client.chat.completions.create(
            model="gpt-5.4",
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        {"type": "text",      "text": review_user},
                    ],
                },
            ],
            max_completion_tokens=16384,
        )
        raw2  = review_resp.choices[0].message.content or ""
        html2 = extract_html(raw2)
        if "</html>" in html2.lower():
            html = html2
            print("p2-OK ", end="", flush=True)
        else:
            print("p2-trunc(kept p1) ", end="", flush=True)

    issues = validate(html)
    out_path = HTML_DIR / f"{slide_id}.html"
    out_path.write_text(html, encoding="utf-8")

    if issues:
        print(f"WARN ({', '.join(issues)})")
    else:
        print("OK")

    return True


def load_slides() -> list[dict]:
    with open(DATASET, encoding="utf-8") as f:
        return json.load(f)["slides"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert slide PNGs to HTML via gpt-5.4.")
    parser.add_argument("--limit",    type=int,   default=None,
                        help="Max number of slides to convert in this run.")
    parser.add_argument("--slide",    default=None,
                        help="Convert a single slide by slide_id.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-convert slides that already have HTML.")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Print what would be converted without calling the API.")
    parser.add_argument("--truncated", action="store_true",
                        help="Re-convert only slides whose HTML is truncated (missing </html>).")
    parser.add_argument("--source",   default=None,
                        help="Comma-separated source companies, e.g. 'Roland Berger,Deloitte'.")
    parser.add_argument("--delay",    type=float, default=1.0,
                        help="Seconds to wait between slides (default 1.0).")
    parser.add_argument("--passes",   type=int,   default=1, choices=[1, 2],
                        help="1 = single-pass (default). 2 = generate + self-review (higher quality, ~2x cost).")
    args = parser.parse_args()

    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-12-01-preview",
        azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
    )

    slides = load_slides()

    EXCLUDED_SOURCES = {"IMF"}
    slides = [s for s in slides if s.get("label", {}).get("source_company") not in EXCLUDED_SOURCES]

    def is_landscape(slide: dict) -> bool:
        p = SLIDES_DIR / f"{slide['slide_id']}.png"
        if not p.exists():
            return False
        with Image.open(p) as img:
            w, h = img.size
        return w > h

    slides = [s for s in slides if is_landscape(s)]

    if args.source:
        allowed = {s.strip() for s in args.source.split(",")}
        slides = [s for s in slides if s.get("label", {}).get("source_company") in allowed]
        print(f"Source filter: {allowed} -> {len(slides)} slides")

    if args.slide:
        slides = [s for s in slides if s["slide_id"] == args.slide]
        if not slides:
            print(f"Slide '{args.slide}' not found in dataset.json")
            sys.exit(1)
    elif args.truncated:
        slides = [
            s for s in slides
            if (HTML_DIR / f"{s['slide_id']}.html").exists()
            and "</html>" not in (HTML_DIR / f"{s['slide_id']}.html").read_text(
                encoding="utf-8", errors="ignore"
            ).lower()
        ]
    elif not args.overwrite:
        slides = [s for s in slides if not (HTML_DIR / f"{s['slide_id']}.html").exists()]

    if args.limit:
        slides = slides[: args.limit]

    mode = f"{args.passes}-pass"
    print(f"Slides to convert: {len(slides)}  mode: {mode}")
    if not slides:
        print("Nothing to do.")
        return

    converted = 0
    for i, slide in enumerate(slides):
        ok = convert_slide(client, slide, passes=args.passes, dry_run=args.dry_run)
        if ok:
            converted += 1
        if not args.dry_run and i < len(slides) - 1:
            time.sleep(args.delay)

    print(f"\nDone — {converted}/{len(slides)} converted.")
    print(f"HTML files in: {HTML_DIR}")


if __name__ == "__main__":
    main()
