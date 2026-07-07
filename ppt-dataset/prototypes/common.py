from __future__ import annotations

import colorsys
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_FILE = BASE_DIR / "dataset.json"
SLIDES_DIR = BASE_DIR / "slides"
OUTPUT_DIR = BASE_DIR / "prototypes" / "output"


def normalize_dataset(raw: Any) -> dict[str, Any]:
    """Return the canonical metadata + slides dataset shape.

    Older fast-ingest runs wrote dataset.json as a raw slide list. The original
    ingestion path writes {"metadata": ..., "slides": [...]}. Keep every
    prototype tolerant, but expose one stable shape to the rest of the code.
    """
    if isinstance(raw, list):
        slides = raw
        sources = sorted(
            {
                (s.get("label") or {}).get("source_company", "Unknown")
                for s in slides
                if isinstance(s, dict)
            }
        )
        return {
            "metadata": {
                "total_slides": len(slides),
                "labeled_slides": len(slides),
                "unlabeled_slides": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "label_schema_version": "1.0",
                "sources": sources,
                "normalization_note": "Loaded from legacy top-level slide list.",
            },
            "slides": slides,
        }

    if isinstance(raw, dict):
        slides = raw.get("slides", [])
        metadata = raw.get("metadata", {})
        metadata.setdefault("total_slides", len(slides))
        metadata.setdefault("labeled_slides", len(slides))
        metadata.setdefault("unlabeled_slides", max(0, metadata["total_slides"] - metadata["labeled_slides"]))
        metadata.setdefault("label_schema_version", "1.0")
        metadata.setdefault(
            "sources",
            sorted({(s.get("label") or {}).get("source_company", "Unknown") for s in slides if isinstance(s, dict)}),
        )
        return {"metadata": metadata, "slides": slides}

    raise ValueError(f"Unsupported dataset shape: {type(raw).__name__}")


def load_dataset() -> dict[str, Any]:
    if not DATASET_FILE.exists():
        raise FileNotFoundError(f"Missing {DATASET_FILE}. Run label_ingest.py first.")
    return normalize_dataset(json.loads(DATASET_FILE.read_text(encoding="utf-8")))


def dataset_slides(dataset: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(dataset, list):
        return dataset
    return dataset.get("slides", [])


def deck_id(slide_id: str) -> str:
    return re.sub(r"_slide_\d{3}$", "", slide_id)


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        return (0, 0, 0)
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def hex_to_hsv(hex_color: str) -> tuple[float, float, float]:
    r, g, b = hex_to_rgb(hex_color)
    return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)


def count_by(slides: list[dict[str, Any]], label_key: str) -> Counter:
    return Counter(slide["label"].get(label_key, "unknown") for slide in slides)


def slide_path(slide: dict[str, Any]) -> Path:
    return BASE_DIR / slide["image_path"]
