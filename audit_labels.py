"""
audit_labels.py - Audit generated slide labels for consistency and risk.

Usage:
  python audit_labels.py

Outputs:
  label_audit_report.md
  label_audit_flags.csv
"""

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from draft_labeler import image_metrics, page_number

BASE_DIR = Path(__file__).parent
LABELS_DIR = BASE_DIR / "labels"
SLIDES_DIR = BASE_DIR / "slides"
REPORT_FILE = BASE_DIR / "label_audit_report.md"
FLAGS_FILE = BASE_DIR / "label_audit_flags.csv"


def deck_id(filename: str) -> str:
    return re.sub(r"_slide_\d{3}\.png$", "", filename)


def risk_for_label(label: dict, metrics: dict[str, float | str]) -> tuple[int, list[str]]:
    flags: list[str] = []
    risk = 0

    filename = label.get("slide_filename", "")
    page = page_number(filename)
    layout = label.get("layout_type")
    chart = label.get("chart_type")
    density = label.get("text_density")
    purpose = label.get("slide_purpose")
    source = label.get("source_company")
    columns = label.get("column_count")
    quality = label.get("estimated_quality_score")
    dark_ratio = float(metrics["dark_ratio"])
    edge_ratio = float(metrics["edge_ratio"])
    colorfulness = float(metrics["colorfulness"])

    if source == "Roland Berger" and not filename.startswith("roland_berger"):
        flags.append("source_company_filename_mismatch")
        risk += 3

    if source != "Roland Berger" and filename.startswith("roland_berger"):
        flags.append("roland_filename_not_roland_source")
        risk += 3

    if layout == "title_slide" and page not in {1, 82}:
        flags.append("title_slide_unusual_page")
        risk += 2

    if layout == "appendix" and purpose != "reference":
        flags.append("appendix_not_reference")
        risk += 2

    if purpose == "transition" and layout != "section_divider":
        flags.append("transition_not_section_divider")
        risk += 2

    if chart == "none" and label.get("has_data_callouts") is True and layout not in {
        "comparison_table",
        "scatter_bubble_chart",
        "two_col_chart",
        "full_width_chart",
    }:
        flags.append("data_callouts_without_chart_or_data_layout")
        risk += 1

    if chart != "none" and layout in {"title_slide", "section_divider", "quote_pullout", "appendix"}:
        flags.append("chart_on_non_chart_layout")
        risk += 2

    if layout in {"two_col_chart", "full_width_chart", "scatter_bubble_chart"} and chart == "none":
        flags.append("chart_layout_without_chart_type")
        risk += 2

    if layout == "scatter_bubble_chart" and chart != "scatter":
        flags.append("scatter_layout_without_scatter_chart")
        risk += 2

    if layout == "comparison_table" and columns < 3:
        flags.append("comparison_table_low_columns")
        risk += 1

    if density == "low" and (dark_ratio > 0.22 or edge_ratio > 0.20):
        flags.append("low_density_but_image_busy")
        risk += 2
    elif density == "high" and dark_ratio < 0.12 and edge_ratio < 0.16:
        flags.append("high_density_but_image_sparse")
        risk += 2

    if label.get("has_icons_illustrations") is False and colorfulness > 45 and layout in {
        "mixed_layout",
        "icon_grid",
        "process_flow_timeline",
        "section_divider",
    }:
        flags.append("possibly_missing_icons_or_illustrations")
        risk += 1

    if quality == 5 and layout == "appendix":
        flags.append("appendix_quality_too_high")
        risk += 1

    palette = label.get("color_palette", {})
    for color_key in ("primary_accent", "background"):
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(palette.get(color_key, ""))):
            flags.append(f"invalid_{color_key}_hex")
            risk += 3

    return risk, flags


