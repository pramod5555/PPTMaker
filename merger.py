"""
merger.py — Rebuild dataset.json from existing /labels/*.json files.

Use this when you want to regenerate dataset.json without re-parsing
batch response files (e.g. after manually editing a label file).

  python merger.py
"""

import logging
import sys
from label_ingest import build_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

if __name__ == "__main__":
    build_dataset()
