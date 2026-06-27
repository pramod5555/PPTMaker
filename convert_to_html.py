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

    # Dry-run: show what would be converted
    python convert_to_html.py --limit 5 --dry-run

    # Re-convert already-done slides (overwrite)
    python convert_to_html.py --limit 5 --overwrite
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

ROOT = Path(__file__).parent.parent
DATASET = Path(__file__).parent / "dataset.json"
SLIDES_DIR = Path(__file__).parent / "slides"
HTML_DIR = ROOT / "html_slides"
HTML_DIR.mkdir(exist_ok=True)

VIEWPORT_W, VIEWPORT_H = 1280, 720

SYSTEM_PROMPT = f"""You are an expert front-end developer who converts presentation slide screenshots into clean, self-contained HTML/CSS.

COORDINATE SCALING — READ THIS FIRST:
The screenshot you receive was rendered from a source slide that is LARGER than the 1280×720 output viewport.
Every pixel value you observe in the image must be scaled down before writing CSS.
The user message provides the exact source dimensions and pre-computed scale factors — apply them to
EVERY `left`, `top`, `width`, `height`, `font-size`, `border-radius`, `padding`, and `margin` value.
A value observed at position X in a {'{SOURCE_W}'}px-wide image becomes: X × x_scale in CSS.
Never write a `left` or `width` value larger than {VIEWPORT_W}, or a `top` / `height` larger than {VIEWPORT_H}.

STRICT REQUIREMENTS — every file must satisfy all of these:
1. Start with <!DOCTYPE html>
2. Include all CSS inside a <style> block in <head> — no external stylesheets
3. The slide root element must be exactly {VIEWPORT_W}px wide and {VIEWPORT_H}px tall
4. The slide root must have: position: relative; overflow: hidden;
5. Use absolute positioning for all child elements to faithfully replicate the layout
6. NO <script> tags
7. NO <img> tags — recreate images/icons with CSS shapes, gradients, or Unicode characters
8. NO external URLs (no http:// or https:// anywhere)
9. Use only web-safe fonts or CSS @font-face with data URIs — prefer system fonts
10. Output ONLY the complete HTML document — no explanation, no markdown fences"""


def build_user_prompt(slide: dict, src_w: int, src_h: int) -> str:
    lbl = slide.get("label", {})
    palette = lbl.get("color_palette", {})

    x_scale = VIEWPORT_W / src_w
    y_scale = VIEWPORT_H / src_h

    meta_lines = [
        f"Source image size : {src_w}×{src_h}px",
        f"Output viewport   : {VIEWPORT_W}×{VIEWPORT_H}px",
        f"X scale factor    : {x_scale:.4f}  — multiply every observed x-position and width by this",
        f"Y scale factor    : {y_scale:.4f}  — multiply every observed y-position, height, and font-size by this",
        f"Layout type       : {lbl.get('layout_type', 'unknown')}",
        f"Chart type        : {lbl.get('chart_type', 'none')}",
        f"Text density      : {lbl.get('text_density', 'medium')}",
        f"Source company    : {lbl.get('source_company', 'unknown')}",
        f"Slide purpose     : {lbl.get('slide_purpose', 'unknown')}",
        f"Column count      : {lbl.get('column_count', 1)}",
        f"Has icons         : {lbl.get('has_icons_illustrations', False)}",
        f"Has callouts      : {lbl.get('has_data_callouts', False)}",
        f"BG color          : {palette.get('background', '#FFFFFF')}",
        f"Accent color      : {palette.get('primary_accent', '#000000')}",
    ]

    return (
        "Convert this presentation slide screenshot into a complete HTML/CSS document.\n\n"
        "IMPORTANT: The screenshot comes from a source slide larger than the output viewport. "
        "Use the scale factors below to convert every pixel measurement before writing CSS. "
        "No CSS value should exceed the output viewport dimensions.\n\n"
        "Scaling and metadata:\n"
        + "\n".join(meta_lines)
        + "\n\nThe screenshot is the visual ground truth. "
        "Faithfully replicate all layout, typography, colors, and structure — scaled to the output viewport."
    )


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def extract_html(raw: str) -> str:
    # Strip markdown fences if the model wrapped the output
    match = re.search(r"```(?:html)?\s*(<!DOCTYPE.*?</html>)\s*```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Try to extract bare DOCTYPE block
    match = re.search(r"(<!DOCTYPE.*?</html>)", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw.strip()


def validate(html: str, slide_id: str) -> list[str]:
    import re as _re
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
    # Only flag URLs in functional positions (src=, href=, url(), @import).
    # Text-node URLs (bibliography citations, footnotes) and the SVG namespace
    # (w3.org/2000/svg) are harmless and must not be flagged.
    functional_url = _re.search(
        r'(?:src|href)\s*=\s*["\']https?://'   # src="..." or href="..."
        r'|url\s*\(\s*["\']?https?://'          # url("...") in CSS
        r'|@import\s+["\']https?://',            # @import "..."
        lower
    )
    if functional_url:
        issues.append("contains external URL")
    return issues


def convert_slide(client: AzureOpenAI, slide: dict, dry_run: bool = False) -> bool:
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

    print(f"  Converting {slide_id} ({src_w}x{src_h} -> {VIEWPORT_W}x{VIEWPORT_H}) ...", end=" ", flush=True)

    b64 = encode_image(img_path)
    response = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                    {"type": "text", "text": build_user_prompt(slide, src_w, src_h)},
                ],
            },
        ],
        max_completion_tokens=8192,
    )

    raw = response.choices[0].message.content or ""
    html = extract_html(raw)
    issues = validate(html, slide_id)

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
    parser.add_argument("--limit", type=int, default=None,
                        help="Max number of slides to convert in this run.")
    parser.add_argument("--slide", default=None,
                        help="Convert a single slide by slide_id.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-convert slides that already have HTML.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be converted without calling the API.")
    parser.add_argument("--truncated", action="store_true",
                        help="Re-convert only slides whose HTML is truncated (missing </html>).")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds to wait between API calls (default 1.0).")
    args = parser.parse_args()

    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-12-01-preview",
        azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
    )

    slides = load_slides()

    # Exclude low-quality or disallowed sources
    EXCLUDED_SOURCES = {"IMF"}
    slides = [s for s in slides if s.get("label", {}).get("source_company") not in EXCLUDED_SOURCES]

    # Only use landscape slides (width > height) — portrait slides are document scans
    def is_landscape(slide: dict) -> bool:
        p = SLIDES_DIR / f"{slide['slide_id']}.png"
        if not p.exists():
            return False
        with Image.open(p) as img:
            w, h = img.size
        return w > h

    slides = [s for s in slides if is_landscape(s)]

    if args.slide:
        slides = [s for s in slides if s["slide_id"] == args.slide]
        if not slides:
            print(f"Slide '{args.slide}' not found in dataset.json (or excluded due to icon overlays)")
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

    print(f"Slides to convert: {len(slides)}")
    if not slides:
        print("Nothing to do.")
        return

    converted = 0
    for i, slide in enumerate(slides):
        ok = convert_slide(client, slide, dry_run=args.dry_run)
        if ok:
            converted += 1
        if not args.dry_run and i < len(slides) - 1:
            time.sleep(args.delay)

    print(f"\nDone — {converted}/{len(slides)} converted.")
    print(f"HTML files in: {HTML_DIR}")


if __name__ == "__main__":
    main()
