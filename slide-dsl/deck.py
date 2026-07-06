"""deck.py — Generate a multi-slide deck from a topic brief.

Two-phase pipeline:
  1. Outline phase  — GPT-4 produces a JSON list of slide descriptions
  2. Slide phase    — each description runs through generate_api → render_slide
  3. Wrap phase     — all slides assembled into a single navigable HTML deck

Usage:
    python slide-dsl/deck.py "Private Equity Market Outlook 2025" --slides 8
    python slide-dsl/deck.py "AI in Healthcare" --slides 6 --no-search
    python slide-dsl/deck.py --outline outline.json --out my_deck.html
    python slide-dsl/deck.py "..." --show-specs
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate import generate_api, SYSTEM_PROMPT
from renderer import render_slide

ROOT = Path(__file__).parent.parent

# ── Outline system prompt ──────────────────────────────────────────────────────
OUTLINE_SYSTEM = """\
You are a management consulting presentation architect. Given a deck topic, \
return a JSON array of slide descriptions for a tight, high-impact deck.

Rules:
- Return ONLY a JSON object: {"slides": [ ... ]}, no commentary.
- Each element: {"slide_type": "cover|chapter|content|cta", "description": "..."}
- Description must be a single self-contained sentence that specifies:
    • the slide's analytical purpose
    • the chart or visual type to use (e.g. "waterfall chart", "KPI grid", "bar chart", "comparison matrix", "process flow", "donut chart", "scatter chart", "gantt chart")
    • the data domain (e.g. "2019–2024 PE fundraising", "top 5 LPs by commitment size")
- Deck flow: cover → 1 chapter divider → 3–6 content slides → CTA/closing
- Every content slide must specify a visual type — no text-only slides unless it's a chapter divider.
- Vary chart types across the deck; do not repeat the same chart type twice.
- Be specific: "Show a waterfall chart of Apple FY2024 revenue bridge from services, Mac, iPhone" \
not "Show revenue data"."""


def generate_outline(topic: str, n_slides: int) -> list[dict]:
    """Ask GPT-4 to produce a slide outline for the given topic."""
    from dotenv import load_dotenv
    from openai import AzureOpenAI

    load_dotenv()
    load_dotenv(ROOT / "ppt-dataset" / ".env")

    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-12-01-preview",
        azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
    )

    user_msg = (
        f"Topic: {topic}\n"
        f"Generate an outline for a {n_slides}-slide consulting deck on this topic. "
        f"Return a JSON array with exactly {n_slides} elements."
    )

    resp = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": OUTLINE_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.9,
        max_completion_tokens=800,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content.strip()
    parsed = json.loads(raw)
    # Handle {"slides": [...]}, {"outline": [...]}, or bare list
    if isinstance(parsed, list):
        return parsed
    for key in ("slides", "outline", "deck", "slide_list"):
        if key in parsed and isinstance(parsed[key], list):
            return parsed[key]
    # Last resort: if every value is a list, take the first
    for v in parsed.values():
        if isinstance(v, list) and v:
            return v
    raise ValueError(f"Unexpected outline shape: {list(parsed.keys())}")


# ── Deck HTML wrapper ──────────────────────────────────────────────────────────
DECK_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: #0d0d0d;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
#topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    height: 44px;
    background: #1a1a1a;
    border-bottom: 1px solid #333;
    flex-shrink: 0;
}
#topbar h1 {
    font-size: 13px;
    font-weight: 600;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 60%;
}
#counter {
    font-size: 12px;
    color: #888;
    white-space: nowrap;
}
#stage {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
}
.slide-frame {
    display: none;
    width: 1280px;
    height: 720px;
    border: none;
    box-shadow: 0 8px 40px rgba(0,0,0,0.6);
    border-radius: 4px;
    transform-origin: center center;
}
.slide-frame.active { display: block; }
#bottombar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    height: 52px;
    background: #1a1a1a;
    border-top: 1px solid #333;
    flex-shrink: 0;
}
.nav-btn {
    background: #2a2a2a;
    color: #ccc;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 7px 20px;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s;
}
.nav-btn:hover  { background: #3a3a3a; color: #fff; }
.nav-btn:active { background: #444; }
.nav-btn:disabled { opacity: 0.3; cursor: default; }
#dots {
    display: flex;
    gap: 6px;
    align-items: center;
}
.dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #444;
    cursor: pointer;
    transition: background 0.15s;
}
.dot.active { background: #00677F; }
.dot:hover  { background: #666; }
"""

DECK_JS = """
const frames  = Array.from(document.querySelectorAll('.slide-frame'));
const dots    = Array.from(document.querySelectorAll('.dot'));
const counter = document.getElementById('counter');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
let current   = 0;

function scaleFrames() {
    const stage = document.getElementById('stage');
    const sw = stage.clientWidth  - 40;
    const sh = stage.clientHeight - 40;
    const scale = Math.min(sw / 1280, sh / 720, 1);
    frames.forEach(f => {
        f.style.transform = `scale(${scale})`;
    });
}

function goto(idx) {
    frames[current].classList.remove('active');
    dots[current].classList.remove('active');
    current = Math.max(0, Math.min(idx, frames.length - 1));
    frames[current].classList.add('active');
    dots[current].classList.add('active');
    counter.textContent = `${current + 1} / ${frames.length}`;
    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === frames.length - 1;
}

dots.forEach((d, i) => d.addEventListener('click', () => goto(i)));
document.getElementById('prevBtn').addEventListener('click', () => goto(current - 1));
document.getElementById('nextBtn').addEventListener('click', () => goto(current + 1));

document.addEventListener('keydown', e => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goto(current + 1);
    if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   goto(current - 1);
});

window.addEventListener('resize', scaleFrames);
scaleFrames();
goto(0);
"""


