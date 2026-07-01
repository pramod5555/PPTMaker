"""
status.py - Quick snapshot of the dataset pipeline state.

  python status.py
"""

import json
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).parent

PDFS_DIR    = BASE_DIR / "pdfs"
SLIDES_DIR  = BASE_DIR / "slides"
BATCHES_DIR = BASE_DIR / "batches"
LABELS_DIR  = BASE_DIR / "labels"
DATASET_FILE = BASE_DIR / "dataset.json"


def fmt(n: int, label: str) -> str:
    return f"  {label:<35} {n}"


def main():
    pdfs    = list(PDFS_DIR.glob("*.pdf"))
    slides  = list(SLIDES_DIR.glob("*.png"))
    batches = list(BATCHES_DIR.glob("batch_*"))
    labeled = [b for b in batches if (b / "response.json").exists()]
    labels  = list(LABELS_DIR.glob("*.json"))

    total_pdf_mb = sum(p.stat().st_size for p in pdfs) / (1024 * 1024)

    print("=" * 52)
    print("  PPT DATASET - PIPELINE STATUS")
    print("=" * 52)
    print(fmt(len(pdfs),    f"PDFs downloaded  ({total_pdf_mb:.0f} MB)"))
    print(fmt(len(slides),  "Slide PNGs in /slides/"))
    print(fmt(len(batches), "Batches in /batches/"))
    print(fmt(len(labeled), "Batches with response.json (labeled)"))
    print(fmt(len(batches) - len(labeled), "Batches still needing labels"))
    print(fmt(len(labels),  "Individual label JSONs in /labels/"))

    dataset_labeled = None
    dataset_total = None
    if DATASET_FILE.exists():
        try:
            ds = json.loads(DATASET_FILE.read_text(encoding="utf-8"))
            if isinstance(ds, list):
                dataset_labeled = len(ds)
                dataset_total = len(ds)
                print(fmt(dataset_labeled, "Slides in dataset.json"))
                print(fmt("legacy list", "dataset.json schema"))
            else:
                meta = ds.get("metadata", {})
                dataset_labeled = meta.get("labeled_slides")
                dataset_total = meta.get("total_slides")
                print(fmt(dataset_labeled if dataset_labeled is not None else "?", "Slides in dataset.json"))
                print(fmt("canonical object", "dataset.json schema"))
        except Exception:
            print(fmt("?", "dataset.json (parse error)"))
    else:
        print(fmt(0, "dataset.json (not yet built)"))

    print()
    # Next recommended action
    if len(pdfs) == 0:
        print("  NEXT: python run_pipeline.py --seeds")
    elif len(slides) == 0:
        print("  NEXT: python run_pipeline.py --skip-scrape")
    elif len(batches) == 0:
        print("  NEXT: python batch_prep.py")
    elif len(labeled) < len(batches):
        remaining = len(batches) - len(labeled)
        print(f"  NEXT: Label {remaining} batch(es) on claude.ai  (see batches/INSTRUCTIONS.txt)")
    elif dataset_labeled == len(slides):
        print("  NEXT: prototype retrieval/generation from the complete dataset")
    elif dataset_total == len(slides) and dataset_labeled:
        print("  NEXT: python normalize_dataset.py && npm run pipeline:refresh")
    else:
        print("  NEXT: python run_pipeline.py --ingest-only")
    print("=" * 52)

    # Per-source breakdown
    if pdfs:
        sources = Counter(p.stem.split("_")[0] for p in pdfs)
        print("\n  PDFs by source:")
        for src, n in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"    {src:<20} {n}")


if __name__ == "__main__":
    main()
