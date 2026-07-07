"""
build_finetune_dataset.py — Package HTML slides as fine-tuning pairs.

Reads dataset.json + html_slides/, excludes collapsed/severe-overflow slides
from the latest audit, and writes JSONL in OpenAI chat fine-tuning format.

Output
------
  finetune_train.jsonl   — 90% of usable pairs (shuffled)
  finetune_val.jsonl     — 10% of usable pairs
  finetune_stats.json    — counts and excluded slide list

Usage
-----
    python build_finetune_dataset.py
    python build_finetune_dataset.py --split 0.85   # custom train ratio
    python build_finetune_dataset.py --dry-run      # stats only, no files written
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

ROOT     = Path(__file__).parent.parent
DATASET  = Path(__file__).parent / "dataset.json"
HTML_DIR = ROOT / "html_slides"
REPORT   = ROOT / "audit_layout_report.json"
QUALITY  = Path(__file__).parent / "quality_exclusions.json"  # from validate_dataset.py
OUT_DIR  = Path(__file__).parent / "finetune"

VIEWPORT_W, VIEWPORT_H = 1280, 720

SYSTEM_PROMPT = f"""You are an expert front-end developer who creates self-contained HTML/CSS presentation slides.

STRICT REQUIREMENTS — every file must satisfy all of these:
1. Start with <!DOCTYPE html>
2. Include all CSS inside a <style> block in <head> — no external stylesheets
3. The slide root element must be exactly {VIEWPORT_W}px wide and {VIEWPORT_H}px tall
4. The slide root must have: position: relative; overflow: hidden;
5. Use absolute positioning for all child elements to faithfully replicate the layout
6. NO <script> tags
7. NO <img> tags — recreate images/icons with CSS shapes, gradients, or Unicode characters
8. NO external URLs (no http:// or https:// anywhere)
9. Use only web-safe or system fonts
10. Output ONLY the complete HTML document — no explanation, no markdown fences"""


def build_prompt(slide: dict) -> str:
    lbl      = slide.get("label", {})
    palette  = lbl.get("color_palette", {})
    company  = lbl.get("source_company", "Unknown")
    layout   = lbl.get("layout_type", "unknown")
    chart    = lbl.get("chart_type", "none")
    purpose  = lbl.get("slide_purpose", "unknown")
    density  = lbl.get("text_density", "medium")
    columns  = lbl.get("column_count", 1)
    icons    = lbl.get("has_icons_illustrations", False)
    callouts = lbl.get("has_data_callouts", False)
    bg       = palette.get("background", "#ffffff")
    accent   = palette.get("primary_accent", "#000000")

    parts = [
        f"Create a {VIEWPORT_W}×{VIEWPORT_H}px HTML/CSS presentation slide.",
        f"Style: {company}.",
        f"Layout: {layout}" + (f", {columns} columns" if columns > 1 else "") + ".",
    ]

    if chart and chart.lower() not in ("none", "unknown", ""):
        parts.append(f"Chart type: {chart}.")

    parts.append(f"Slide purpose: {purpose}.")
    parts.append(f"Text density: {density}.")

    if icons:
        parts.append("Include icons or illustrations (use CSS shapes, not images).")
    if callouts:
        parts.append("Include data callout boxes with key statistics.")

    parts.append(f"Background color: {bg}.")
    parts.append(f"Primary accent color: {accent}.")

    return " ".join(parts)


def get_excluded(report: dict) -> set[str]:
    excluded = set()
    for s in report["slides"]:
        issues = s["issues"]
        is_collapsed = any(i.startswith("collapsed") for i in issues)
        is_severe = False
        for i in issues:
            if i.startswith("overflow"):
                m_r = re.search(r"right=(\d+)", i)
                m_b = re.search(r"bot=(\d+)", i)
                worst_r = int(m_r.group(1)) if m_r else 0
                worst_b = int(m_b.group(1)) if m_b else 0
                if worst_r >= 1380 or worst_b >= 780:
                    is_severe = True
        if is_collapsed or is_severe:
            excluded.add(s["slide_id"])
    return excluded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", type=float, default=0.9,
                        help="Train split ratio (default 0.9)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(DATASET, encoding="utf-8") as f:
        all_slides = json.load(f)["slides"]

    # Legacy audit exclusions (collapsed/severe overflow from old audit tool)
    excluded = set()
    if REPORT.exists():
        with open(REPORT, encoding="utf-8") as f:
            report = json.load(f)
        excluded = get_excluded(report)

    # Layout-validation exclusions from validate_dataset.py (takes priority)
    if QUALITY.exists():
        with open(QUALITY, encoding="utf-8") as f:
            q = json.load(f)
        quality_excluded = set(q.get("excluded_slide_ids", []))
        excluded = excluded | quality_excluded
        print(f"Quality gate: {len(quality_excluded)} slides excluded by validate_dataset.py")
    meta = {s["slide_id"]: s for s in all_slides}

    pairs = []
    skipped_no_html = []
    skipped_truncated = []
    skipped_audit = list(excluded)

    for html_path in sorted(HTML_DIR.glob("*.html")):
        sid = html_path.stem
        if sid not in meta:
            continue
        if sid in excluded:
            continue

        html = html_path.read_text(encoding="utf-8", errors="ignore")
        if "</html>" not in html.lower():
            skipped_truncated.append(sid)
            continue

        prompt = build_prompt(meta[sid])
        pairs.append({
            "messages": [
                {"role": "system",  "content": SYSTEM_PROMPT},
                {"role": "user",    "content": prompt},
                {"role": "assistant", "content": html},
            ]
        })

    random.seed(args.seed)
    random.shuffle(pairs)

    n_train = int(len(pairs) * args.split)
    train   = pairs[:n_train]
    val     = pairs[n_train:]

    stats = {
        "total_pairs":      len(pairs),
        "train":            len(train),
        "val":              len(val),
        "excluded_audit":   len(skipped_audit),
        "excluded_truncated": len(skipped_truncated),
        "excluded_no_html": len(skipped_no_html),
        "train_ratio":      args.split,
        "excluded_slide_ids": sorted(skipped_audit),
    }

    print(f"Total usable pairs : {len(pairs)}")
    print(f"  Train            : {len(train)}")
    print(f"  Val              : {len(val)}")
    print(f"Excluded (audit)   : {len(skipped_audit)}  (collapsed + severe overflow)")
    print(f"Excluded (truncated): {len(skipped_truncated)}")

    if args.dry_run:
        print("\nDRY RUN — no files written.")
        return

    OUT_DIR.mkdir(exist_ok=True)

    train_path = OUT_DIR / "finetune_train.jsonl"
    val_path   = OUT_DIR / "finetune_val.jsonl"
    stats_path = OUT_DIR / "finetune_stats.json"

    with open(train_path, "w", encoding="utf-8") as f:
        for p in train:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for p in val:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\nWritten to: {OUT_DIR}")
    print(f"  {train_path.name}  ({train_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  {val_path.name}    ({val_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  {stats_path.name}")


if __name__ == "__main__":
    main()
