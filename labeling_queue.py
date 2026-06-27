"""
labeling_queue.py - Generate a CSV queue for manual/assisted labeling.

Usage:
  python labeling_queue.py

Output:
  labeling_queue.csv
"""

import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
BATCHES_DIR = BASE_DIR / "batches"
QUEUE_FILE = BASE_DIR / "labeling_queue.csv"

BATCH_RE = re.compile(r"batch_\d{3}$")


def source_from_filename(filename: str) -> str:
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
    if lower.startswith("adb"):
        return "ADB"
    if lower.startswith("imf"):
        return "IMF"
    if lower.startswith("pwc"):
        return "PwC"
    if lower.startswith("oecd"):
        return "OECD"
    if lower.startswith("accenture"):
        return "Accenture"
    return "Unknown"


def priority_for_batch(sources: set[str]) -> int:
    if "Roland Berger" in sources:
        return 1
    if sources & {"BCG", "Bain", "McKinsey", "Deloitte", "WEF"}:
        return 2
    return 3


def main() -> None:
    rows: list[dict[str, str | int]] = []
    batch_dirs = sorted(
        [p for p in BATCHES_DIR.glob("batch_*") if p.is_dir() and BATCH_RE.fullmatch(p.name)]
    )

    for batch_dir in batch_dirs:
        pngs = sorted(p.name for p in batch_dir.glob("*.png"))
        sources = {source_from_filename(name) for name in pngs}
        response_exists = (batch_dir / "response.json").exists()
        status = "labeled" if response_exists else "pending"
        priority = priority_for_batch(sources)

        rows.append(
            {
                "priority": priority,
                "batch_id": batch_dir.name,
                "status": status,
                "response_exists": str(response_exists).lower(),
                "slide_count": len(pngs),
                "sources": "; ".join(sorted(sources)),
                "first_slide": pngs[0] if pngs else "",
                "last_slide": pngs[-1] if pngs else "",
                "notes": "Roland Berger priority" if "Roland Berger" in sources else "",
            }
        )

    rows.sort(key=lambda row: (int(row["priority"]), str(row["batch_id"])))

    with QUEUE_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "priority",
                "batch_id",
                "status",
                "response_exists",
                "slide_count",
                "sources",
                "first_slide",
                "last_slide",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    pending = sum(1 for row in rows if row["status"] == "pending")
    roland_pending = sum(
        1 for row in rows if row["status"] == "pending" and "Roland Berger" in row["sources"]
    )

    print(f"Wrote {QUEUE_FILE}")
    print(f"Total batches      : {len(rows)}")
    print(f"Pending batches    : {pending}")
    print(f"Roland pending     : {roland_pending}")
    print("Suggested next set : priority=1 batches first")


if __name__ == "__main__":
    main()
