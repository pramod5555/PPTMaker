"""
Create a style-generation readiness report.

This is the QC checkpoint before using the corpus to generate high-fidelity
consulting decks from prompts.

Usage:
    python prototypes/style_readiness_report.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from common import BASE_DIR, ensure_output_dir, load_dataset
from recipe_catalog import RECIPES

OUT_DIR = ensure_output_dir()
FIDELITY_PATH = OUT_DIR / "fidelity_summary.json"
INDEX_PATH = OUT_DIR / "retrieval_index.json"
GOLD_PATH = OUT_DIR / "gold_style_bank.json"
REPORT_JSON = OUT_DIR / "style_readiness_report.json"
REPORT_MD = OUT_DIR / "style_readiness_report.md"


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def source_counts(records: list[dict[str, Any]]) -> Counter[str]:
    return Counter(
        r.get("source_company")
        or (r.get("label") or {}).get("source_company")
        or "Unknown"
        for r in records
    )


def recipe_counts(records: list[dict[str, Any]]) -> Counter[str]:
    return Counter((r.get("fidelity") or {}).get("design_recipe", "unknown") for r in records)


def chart_counts(records: list[dict[str, Any]]) -> Counter[str]:
    return Counter((r.get("label") or {}).get("chart_type", "unknown") for r in records)


def main() -> None:
    dataset = load_dataset()
    slides = dataset.get("slides", [])
    fidelity = load_json(FIDELITY_PATH, [])
    index = load_json(INDEX_PATH, {})
    gold = load_json(GOLD_PATH, [])

    label_files = list((BASE_DIR / "labels").glob("*.json"))
    slide_pngs = list((BASE_DIR / "slides").glob("*.png"))

    checks = []
    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    check("dataset_schema", isinstance(dataset, dict) and "metadata" in dataset and "slides" in dataset, "dataset.json is canonical object")
    check("dataset_slide_coverage", len(slides) == len(slide_pngs), f"{len(slides)} dataset slides / {len(slide_pngs)} PNGs")
    check("fidelity_coverage", len(fidelity) == len(slides), f"{len(fidelity)} fidelity records / {len(slides)} dataset slides")
    check("retrieval_coverage", index.get("count") == len(slides), f"{index.get('count')} retrieval records / {len(slides)} dataset slides")
    check("gold_bank_size", len(gold) >= 200, f"{len(gold)} gold slides")
    gold_sources = source_counts(gold)
    check("roland_floor", gold_sources.get("Roland Berger", 0) >= 120, f"{gold_sources.get('Roland Berger', 0)} Roland Berger gold slides")
    check("manual_label_files", len(label_files) == len(slides), f"{len(label_files)} label files / {len(slides)} dataset slides; mismatch is expected if auto-label ingestion was used")

    recipe_coverage = recipe_counts(gold)
    recipe_requirements = {
        recipe_id: sum(1 for r in gold if set(recipe.retrieval_recipe.split(" + ")) <= set(((r.get("fidelity") or {}).get("design_recipe", "")).split(" + ")))
        for recipe_id, recipe in RECIPES.items()
    }

    report = {
        "counts": {
            "slide_pngs": len(slide_pngs),
            "dataset_slides": len(slides),
            "fidelity_records": len(fidelity),
            "retrieval_records": index.get("count"),
            "gold_slides": len(gold),
            "label_files": len(label_files),
        },
        "dataset_sources": dict(source_counts(slides).most_common()),
        "gold_sources": dict(gold_sources.most_common()),
        "gold_chart_types": dict(chart_counts(gold).most_common()),
        "gold_design_recipes": dict(recipe_coverage.most_common()),
        "recipe_catalog_anchor_coverage": recipe_requirements,
        "checks": checks,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Style Readiness Report",
        "",
        "## Checks",
    ]
    for item in checks:
        mark = "PASS" if item["ok"] else "WARN"
        lines.append(f"- {mark}: {item['name']} - {item['detail']}")

    lines.extend(["", "## Gold Bank Sources"])
    lines.extend(f"- {k}: {v}" for k, v in gold_sources.most_common())
    lines.extend(["", "## Gold Bank Chart Types"])
    lines.extend(f"- {k}: {v}" for k, v in chart_counts(gold).most_common())
    lines.extend(["", "## Recipe Catalog Anchor Coverage"])
    lines.extend(f"- {k}: {v}" for k, v in recipe_requirements.items())
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_JSON}")
    print(f"Wrote {REPORT_MD}")
    for item in checks:
        mark = "PASS" if item["ok"] else "WARN"
        print(f"{mark:<4} {item['name']:<24} {item['detail']}")


if __name__ == "__main__":
    main()
