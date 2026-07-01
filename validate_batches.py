"""
validate_batches.py - Check batch folders and Claude response files.

Usage:
  python validate_batches.py

This script is safe to run before or after labeling. Before labeling, it checks
that every batch has PNGs and a prompt.txt. After labeling, it also validates
response.json files against the expected schema and filenames.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

from label_ingest import strip_fences

BASE_DIR = Path(__file__).parent
BATCHES_DIR = BASE_DIR / "batches"
SLIDES_DIR = BASE_DIR / "slides"

BATCH_RE = re.compile(r"batch_\d{3}$")
BATCH_SIZE = 5

LAYOUT_TYPES = {
    "title_slide",
    "section_divider",
    "three_col_text",
    "two_col_chart",
    "full_width_chart",
    "scatter_bubble_chart",
    "process_flow_timeline",
    "comparison_table",
    "icon_grid",
    "exec_summary",
    "quote_pullout",
    "appendix",
    "mixed_layout",
}
CHART_TYPES = {"bar", "line", "scatter", "pie", "waterfall", "mixed", "none"}
TEXT_DENSITIES = {"low", "medium", "high"}
SOURCE_COMPANIES = {
    "Roland Berger",
    "BCG",
    "McKinsey",
    "Bain",
    "WEF",
    "Deloitte",
    "World Bank",
    "ADB",
    "IMF",
    "PwC",
    "OECD",
    "Accenture",
    "Unknown",
}
SLIDE_PURPOSES = {
    "data_evidence",
    "framing_context",
    "recommendation",
    "process_explanation",
    "executive_summary",
    "transition",
    "reference",
}


def list_batches() -> list[Path]:
    return sorted(
        [p for p in BATCHES_DIR.glob("batch_*") if p.is_dir() and BATCH_RE.fullmatch(p.name)]
    )


def expected_filenames(batch_dir: Path) -> list[str]:
    return sorted(p.name for p in batch_dir.glob("*.png"))


def parse_response(path: Path) -> tuple[list[dict] | None, str | None]:
    try:
        raw = strip_fences(path.read_text(encoding="utf-8"))
        data = json.loads(raw)
    except Exception as exc:
        return None, f"could not parse JSON: {exc}"
    if not isinstance(data, list):
        return None, f"expected JSON array, got {type(data).__name__}"
    if not all(isinstance(item, dict) for item in data):
        return None, "every response item must be an object"
    return data, None


def validate_label(obj: dict, batch_dir: Path, expected: set[str]) -> list[str]:
    errors: list[str] = []
    filename = obj.get("slide_filename")

    if filename not in expected:
        errors.append(f"{batch_dir.name}: unexpected slide_filename {filename!r}")
    if obj.get("layout_type") not in LAYOUT_TYPES:
        errors.append(f"{batch_dir.name}/{filename}: invalid layout_type")
    if obj.get("chart_type") not in CHART_TYPES:
        errors.append(f"{batch_dir.name}/{filename}: invalid chart_type")
    if obj.get("text_density") not in TEXT_DENSITIES:
        errors.append(f"{batch_dir.name}/{filename}: invalid text_density")
    if obj.get("source_company") not in SOURCE_COMPANIES:
        errors.append(f"{batch_dir.name}/{filename}: invalid source_company")
    if obj.get("slide_purpose") not in SLIDE_PURPOSES:
        errors.append(f"{batch_dir.name}/{filename}: invalid slide_purpose")

    for bool_key in ("has_icons_illustrations", "has_data_callouts", "headline_present"):
        if not isinstance(obj.get(bool_key), bool):
            errors.append(f"{batch_dir.name}/{filename}: {bool_key} must be boolean")

    column_count = obj.get("column_count")
    if not isinstance(column_count, int) or not 0 <= column_count <= 4:
        errors.append(f"{batch_dir.name}/{filename}: column_count must be integer 0-4")

    quality = obj.get("estimated_quality_score")
    if not isinstance(quality, int) or not 1 <= quality <= 5:
        errors.append(f"{batch_dir.name}/{filename}: estimated_quality_score must be integer 1-5")

    palette = obj.get("color_palette")
    if not isinstance(palette, dict):
        errors.append(f"{batch_dir.name}/{filename}: color_palette must be object")
    else:
        hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for key in ("primary_accent", "background"):
            if not isinstance(palette.get(key), str) or not hex_re.fullmatch(palette[key]):
                errors.append(f"{batch_dir.name}/{filename}: color_palette.{key} must be #RRGGBB")

    return errors


def main() -> int:
    batches = list_batches()
    slide_names = {p.name for p in SLIDES_DIR.glob("*.png")}
    assigned: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    response_status = Counter()

    for idx, batch_dir in enumerate(batches, start=1):
        pngs = expected_filenames(batch_dir)
        assigned.extend(pngs)

        if not pngs:
            errors.append(f"{batch_dir.name}: no PNG files")
        elif len(pngs) != BATCH_SIZE and idx != len(batches):
            warnings.append(f"{batch_dir.name}: has {len(pngs)} PNGs, expected {BATCH_SIZE}")

        missing_from_slides = sorted(set(pngs) - slide_names)
        if missing_from_slides:
            errors.append(f"{batch_dir.name}: PNGs not present in /slides/: {missing_from_slides}")

        prompt_path = batch_dir / "prompt.txt"
        if not prompt_path.exists():
            errors.append(f"{batch_dir.name}: missing prompt.txt")
        else:
            prompt_text = prompt_path.read_text(encoding="utf-8", errors="replace")
            for filename in pngs:
                if filename not in prompt_text:
                    errors.append(f"{batch_dir.name}: prompt.txt missing {filename}")

        response_path = batch_dir / "response.json"
        if not response_path.exists():
            response_status["missing"] += 1
            continue

        data, parse_error = parse_response(response_path)
        if parse_error:
            response_status["invalid"] += 1
            errors.append(f"{batch_dir.name}/response.json: {parse_error}")
            continue

        response_status["present"] += 1
        returned = [item.get("slide_filename") for item in data or []]
        if returned != pngs:
            errors.append(f"{batch_dir.name}/response.json: filenames/order differ from batch PNGs")
        if len(returned) != len(pngs):
            errors.append(
                f"{batch_dir.name}/response.json: has {len(returned)} objects, expected {len(pngs)}"
            )

        expected = set(pngs)
        for item in data or []:
            errors.extend(validate_label(item, batch_dir, expected))

    duplicate_assignments = sorted(name for name, count in Counter(assigned).items() if count > 1)
    if duplicate_assignments:
        errors.append(f"duplicate slide assignments: {duplicate_assignments[:20]}")

    unbatched = sorted(slide_names - set(assigned))
    if unbatched:
        errors.append(f"{len(unbatched)} slide(s) in /slides/ are not assigned to a batch")

    print("=" * 56)
    print("  BATCH VALIDATION")
    print("=" * 56)
    print(f"  Slide PNGs in /slides/       : {len(slide_names)}")
    print(f"  Batch folders                : {len(batches)}")
    print(f"  Slide assignments in batches : {len(assigned)}")
    print(f"  Responses present            : {response_status['present']}")
    print(f"  Responses missing            : {response_status['missing']}")
    print(f"  Responses invalid            : {response_status['invalid']}")
    print(f"  Warnings                     : {len(warnings)}")
    print(f"  Errors                       : {len(errors)}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings[:50]:
            print(f"  - {warning}")
        if len(warnings) > 50:
            print(f"  ... {len(warnings) - 50} more")

    if errors:
        print("\nErrors:")
        for error in errors[:80]:
            print(f"  - {error}")
        if len(errors) > 80:
            print(f"  ... {len(errors) - 80} more")
        return 1

    print("\nOK: batch folders are internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
