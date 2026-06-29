"""
draft_labeler.py - Generate assisted draft labels for selected batch folders.

This is a fallback when browser-based labeling is unavailable. It creates
Claude-compatible batches/batch_XXX/response.json files using filename and
image heuristics. Treat the output as draft labels: useful for pipeline work,
but lower confidence than human-reviewed visual labels.

Usage:
  python draft_labeler.py --priority roland
  python draft_labeler.py --start 37 --end 69
"""

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

BASE_DIR = Path(__file__).parent
BATCHES_DIR = BASE_DIR / "batches"
SLIDES_DIR = BASE_DIR / "slides"


def page_number(filename: str) -> int:
    match = re.search(r"_slide_(\d{3})\.png$", filename)
    return int(match.group(1)) if match else 0


def source_company(filename: str) -> str:
    lower = filename.lower()
    if lower.startswith("roland_berger"):
        return "Roland Berger"
    if lower.startswith("bcg"):
        return "BCG"
    if lower.startswith("mckinsey"):
        return "McKinsey"
    if lower.startswith("bain"):
        return "Bain"
    if lower.startswith("wef"):
        return "WEF"
    if lower.startswith("deloitte"):
        return "Deloitte"
    if lower.startswith("worldbank"):
        return "World Bank"
    if lower.startswith("imf"):
        return "IMF"
    if lower.startswith("accenture"):
        return "Accenture"
    if lower.startswith("oliver_wyman"):
        return "Oliver Wyman"
    if lower.startswith("strategy_and"):
        return "Strategy&"
    if lower.startswith("kpmg"):
        return "KPMG"
    if lower.startswith("pwc"):
        return "PwC"
    if lower.startswith("kearney"):
        return "Kearney"
    if lower.startswith("trend_compendium"):
        return "Roland Berger"
    return "Unknown"


