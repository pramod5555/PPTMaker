from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from common import BASE_DIR

OUT_DIR = BASE_DIR / "fidelity_contact_sheets"
SUMMARY_CSV = BASE_DIR / "prototypes" / "output" / "fidelity_summary.csv"
FIDELITY_DIR = BASE_DIR / "fidelity"

COLORS = {
    "left_rail": "#6B3FA0",
    "title_region": "#111216",
    "subtitle_region": "#6C7480",
    "main_content_region": "#168C9B",
    "right_panel": "#F2A541",
    "footer_region": "#D75A4A",
}


def font(size: int, bold: bool = False):
    for name in (["arialbd.ttf", "arial.ttf"] if bold else ["arial.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def box_from_norm(box: dict[str, float], w: int, h: int) -> tuple[int, int, int, int]:
    return (
        int(box["x"] * w),
        int(box["y"] * h),
        int((box["x"] + box["w"]) * w),
        int((box["y"] + box["h"]) * h),
    )


def draw_regions(draw: ImageDraw.ImageDraw, record: dict[str, Any], scale: float) -> None:
    regions = record["fidelity"]["regions"]
    for name, box in regions.items():
        if not box or name == "vertical_divider":
            continue
        color = COLORS.get(name, "#168C9B")
        x0, y0, x1, y1 = box_from_norm(box, int(record["dimensions"]["width"] * scale), int(record["dimensions"]["height"] * scale))
        draw.rectangle([x0, y0, x1, y1], outline=color, width=3)
        draw.text((x0 + 3, y0 + 3), name.replace("_region", ""), fill=color, font=font(11, True))


def make_cell(record: dict[str, Any]) -> Image.Image:
    src = Image.open(BASE_DIR / record["image_path"]).convert("RGB")
    src.thumbnail((420, 240))
    scale = src.width / record["dimensions"]["width"]
    annotated = src.copy()
    draw = ImageDraw.Draw(annotated)
    draw_regions(draw, record, scale)

    cell = Image.new("RGB", (460, 360), "white")
    cell.paste(annotated, ((460 - annotated.width) // 2, 8))
    d = ImageDraw.Draw(cell)
    y = 260
    d.text((10, y), record["slide_id"][:62], fill=(25, 25, 25), font=font(10))
    d.text((10, y + 25), record["fidelity"]["design_recipe"][:66], fill=(25, 25, 25), font=font(11, True))
    d.text(
        (10, y + 52),
        f"anchor={record['fidelity']['style_anchor_score']} | rail={record['fidelity']['has_left_nav_rail']} | panel={record['fidelity']['has_right_insight_panel']}",
        fill=(55, 55, 55),
        font=font(11),
    )
    d.text(
        (10, y + 78),
        f"{record['label'].get('layout_type')} | {record['label'].get('chart_type')} | q={record['label'].get('estimated_quality_score')}",
        fill=(55, 55, 55),
        font=font(11),
    )
    return cell


def load_records(limit: int, source: str | None) -> list[dict[str, Any]]:
    with SUMMARY_CSV.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if source:
        rows = [r for r in rows if r["source_company"] == source]
    rows = sorted(rows, key=lambda r: float(r["style_anchor_score"]), reverse=True)
    if limit:
        rows = rows[:limit]
    records = []
    for row in rows:
        path = FIDELITY_DIR / f"{row['slide_id']}.json"
        if path.exists():
            records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Create annotated contact sheets for fidelity feature review.")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--source", default="Roland Berger")
    parser.add_argument("--per-sheet", type=int, default=6)
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    records = load_records(args.limit, args.source or None)
    if not records:
        raise SystemExit("No fidelity records found. Run extract_fidelity_features.py first.")

    for sheet_idx in range(0, len(records), args.per_sheet):
        chunk = records[sheet_idx : sheet_idx + args.per_sheet]
        cells = [make_cell(r) for r in chunk]
        sheet = Image.new("RGB", (460 * len(cells), 360), "white")
        for i, cell in enumerate(cells):
            sheet.paste(cell, (i * 460, 0))
        out = OUT_DIR / f"fidelity_sheet_{sheet_idx // args.per_sheet + 1:03d}.jpg"
        sheet.save(out, quality=92)
        print(out)


if __name__ == "__main__":
    main()
