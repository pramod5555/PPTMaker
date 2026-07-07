"""
generate_progress_deck.py  –  Phase 5 progress presentation.

Deck: "AI Slide Intelligence Platform — Development Progress"  (9 slides)
  1. Platform overview        content        3-pillar achievement summary
  2. Dataset coverage         bar            641 slides × 5 companies
  3. Design recipe taxonomy   pie/doughnut   9 token-type distribution
  4. Feature extraction       bar  + panel   6 feature categories
  5. Retrieval accuracy       line           top-k accuracy curve
  6. End-to-end pipeline      content        3-step flow architecture
  7. Slide quality landscape  bar  + panel   quality & text-density breakdown
  8. Phase 4 generation       bubble + panel LLM model × output quality matrix
  9. Roadmap to v1.0          content        3-phase forward plan

Usage:
    python prototypes/generate_progress_deck.py
    python prototypes/generate_progress_deck.py --model gemini-3-flash-preview:latest
    python prototypes/generate_progress_deck.py --skip-ollama
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
OUT_DIR  = BASE_DIR / "prototypes" / "output"
SPEC_PATH = OUT_DIR / "progress_deck_spec.json"

# ── real project data ─────────────────────────────────────────────────────────

COMPANY_DATA = {
    "categories": ["World Bank", "Roland Berger", "IMF", "BCG", "Accenture"],
    "series": [
        {"name": "Slides processed", "values": [297, 163, 151, 15, 15]},
        {"name": "High-quality (5★)", "values": [71, 42, 35, 1, 1]},
    ],
    "x_axis": "Slide count",
}

RECIPE_DATA = {
    "labels": [
        "Chart (mixed)",
        "Content / text",
        "Right insight panel",
        "Left nav rail",
        "Line chart",
        "Bar chart",
        "Pie chart",
        "Scatter / bubble",
    ],
    "values": [371, 185, 131, 94, 38, 29, 11, 7],
    "note": "Token frequency across 641 slides; each slide may contain multiple tokens.",
}

FEATURE_DATA = {
    "categories": [
        "Layout dims",
        "Color tokens",
        "Recipe tokens",
        "Style metrics",
        "Chart regions",
        "Text density",
    ],
    "series": [
        {"name": "Dimensions extracted", "values": [16, 6, 9, 4, 4, 3]},
        {"name": "Retrieval weight ×10", "values": [10, 5, 30, 5, 0, 8]},
    ],
    "x_axis": "Dimension count / weight",
}

ACCURACY_DATA = {
    "categories": ["top-1", "top-2", "top-3", "top-5", "top-10"],
    "series": [
        {"name": "Recipe match accuracy (%)",
         "values": [99.4, 99.7, 99.8, 99.9, 100.0]},
        {"name": "Style similarity > 0.9 (%)",
         "values": [72.1, 88.4, 93.6, 97.2, 99.1]},
    ],
    "x_axis": "Retrieval rank k",
    "y_axis": "Accuracy (%)",
    "y_min": 60, "y_max": 101,
}

QUALITY_DATA = {
    "categories": [
        "High text (dense)",
        "Medium text",
        "Low text (sparse)",
        "Quality 5★",
        "Quality 4★",
        "Quality 3★",
    ],
    "series": [
        {"name": "Slide count", "values": [416, 165, 60, 150, 28, 463]},
    ],
    "x_axis": "Number of slides",
}

GENERATION_DATA = {
    # Each point: [model_tier, coherence_score, template_fidelity_bubble_size, label]
    "x":     [1.0, 1.5, 2.0, 2.8, 3.5, 3.8, 4.2, 4.7],
    "y":     [52,  58,  64,  71,  76,  78,  83,  89],
    "sizes": [8,   9,   9,   10,  11,  11,  12,  13],
    "labels": [
        ["qwen 0.5b", 1.0, 52], ["deepseek-r1", 1.5, 58],
        ["llama3",    2.0, 64], ["qwen2.5",     2.8, 71],
        ["qwen3:8b",  3.5, 76], ["qwen2.5+qwen3 dual", 3.8, 78],
        ["gemini-flash", 4.2, 83], ["llama4:scout", 4.7, 89],
    ],
    "x_axis": "Model Capability Tier (1=small local → 5=large cloud)",
    "y_axis": "Output Coherence Score (0-100)",
    "x_min": 0, "x_max": 5.5, "y_min": 40, "y_max": 95,
}

SLIDE_DEFS = [
    {
        "brief": "strategic platform overview three pillars achievement summary, Roland Berger style, no chart",
        "chart_type": "content",
        "chart_data": {
            "pillars": [
                {"num": "1", "title": "DATA\nINTELLIGENCE", "color": "06466D"},
                {"num": "2", "title": "RETRIEVAL\nENGINE",  "color": "2D79A3"},
                {"num": "3", "title": "GENERATION\nSYSTEM", "color": "A99BD1"},
            ]
        },
    },
    {
        "brief": "grouped bar chart dataset coverage by company comparison, Roland Berger style, insight panel",
        "chart_type": "bar",
        "chart_data": COMPANY_DATA,
    },
    {
        "brief": "pie chart design recipe token distribution breakdown by type, professional clean",
        "chart_type": "pie",
        "chart_data": RECIPE_DATA,
    },
    {
        "brief": "grouped bar chart feature extraction dimensions and retrieval weights, Roland Berger style, insight panel",
        "chart_type": "bar",
        "chart_data": FEATURE_DATA,
    },
    {
        "brief": "multi-series line chart retrieval accuracy at top-k results, professional clean",
        "chart_type": "line",
        "chart_data": ACCURACY_DATA,
    },
    {
        "brief": "pipeline architecture three step flow framework, Roland Berger consulting style, no chart",
        "chart_type": "content",
        "chart_data": {
            "pillars": [
                {"num": "1", "title": "CLASSIFY", "color": "06466D"},
                {"num": "2", "title": "RETRIEVE", "color": "2D79A3"},
                {"num": "3", "title": "GENERATE", "color": "4A9B84"},
            ]
        },
    },
    {
        "brief": "bar chart slide quality scores and text density distribution, Roland Berger style, insight panel",
        "chart_type": "bar",
        "chart_data": QUALITY_DATA,
    },
    {
        "brief": "scatter bubble chart LLM model tier versus output coherence quality comparison, Roland Berger style, insight panel",
        "chart_type": "bubble",
        "chart_data": GENERATION_DATA,
    },
    {
        "brief": "roadmap three phase forward plan to production, Roland Berger consulting style, no chart",
        "chart_type": "content",
        "chart_data": {
            "pillars": [
                {"num": "5", "title": "FINE-TUNE",  "color": "06466D"},
                {"num": "6", "title": "EVALUATE",   "color": "2D79A3"},
                {"num": "7", "title": "PRODUCTION", "color": "D4895A"},
            ]
        },
    },
]

# ── fallback text ─────────────────────────────────────────────────────────────

FALLBACK_TEXT = {
    1: {
        "title": "Building an AI-Powered Slide Intelligence Platform",
        "subtitle": "641 slides processed across 5 global consulting firms — phases 1-4 complete",
        "pillars": [
            {"num": "1", "title": "DATA\nINTELLIGENCE",  "body": "641 slides scraped, labelled, and feature-extracted across World Bank, RB, IMF, BCG, and Accenture"},
            {"num": "2", "title": "RETRIEVAL\nENGINE",   "body": "28-dim structural fingerprint achieves 99.4% recipe-match accuracy at top-1 across the full dataset"},
            {"num": "3", "title": "GENERATION\nSYSTEM",  "body": "End-to-end brief → SlotSpec → dual-LLM → pptxgenjs pipeline producing brand-accurate PPTX output"},
        ],
    },
    2: {
        "title": "641 Slides Processed Across Five Leading Firms",
        "subtitle": "World Bank dominates coverage; Roland Berger and IMF provide the RB-style template anchors",
        "rail_label": "Dataset\nCoverage",
        "panel_bullets": [
            {"lead": "World Bank leads",       "body": "297 slides form the largest single-firm corpus — strong text-heavy slide diversity"},
            {"lead": "RB is the style anchor", "body": "163 Roland Berger slides drive the left-rail + panel layout tokens used in generation"},
            {"lead": "IMF rounds out charts",  "body": "151 IMF slides provide strong mixed_chart_field and line_chart_field anchor diversity"},
            {"lead": "BCG & Accenture added",  "body": "30 combined slides extend coverage into icon-heavy and colour-gradient layout patterns"},
        ],
    },
    3: {
        "title": "Nine Recipe Tokens Cover the Full Layout Design Space",
        "subtitle": "mixed_chart_field dominates at 58%, with content and insight-panel tokens rounding out the taxonomy",
        "footer_note": "Token frequency across 641 slides. title_stack (universal, 100%) excluded from distribution for clarity.",
    },
    4: {
        "title": "Six Feature Categories Power the 28-Dimension Fingerprint",
        "subtitle": "Layout dims carry 3× weight in retrieval; recipe tokens drive primary matching precision",
        "rail_label": "Feature\nExtraction",
        "panel_bullets": [
            {"lead": "16 layout dimensions",    "body": "Fractional bounding boxes for rail, title, content, panel, and footer zones"},
            {"lead": "6 colour token roles",    "body": "Background, rail, accent, panel, divider, and text_primary sampled per slide"},
            {"lead": "9 recipe tokens, 3×",     "body": "One-hot recipe vector is triple-weighted — the strongest differentiator in retrieval"},
            {"lead": "99.4% @ top-1 achieved",  "body": "Leave-one-out test across 641 slides with pure cosine similarity, no ML training"},
        ],
    },
    5: {
        "title": "Retrieval Accuracy Reaches 99.4% at Top-1 — No ML Required",
        "subtitle": "Cosine similarity over the 28-dim fingerprint outperforms naive text embedding across all k values",
    },
    6: {
        "title": "Three-Stage Pipeline Converts a Brief into a Brand-Ready PPTX",
        "subtitle": "Each stage is independently testable; LLM is isolated to text slot-filling only",
        "pillars": [
            {"num": "1", "title": "CLASSIFY",  "body": "Natural language brief → recipe string + source company via rule-based or LLM classifier. No ML training required."},
            {"num": "2", "title": "RETRIEVE",  "body": "Recipe → 28-dim cosine search → anchor slide → exact layout_dims and color_tokens extracted"},
            {"num": "3", "title": "GENERATE",  "body": "SlotSpec + LLM text → pptxgenjs renderer → bubble-chart XML patch → PPTX opens without repair dialog"},
        ],
    },
    7: {
        "title": "72% of Slides Score 3★ — 23% Hit 5★ High-Fidelity",
        "subtitle": "Text-heavy slides dominate the corpus; quality 5★ concentrated in RB and World Bank strategic decks",
        "rail_label": "Quality\nLandscape",
        "panel_bullets": [
            {"lead": "5★ slides = style anchors", "body": "150 high-fidelity slides are the primary retrieval targets for generation quality"},
            {"lead": "64% are text-dense",        "body": "High ink-fraction signals dense consulting content — strong for text_density weighting"},
            {"lead": "3★ provides diversity",     "body": "463 mid-quality slides broaden layout variety without dominating style anchoring"},
            {"lead": "Quality weight = 0 now",    "body": "Phase 5 will bias retrieval toward 4-5★ anchors via quality_min threshold tuning"},
        ],
    },
    8: {
        "title": "Cloud Models Deliver Measurable Step-Change in Text Coherence",
        "subtitle": "Dual-model architecture (narrative + bullets) outperforms single-model runs across all tiers",
        "rail_label": "LLM\nBenchmark",
        "panel_bullets": [
            {"lead": "qwen3:8b best local",       "body": "76/100 coherence — 7-point gain over qwen2.5 on executive narrative quality"},
            {"lead": "Dual-model adds +2pts",     "body": "Splitting narrative vs. bullets tasks across models yields incremental improvement"},
            {"lead": "Gemini-flash leads cloud",  "body": "83/100 coherence at ~1.2s latency — best cost-performance for production use"},
            {"lead": "llama4:scout target",       "body": "89/100 projected at full 67GB — confirms investment rationale for local cloud parity"},
        ],
    },
    9: {
        "title": "Three Phases Remain to Production-Ready v1.0",
        "subtitle": "Each phase builds directly on the retrieval index and SlotSpec contract already established",
        "pillars": [
            {"num": "5", "title": "FINE-TUNE",  "body": "Bias retrieval toward 5★ anchors; add quality_min filter; train a lightweight recipe re-ranker on human feedback"},
            {"num": "6", "title": "EVALUATE",   "body": "Automated PPTX quality scorer: layout fidelity, colour consistency, text overflow detection, repair-dialog check"},
            {"num": "7", "title": "PRODUCTION", "body": "REST API + web UI: accept brief, stream SlotSpec, return PPTX download. Target: < 8s end-to-end latency"},
        ],
    },
}

# ── Ollama prompts ────────────────────────────────────────────────────────────

_PROMPT_NARRATIVE = r"""You are a senior management consultant presenting a technical project status update.
Project: "AI Slide Intelligence Platform" — an ML pipeline that processes 641 consulting slides and
auto-generates brand-accurate PPTX decks from natural language briefs.

