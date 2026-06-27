"""
ingest_new_slides.py — Fast ingestion of new slide PNGs into the full pipeline.

Finds PNGs in /slides/ that are NOT yet in dataset.json, auto-labels them,
runs feature extraction, then rebuilds the retrieval index.

Usage:
    python ingest_new_slides.py                  # full auto pipeline
    python ingest_new_slides.py --label-only     # stop after dataset.json
    python ingest_new_slides.py --features-only  # skip to feature extraction
    python ingest_new_slides.py --limit 200      # cap new slides to ingest
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

BASE_DIR  = Path(__file__).parent
SLIDES_DIR = BASE_DIR / "slides"
DATASET_FILE = BASE_DIR / "dataset.json"
FIDELITY_JSON = BASE_DIR / "prototypes" / "output" / "fidelity_summary.json"

sys.path.insert(0, str(BASE_DIR / "prototypes"))


# ── re-use draft_labeler's logic without importing to avoid batch dependency ──

def _source_company(filename: str) -> str:
    fn = filename.lower()
    if fn.startswith("roland_berger"):    return "Roland Berger"
    if fn.startswith("bain"):             return "Bain"
    if fn.startswith("deloitte"):         return "Deloitte"
    if fn.startswith("bcg"):              return "BCG"
    if fn.startswith("mckinsey"):         return "McKinsey"
    if fn.startswith("worldbank"):        return "World Bank"
    if fn.startswith("imf"):              return "IMF"
    if fn.startswith("accenture"):        return "Accenture"
    if fn.startswith("wef"):              return "WEF"
    return "Unknown"


def _image_heuristics(path: Path) -> dict:
    """Quick pixel stats for slide classification."""
    with Image.open(path).convert("RGB") as img:
        small = img.resize((160, 90))
        pixels = list(small.getdata())
        w, h = small.size

        # Background: corner average
        corner_pixels = []
        for x0, y0 in ((0, 0), (w - 20, 0), (0, h - 20), (w - 20, h - 20)):
            for x in range(x0, min(x0 + 20, w)):
                for y in range(y0, min(y0 + 20, h)):
                    corner_pixels.append(small.getpixel((x, y)))
        bg = tuple(int(sum(c) / len(corner_pixels)) for c in zip(*corner_pixels))

        gray_vals = [int(sum(p) / 3) for p in pixels]
        dark_ratio = sum(1 for v in gray_vals if v < 170) / len(gray_vals)

        colorfulness = sum(max(p) - min(p) for p in pixels) / len(pixels)
        lightness = sum(gray_vals) / len(gray_vals)

    return {
        "background": "#{:02X}{:02X}{:02X}".format(*bg),
        "primary_accent": "#007ACC",   # default; feature extractor will refine
        "dark_ratio": dark_ratio,
        "colorfulness": colorfulness,
        "lightness": lightness,
    }


def _density(dark_ratio: float, colorfulness: float) -> str:
    if dark_ratio > 0.33 or colorfulness > 0.29:  return "high"
    if dark_ratio > 0.15 or colorfulness > 0.16:  return "medium"
    return "low"


def _classify(filename: str, m: dict) -> dict:
    """Heuristic classification identical to draft_labeler logic."""
    company = _source_company(filename)
    density = _density(m["dark_ratio"], m["colorfulness"])
    lc      = m["lightness"]
    color   = m["colorfulness"]

    # Bain / consulting firms
    quality = 5 if company == "Roland Berger" else 4
    if company in ("Bain", "Deloitte", "McKinsey"):
        quality = 4
    elif company not in ("Roland Berger", "BCG", "Accenture"):
        quality = 3

    if lc < 100:
        layout, chart, purpose, cols = "section_divider", "none", "transition", 1
    elif density == "high" and color < 20:
        layout, chart, purpose, cols = "three_col_text", "none", "framing_context", 2
    elif density in ("medium", "high") and color > 25:
        layout, chart, purpose, cols = "two_col_chart", "bar",  "data_evidence",   2
    elif color > 35:
        layout, chart, purpose, cols = "mixed_layout",  "mixed","framing_context",  2
    else:
        layout, chart, purpose, cols = "exec_summary",  "none", "executive_summary",1

    return {
        "slide_filename": filename,
        "layout_type": layout,
        "chart_type": chart,
        "text_density": density,
        "has_icons_illustrations": color > 28,
        "has_data_callouts": chart != "none",
        "column_count": cols,
        "color_palette": {
            "primary_accent": m["primary_accent"],
            "background":     m["background"],
        },
        "headline_present": layout != "appendix",
        "source_company": company,
        "slide_purpose": purpose,
        "estimated_quality_score": quality,
    }


# ── load existing dataset ─────────────────────────────────────────────────────

def load_dataset() -> list[dict]:
    if not DATASET_FILE.exists():
        return []
    raw = json.loads(DATASET_FILE.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else raw.get("slides", [])


def write_dataset(slides: list[dict]) -> None:
    source_counts = Counter(
        (slide.get("label") or {}).get("source_company", "Unknown")
        for slide in slides
    )
    total_pngs = len(list(SLIDES_DIR.glob("*.png")))
    dataset = {
        "metadata": {
            "total_slides": total_pngs,
            "labeled_slides": len(slides),
            "unlabeled_slides": max(0, total_pngs - len(slides)),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "label_schema_version": "1.0",
            "sources": sorted(source_counts),
            "source_counts": dict(sorted(source_counts.items())),
            "labeling_mode": "heuristic_auto_label",
        },
        "slides": slides,
    }
    DATASET_FILE.write_text(json.dumps(dataset, indent=2), encoding="utf-8")


def load_fidelity() -> list[dict]:
    if not FIDELITY_JSON.exists():
        return []
    raw = json.loads(FIDELITY_JSON.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


# ── main ingestion ────────────────────────────────────────────────────────────

def ingest_labels(limit: int = 0) -> list[dict]:
    """Auto-label new PNGs and append to dataset.json. Returns new slide entries."""
    existing = {s["slide_id"] for s in load_dataset()}
    all_pngs = sorted(SLIDES_DIR.glob("*.png"))

    new_pngs = [p for p in all_pngs if p.stem not in existing]
    if limit > 0:
        new_pngs = new_pngs[:limit]

    if not new_pngs:
        print("  No new slides to label.")
        return []

    print(f"  Auto-labeling {len(new_pngs)} new slides ...")
    new_entries = []
    for i, png in enumerate(new_pngs, 1):
        try:
            m    = _image_heuristics(png)
            lbl  = _classify(png.name, m)
            entry = {
                "slide_id":   png.stem,
                "image_path": f"slides/{png.name}",
                "label":      lbl,
            }
            new_entries.append(entry)
        except Exception as exc:
            print(f"    [warn] {png.name}: {exc}")
        if i % 100 == 0:
            print(f"    ... {i}/{len(new_pngs)}")

    # Append to dataset.json
    existing_entries = load_dataset()
    merged = existing_entries + new_entries
    write_dataset(merged)
    print(f"  dataset.json: {len(existing_entries)} + {len(new_entries)} = {len(merged)} total")
    return new_entries


def run_feature_extraction(new_entries: list[dict]) -> None:
    """Run extract_fidelity_features.py on ALL slides (appends new ones to summary)."""
    print(f"\n  Running feature extraction on {len(new_entries)} new slides ...")

    # Import extract_one directly and append results to fidelity_summary.json
    import sys
    sys.path.insert(0, str(BASE_DIR / "prototypes"))
    from extract_fidelity_features import extract_one

    existing_fidelity = load_fidelity()
    existing_ids = {f["slide_id"] for f in existing_fidelity}

    new_fidelity = []
    for i, slide in enumerate(new_entries, 1):
        if slide["slide_id"] in existing_ids:
            continue
        try:
            result = extract_one(slide)
            new_fidelity.append(result)
        except Exception as exc:
            print(f"    [warn] {slide['slide_id']}: {exc}")
        if i % 50 == 0:
            print(f"    ... {i}/{len(new_entries)} extracted")

    merged = existing_fidelity + new_fidelity
    FIDELITY_JSON.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"  fidelity_summary.json: {len(existing_fidelity)} + {len(new_fidelity)} = {len(merged)} total")


def rebuild_index() -> None:
    print("\n  Rebuilding retrieval index ...")
    from retrieval import build_index
    idx = build_index()
    print(f"  Index rebuilt: {len(idx)} entries")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest new slide PNGs into the full pipeline")
    parser.add_argument("--label-only",    action="store_true")
    parser.add_argument("--features-only", action="store_true")
    parser.add_argument("--limit",         type=int, default=0)
    args = parser.parse_args()

    if not args.features_only:
        print("Step 1: Auto-labeling new slides ...")
        new_entries = ingest_labels(args.limit)
        if not new_entries:
            print("Nothing new — exiting.")
            return
    else:
        print("Step 1: Skipped (--features-only)")
        # Load all entries not yet in fidelity_summary.json
        all_slides = load_dataset()
        fid_ids    = {f["slide_id"] for f in load_fidelity()}
        new_entries = [s for s in all_slides if s["slide_id"] not in fid_ids]
        print(f"  Found {len(new_entries)} slides missing fidelity features")

    if args.label_only:
        print("Stopping after label step (--label-only)")
        return

    print("\nStep 2: Feature extraction ...")
    run_feature_extraction(new_entries)

    print("\nStep 3: Rebuilding retrieval index ...")
    rebuild_index()

    print("\nAll done. New slides are live in the retrieval system.")


if __name__ == "__main__":
    main()
