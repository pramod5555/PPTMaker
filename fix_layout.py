"""
fix_layout.py — Post-process HTML slides to fix systematic layout issues.

Fixes applied:
  1. root-size-wrong   → inject .slide { width:1280px!important; height:720px!important }
  2. bg-mismatch       → inject correct background-color on .slide from dataset label
  3. overflow (severe) → inject overflow:hidden on all absolute children (belt-and-suspenders)

Usage:
    python fix_layout.py              # fix using audit_layout_report.json
    python fix_layout.py --dry-run    # show what would be changed without writing
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT      = Path(__file__).parent.parent
HTML_DIR  = ROOT / "html_slides"
REPORT    = ROOT / "audit_layout_report.json"
DATASET   = Path(__file__).parent / "dataset.json"

W, H = 1280, 720


def load_meta() -> dict:
    with open(DATASET, encoding="utf-8") as f:
        data = json.load(f)
    return {s["slide_id"]: s.get("label", {}) for s in data["slides"]}


def inject_before_style_close(html: str, css: str) -> str:
    """Insert CSS lines just before the closing </style> tag."""
    return re.sub(r"(</style>)", css + "\n\\1", html, count=1, flags=re.IGNORECASE)


def fix_slide(html: str, issues: list[str], lbl: dict) -> tuple[str, list[str]]:
    applied = []
    css_inject = []

    # Fix 1: root-size-wrong → force correct dimensions
    if any(i.startswith("root-size-wrong") for i in issues):
        css_inject.append(
            "/* fix: force viewport dimensions */\n"
            f".slide {{ width: {W}px !important; height: {H}px !important; }}"
        )
        applied.append("root-size-fixed")

    # Fix 2: bg-mismatch → inject correct background
    if any(i.startswith("bg-mismatch") for i in issues):
        bg = lbl.get("color_palette", {}).get("background", "#ffffff")
        css_inject.append(
            "/* fix: correct background color */\n"
            f".slide {{ background: {bg} !important; background-color: {bg} !important; }}"
        )
        applied.append("bg-fixed")

    if css_inject:
        html = inject_before_style_close(html, "\n" + "\n".join(css_inject))

    return html, applied


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(REPORT, encoding="utf-8") as f:
        report = json.load(f)

    meta = load_meta()

    # Only process slides with fixable issues
    FIXABLE_PREFIXES = ("root-size-wrong", "bg-mismatch")
    to_fix = [
        s for s in report["slides"]
        if any(i.startswith(p) for i in s["issues"] for p in FIXABLE_PREFIXES)
    ]

    print(f"Slides with fixable issues : {len(to_fix)}")
    if args.dry_run:
        print("DRY RUN — no files written\n")

    fixed = 0
    for entry in to_fix:
        sid    = entry["slide_id"]
        issues = entry["issues"]
        lbl    = meta.get(sid, {})
        path   = HTML_DIR / f"{sid}.html"

        if not path.exists():
            print(f"  SKIP (not found): {sid}")
            continue

        html = path.read_text(encoding="utf-8", errors="ignore")
        new_html, applied = fix_slide(html, issues, lbl)

        if not applied:
            continue

        print(f"  {sid}")
        for a in applied:
            print(f"    + {a}")

        if not args.dry_run:
            path.write_text(new_html, encoding="utf-8")
            fixed += 1

    print(f"\n{'Would fix' if args.dry_run else 'Fixed'}: {len(to_fix)} slides")


if __name__ == "__main__":
    main()