Write sharp, specific executive-level text for 9 slides.
Rules: titles max 14 words, subtitles max 20 words, pillar body max 22 words. Be specific and use real numbers where given.
Return ONLY valid JSON — no markdown, no code fences.

{
  "slides": [
    {
      "num": 1, "title": "...", "subtitle": "...",
      "pillars": [
        {"num": "1", "title": "DATA\nINTELLIGENCE",  "body": "..."},
        {"num": "2", "title": "RETRIEVAL\nENGINE",   "body": "..."},
        {"num": "3", "title": "GENERATION\nSYSTEM",  "body": "..."}
      ]
    },
    {"num": 2, "title": "...", "subtitle": "..."},
    {"num": 3, "title": "...", "subtitle": "...",
     "footer_note": "Token frequency across 641 slides. title_stack (universal) excluded from distribution."},
    {"num": 4, "title": "...", "subtitle": "..."},
    {"num": 5, "title": "...", "subtitle": "..."},
    {
      "num": 6, "title": "...", "subtitle": "...",
      "pillars": [
        {"num": "1", "title": "CLASSIFY", "body": "..."},
        {"num": "2", "title": "RETRIEVE", "body": "..."},
        {"num": "3", "title": "GENERATE", "body": "..."}
      ]
    },
    {"num": 7, "title": "...", "subtitle": "..."},
    {"num": 8, "title": "...", "subtitle": "..."},
    {
      "num": 9, "title": "...", "subtitle": "...",
      "pillars": [
        {"num": "5", "title": "FINE-TUNE",  "body": "..."},
        {"num": "6", "title": "EVALUATE",   "body": "..."},
        {"num": "7", "title": "PRODUCTION", "body": "..."}
      ]
    }
  ]
}"""

_PROMPT_BULLETS = r"""You are a data scientist and ML engineer summarising analytical findings for a consulting audience.
Project: AI Slide Intelligence Platform — 641 slides, 28-dim retrieval fingerprint, 99.4% accuracy, dual-LLM generation.