def main() -> None:
    labels = []
    rows = []
    layout_counts = Counter()
    chart_counts = Counter()
    source_counts = Counter()
    purpose_counts = Counter()
    deck_counts = Counter()
    risk_counts = Counter()
    flags_by_type = Counter()
    risk_by_deck: dict[str, list[int]] = defaultdict(list)

    for label_file in sorted(LABELS_DIR.glob("*.json")):
        label = json.loads(label_file.read_text(encoding="utf-8"))
        filename = label.get("slide_filename", f"{label_file.stem}.png")
        slide_path = SLIDES_DIR / filename
        if not slide_path.exists():
            risk = 5
            flags = ["slide_image_missing"]
            metrics = {
                "dark_ratio": 0.0,
                "edge_ratio": 0.0,
                "colorfulness": 0.0,
                "primary_accent": "",
                "background": "",
            }
        else:
            metrics = image_metrics(slide_path)
            risk, flags = risk_for_label(label, metrics)

        deck = deck_id(filename)
        labels.append(label)
        layout_counts[label.get("layout_type", "unknown")] += 1
        chart_counts[label.get("chart_type", "unknown")] += 1
        source_counts[label.get("source_company", "Unknown")] += 1
        purpose_counts[label.get("slide_purpose", "unknown")] += 1
        deck_counts[deck] += 1
        risk_counts[risk] += 1
        risk_by_deck[deck].append(risk)
        for flag in flags:
            flags_by_type[flag] += 1

        if risk or flags:
            rows.append(
                {
                    "risk": risk,
                    "slide_filename": filename,
                    "deck": deck,
                    "layout_type": label.get("layout_type", ""),
                    "chart_type": label.get("chart_type", ""),
                    "text_density": label.get("text_density", ""),
                    "source_company": label.get("source_company", ""),
                    "slide_purpose": label.get("slide_purpose", ""),
                    "estimated_quality_score": label.get("estimated_quality_score", ""),
                    "flags": ";".join(flags),
                    "dark_ratio": f"{float(metrics['dark_ratio']):.3f}",
                    "edge_ratio": f"{float(metrics['edge_ratio']):.3f}",
                    "colorfulness": f"{float(metrics['colorfulness']):.1f}",
                }
            )

    rows.sort(key=lambda row: (-int(row["risk"]), row["slide_filename"]))

    with FLAGS_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "risk",
                "slide_filename",
                "deck",
                "layout_type",
                "chart_type",
                "text_density",
                "source_company",
                "slide_purpose",
                "estimated_quality_score",
                "flags",
                "dark_ratio",
                "edge_ratio",
                "colorfulness",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    report_lines = [
        "# Label Audit Report",
        "",
        f"Total labels audited: {len(labels)}",
        f"Flagged labels: {len(rows)}",
        f"High-risk labels (risk >= 3): {sum(1 for row in rows if int(row['risk']) >= 3)}",
        "",
        "## Labels by source",
    ]

    for key, count in source_counts.most_common():
        report_lines.append(f"- {key}: {count}")

    report_lines.extend(["", "## Labels by deck"])
    for key, count in deck_counts.most_common():
        avg_risk = sum(risk_by_deck[key]) / len(risk_by_deck[key])
        report_lines.append(f"- {key}: {count} labels, avg risk {avg_risk:.2f}")

    report_lines.extend(["", "## Layout distribution"])
    for key, count in layout_counts.most_common():
        report_lines.append(f"- {key}: {count}")

    report_lines.extend(["", "## Chart distribution"])
    for key, count in chart_counts.most_common():
        report_lines.append(f"- {key}: {count}")

    report_lines.extend(["", "## Purpose distribution"])
    for key, count in purpose_counts.most_common():
        report_lines.append(f"- {key}: {count}")

    report_lines.extend(["", "## Flag types"])
    if flags_by_type:
        for key, count in flags_by_type.most_common():
            report_lines.append(f"- {key}: {count}")
    else:
        report_lines.append("- No flags")

    report_lines.extend(["", "## Highest-risk labels"])
    if rows:
        for row in rows[:25]:
            report_lines.append(
                f"- risk {row['risk']}: {row['slide_filename']} "
                f"({row['layout_type']}, {row['chart_type']}) - {row['flags']}"
            )
    else:
        report_lines.append("- No flagged labels")

    report_lines.extend(
        [
            "",
            "## Audit Notes",
            "- This audit checks consistency and visual heuristics, not human semantic truth.",
            "- High-risk rows should be visually reviewed before treating labels as final.",
            "- `label_audit_flags.csv` contains the complete flag list.",
            "",
        ]
    )

    REPORT_FILE.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Wrote {REPORT_FILE}")
    print(f"Wrote {FLAGS_FILE}")
    print(f"Total labels audited : {len(labels)}")
    print(f"Flagged labels       : {len(rows)}")
    print(f"High-risk labels     : {sum(1 for row in rows if int(row['risk']) >= 3)}")


if __name__ == "__main__":
    main()
