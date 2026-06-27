"""
Stage 1 – HTML/CSS slide dataset coordinator.

Tracks which slides still need to be converted and reports progress.
The actual PNG → HTML conversion is done by Claude Code directly (no API
key required — it runs within your Pro subscription session).

Usage
-----
    # Show how many slides are done vs pending
    python slides_to_html.py --status

    # List pending slide IDs (feed to Claude Code for next batch)
    python slides_to_html.py --list-pending --limit 10

    # Validate all existing HTML files (structural sanity check)
    python slides_to_html.py --validate

    # Print a summary grouped by layout_type
    python slides_to_html.py --breakdown
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATASET = ROOT / "dataset.json"
HTML_DIR = ROOT / "html_slides"
HTML_DIR.mkdir(exist_ok=True)

VIEWPORT_W, VIEWPORT_H = 1280, 720


def _load_slides() -> list[dict]:
    with open(DATASET) as f:
        return json.load(f)["slides"]


def _is_done(slide: dict) -> bool:
    return (HTML_DIR / f"{slide['slide_id']}.html").exists()


def _validate_html(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()
    issues = []
    if "<!doctype html>" not in lower:
        issues.append("missing DOCTYPE")
    if "<style" not in lower:
        issues.append("missing <style>")
    if f"{VIEWPORT_W}px" not in text:
        issues.append(f"missing {VIEWPORT_W}px width")
    if f"{VIEWPORT_H}px" not in text:
        issues.append(f"missing {VIEWPORT_H}px height")
    if "position: relative" not in lower:
        issues.append("missing relative-positioned slide root")
    if "overflow: hidden" not in lower:
        issues.append("missing overflow hidden")
    if "<script" in lower:
        issues.append("contains <script> (JS not allowed)")
    if "<img" in lower:
        issues.append("contains <img> (images not allowed)")
    if "http://" in lower or "https://" in lower:
        issues.append("contains external URL")
    return issues


def cmd_status(slides: list[dict]) -> None:
    done = [s for s in slides if _is_done(s)]
    pending = [s for s in slides if not _is_done(s)]
    pct = 100 * len(done) / len(slides) if slides else 0
    print(f"Total slides : {len(slides)}")
    print(f"Converted    : {len(done)}  ({pct:.1f}%)")
    print(f"Pending      : {len(pending)}")
    print(f"HTML dir     : {HTML_DIR}")


def cmd_list_pending(slides: list[dict], limit: int | None) -> None:
    pending = [s for s in slides if not _is_done(s)]
    if limit:
        pending = pending[:limit]
    for s in pending:
        lbl = s.get("label", {})
        print(f"{s['slide_id']}  |  {lbl.get('layout_type','?')}  |  {lbl.get('chart_type','?')}")


def cmd_validate(slides: list[dict]) -> None:
    done = [s for s in slides if _is_done(s)]
    ok = bad = 0
    for s in done:
        path = HTML_DIR / f"{s['slide_id']}.html"
        issues = _validate_html(path)
        if issues:
            print(f"WARN  {s['slide_id']}: {', '.join(issues)}")
            bad += 1
        else:
            ok += 1
    print(f"\nValidated {len(done)} files — {ok} OK, {bad} with issues.")


def cmd_breakdown(slides: list[dict]) -> None:
    from collections import Counter
    done = [s for s in slides if _is_done(s)]
    pending = [s for s in slides if not _is_done(s)]

    layout_done: Counter = Counter()
    layout_pending: Counter = Counter()
    for s in done:
        layout_done[s.get("label", {}).get("layout_type", "unknown")] += 1
    for s in pending:
        layout_pending[s.get("label", {}).get("layout_type", "unknown")] += 1

    all_layouts = sorted(set(list(layout_done.keys()) + list(layout_pending.keys())))
    print(f"{'Layout type':<30} {'Done':>6} {'Pending':>8}")
    print("-" * 48)
    for lt in all_layouts:
        print(f"{lt:<30} {layout_done[lt]:>6} {layout_pending[lt]:>8}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Track HTML/CSS slide conversion progress."
    )
    parser.add_argument("--status", action="store_true",
                        help="Show overall progress.")
    parser.add_argument("--list-pending", action="store_true",
                        help="List slide IDs not yet converted.")
    parser.add_argument("--validate", action="store_true",
                        help="Run structural validation on all existing HTML files.")
    parser.add_argument("--breakdown", action="store_true",
                        help="Show progress grouped by layout_type.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of results (for --list-pending).")
    args = parser.parse_args()

    slides = _load_slides()

    if args.validate:
        cmd_validate(slides)
    elif args.list_pending:
        cmd_list_pending(slides, args.limit)
    elif args.breakdown:
        cmd_breakdown(slides)
    else:
        cmd_status(slides)


if __name__ == "__main__":
    main()
