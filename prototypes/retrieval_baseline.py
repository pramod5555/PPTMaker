from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageStat

from common import BASE_DIR, OUTPUT_DIR, deck_id, ensure_output_dir, hex_to_hsv, load_dataset, slide_path


CATEGORY_WEIGHTS = {
    "layout_type": 2.0,
    "chart_type": 1.3,
    "text_density": 0.9,
    "slide_purpose": 1.2,
    "source_company": 0.5,
}


def image_features(path: Path) -> dict[str, float]:
    with Image.open(path).convert("RGB") as img:
        small = img.resize((160, 90))
        gray = small.convert("L")
        stat = ImageStat.Stat(gray)
        w, h = small.size
        pixels = list(small.getdata())
        dark_ratio = sum(1 for value in gray.getdata() if value < 170) / (w * h)
        edge = gray.filter(ImageFilter.FIND_EDGES)
        edge_ratio = sum(1 for value in edge.getdata() if value > 35) / (w * h)
        colorfulness = sum(max(p) - min(p) for p in pixels) / len(pixels) / 255
        return {
            "brightness": stat.mean[0] / 255,
            "contrast": stat.stddev[0] / 128,
            "dark_ratio": dark_ratio,
            "edge_ratio": edge_ratio,
            "colorfulness": colorfulness,
        }


def slide_features(slide: dict[str, Any]) -> dict[str, Any]:
    label = slide["label"]
    palette = label.get("color_palette", {})
    accent_h, accent_s, accent_v = hex_to_hsv(palette.get("primary_accent", "#000000"))
    bg_h, bg_s, bg_v = hex_to_hsv(palette.get("background", "#FFFFFF"))
    image = image_features(slide_path(slide))

    numeric = {
        **image,
        "column_count": float(label.get("column_count", 0)) / 4,
        "quality": float(label.get("estimated_quality_score", 0)) / 5,
        "has_icons": 1.0 if label.get("has_icons_illustrations") else 0.0,
        "has_data_callouts": 1.0 if label.get("has_data_callouts") else 0.0,
        "headline_present": 1.0 if label.get("headline_present") else 0.0,
        "accent_h": accent_h,
        "accent_s": accent_s,
        "accent_v": accent_v,
        "bg_h": bg_h,
        "bg_s": bg_s,
        "bg_v": bg_v,
    }
    categories = {key: label.get(key, "unknown") for key in CATEGORY_WEIGHTS}
    return {
        "slide_id": slide["slide_id"],
        "image_path": slide["image_path"],
        "deck_id": deck_id(slide["slide_id"]),
        "label": label,
        "numeric": numeric,
        "categories": categories,
    }


def distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    total = 0.0
    for key, av in a["numeric"].items():
        bv = b["numeric"].get(key, 0.0)
        total += (av - bv) ** 2
    for key, weight in CATEGORY_WEIGHTS.items():
        if a["categories"].get(key) != b["categories"].get(key):
            total += weight
    return math.sqrt(total)


def build_index() -> list[dict[str, Any]]:
    dataset = load_dataset()
    return [slide_features(slide) for slide in dataset.get("slides", [])]


def write_index(index: list[dict[str, Any]]) -> Path:
    out_dir = ensure_output_dir()
    path = out_dir / "feature_index.json"
    path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return path


def find_query(index: list[dict[str, Any]], query: str) -> dict[str, Any]:
    for item in index:
        if item["slide_id"] == query or Path(item["image_path"]).stem == query:
            return item
    raise SystemExit(f"Query slide not found in dataset: {query}")


def render_html(query_item: dict[str, Any], results: list[tuple[float, dict[str, Any]]]) -> Path:
    out_dir = ensure_output_dir()
    out_path = out_dir / f"retrieval_results_{query_item['slide_id']}.html"

    def card(item: dict[str, Any], score: float | None = None) -> str:
        label = item["label"]
        image_src = "../" + item["image_path"].replace("\\", "/")
        score_text = "" if score is None else f"<div class='score'>distance {score:.3f}</div>"
        return f"""
        <section class="card">
          <img src="{html.escape(image_src)}" alt="{html.escape(item['slide_id'])}">
          <h3>{html.escape(item['slide_id'])}</h3>
          {score_text}
          <p>{html.escape(label.get('layout_type', ''))} / {html.escape(label.get('chart_type', ''))}</p>
          <p>{html.escape(label.get('slide_purpose', ''))} / {html.escape(label.get('text_density', ''))}</p>
          <p>{html.escape(label.get('source_company', ''))}</p>
        </section>
        """

    html_text = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Retrieval Baseline - {html.escape(query_item['slide_id'])}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7f7; color: #111; }}
    h1, h2 {{ margin-bottom: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }}
    .card {{ background: #fff; border: 1px solid #ddd; padding: 12px; border-radius: 6px; }}
    img {{ width: 100%; height: auto; border: 1px solid #eee; background: white; }}
    h3 {{ font-size: 13px; overflow-wrap: anywhere; }}
    p, .score {{ margin: 4px 0; font-size: 12px; }}
    .score {{ font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Retrieval Baseline</h1>
  <h2>Query</h2>
  <div class="grid">{card(query_item)}</div>
  <h2>Nearest Slides</h2>
  <div class="grid">{''.join(card(item, score) for score, item in results)}</div>
</body>
</html>
"""
    out_path.write_text(html_text, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a simple slide retrieval baseline.")
    parser.add_argument("--query", required=True, help="slide_id to search from")
    parser.add_argument("--top-k", type=int, default=8)
    args = parser.parse_args()

    index = build_index()
    index_path = write_index(index)
    query_item = find_query(index, args.query)
    results = [
        (distance(query_item, item), item)
        for item in index
        if item["slide_id"] != query_item["slide_id"]
    ]
    results.sort(key=lambda pair: pair[0])
    top = results[: args.top_k]

    html_path = render_html(query_item, top)

    print(f"Wrote {index_path}")
    print(f"Wrote {html_path}")
    print(f"Query: {query_item['slide_id']}")
    for score, item in top:
        label = item["label"]
        print(
            f"{score:.3f}  {item['slide_id']}  "
            f"{label.get('layout_type')} / {label.get('chart_type')} / {label.get('slide_purpose')}"
        )


if __name__ == "__main__":
    main()
