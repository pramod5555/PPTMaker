"""
extract_vision_features.py — Vision-model feature extraction for slide PNGs.

Uses claude-haiku-4-5 (cheap, fast) to classify each slide with 12 rich features
that pixel heuristics cannot capture: chart complexity, visual polish, layout
sophistication, etc.  Results saved to vision_features.json and merged back
into dataset.json label blocks.

Usage
-----
    python extract_vision_features.py                 # all slides missing features
    python extract_vision_features.py --limit 50      # first 50 pending
    python extract_vision_features.py --source "Roland Berger,BCG"
    python extract_vision_features.py --overwrite     # re-extract all
    python extract_vision_features.py --merge-only    # skip extraction, just merge
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI
from PIL import Image

load_dotenv()

BASE_DIR    = Path(__file__).parent
SLIDES_DIR  = BASE_DIR / "slides"
DATASET     = BASE_DIR / "dataset.json"
FEATURES_DB = BASE_DIR / "vision_features.json"

MODEL      = "gpt-5.4"
MAX_TOKENS = 512
DELAY      = 0.5   # seconds between calls

EXTRACTION_PROMPT = """\
Analyse this consulting presentation slide and return ONLY a JSON object — no prose, no markdown fences.

Required fields:
{
  "quality_score": <int 1-5>,
  "layout_type": "<cover|section_divider|exec_summary|two_col_chart|three_col_text|full_chart|mixed_layout|table|diagram|full_page_text>",
  "chart_type": "<none|bar|stacked_bar|line|scatter|bubble|donut|pie|table|heat_map|waterfall|funnel|mixed>",
  "chart_complexity": "<none|simple|moderate|complex>",
  "text_density": "<low|medium|high>",
  "has_custom_diagrams": <true|false>,
  "has_data_callouts": <true|false>,
  "color_sophistication": "<basic|professional|sophisticated>",
  "information_density": "<low|medium|high>",
  "slide_purpose": "<transition|framing|data_evidence|executive_summary|recommendation|appendix>",
  "visual_polish": <int 1-5>
}

Scoring guide:
  quality_score  1=blank/broken  2=plain text  3=basic layout  4=professional  5=premier consulting (dense, multi-layer)
  visual_polish  1=no design     2=minimal     3=standard corp  4=refined       5=award-level layout precision
"""


def encode_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def extract_one(client: AzureOpenAI, slide_id: str) -> dict | None:
    img_path = SLIDES_DIR / f"{slide_id}.png"
    if not img_path.exists():
        return None

    b64 = encode_image(img_path)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_completion_tokens=MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text",      "text": EXTRACTION_PROMPT},
                ],
            }],
        )
        text = resp.choices[0].message.content.strip()
        # Strip markdown fences if model adds them
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        features = json.loads(text)
        features["slide_id"] = slide_id
        return features
    except (json.JSONDecodeError, Exception) as exc:
        print(f" ERR({exc.__class__.__name__})", end="", flush=True)
        return None


def load_features() -> dict[str, dict]:
    if FEATURES_DB.exists():
        return {f["slide_id"]: f for f in json.loads(FEATURES_DB.read_text(encoding="utf-8"))}
    return {}


def save_features(features: dict[str, dict]) -> None:
    FEATURES_DB.write_text(
        json.dumps(list(features.values()), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def merge_into_dataset(features: dict[str, dict]) -> int:
    """Write vision features back into each slide's label block in dataset.json."""
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    slides = raw.get("slides", raw) if isinstance(raw, dict) else raw
    updated = 0
    for slide in slides:
        sid = slide.get("slide_id", "")
        if sid in features:
            lbl = slide.get("label") or {}
            if not isinstance(lbl, dict):
                lbl = {}
            lbl.update({
                "estimated_quality_score": features[sid].get("quality_score", lbl.get("estimated_quality_score")),
                "visual_polish":           features[sid].get("visual_polish"),
                "layout_type":             features[sid].get("layout_type",      lbl.get("layout_type")),
                "chart_type":              features[sid].get("chart_type",        lbl.get("chart_type")),
                "chart_complexity":        features[sid].get("chart_complexity"),
                "text_density":            features[sid].get("text_density",      lbl.get("text_density")),
                "has_custom_diagrams":     features[sid].get("has_custom_diagrams"),
                "has_data_callouts":       features[sid].get("has_data_callouts", lbl.get("has_data_callouts")),
                "color_sophistication":    features[sid].get("color_sophistication"),
                "information_density":     features[sid].get("information_density"),
                "slide_purpose":           features[sid].get("slide_purpose",     lbl.get("slide_purpose")),
            })
            slide["label"] = lbl
            updated += 1
    if isinstance(raw, dict):
        raw["slides"] = slides
    DATASET.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    return updated


