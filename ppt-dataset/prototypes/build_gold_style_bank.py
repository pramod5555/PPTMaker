"""
Build a Roland Berger-weighted gold style bank from fidelity_summary.json.

The gold bank is the curated source for high-fidelity generation. It keeps the
best structural anchors and avoids letting the larger Deloitte/World Bank/IMF
corpus drown out the consulting-style references.

Usage:
    python prototypes/build_gold_style_bank.py --limit 240
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common import BASE_DIR, ensure_output_dir

SUMMARY_JSON = ensure_output_dir() / "fidelity_summary.json"

SOURCE_WEIGHTS = {
    "Roland Berger": 2.8,
    "BCG": 2.1,
    "Bain": 1.9,
    "Accenture": 1.6,
    "Deloitte": 1.0,
    "World Bank": 0.55,
    "IMF": 0.45,
}

RECIPE_BONUS = {
    "left_nav_rail": 1.0,
    "right_insight_panel": 0.9,
    "scatter_evidence_field": 0.7,
    "bar_chart_field": 0.5,
    "mixed_chart_field": 0.4,
    "title_stack": 0.2,
}


def load_records() -> list[dict[str, Any]]:
    if not SUMMARY_JSON.exists():
        raise FileNotFoundError(f"Missing {SUMMARY_JSON}. Run npm run pipeline:refresh first.")
    return json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))


def score_record(record: dict[str, Any]) -> float:
    label = record.get("label") or {}
    fidelity = record.get("fidelity") or {}
    source = record.get("source_company") or label.get("source_company") or "Unknown"
    recipe = fidelity.get("design_recipe", "")
    quality = float(label.get("estimated_quality_score") or 0)
    anchor = float(fidelity.get("style_anchor_score") or 0)
    whitespace = float(fidelity.get("whitespace_share") or 0)
    has_panel = 1.0 if fidelity.get("has_right_insight_panel") else 0.0
    has_rail = 1.0 if fidelity.get("has_left_nav_rail") else 0.0

    recipe_score = sum(bonus for token, bonus in RECIPE_BONUS.items() if token in recipe)
    source_weight = SOURCE_WEIGHTS.get(source, 0.75)
    whitespace_bonus = 0.6 if 0.18 <= whitespace <= 0.72 else -0.4

    return round(
        source_weight * (quality * 1.4 + anchor * 1.1 + recipe_score)
        + has_panel * 0.7
        + has_rail * 0.5
        + whitespace_bonus,
        4,
    )


def diversify(records: list[dict[str, Any]], limit: int, per_deck: int, per_recipe: int) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    deck_counts: Counter[str] = Counter()
    recipe_counts: Counter[str] = Counter()

    for record in records:
        slide_id = record["slide_id"]
        deck_id = slide_id.rsplit("_slide_", 1)[0]
        recipe = (record.get("fidelity") or {}).get("design_recipe", "unknown")
        if deck_counts[deck_id] >= per_deck:
            continue
        if recipe_counts[recipe] >= per_recipe:
            continue
        chosen.append(record)
        deck_counts[deck_id] += 1
        recipe_counts[recipe] += 1
        if len(chosen) >= limit:
            break
    return chosen


def ensure_source_floor(
    chosen: list[dict[str, Any]],
    ranked: list[dict[str, Any]],
    source: str,
    floor: int,
    limit: int,
) -> list[dict[str, Any]]:
    """Force a minimum number of style-target slides into the bank.

    For Roland Berger fidelity, source purity matters more than deck diversity.
    This swaps out lower-ranked non-target slides until the source floor is met.
    """
    if floor <= 0:
        return chosen

    chosen_ids = {r["slide_id"] for r in chosen}
    current = [r for r in chosen if (r.get("source_company") or "Unknown") == source]
    if len(current) >= floor:
        return chosen

    additions = [
        r for r in ranked
        if (r.get("source_company") or "Unknown") == source and r["slide_id"] not in chosen_ids
    ]
    needed = floor - len(current)
    additions = additions[:needed]
    if not additions:
        return chosen

    protected = {r["slide_id"] for r in current + additions}
    removable = [
        r for r in sorted(chosen, key=lambda x: x["gold_score"])
        if r["slide_id"] not in protected and (r.get("source_company") or "Unknown") != source
    ]
    remove_ids = {r["slide_id"] for r in removable[: len(additions)]}
    merged = [r for r in chosen if r["slide_id"] not in remove_ids] + additions
    merged.sort(key=lambda r: r["gold_score"], reverse=True)
    return merged[:limit]


def row_for(record: dict[str, Any]) -> dict[str, Any]:
    label = record.get("label") or {}
    fid = record.get("fidelity") or {}
    td = fid.get("text_density") or {}
    colors = fid.get("color_tokens") or {}
    dims = fid.get("layout_dims") or {}
    return {
        "slide_id": record["slide_id"],
        "image_path": record["image_path"],
        "source_company": record.get("source_company") or label.get("source_company"),
        "layout_type": label.get("layout_type"),
        "chart_type": label.get("chart_type"),
        "quality": label.get("estimated_quality_score"),
        "gold_score": record["gold_score"],
        "style_anchor_score": fid.get("style_anchor_score"),
        "design_recipe": fid.get("design_recipe"),
        "has_left_nav_rail": fid.get("has_left_nav_rail"),
        "has_right_insight_panel": fid.get("has_right_insight_panel"),
        "whitespace_share": fid.get("whitespace_share"),
        "ink_fraction": td.get("ink_fraction"),
        "text_density": td.get("category"),
        "background": colors.get("background"),
        "rail": colors.get("rail"),
        "accent": colors.get("accent"),
        "panel": colors.get("panel"),
        "content_x": dims.get("content_x"),
        "content_y": dims.get("content_y"),
        "content_w": dims.get("content_w"),
        "content_h": dims.get("content_h"),
    }


def write_outputs(chosen: list[dict[str, Any]]) -> None:
    out_dir = ensure_output_dir()
    json_path = out_dir / "gold_style_bank.json"
    csv_path = out_dir / "gold_style_bank.csv"
    md_path = out_dir / "gold_style_bank_summary.md"

    rows = [row_for(record) for record in chosen]
    json_path.write_text(json.dumps(chosen, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    by_source = Counter(row["source_company"] for row in rows)
    by_recipe = Counter(row["design_recipe"] for row in rows)
    by_chart = Counter(row["chart_type"] for row in rows)

    lines = [
        "# Gold Style Bank",
        "",
        f"Slides selected: {len(rows)}",
        "",
        "## By Source",
    ]
    lines.extend(f"- {k}: {v}" for k, v in by_source.most_common())
    lines.extend(["", "## By Chart Type"])
    lines.extend(f"- {k}: {v}" for k, v in by_chart.most_common())
    lines.extend(["", "## Top Recipes"])
    lines.extend(f"- {k}: {v}" for k, v in by_recipe.most_common(20))

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a consulting-style gold bank.")
    parser.add_argument("--limit", type=int, default=240)
    parser.add_argument("--per-deck", type=int, default=75)
    parser.add_argument("--per-recipe", type=int, default=60)
    parser.add_argument("--roland-floor", type=int, default=120)
    args = parser.parse_args()

    records = load_records()
    for record in records:
        record["gold_score"] = score_record(record)
    ranked = sorted(records, key=lambda r: r["gold_score"], reverse=True)
    chosen = diversify(ranked, args.limit, args.per_deck, args.per_recipe)
    chosen = ensure_source_floor(chosen, ranked, "Roland Berger", args.roland_floor, args.limit)
    write_outputs(chosen)

    print("\nSelected sources:")
    for source, count in Counter((r.get("source_company") or "Unknown") for r in chosen).most_common():
        print(f"  {source:<20} {count}")


if __name__ == "__main__":
    main()
