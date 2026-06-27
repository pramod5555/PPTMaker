from __future__ import annotations

import csv
from collections import Counter

from common import count_by, deck_id, ensure_output_dir, load_dataset


def main() -> None:
    dataset = load_dataset()
    slides = dataset.get("slides", [])
    out_dir = ensure_output_dir()

    manifest_path = out_dir / "manifest.csv"
    fields = [
        "slide_id",
        "deck_id",
        "image_path",
        "layout_type",
        "chart_type",
        "text_density",
        "source_company",
        "slide_purpose",
        "estimated_quality_score",
        "column_count",
        "has_icons_illustrations",
        "has_data_callouts",
        "headline_present",
        "primary_accent",
        "background",
    ]

    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for slide in slides:
            label = slide["label"]
            palette = label.get("color_palette", {})
            writer.writerow(
                {
                    "slide_id": slide["slide_id"],
                    "deck_id": deck_id(slide["slide_id"]),
                    "image_path": slide["image_path"],
                    "layout_type": label.get("layout_type"),
                    "chart_type": label.get("chart_type"),
                    "text_density": label.get("text_density"),
                    "source_company": label.get("source_company"),
                    "slide_purpose": label.get("slide_purpose"),
                    "estimated_quality_score": label.get("estimated_quality_score"),
                    "column_count": label.get("column_count"),
                    "has_icons_illustrations": label.get("has_icons_illustrations"),
                    "has_data_callouts": label.get("has_data_callouts"),
                    "headline_present": label.get("headline_present"),
                    "primary_accent": palette.get("primary_accent"),
                    "background": palette.get("background"),
                }
            )

    deck_counts = Counter(deck_id(slide["slide_id"]) for slide in slides)
    summary_lines = [
        "# Dataset Prototype Summary",
        "",
        f"Slides: {len(slides)}",
        f"Decks: {len(deck_counts)}",
        "",
        "## By Deck",
    ]
    for key, count in deck_counts.most_common():
        summary_lines.append(f"- {key}: {count}")

    for title, key in [
        ("By Layout", "layout_type"),
        ("By Chart Type", "chart_type"),
        ("By Purpose", "slide_purpose"),
        ("By Source", "source_company"),
        ("By Text Density", "text_density"),
    ]:
        summary_lines.extend(["", f"## {title}"])
        for value, count in count_by(slides, key).most_common():
            summary_lines.append(f"- {value}: {count}")

    summary_path = out_dir / "dataset_summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"Wrote {manifest_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