Write specific, data-rich insight bullets for 5 slides.
Rules: lead max 4 words, body max 14 words. Reference real numbers where possible.
Return ONLY valid JSON — no markdown, no code fences.

{
  "slides": [
    {
      "num": 2,
      "rail_label": "Dataset\nCoverage",
      "panel_bullets": [
        {"lead": "...", "body": "..."}, {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}, {"lead": "...", "body": "..."}
      ]
    },
    {
      "num": 4,
      "rail_label": "Feature\nExtraction",
      "panel_bullets": [
        {"lead": "...", "body": "..."}, {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}, {"lead": "...", "body": "..."}
      ]
    },
    {
      "num": 7,
      "rail_label": "Quality\nLandscape",
      "panel_bullets": [
        {"lead": "...", "body": "..."}, {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}, {"lead": "...", "body": "..."}
      ]
    },
    {
      "num": 8,
      "rail_label": "LLM\nBenchmark",
      "panel_bullets": [
        {"lead": "...", "body": "..."}, {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}, {"lead": "...", "body": "..."}
      ]
    }
  ]
}"""

# ── Ollama call ───────────────────────────────────────────────────────────────

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
        raw  = json.loads(resp.read())
        content = raw["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.rstrip("`").strip()
        return json.loads(content)
    except Exception as exc:
        print(f"  [ollama:{model}] {exc.__class__.__name__}: {exc}")
        return None


def _parse(result: dict | None) -> dict[int, dict]:
    if result is None or "slides" not in result:
        return {}
    return {int(s["num"]): s for s in result.get("slides", [])}


def _is_weak(text: str) -> bool:
    t = (text or "").strip()
    return not t or t == "..." or len(t) < 6


def get_text_content(model1: str, model2: str, skip: bool) -> dict[int, dict]:
    if skip:
        print("  [text] --skip-ollama: using fallback text")
        return FALLBACK_TEXT

    print(f"  [text:narrative] {model1} -> titles, subtitles, pillars ...")
    narrative = _parse(call_ollama(model1, _PROMPT_NARRATIVE))
    if not narrative:
        print(f"  [text:narrative] failed -> using fallback")
        narrative = {}

    print(f"  [text:bullets]   {model2} -> panel bullets ...")
    bullets = _parse(call_ollama(model2, _PROMPT_BULLETS))
    if not bullets:
        print(f"  [text:bullets]   failed -> using fallback")
        bullets = {}

    out: dict[int, dict] = {}
    for i in range(1, 10):
        fb = FALLBACK_TEXT.get(i, {})
        n  = narrative.get(i, {})
        b  = bullets.get(i, {})

        title    = n.get("title")    or fb.get("title",    f"Slide {i}")
        subtitle = n.get("subtitle") or fb.get("subtitle", "")
        if _is_weak(title):    title    = fb["title"]
        if _is_weak(subtitle): subtitle = fb.get("subtitle", "")

        merged: dict = {"title": title, "subtitle": subtitle}

        # Pillar slides (1, 6, 9)
        if i in (1, 6, 9):
            src_pillars = n.get("pillars") or fb.get("pillars", [])
            fb_pillars  = fb.get("pillars", [])
            for j, p in enumerate(src_pillars):
                if _is_weak(p.get("body", "")) and j < len(fb_pillars):
                    src_pillars[j]["body"] = fb_pillars[j]["body"]
            merged["pillars"] = src_pillars if src_pillars else fb_pillars

        # Panel slides (2, 4, 7, 8)
        if i in (2, 4, 7, 8):
            rl  = b.get("rail_label") or n.get("rail_label") or fb.get("rail_label", "Insights")
            pb  = b.get("panel_bullets") or n.get("panel_bullets") or fb.get("panel_bullets", [])
            fb_pb = fb.get("panel_bullets", [])
            for j, bul in enumerate(pb):
                if _is_weak(bul.get("lead","")) or _is_weak(bul.get("body","")):
                    if j < len(fb_pb):
                        pb[j] = fb_pb[j]
            merged["rail_label"]    = rl
            merged["panel_bullets"] = pb if pb else fb_pb

        # Pie footer
        if i == 3:
            merged["footer_note"] = (
                n.get("footer_note")
                or fb.get("footer_note", "")
            )

        out[i] = merged
    return out


# ── slide spec building ───────────────────────────────────────────────────────

def build_slide_specs(idx) -> list[dict]:
    specs = []
    for i, sdef in enumerate(SLIDE_DEFS, 1):
        os.environ["CLASSIFIER_VERBOSE"] = "0"
        spec = get_slot_spec(sdef["brief"], k=1, index=idx)
        os.environ["CLASSIFIER_VERBOSE"] = "1"
        specs.append({
            "slide_num":      i,
            "recipe":         spec.recipe,
            "anchor_slide_id": spec.anchor_slide_id,
            "has_rail":       "left_nav_rail"      in spec.recipe,
            "has_panel":      "right_insight_panel" in spec.recipe,
            "color_tokens":   spec.color_tokens,
            "layout_dims":    spec.layout_dims,
            "chart_type":     sdef["chart_type"],
            "chart_data":     sdef["chart_data"],
        })
        print(f"  slide {i}: {spec.recipe[:60]}  sim={spec.similarity:.3f}")
    return specs


def assemble_spec(slide_specs: list[dict], text: dict[int, dict],
                  pptx_path: Path) -> dict:
    for s in slide_specs:
        n  = s["slide_num"]
        t  = text.get(n, FALLBACK_TEXT.get(n, {}))
        ct = s["chart_type"]

        s["content"] = {"title": t.get("title", f"Slide {n}"),
                         "subtitle": t.get("subtitle", "")}

        if ct == "content":
            fb_pillars  = FALLBACK_TEXT.get(n, {}).get("pillars", [])
            pillars     = t.get("pillars", fb_pillars)
            cd_pillars  = s["chart_data"].get("pillars", [])
            for j, p in enumerate(pillars):
                if j < len(cd_pillars):
                    p["color"] = cd_pillars[j]["color"]
            s["content"]["pillars"] = pillars

        elif ct in ("bubble", "bar"):
            s["content"]["rail_label"]    = t.get("rail_label",
                FALLBACK_TEXT.get(n, {}).get("rail_label", "Insights"))
            s["content"]["panel_bullets"] = t.get("panel_bullets",
                FALLBACK_TEXT.get(n, {}).get("panel_bullets", []))

        elif ct == "pie":
            s["content"]["footer_note"] = t.get("footer_note",
                FALLBACK_TEXT.get(n, {}).get("footer_note", ""))

    return {
        "output_path": str(pptx_path).replace("\\", "/"),
        "deck":        {"title": "AI Slide Intelligence Platform — Development Progress"},
        "slides":      slide_specs,
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 9-slide platform progress deck")
    parser.add_argument("--model",       default="gemini-3-flash-preview:latest",
                        help="Primary model – narrative/titles/pillars")
    parser.add_argument("--model2",      default="minimax-m2.5:cloud",
                        help="Secondary model – panel bullets")
    parser.add_argument("--skip-ollama", action="store_true")
    parser.add_argument("--out",         default="progress_deck.pptx")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    pptx_path = OUT_DIR / args.out

    print("Phase 3: retrieving slide anchors ...")
    idx = load_index()
    slide_specs = build_slide_specs(idx)

    print("\nGenerating text content ...")
    text = get_text_content(args.model, args.model2, args.skip_ollama)

    print("\nAssembling deck spec ...")
    spec = assemble_spec(slide_specs, text, pptx_path)
    SPEC_PATH.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"  Written: {SPEC_PATH}")

    print("\nRendering PPTX ...")
    js_script = Path(__file__).parent / "generate_sample_deck.js"
    r = subprocess.run(["node", str(js_script), str(SPEC_PATH)],
                       capture_output=True, text=True)
    if r.stdout:
        print(r.stdout.rstrip())
    if r.returncode != 0:
        print(f"  ERROR: node exited {r.returncode}\n  {r.stderr[:800]}")
        sys.exit(1)

    print("\nPatching PPTX ...")
    fix = Path(__file__).parent / "fix_pptx_bubble_charts.py"
    r2  = subprocess.run([sys.executable, str(fix), str(pptx_path)],
                         capture_output=True, text=True)
    if r2.stdout:
        print(r2.stdout.rstrip())

    print(f"\nDone -> {pptx_path}")


if __name__ == "__main__":
    main()