def hex_color(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def image_metrics(path: Path) -> dict[str, float | str]:
    with Image.open(path).convert("RGB") as img:
        small = img.resize((160, 90))
        pixels = list(small.getdata())

        # Page backgrounds are usually visible in the corners.
        w, h = small.size
        corner_pixels = []
        for x0, y0 in ((0, 0), (w - 20, 0), (0, h - 20), (w - 20, h - 20)):
            for x in range(x0, min(x0 + 20, w)):
                for y in range(y0, min(y0 + 20, h)):
                    corner_pixels.append(small.getpixel((x, y)))
        bg = tuple(int(sum(channel) / len(corner_pixels)) for channel in zip(*corner_pixels))

        # Accent: pick saturated, non-background pixels and average the strongest set.
        saturated = []
        for r, g, b in pixels:
            mx, mn = max(r, g, b), min(r, g, b)
            if mx - mn > 45 and abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 70:
                saturated.append((r, g, b, mx - mn))
        saturated.sort(key=lambda p: p[3], reverse=True)
        if saturated:
            top = saturated[: max(20, len(saturated) // 8)]
            accent = tuple(int(sum(p[i] for p in top) / len(top)) for i in range(3))
        else:
            accent = (0, 122, 135)

        gray = small.convert("L")
        stat = ImageStat.Stat(gray)
        mean_lightness = stat.mean[0]
        dark_ratio = sum(1 for value in gray.getdata() if value < 170) / (w * h)

        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_ratio = sum(1 for value in edges.getdata() if value > 35) / (w * h)

        colorfulness = sum(max(p) - min(p) for p in pixels) / len(pixels)

    return {
        "background": hex_color(bg),
        "primary_accent": hex_color(accent),
        "mean_lightness": mean_lightness,
        "dark_ratio": dark_ratio,
        "edge_ratio": edge_ratio,
        "colorfulness": colorfulness,
    }


def text_density(metrics: dict[str, float | str]) -> str:
    dark_ratio = float(metrics["dark_ratio"])
    edge_ratio = float(metrics["edge_ratio"])
    if dark_ratio > 0.33 or edge_ratio > 0.29:
        return "high"
    if dark_ratio > 0.15 or edge_ratio > 0.16:
        return "medium"
    return "low"


def roland_layout(filename: str, metrics: dict[str, float | str]) -> tuple[str, str, str, int]:
    page = page_number(filename)
    lower = filename.lower()
    density = text_density(metrics)
    dark_ratio = float(metrics["dark_ratio"])
    colorfulness = float(metrics["colorfulness"])
    lightness = float(metrics["mean_lightness"])

    if page == 1 or page == 82:
        return "title_slide", "none", "framing_context", 1

    if "cop_vdma" in lower:
        if page in {3, 30, 31, 32}:
            return "appendix", "none", "reference", 1
        if page in {4, 8}:
            return "section_divider", "none", "transition", 1
        if page == 7:
            return "exec_summary", "none", "executive_summary", 2
        if lightness < 190 and colorfulness > 35 and density in {"low", "medium"}:
            return "section_divider", "none", "transition", 1
        if page in {6, 9, 10, 11, 14, 15, 16, 19, 21, 22, 24, 26, 28, 29}:
            return "two_col_chart", "bar", "data_evidence", 2
        if density == "high":
            return "three_col_text", "none", "framing_context", 2
        return "mixed_layout", "mixed", "framing_context", 2

    if "2030" in lower:
        if page in {2, 3}:
            return "appendix" if page == 2 else "mixed_layout", "none", "reference", 1
        if page in {4, 5, 7, 8, 14, 20, 26, 32, 38, 44}:
            return "icon_grid", "none", "framing_context", 4
        if page in {6, 9, 15, 21, 27, 33, 39, 45}:
            return "process_flow_timeline", "none", "process_explanation", 3
        if page in {10, 16, 22, 28, 34, 40, 46}:
            return "comparison_table", "none", "data_evidence", 4
        if page >= 47:
            return "appendix", "none", "reference", 1
        if density == "high":
            return "three_col_text", "none", "framing_context", 3
        return "mixed_layout", "mixed", "framing_context", 2

    if "2050" in lower:
        if page in {2, 3, 79, 80, 81}:
            return "appendix", "none", "reference", 1
        if page == 4:
            return "section_divider", "none", "transition", 1
        if page in {8, 9, 11, 15, 16, 20, 53}:
            return "scatter_bubble_chart", "scatter", "data_evidence", 2
        if page in {21, 22, 33, 43, 44, 46, 50, 56, 61}:
            return "full_width_chart", "line", "data_evidence", 2
        if page in {10, 24, 25, 27, 32, 34, 36, 39, 40, 52, 54}:
            return "two_col_chart", "pie", "data_evidence", 2
        if page in {12, 13, 14, 19, 23, 26, 35, 37, 41, 45, 55, 59, 60, 62, 63}:
            return "two_col_chart", "bar", "data_evidence", 2
        if page in {7, 28, 42, 48, 49, 51, 57, 58}:
            return "comparison_table", "none", "data_evidence", 4
        if page in {5, 6, 17, 18, 29, 30, 31, 38, 47}:
            return "process_flow_timeline", "mixed", "process_explanation", 3
        if dark_ratio > 0.28:
            return "three_col_text", "none", "framing_context", 3
        return "mixed_layout", "mixed", "framing_context", 2

    return "mixed_layout", "mixed", "framing_context", 2


def generic_layout(filename: str, metrics: dict[str, float | str]) -> tuple[str, str, str, int]:
    page = page_number(filename)
    company = source_company(filename)
    density = text_density(metrics)
    dark_ratio = float(metrics["dark_ratio"])
    edge_ratio = float(metrics["edge_ratio"])
    colorfulness = float(metrics["colorfulness"])

    if page == 1:
        return "title_slide", "none", "framing_context", 1

    if company in {"BCG", "Accenture", "Bain", "Deloitte", "McKinsey"}:
        if page in {2, 3} and density in {"medium", "high"}:
            return "exec_summary", "none", "executive_summary", 2
        if edge_ratio > 0.23 and colorfulness > 20:
            return "mixed_layout", "mixed", "data_evidence", 2
        if dark_ratio > 0.24:
            return "three_col_text", "none", "framing_context", 2
        if colorfulness > 35:
            return "icon_grid", "none", "framing_context", 3
        return "mixed_layout", "mixed", "framing_context", 2

    if company == "IMF":
        if page in {2, 3} and density == "high":
            return "three_col_text", "none", "framing_context", 2
        if edge_ratio > 0.25 or (dark_ratio > 0.18 and colorfulness > 18):
            if colorfulness > 32:
                return "two_col_chart", "mixed", "data_evidence", 2
            return "full_width_chart", "line", "data_evidence", 1
        if dark_ratio > 0.30:
            return "comparison_table", "none", "data_evidence", 4
        if density == "high":
            return "three_col_text", "none", "framing_context", 2
        return "mixed_layout", "mixed", "framing_context", 2

    if density == "high":
        return "three_col_text", "none", "framing_context", 2
    if edge_ratio > 0.22:
        return "two_col_chart", "mixed", "data_evidence", 2
    return "mixed_layout", "mixed", "data_evidence", 2


def draft_label(slide_path: Path) -> dict:
    filename = slide_path.name
    metrics = image_metrics(slide_path)
    company = source_company(filename)

    if company == "Roland Berger":
        layout, chart, purpose, columns = roland_layout(filename, metrics)
    else:
        layout, chart, purpose, columns = generic_layout(filename, metrics)

    density = text_density(metrics)
    has_data_callouts = chart != "none" or layout in {
        "comparison_table",
        "two_col_chart",
        "full_width_chart",
        "scatter_bubble_chart",
    }
    has_icons = layout in {
        "icon_grid",
        "process_flow_timeline",
        "mixed_layout",
        "section_divider",
        "title_slide",
    } or float(metrics["colorfulness"]) > 28
    headline_present = layout != "appendix" or density != "high"

    quality = 5 if company == "Roland Berger" and layout != "appendix" else 4
    if company not in {"Roland Berger", "BCG", "Bain", "McKinsey", "Deloitte", "WEF"}:
        quality = 3

    return {
        "slide_filename": filename,
        "layout_type": layout,
        "chart_type": chart,
        "text_density": density,
        "has_icons_illustrations": bool(has_icons),
        "has_data_callouts": bool(has_data_callouts),
        "column_count": columns,
        "color_palette": {
            "primary_accent": str(metrics["primary_accent"]),
            "background": str(metrics["background"]),
        },
        "headline_present": bool(headline_present),
        "source_company": company,
        "slide_purpose": purpose,
        "estimated_quality_score": quality,
    }


def batch_has_roland(batch_dir: Path) -> bool:
    return any(p.name.lower().startswith("roland_berger") for p in batch_dir.glob("*.png"))


def selected_batches(args: argparse.Namespace) -> list[Path]:
    batches = sorted([p for p in BATCHES_DIR.glob("batch_*") if p.is_dir()])
    if args.priority == "roland":
        return [p for p in batches if batch_has_roland(p)]
    if args.priority == "consulting":
        return [
            p
            for p in batches
            if any(
                source_company(slide.name)
                in {"BCG", "Accenture", "Bain", "Deloitte", "McKinsey", "Oliver Wyman", "Strategy&"}
                for slide in p.glob("*.png")
            )
        ]
    if args.start is not None and args.end is not None:
        wanted = {f"batch_{i:03d}" for i in range(args.start, args.end + 1)}
        return [p for p in batches if p.name in wanted]
    raise SystemExit("Use --priority roland, --priority consulting, or both --start and --end.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate draft labels for selected batches.")
    parser.add_argument(
        "--priority",
        choices=["roland", "consulting"],
        help="Generate labels for priority group.",
    )
    parser.add_argument("--start", type=int, help="First batch number.")
    parser.add_argument("--end", type=int, help="Last batch number.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing response.json files for selected batches.",
    )
    args = parser.parse_args()

    batches = selected_batches(args)
    labels_written = 0
    responses_written = 0

    for batch_dir in batches:
        response_path = batch_dir / "response.json"
        if response_path.exists() and not args.overwrite:
            print(f"Skip existing response: {response_path}")
            continue

        labels = []
        for png in sorted(batch_dir.glob("*.png"), key=lambda p: p.name):
            labels.append(draft_label(SLIDES_DIR / png.name))

        response_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")
        labels_written += len(labels)
        responses_written += 1
        print(f"Wrote {response_path} ({len(labels)} labels)")

    print(f"\nResponses written : {responses_written}")
    print(f"Labels drafted    : {labels_written}")


if __name__ == "__main__":
    main()