def wrap_deck(title: str, slides_html: list[str]) -> str:
    n = len(slides_html)

    frames_html = "\n".join(
        f'<iframe class="slide-frame" srcdoc="{_escape_srcdoc(html)}" '
        f'sandbox="allow-same-origin"></iframe>'
        for html in slides_html
    )

    dots_html = "\n".join(
        f'<div class="dot" title="Slide {i+1}"></div>'
        for i in range(n)
    )

    return textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{_esc(title)}</title>
        <style>{DECK_CSS}</style>
        </head>
        <body>
        <div id="topbar">
          <h1>{_esc(title)}</h1>
          <span id="counter">1 / {n}</span>
        </div>
        <div id="stage">
        {frames_html}
        </div>
        <div id="bottombar">
          <button class="nav-btn" id="prevBtn">&larr; Prev</button>
          <div id="dots">
        {dots_html}
          </div>
          <button class="nav-btn" id="nextBtn">Next &rarr;</button>
        </div>
        <script>{DECK_JS}</script>
        </body>
        </html>
    """)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _escape_srcdoc(html: str) -> str:
    """Escape HTML for use in srcdoc attribute."""
    return html.replace("&", "&amp;").replace('"', "&quot;")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Generate a multi-slide consulting deck")
    ap.add_argument("topic", nargs="?", default="",
                    help="Deck topic (e.g. 'Private Equity Market Outlook 2025')")
    ap.add_argument("--slides",   type=int, default=8,
                    help="Number of slides to generate (default: 8)")
    ap.add_argument("--outline",  default="",
                    help="Path to JSON outline file (skips outline generation)")
    ap.add_argument("--out",      default="",
                    help="Output HTML path (default: slide-dsl/generated/<slug>_deck.html)")
    ap.add_argument("--no-search", action="store_true",
                    help="Skip Tavily web search when generating slides")
    ap.add_argument("--show-specs", action="store_true",
                    help="Print each DSL spec after generation")
    args = ap.parse_args()

    if not args.topic and not args.outline:
        ap.error("Provide a topic or --outline file")

    # ── Phase 1: get outline ──────────────────────────────────────────────────
    if args.outline:
        outline_path = Path(args.outline)
        if not outline_path.exists():
            sys.exit(f"Outline file not found: {outline_path}")
        outline = json.loads(outline_path.read_text())
        topic = outline[0].get("topic", outline_path.stem)
        print(f"Loaded outline: {len(outline)} slides from {outline_path}")
    else:
        topic = args.topic
        print(f"\nGenerating outline for: {topic}")
        outline = generate_outline(topic, args.slides)
        print(f"Outline: {len(outline)} slides")
        for i, s in enumerate(outline):
            print(f"  {i+1}. [{s.get('slide_type','?')}] {s.get('description','')[:80]}")

    # ── Phase 2: generate each slide ─────────────────────────────────────────
    slides_html: list[str] = []
    failed = 0

    for i, slide_def in enumerate(outline):
        desc = slide_def.get("description", "")
        stype = slide_def.get("slide_type", "content")
        print(f"\n[{i+1}/{len(outline)}] {stype}: {desc[:70]}")

        try:
            prompt = desc
            if stype in ("cover", "chapter", "cta"):
                prompt = f"[{stype.upper()}] {desc}"
            else:
                # Push GPT to fill slides with dense, specific data
                prompt += (
                    " Use at least 6 data points or items. "
                    "Every number must be specific (no round placeholders). "
                    "For bar/line charts: 6–8 bars or time periods. "
                    "For KPI grids: 4–6 items. "
                    "For bullet lists: 5–7 items with sub-bullets. "
                    "For comparison matrices: 4–6 rows."
                )

            spec = generate_api(prompt, use_search=not args.no_search)

            # Inject correct page number regardless of what GPT generated
            spec.setdefault("footer", {})["page"] = i + 1

            if args.show_specs:
                print(json.dumps(spec, indent=2, ensure_ascii=False))

            html = render_slide(spec)
            slides_html.append(html)
            print(f"  OK — {spec.get('layout','?')} layout, "
                  f"blocks: {list(spec.get('content', {}).keys())}")
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1
            # Insert an error placeholder slide so the deck index stays correct
            slides_html.append(_error_slide(i + 1, str(e)))

    # ── Phase 3: assemble deck ────────────────────────────────────────────────
    deck_html = wrap_deck(topic, slides_html)

    if args.out:
        out = Path(args.out)
    else:
        slug = topic[:50].lower()
        slug = "".join(c if c.isalnum() else "_" for c in slug).strip("_")
        out  = ROOT / "slide-dsl" / "generated" / f"{slug}_deck.html"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(deck_html, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"Deck:    {len(slides_html)} slides  ({failed} failed)")
    print(f"Output:  {out}")
    print(f"Open:    file:///{out.as_posix()}")
    print(f"{'='*60}")


def _error_slide(n: int, msg: str) -> str:
    safe_msg = _esc(msg)[:200]
    return textwrap.dedent(f"""\
        <!DOCTYPE html><html><head><meta charset="UTF-8">
        <style>
          body {{background:#fff;display:flex;align-items:center;justify-content:center;
                 height:720px;width:1280px;font-family:sans-serif;}}
          .box {{text-align:center;color:#999;}}
          .n   {{font-size:64px;font-weight:700;color:#eee;}}
          .err {{font-size:12px;color:#ccc;margin-top:8px;max-width:600px;}}
        </style></head><body>
        <div class="box">
          <div class="n">{n}</div>
          <div>Slide generation failed</div>
          <div class="err">{safe_msg}</div>
        </div></body></html>
    """)


if __name__ == "__main__":
    main()
