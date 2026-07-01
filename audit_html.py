"""
audit_html.py — Tier 1 structural audit of all generated HTML slides.

Checks for:
  1. Functional external URLs (src=/href=/url() pointing to http/https)
  2. Missing overflow:hidden on root
  3. CSS pixel values exceeding viewport (coordinate scaling failures)
  4. Background luminance mismatch vs source label
  5. Near-empty output (model error/truncation)
  6. Missing <style> block

Usage:
    python audit_html.py
    python audit_html.py --rerun   # re-convert all flagged slides after audit
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT       = Path(__file__).parent.parent
HTML_DIR   = ROOT / "html_slides"
DATASET    = Path(__file__).parent / "dataset.json"

VIEWPORT_W, VIEWPORT_H = 1280, 720
OVERSIZE_GRACE = 1400   # allow up to ~10% over 1280 before flagging


def load_meta() -> dict:
    with open(DATASET, encoding="utf-8") as f:
        data = json.load(f)
    return {s["slide_id"]: s.get("label", {}) for s in data["slides"]}


def lum(hex_color: str) -> float | None:
    """Return perceived luminance (0-255) of a hex color string."""
    hx = hex_color.lstrip("#")
    if len(hx) == 3:
        hx = hx[0]*2 + hx[1]*2 + hx[2]*2
    if len(hx) != 6:
        return None
    try:
        r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
        return (r * 299 + g * 587 + b * 114) / 1000
    except ValueError:
        return None


def audit_slide(html: str, slide_id: str, meta: dict) -> list[str]:
    lower = html.lower()
    flat  = lower.replace(" ", "")
    issues = []

    # 1. Functional external URL
    if re.search(
        r'(?:src|href)\s*=\s*["\']https?://'
        r'|url\s*\(\s*["\']?https?://'
        r'|@import\s+["\']https?://',
        lower
    ):
        issues.append("functional-external-url")

    # 2. Missing overflow:hidden
    if "overflow:hidden" not in flat:
        issues.append("no-overflow-hidden")

    # 3. Oversized CSS pixel values (scaling failure)
    px_vals = [int(m) for m in re.findall(r"(?:left|top|width|height)\s*:\s*(\d+)px", lower)]
    bad = [v for v in px_vals if v > OVERSIZE_GRACE]
    if bad:
        issues.append("oversized-px:{}".format(max(bad)))

    # 4. Background luminance mismatch
    lbl = meta.get(slide_id, {})
    bg_hex = lbl.get("color_palette", {}).get("background", "")
    src_lum = lum(bg_hex) if bg_hex else None
    if src_lum is not None:
        bgs = re.findall(r"background(?:-color)?\s*:\s*(#[0-9a-f]{3,6})", lower)
        if bgs:
            html_lum = lum(bgs[0])
            if html_lum is not None:
                if (src_lum > 128 and html_lum < 80) or (src_lum < 80 and html_lum > 180):
                    issues.append("bg-mismatch:src={:.0f},html={:.0f}".format(src_lum, html_lum))

    # 5. Near-empty output
    if len(html.strip()) < 500:
        issues.append("too-short")

    # 6. Missing style block
    if "<style" not in lower:
        issues.append("no-style-block")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Tier 1 HTML audit")
    parser.add_argument("--rerun", action="store_true",
                        help="Re-convert all flagged slides after audit")
    args = parser.parse_args()

    meta = load_meta()
    files = sorted(HTML_DIR.glob("*.html"))

    clean   = 0
    flagged = []

    for hf in files:
        html   = hf.read_text(encoding="utf-8", errors="ignore")
        issues = audit_slide(html, hf.stem, meta)
        if issues:
            src = meta.get(hf.stem, {}).get("source_company", "?")
            flagged.append((hf.stem, src, issues))
        else:
            clean += 1

    issue_counts: Counter = Counter()
    for _, _, issues in flagged:
        for i in issues:
            issue_counts[i.split(":")[0]] += 1

    print("=" * 60)
    print("  TIER 1 HTML AUDIT")
    print("=" * 60)
    print("Total HTML : {}".format(len(files)))
    print("Clean      : {}".format(clean))
    print("Flagged    : {}".format(len(flagged)))
    print()

    if issue_counts:
        print("Issue breakdown:")
        for issue, cnt in issue_counts.most_common():
            print("  {:<40} {}".format(issue, cnt))
        print()

    if flagged:
        print("Flagged slides:")
        by_src: dict[str, list] = {}
        for sid, src, issues in flagged:
            by_src.setdefault(src, []).append((sid, issues))
        for src, entries in sorted(by_src.items()):
            print("  [{}]  {} slides".format(src, len(entries)))
            for sid, issues in entries:
                print("    {}".format(sid))
                for i in issues:
                    print("      - {}".format(i))
    else:
        print("All slides pass Tier 1 audit.")

    if args.rerun and flagged:
        print()
        print("Re-converting {} flagged slides ...".format(len(flagged)))
        convert_script = Path(__file__).parent / "convert_to_html.py"
        for sid, _, _ in flagged:
            print("  {}".format(sid))
            subprocess.run(
                [sys.executable, str(convert_script), "--slide", sid, "--overwrite"],
                check=False
            )

    # Write CSV for easy review
    csv_path = Path(__file__).parent / "audit_tier1_flags.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("slide_id,source,issues\n")
        for sid, src, issues in flagged:
            f.write('{},{},{}\n'.format(sid, src, "|".join(issues)))
    print()
    print("Flags CSV  : {}".format(csv_path))


if __name__ == "__main__":
    main()
