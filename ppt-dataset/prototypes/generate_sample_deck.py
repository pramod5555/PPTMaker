"""
generate_sample_deck.py  -  Phase 4 sample deck orchestrator.

Deck: "Global AI Investment & Digital Readiness 2025"  (5 slides)
  1. Strategic overview    content_field           (3-pillar layout)
  2. AI Investment Scatter scatter_evidence_field  (RB rail + panel)
  3. Sector Bar Chart      bar_chart_field         (RB rail + panel)
  4. Investment Trend Line line_chart_field        (full-width)
  5. Allocation Pie        pie_chart_field         (half-width + legend)

Pipeline:
  brief -> Phase 3 pipeline() -> SlotSpec (layout_dims + color_tokens)
  Ollama -> text content (titles, subtitles, bullets)
  deck_spec.json -> generate_sample_deck.js -> sample_deck.pptx
  fix_pptx_bubble_charts.py -> patch bubble-chart XML

Usage:
    python prototypes/generate_sample_deck.py
    python prototypes/generate_sample_deck.py --model gemini-3-flash-preview:latest
    python prototypes/generate_sample_deck.py --skip-ollama
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from recipe_classifier import pipeline as get_slot_spec
from retrieval import load_index

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "prototypes" / "output"
SPEC_PATH = OUT_DIR / "deck_spec.json"
PPTX_PATH = OUT_DIR / "sample_deck.pptx"

# ── slide definitions ─────────────────────────────────────────────────────────

SLIDE_DEFS = [
    {
        "brief": "strategic overview three pillars framework, Roland Berger consulting style, no chart",
        "chart_type": "content",
        "chart_data": {
            "pillars": [
                {"num": "1", "title": "STRATEGY",      "color": "2D79A3"},
                {"num": "2", "title": "INFRASTRUCTURE", "color": "06466D"},
                {"num": "3", "title": "TALENT",         "color": "4A5568"},
            ]
        },
    },
    {
        "brief": "scatter bubble chart AI investment intensity versus digital readiness, Roland Berger style, insight panel",
        "chart_type": "bubble",
        "chart_data": {
            "x":     [0.3, 0.5, 0.9, 1.1, 1.7, 1.6, 1.9, 2.2, 2.5, 2.8, 3.1, 3.5, 3.9, 4.2, 4.7],
            "y":     [28,  33,  37,  41,  49,  48,  52,  56,  59,  62,  65,  68,  71,  74,  77 ],
            "sizes": [7,   8,   8,   9,   10,  10,  10,  11,  12,  12,  13,  13,  14,  14,  15 ],
            "labels": [
                ["Brazil", 0.3, 28], ["India", 0.5, 33], ["Mexico", 0.9, 37],
                ["Poland", 1.1, 41], ["France", 1.6, 48], ["Australia", 1.7, 49],
                ["Japan",  1.9, 52], ["Germany", 2.2, 56], ["UK", 2.5, 59],
                ["Canada", 2.8, 62], ["S. Korea", 3.1, 65], ["Sweden", 3.5, 68],
                ["Singapore", 3.9, 71], ["US", 4.2, 74], ["Switzerland", 4.7, 77],
            ],
            "x_axis": "AI Investment Intensity (% of Operating Cost)",
            "y_axis": "Digital Readiness Index",
            "x_min": 0, "x_max": 5, "y_min": 20, "y_max": 82,
        },
    },
    {
        "brief": "grouped bar chart AI investment by industry sector comparison, Roland Berger style, insight panel",
        "chart_type": "bar",
        "chart_data": {
            "categories": [
                "Financial Services", "Healthcare", "Manufacturing",
                "Retail & CPG", "Telecom", "Energy & Utilities",
                "Government", "Education",
            ],
            "series": [
                {"name": "2023 Actual",   "values": [4.2, 3.1, 2.8, 2.5, 2.2, 1.9, 1.3, 0.8]},
                {"name": "2025 Estimate", "values": [6.1, 5.2, 4.4, 3.8, 3.5, 3.1, 2.4, 1.6]},
            ],
            "x_axis": "AI Investment as % of Sector Revenue",
        },
    },
    {
        "brief": "multi-series line chart AI investment trends 2019 to 2025, professional clean",
        "chart_type": "line",
        "chart_data": {
            "categories": ["2019", "2020", "2021", "2022", "2023", "2024", "2025E"],
            "series": [
                {"name": "AI Infrastructure",       "values": [18,  22,  31,  48,  69,  96, 135]},
                {"name": "Enterprise Applications",  "values": [28,  31,  43,  59,  77, 100, 129]},
                {"name": "Foundation Models & R&D",  "values": [12,  15,  25,  39,  53,  73,  96]},
            ],
            "x_axis": "Year",
            "y_axis": "Global Investment (USD Billion)",
            "y_min": 0, "y_max": 160,
        },
    },
    {
        "brief": "pie chart AI investment allocation breakdown by type, professional clean",
        "chart_type": "pie",
        "chart_data": {
            "labels": [
                "Platform & Infrastructure",
                "Applied AI Solutions",
                "Foundation Models",
                "AI Governance & Risk",
                "Edge & Embedded AI",
            ],
            "values": [34, 28, 21, 9, 8],
            "note": "Source: Illustrative estimates based on industry research; values are representative, 2025E",
        },
    },
]

# ── fallback text ─────────────────────────────────────────────────────────────

FALLBACK_TEXT = {
    1: {
        "title": "The AI Investment Imperative",
        "subtitle": "Three levers that separate leaders from laggards in the AI economy",
        "pillars": [
            {"num": "1", "title": "STRATEGY",      "body": "Define a clear AI investment thesis tied to measurable business outcomes and board-level accountability"},
            {"num": "2", "title": "INFRASTRUCTURE", "body": "Build scalable data pipelines and compute capacity to sustain continuous AI model delivery at enterprise scale"},
            {"num": "3", "title": "TALENT",         "body": "Cultivate cross-functional AI fluency from executive leadership to frontline operations and vendor management"},
        ],
    },
    2: {
        "title": "Investment Intensity Drives Digital Readiness Outcomes",
        "subtitle": "Illustrative benchmark of 15 economies plotted by AI spend and digital readiness index",
        "rail_label": "AI\nReadiness",
        "panel_bullets": [
            {"lead": "Leaders invest 5x more",   "body": "Top-quartile economies allocate 4x operating budget to AI vs laggards"},
            {"lead": "Compounding advantage",    "body": "High investment correlates with accelerating readiness — the gap widens annually"},
            {"lead": "Execution quality varies", "body": "Dispersion around the trend line signals governance and talent as key differentiators"},
            {"lead": "Asia leads on maturity",   "body": "Singapore, South Korea, and Switzerland show highest combined investment and readiness"},
        ],
    },
    3: {
        "title": "Financial Services and Healthcare Lead Sector AI Adoption",
        "subtitle": "AI investment intensity by sector: 2023 actual vs 2025 estimate (% of sector revenue)",
        "rail_label": "Sector\nAnalysis",
        "panel_bullets": [
            {"lead": "FinServ accelerates fastest",    "body": "Regulatory tailwind and data richness make Financial Services the dominant adopter through 2025"},
            {"lead": "Healthcare closes the gap",      "body": "Diagnostics, drug discovery and admin automation drive accelerated healthcare AI investment"},
            {"lead": "Manufacturing lags expectations","body": "Legacy systems and integration complexity continue to slow AI deployment in industrial settings"},
            {"lead": "Government share grows",         "body": "Public sector investment rising from a low base, led by defence and benefits automation platforms"},
        ],
    },
    4: {
        "title": "Three Waves of Global AI Investment: 2019-2025",
        "subtitle": "Cumulative momentum across infrastructure, enterprise applications, and foundational research",
    },
    5: {
        "title": "Where the Capital Is Going",
        "subtitle": "Global AI investment allocation by category, 2025 estimate",
        "footer_note": "Source: Illustrative estimates based on synthesised industry research; values are representative, 2025E",
    },
}

# ── Ollama prompts (split by model role) ─────────────────────────────────────

# llama4 / primary model: strategic narrative — titles, subtitles, pillar bodies
_PROMPT_NARRATIVE = """You are a senior management consultant writing slide headlines for a professional deck.
Deck topic: "Global AI Investment & Digital Readiness 2025"

