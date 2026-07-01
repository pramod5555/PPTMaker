from __future__ import annotations

import argparse
import json
from pathlib import Path

from retrieval_baseline import build_index, distance, find_query
from common import ensure_output_dir


def compact_slide(item: dict, distance_score: float | None = None) -> dict:
    label = item["label"]
    payload = {
        "slide_id": item["slide_id"],
        "image_path": item["image_path"],
        "layout_type": label.get("layout_type"),
        "chart_type": label.get("chart_type"),
        "text_density": label.get("text_density"),
        "slide_purpose": label.get("slide_purpose"),
        "source_company": label.get("source_company"),
        "column_count": label.get("column_count"),
        "has_icons_illustrations": label.get("has_icons_illustrations"),
        "has_data_callouts": label.get("has_data_callouts"),
        "color_palette": label.get("color_palette"),
        "estimated_quality_score": label.get("estimated_quality_score"),
    }
    if distance_score is not None:
        payload["retrieval_distance"] = round(distance_score, 4)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a compact retrieval context pack for generation prompts."
    )
    parser.add_argument("--query", required=True, help="slide_id to use as the target style/query")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    index = build_index()
    query = find_query(index, args.query)
    results = [(distance(query, item), item) for item in index if item["slide_id"] != query["slide_id"]]
    results.sort(key=lambda pair: pair[0])

    pack = {
        "task": "Use these retrieved consulting-slide examples as style/layout references for PPT generation.",
        "query_slide": compact_slide(query),
        "nearest_examples": [compact_slide(item, score) for score, item in results[: args.top_k]],
        "generation_notes": [
            "Prefer layouts and visual hierarchy from nearest_examples.",
            "Use color_palette as a style cue, not as a mandatory exact palette.",
            "Do not copy proprietary text; use structure, density, chart style, and composition as references.",
        ],
    }

    out_dir = ensure_output_dir()
    out_path = out_dir / f"prompt_pack_{query['slide_id']}.json"
    out_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(json.dumps(pack, indent=2)[:1800])


if __name__ == "__main__":
    main()
