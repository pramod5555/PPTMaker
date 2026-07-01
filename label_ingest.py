"""
label_ingest.py — Parse batch response.json files → /labels/ → dataset.json

Run after completing manual labeling on claude.ai:
  python label_ingest.py

Safe to re-run at any time; it overwrites existing label files and rebuilds
dataset.json from scratch each time.
"""

import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
BATCHES_DIR = BASE_DIR / "batches"
LABELS_DIR = BASE_DIR / "labels"
SLIDES_DIR = BASE_DIR / "slides"
DATASET_FILE = BASE_DIR / "dataset.json"

LABELS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def strip_fences(text: str) -> str:
    """Remove markdown code fences Claude sometimes wraps JSON in."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first line (```json or ```) and last line (```)
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    return text


def ingest_responses() -> int:
    """
    Scan batches/batch_*/response.json, parse each JSON array,
    and write one label file per slide to /labels/.
    Returns total number of labels written.
    """
    response_files = sorted(BATCHES_DIR.glob("batch_*/response.json"))

    if not response_files:
        log.warning(
            "No response.json files found in batches/. "
            "Complete manual labeling on claude.ai first."
        )
        return 0

    total_written = 0
    total_failed = 0

    for resp_file in response_files:
        batch_name = resp_file.parent.name
        try:
            raw = strip_fences(resp_file.read_text(encoding="utf-8"))
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            log.error(f"{batch_name}/response.json: JSON parse error — {e}")
            total_failed += 1
            continue
        except Exception as e:
            log.error(f"{batch_name}/response.json: Read error — {e}")
            total_failed += 1
            continue

        if not isinstance(data, list):
            log.error(f"{batch_name}/response.json: Expected array, got {type(data).__name__}")
            total_failed += 1
            continue

        for slide_obj in data:
            filename = slide_obj.get("slide_filename", "")
            if not filename:
                log.warning(f"{batch_name}: Slide object missing slide_filename — skipped")
                continue

            stem = Path(filename).stem
            label_path = LABELS_DIR / f"{stem}.json"
            try:
                label_path.write_text(json.dumps(slide_obj, indent=2), encoding="utf-8")
                total_written += 1
                log.info(f"Wrote label: {stem}.json")
            except Exception as e:
                log.error(f"Could not write {stem}.json: {e}")
                total_failed += 1

    log.info(
        f"Ingested {total_written} labels from {len(response_files)} batch(es) "
        f"({total_failed} failure(s))"
    )
    return total_written


def build_dataset() -> None:
    """
    Merge all /labels/*.json into dataset.json and print a summary report.
    """
    label_files = sorted(LABELS_DIR.glob("*.json"))
    slide_png_names = {f.name for f in SLIDES_DIR.glob("*.png")}

    slides_out = []
    stats: dict = {
        "layout_type": defaultdict(int),
        "source_company": defaultdict(int),
        "chart_type": defaultdict(int),
        "quality_scores": [],
        "missing_label": 0,
    }

    for label_file in label_files:
        try:
            label = json.loads(label_file.read_text(encoding="utf-8"))
        except Exception as e:
            log.error(f"Could not read label {label_file.name}: {e}")
            stats["missing_label"] += 1
            continue

        slide_filename = label.get("slide_filename") or (label_file.stem + ".png")
        slide_id = Path(slide_filename).stem

        slides_out.append(
            {
                "slide_id": slide_id,
                "image_path": f"slides/{slide_filename}",
                "label": label,
            }
        )

        stats["layout_type"][label.get("layout_type", "unknown")] += 1
        stats["source_company"][label.get("source_company", "Unknown")] += 1
        stats["chart_type"][label.get("chart_type", "none")] += 1
        q = label.get("estimated_quality_score")
        if isinstance(q, (int, float)):
            stats["quality_scores"].append(float(q))

    sources = sorted({s["label"].get("source_company", "Unknown") for s in slides_out})
    avg_q = (
        sum(stats["quality_scores"]) / len(stats["quality_scores"])
        if stats["quality_scores"]
        else 0.0
    )

    dataset = {
        "metadata": {
            "total_slides": len(slide_png_names),
            "labeled_slides": len(slides_out),
            "unlabeled_slides": len(slide_png_names) - len(slides_out),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "label_schema_version": "1.0",
            "sources": sources,
        },
        "slides": slides_out,
    }

    DATASET_FILE.write_text(json.dumps(dataset, indent=2), encoding="utf-8")

    # ─── Summary report ───────────────────────────────────────────────────────
    print("\n" + "=" * 52)
    print("  DATASET SUMMARY")
    print("=" * 52)
    print(f"  Total slide PNGs in /slides/  : {len(slide_png_names)}")
    print(f"  Labeled slides                : {len(slides_out)}")
    print(f"  Unlabeled slides              : {len(slide_png_names) - len(slides_out)}")
    print(f"  Failed / unreadable labels    : {stats['missing_label']}")
    print(f"  Avg estimated quality score   : {avg_q:.2f} / 5.0")

    print("\n  Layout types:")
    for k, v in sorted(stats["layout_type"].items(), key=lambda x: -x[1]):
        print(f"    {k:<30} {v}")

    print("\n  Source companies:")
    for k, v in sorted(stats["source_company"].items(), key=lambda x: -x[1]):
        print(f"    {k:<30} {v}")

    print("\n  Chart types:")
    for k, v in sorted(stats["chart_type"].items(), key=lambda x: -x[1]):
        print(f"    {k:<30} {v}")

    print(f"\n  dataset.json -> {DATASET_FILE}")
    print("=" * 52)


def main():
    log.info("=== label_ingest.py ===")
    written = ingest_responses()
    existing_labels = list(LABELS_DIR.glob("*.json"))

    if written > 0 or existing_labels:
        build_dataset()
    else:
        print(
            "\nNo labels to process yet.\n"
            "Complete batch labeling on claude.ai first, then re-run this script."
        )


if __name__ == "__main__":
    main()
