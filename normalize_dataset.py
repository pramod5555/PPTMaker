"""
normalize_dataset.py - Rewrite dataset.json to the canonical object schema.

This is intentionally small and safe:
  - accepts either legacy top-level list or canonical {"metadata", "slides"}
  - writes a timestamped backup before changing dataset.json
  - preserves every slide entry unchanged

Usage:
    python normalize_dataset.py
"""
from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent
DATASET_FILE = BASE_DIR / "dataset.json"
SLIDES_DIR = BASE_DIR / "slides"


def normalize(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        slides = raw.get("slides", [])
        metadata = raw.get("metadata", {})
    elif isinstance(raw, list):
        slides = raw
        metadata = {}
    else:
        raise ValueError(f"Unsupported dataset shape: {type(raw).__name__}")

    png_count = len(list(SLIDES_DIR.glob("*.png")))
    source_counts = Counter(
        (slide.get("label") or {}).get("source_company", "Unknown")
        for slide in slides
        if isinstance(slide, dict)
    )

    metadata = {
        **metadata,
        "total_slides": png_count or len(slides),
        "labeled_slides": len(slides),
        "unlabeled_slides": max(0, (png_count or len(slides)) - len(slides)),
        "created_at": metadata.get("created_at") or datetime.now(timezone.utc).isoformat(),
        "normalized_at": datetime.now(timezone.utc).isoformat(),
        "label_schema_version": metadata.get("label_schema_version", "1.0"),
        "sources": sorted(source_counts),
        "source_counts": dict(sorted(source_counts.items())),
    }
    return {"metadata": metadata, "slides": slides}


def main() -> None:
    if not DATASET_FILE.exists():
        raise SystemExit(f"Missing {DATASET_FILE}")

    raw = json.loads(DATASET_FILE.read_text(encoding="utf-8"))
    dataset = normalize(raw)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DATASET_FILE.with_name(f"dataset.backup_{stamp}.json")
    shutil.copy2(DATASET_FILE, backup)
    DATASET_FILE.write_text(json.dumps(dataset, indent=2), encoding="utf-8")

    print(f"Wrote canonical dataset: {DATASET_FILE}")
    print(f"Backup: {backup}")
    print(f"Slides: {dataset['metadata']['labeled_slides']}/{dataset['metadata']['total_slides']}")
    print("Sources:")
    for source, count in dataset["metadata"]["source_counts"].items():
        print(f"  {source:<20} {count}")


if __name__ == "__main__":
    main()