Rules: titles max 12 words, subtitles max 18 words, pillar body max 18 words.
Return ONLY valid JSON — no markdown, no code fences, no explanation.

{
  "slides": [
    {
      "num": 1,
      "title": "...",
      "subtitle": "...",
      "pillars": [
        {"num": "1", "title": "STRATEGY",       "body": "..."},
        {"num": "2", "title": "INFRASTRUCTURE",  "body": "..."},
        {"num": "3", "title": "TALENT",          "body": "..."}
      ]
    },
    {"num": 2, "title": "...", "subtitle": "..."},
    {"num": 3, "title": "...", "subtitle": "..."},
    {"num": 4, "title": "...", "subtitle": "..."},
    {"num": 5, "title": "...", "subtitle": "...",
     "footer_note": "Source: Illustrative estimates based on industry research; values are representative, 2025E"}
  ]
}"""

# qwen3 / secondary model: analytical bullets — insight panel content
_PROMPT_BULLETS = """You are an analyst writing insight bullet points for a professional consulting presentation.
Deck topic: "Global AI Investment & Digital Readiness 2025"

Rules: 'lead' max 4 words, 'body' max 12 words. Be specific and data-driven.
Return ONLY valid JSON — no markdown, no code fences, no explanation.

{
  "slides": [
    {
      "num": 2,
      "rail_label": "AI\\nReadiness",
      "panel_bullets": [
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}
      ]
    },
    {
      "num": 3,
      "rail_label": "Sector\\nAnalysis",
      "panel_bullets": [
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}
      ]
    }
  ]
}"""


import re as _re_md

def _strip_md_values(v):
    if isinstance(v, str):
        return _re_md.sub(r'\*+([^*]+)\*+', r'\1', v).strip()
    if isinstance(v, list):
        return [_strip_md_values(i) for i in v]
    if isinstance(v, dict):
        return {k: _strip_md_values(val) for k, val in v.items()}
    return v


def call_ollama(model: str, prompt: str, timeout: int = 240) -> dict | None:
    payload = json.dumps({
        "model": model, "stream": False, "format": "json",
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        raw = json.loads(resp.read())
        content = raw["message"]["content"]
        # strip any accidental markdown code fences
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.rstrip("`").strip()
        result = json.loads(content)
        return _strip_md_values(result)
    except Exception as exc:
        print(f"  [ollama:{model}] {exc.__class__.__name__}: {exc}")
        return None


def _parse_slides(result: dict | None) -> dict[int, dict]:
    if result is None or "slides" not in result:
        return {}
    return {int(s["num"]): s for s in result.get("slides", [])}


def _is_weak(text: str) -> bool:
    """Return True if the string looks like an unfilled placeholder or is very short."""
    t = (text or "").strip()
    return not t or t == "..." or len(t) < 6


def get_text_content(model1: str, model2: str, skip: bool) -> dict[int, dict]:
    """
    Dual-model content generation:
      model1 (llama4:scout)  -> strategic narrative: titles, subtitles, pillar bodies
      model2 (qwen3:8b)      -> analytical bullets:  panel_bullets for slides 2-3
    Results are merged; per-field fallback fills any gap.
    """
    if skip:
        print("  [text] --skip-ollama: using built-in fallback text")
        return FALLBACK_TEXT

    # -- pass 1: narrative (model1) -------------------------------------------
    print(f"  [text:narrative] {model1} -> titles, subtitles, pillar bodies ...")
    narrative = _parse_slides(call_ollama(model1, _PROMPT_NARRATIVE))
    if not narrative:
        print(f"  [text:narrative] {model1} failed -> using fallback for narrative")
        narrative = {}

    # -- pass 2: bullets (model2) ---------------------------------------------
    print(f"  [text:bullets]   {model2} -> insight panel bullets ...")
    bullets = _parse_slides(call_ollama(model2, _PROMPT_BULLETS))
    if not bullets:
        print(f"  [text:bullets]   {model2} failed -> using fallback for bullets")
        bullets = {}

    # -- merge ---------------------------------------------------------------
    out: dict[int, dict] = {}
    for i in range(1, 6):
        fb = FALLBACK_TEXT.get(i, {})
        n  = narrative.get(i, {})
        b  = bullets.get(i, {})
        merged: dict = {}

        title    = n.get("title")    or fb.get("title",    f"Slide {i}")
        subtitle = n.get("subtitle") or fb.get("subtitle", "")
        if _is_weak(title):    title    = fb.get("title",    f"Slide {i}")
        if _is_weak(subtitle): subtitle = fb.get("subtitle", "")

        merged["title"]    = title
        merged["subtitle"] = subtitle

        if i == 1:
            pillars = n.get("pillars") or fb.get("pillars", [])
            for j, p in enumerate(pillars):
                if _is_weak(p.get("body", "")):
                    pillars[j]["body"] = fb["pillars"][j]["body"] if j < len(fb.get("pillars", [])) else ""
            merged["pillars"] = pillars

        if i in (2, 3):
            rl = b.get("rail_label") or n.get("rail_label") or fb.get("rail_label", "AI\nInsights")
            pb = b.get("panel_bullets") or n.get("panel_bullets") or fb.get("panel_bullets", [])
            # patch any weak bullets with fallback
            fb_pb = fb.get("panel_bullets", [])
            for j, bul in enumerate(pb):
                if _is_weak(bul.get("lead", "")) or _is_weak(bul.get("body", "")):
                    pb[j] = fb_pb[j] if j < len(fb_pb) else bul
            merged["rail_label"]    = rl
            merged["panel_bullets"] = pb if pb else fb_pb

        if i == 5:
            merged["footer_note"] = (
                n.get("footer_note")
                or b.get("footer_note")
                or fb.get("footer_note", "")
            )

        out[i] = merged

    return out


# ── assemble spec ─────────────────────────────────────────────────────────────

def build_slide_specs(idx) -> list[dict]:
    specs = []
    for i, sdef in enumerate(SLIDE_DEFS, 1):
        os.environ["CLASSIFIER_VERBOSE"] = "0"
        spec = get_slot_spec(sdef["brief"], k=1, index=idx)
        os.environ["CLASSIFIER_VERBOSE"] = "1"
        specs.append({
            "slide_num": i,
            "recipe": spec.recipe,
            "anchor_slide_id": spec.anchor_slide_id,
            "has_rail": "left_nav_rail" in spec.recipe,
            "has_panel": "right_insight_panel" in spec.recipe,
            "color_tokens": spec.color_tokens,
            "layout_dims": spec.layout_dims,
            "chart_type": sdef["chart_type"],
            "chart_data": sdef["chart_data"],
        })
        print(f"  slide {i}: {spec.recipe[:64]}  sim={spec.similarity:.3f}")
    return specs


def assemble_spec(slide_specs: list[dict], text: dict[int, dict]) -> dict:
    for s in slide_specs:
        n = s["slide_num"]
        t = text.get(n, FALLBACK_TEXT.get(n, {}))
        s["content"] = {"title": t.get("title", f"Slide {n}"), "subtitle": t.get("subtitle", "")}
        ct = s["chart_type"]
        if ct == "content":
            fb_pillars = FALLBACK_TEXT[1]["pillars"]
            pillars = t.get("pillars", fb_pillars)
            cd_pillars = s["chart_data"]["pillars"]
            for j, p in enumerate(pillars):
                if j < len(cd_pillars):
                    p["color"] = cd_pillars[j]["color"]
            s["content"]["pillars"] = pillars
        elif ct in ("bubble", "bar"):
            s["content"]["rail_label"]    = t.get("rail_label", FALLBACK_TEXT[n].get("rail_label", "AI\nInsights"))
            s["content"]["panel_bullets"] = t.get("panel_bullets", FALLBACK_TEXT[n].get("panel_bullets", []))
        elif ct == "pie":
            s["content"]["footer_note"] = t.get("footer_note", FALLBACK_TEXT[5]["footer_note"])
    return {
        "output_path": str(PPTX_PATH).replace("\\", "/"),
        "deck": {"title": "Global AI Investment & Digital Readiness 2025"},
        "slides": slide_specs,
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sample 5-slide AI investment deck")
    parser.add_argument("--model",  default="gemma3:27b-cloud",
                        help="Primary model for narrative text (titles/subtitles/pillars)")
    parser.add_argument("--model2", default="gemma3:27b-cloud",
                        help="Secondary model for analytical bullets (panel content)")
    parser.add_argument("--skip-ollama", action="store_true")
    parser.add_argument("--out", default=None,
                        help="Override output PPTX filename (default: sample_deck.pptx)")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    pptx_path = OUT_DIR / (args.out if args.out else "sample_deck.pptx")

    print("Phase 3: retrieving slide anchors ...")
    idx = load_index()
    slide_specs = build_slide_specs(idx)

    print("\nGenerating text content ...")
    text = get_text_content(args.model, args.model2, args.skip_ollama)

    print("\nAssembling deck spec ...")
    spec = assemble_spec(slide_specs, text)
    spec["output_path"] = str(pptx_path).replace("\\", "/")
    SPEC_PATH.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"  Written: {SPEC_PATH}")

    print("\nRendering PPTX ...")
    js_script = Path(__file__).parent / "generate_sample_deck.js"
    r = subprocess.run(["node", str(js_script), str(SPEC_PATH)], capture_output=True, text=True)
    if r.stdout:
        print(r.stdout.rstrip())
    if r.returncode != 0:
        print(f"  ERROR: node exited {r.returncode}\n  {r.stderr[:800]}")
        sys.exit(1)

    print("\nPatching PPTX ...")
    fix = Path(__file__).parent / "fix_pptx_bubble_charts.py"
    r2 = subprocess.run([sys.executable, str(fix), str(pptx_path)], capture_output=True, text=True)
    if r2.stdout:
        print(r2.stdout.rstrip())

    print(f"\nDone -> {pptx_path}")


if __name__ == "__main__":
    main()