def prune_low_quality(min_score: int, delete_pngs: bool = False) -> tuple[int, int]:
    """
    Remove slides from dataset.json whose vision quality_score < min_score.
    Slides not yet scored by vision model are left untouched.
    Returns (removed_count, remaining_count).
    """
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    slides = raw.get("slides", raw) if isinstance(raw, dict) else raw

    keep, removed = [], []
    for slide in slides:
        lbl = slide.get("label") or {}
        score = lbl.get("estimated_quality_score")
        # Only prune if vision model has scored this slide (score is an int, not None)
        if score is not None and isinstance(score, (int, float)) and score < min_score:
            removed.append(slide["slide_id"])
        else:
            keep.append(slide)

    if removed:
        if isinstance(raw, dict):
            raw["slides"] = keep
        DATASET.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        if delete_pngs:
            for sid in removed:
                png = SLIDES_DIR / f"{sid}.png"
                if png.exists():
                    png.unlink()
        print(f"Pruned {len(removed)} low-quality slides (score < {min_score}). {len(keep)} remain.")
    else:
        print(f"Nothing to prune at threshold {min_score}. {len(keep)} slides kept.")

    return len(removed), len(keep)


def main() -> None:
    parser = argparse.ArgumentParser(description="Vision-model slide feature extraction.")
    parser.add_argument("--limit",           type=int,   default=None)
    parser.add_argument("--source",          default=None, help="Comma-separated source_company filter")
    parser.add_argument("--overwrite",       action="store_true", help="Re-extract slides already done")
    parser.add_argument("--merge-only",      action="store_true", help="Skip extraction, just merge features into dataset.json")
    parser.add_argument("--delay",           type=float, default=DELAY)
    parser.add_argument("--prune",           type=int,   default=None,
                        metavar="MIN_SCORE", help="After merge, remove slides with quality_score < MIN_SCORE from dataset.json")
    parser.add_argument("--delete-pngs",     action="store_true", help="With --prune: also delete PNG files of pruned slides")
    args = parser.parse_args()

    # ── merge-only shortcut ───────────────────────────────────────────────────
    if args.merge_only:
        feats = load_features()
        n = merge_into_dataset(feats)
        print(f"Merged {n} slides into dataset.json")
        if args.prune:
            prune_low_quality(args.prune, delete_pngs=args.delete_pngs)
        return

    # ── load dataset ──────────────────────────────────────────────────────────
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    slides = raw.get("slides", []) if isinstance(raw, dict) else raw

    # ── source filter ─────────────────────────────────────────────────────────
    if args.source:
        allowed = {s.strip() for s in args.source.split(",")}
        slides = [s for s in slides if s.get("label", {}).get("source_company") in allowed]
        print(f"Source filter: {allowed} -> {len(slides)} slides")

    # ── landscape filter ──────────────────────────────────────────────────────
    def is_landscape(sid: str) -> bool:
        p = SLIDES_DIR / f"{sid}.png"
        if not p.exists():
            return False
        with Image.open(p) as img:
            w, h = img.size
        return w > h

    slides = [s for s in slides if is_landscape(s["slide_id"])]

    # ── skip already-done ─────────────────────────────────────────────────────
    existing = load_features()
    if not args.overwrite:
        slides = [s for s in slides if s["slide_id"] not in existing]

    if args.limit:
        slides = slides[: args.limit]

    if not slides:
        print("Nothing to extract.")
        # Still merge whatever we have
        n = merge_into_dataset(existing)
        print(f"Merged {n} existing features into dataset.json")
        return

    print(f"Extracting features for {len(slides)} slides using {MODEL} ...")

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        sys.exit("AZURE_OPENAI_API_KEY not set in .env")

    client = AzureOpenAI(
        api_key=api_key,
        api_version="2024-12-01-preview",
        azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
    )
    done = ok = 0

    for slide in slides:
        sid = slide["slide_id"]
        print(f"  [{done+1}/{len(slides)}] {sid[:60]} ...", end=" ", flush=True)
        result = extract_one(client, sid)
        if result:
            existing[sid] = result
            ok += 1
            print(f"OK (q={result.get('quality_score')} p={result.get('visual_polish')})")
        else:
            print("SKIP")
        done += 1
        # Save every 25 slides so progress isn't lost on interruption
        if done % 25 == 0:
            save_features(existing)
        time.sleep(args.delay)

    save_features(existing)
    print(f"\nDone: {ok}/{done} extracted -> {FEATURES_DB.name}")

    print("Merging into dataset.json ...")
    n = merge_into_dataset(existing)
    print(f"Updated {n} slides in dataset.json")

    if args.prune:
        print(f"\nPruning slides with quality_score < {args.prune} ...")
        prune_low_quality(args.prune, delete_pngs=args.delete_pngs)


if __name__ == "__main__":
    main()
