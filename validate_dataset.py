"""validate_dataset.py
Batch validation of all individual slide HTML files in html_slides/.

Reuses the same check functions from validate_slides.py but reads files
directly (no srcdoc encoding) and produces an aggregate quality report.

Usage:
    python ppt-dataset/validate_dataset.py
    python ppt-dataset/validate_dataset.py --fix     # auto-fix safe issues in-place
    python ppt-dataset/validate_dataset.py --source bain  # filter by source prefix
"""
import re
import sys
import json
from pathlib import Path
from collections import defaultdict

ROOT  = Path(__file__).parent.parent
SLIDES_DIR = ROOT / "html_slides"

# -- reuse all check functions verbatim from validate_slides.py ---------------

def check_sub_zindex(html, idx=0):
    issues = []
    sub = re.search(r'\.sub\s*\{([^}]+)\}', html)
    if sub and 'z-index' not in sub.group(1):
        issues.append("sub missing z-index:1")
    return issues

def check_chart_clears_sub(html, idx=0):
    issues = []
    sub = re.search(r'\.sub\s*\{[^}]*?top:\s*(\d+)px', html)
    if not sub:
        return issues
    sub_top = int(sub.group(1))
    for cls in [r'\.chart-wrap', r'\.chart\b', r'\.col\b']:
        m = re.search(cls + r'\s*\{[^}]*?top:\s*(\d+)px', html, re.DOTALL)
        if m:
            chart_top = int(m.group(1))
            if chart_top < sub_top + 25:
                issues.append(
                    f"{cls.strip('\\.')} top:{chart_top} too close to sub top:{sub_top} "
                    f"(need >= {sub_top + 25})"
                )
    return issues

def check_position_absolute_on_children(html, idx=0):
    issues = []
    for cls in ['.num-badge', '.enabler-text', '.big', '.small']:
        key = cls.lstrip('.')
        m = re.search(r'\.' + key + r'\s*\{([^}]+)\}', html)
        if m and 'left' in m.group(1) and 'position' not in m.group(1):
            issues.append(f"{cls} uses left/top without position:absolute")
    return issues

def check_svg_hgrid_lines(html, idx=0):
    bad = re.findall(r'<line x1="0" y1="\d+" x2="\d+" y2="\d+"', html)
    return [f"{len(bad)} horizontal grid lines start at x1=0"] if bad else []

def check_svg_vgrid_lines(html, idx=0):
    has_header = bool(re.search(r'<rect[^>]+y="0"[^>]+height="\d+"[^>]*/>', html))
    if not has_header:
        return []
    bad = re.findall(r'<line x1="(\d+)" y1="0" x2="\1" y2="\d+"', html)
    return [f"{len(bad)} vertical grid lines start at y1=0"] if bad else []

def check_header_rect_stroke(html, idx=0):
    bad = re.findall(
        r'<rect[^>]+y="0"[^>]+height="\d{1,2}"[^>]+stroke="[^n][^>]+"', html)
    return [f"{len(bad)} header rect(s) have stroke"] if bad else []

def check_label_color_vs_bar(html, idx=0):
    issues = []
    rects = []
    for m in re.finditer(r'<rect x="([\d.]+)"[^>]+width="([\d.]+)"[^>]+fill="(#[0-9A-Fa-f]{6})"', html):
        x, w, fill = float(m.group(1)), float(m.group(2)), m.group(3)
        if fill not in ('#FAFAFA','#EFF7FA','#FFFFFF','#F0F0F0','#E8E8E8','#EAF3F6','#DCE9ED'):
            rects.append((x, x + w, fill))
    for m in re.finditer(r'<text x="([\d.]+)"[^>]*text-anchor="end"[^>]*fill="(#[0-9A-Fa-f]{6})"[^>]*>[\d.%]+<', html):
        tx, tfill = float(m.group(1)), m.group(2)
        for (rx, rx_end, rfill) in rects:
            if rfill == tfill and tx > rx and tx < rx_end + 5:
                issues.append(f"end-label fill={tfill} at x={tx:.0f} overlaps bar — invisible")
    return issues

def check_svg_bottom_clearance(html, idx=0):
    issues = []
    for svg_m in re.finditer(r'<svg[^>]+height="(\d+)"[^>]*viewBox="0 0 \d+ \1"', html):
        svgh = int(svg_m.group(1))
        block = html[svg_m.start():svg_m.start() + 8000]
        y_vals = [int(v) for v in re.findall(r'\b(?:y|cy)="(\d+)"', block) if int(v) <= svgh]
        if y_vals and svgh - max(y_vals) < 10:
            issues.append(f"SVG h={svgh} last-y={max(y_vals)} ({svgh-max(y_vals)}px clearance)")
    return issues

def check_annotation_box_overflow(html, idx=0):
    issues = []
    for svg_m in re.finditer(r'<svg[^>]+viewBox="0 0 (\d+) \d+"', html):
        vw = int(svg_m.group(1))
        block = html[svg_m.start():svg_m.start() + 8000]
        for rm in re.finditer(r'<rect x="([\d.]+)"[^>]+width="([\d.]+)"', block):
            rx, rw = float(rm.group(1)), float(rm.group(2))
            if rx + rw > vw + 1:
                issues.append(f"rect x={rx:.0f}+w={rw:.0f}={rx+rw:.0f} > viewBox w={vw}")
    return issues

ALL_CHECKS = [
    ("sub_zindex",       check_sub_zindex),
    ("chart_clears_sub", check_chart_clears_sub),
    ("pos_absolute",     check_position_absolute_on_children),
    ("svg_hgrid",        check_svg_hgrid_lines),
    ("svg_vgrid",        check_svg_vgrid_lines),
    ("header_stroke",    check_header_rect_stroke),
    ("label_color_bar",  check_label_color_vs_bar),
    ("svg_bottom",       check_svg_bottom_clearance),
    # annotation_overflow excluded: Roland Berger uses small-viewBox SVG components
    # that legitimately place rects outside the viewport window — not a real render bug.
]


def autofix_slide(html):
    """Apply the same safe fixes as validate_slides.py."""
    issues_all = []
    for _, chk in ALL_CHECKS:
        issues_all.extend(chk(html))
    changed = []

    if any("sub missing z-index" in i for i in issues_all):
        before = html
        html = re.sub(r'(\.sub\s*\{)', r'\1z-index:1;', html)
        if html != before: changed.append("z-index:1 -> .sub")

    if any("x1=0" in i for i in issues_all):  # matches "h-gridlines at x1=0"
        vline = re.search(r'<line x1="(\d+)" y1="\d+" x2="\1" y2="\d+"', html)
        label_w = vline.group(1) if vline else "180"
        before = html
        html = re.sub(
            r'<line x1="0" y1="(\d+)" x2="(\d+)" y2="\1"',
            lambda m: f'<line x1="{label_w}" y1="{m.group(1)}" x2="{m.group(2)}" y2="{m.group(1)}"',
            html)
        if html != before: changed.append(f"hgrid x1->{label_w}")

    if any("y1=0" in i for i in issues_all):  # matches "vertical grid lines start at y1=0"
        header_rects = re.findall(r'<rect[^>]+y="0"[^>]+height="(\d+)"', html)
        header_h = max(int(h) for h in header_rects) if header_rects else 50
        before = html
        html = re.sub(
            r'(<line x1="(\d+)" )y1="0"( x2="\2" y2="\d+")',
            lambda m: m.group(0).replace('y1="0"', f'y1="{header_h}"'), html)
        if html != before: changed.append(f"vgrid y1->{header_h}")

    if any("header rect" in i and "stroke" in i for i in issues_all):
        before = html
        html = re.sub(r'(<rect[^>]+y="0"[^>]+height="\d{1,2}"[^>]+) stroke="[^"]+"', r'\1', html)
        if html != before: changed.append("removed header stroke")

    for issue in issues_all:
        m = re.search(
            r'([\w\-\\b]+) top:(\d+) too close to sub top:(\d+) \(need >= (\d+)\)', issue)
        if m:
            cls_name = m.group(1).replace(r'\b', '')
            cur_top, req_top = m.group(2), m.group(4)
            pattern = (r'(\.' + re.escape(cls_name) +
                       r'[\w\-]*\s*\{[^}]*?)top:\s*' + re.escape(cur_top) + r'px')
            before = html
            html = re.sub(pattern, rf'\g<1>top:{req_top}px', html, flags=re.DOTALL)
            if html != before: changed.append(f".{cls_name} top {cur_top}->{req_top}px")

    # Fix svg_bottom: when last SVG element is < 10px from declared SVG height,
    # expand the SVG height by 20px (adds blank buffer — safe, no data lost).
    if any("px clearance" in i for i in issues_all):
        def expand_svg_height(m2):
            tag = m2.group(0)
            h_m = re.search(r'height="(\d+)"', tag)
            vb_m = re.search(r'viewBox="(0 0 \d+) (\d+)"', tag)
            if not h_m:
                return tag
            old_h = int(h_m.group(1))
            new_h = old_h + 20
            tag = tag.replace(f'height="{old_h}"', f'height="{new_h}"', 1)
            if vb_m and vb_m.group(2) == str(old_h):
                tag = tag.replace(f'viewBox="{vb_m.group(1)} {old_h}"',
                                  f'viewBox="{vb_m.group(1)} {new_h}"', 1)
            return tag
        before = html
        html = re.sub(r'<svg[^>]+height="\d+"[^>]*>', expand_svg_height, html)
        if html != before:
            changed.append("expanded SVG height +20px (bottom clearance)")

    return html, changed


def validate_file(path: Path):
    """Return (issue_count, {category: count}, issues_list)."""
    html = path.read_text(encoding="utf-8", errors="ignore")
    by_category = {}
    all_issues = []
    for name, chk in ALL_CHECKS:
        found = chk(html)
        if found:
            by_category[name] = len(found)
            all_issues.extend(found)
    return len(all_issues), by_category, all_issues


def main():
    fix_mode  = "--fix"    in sys.argv
    src_filter = None
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            src_filter = arg.lower()

    files = sorted(SLIDES_DIR.glob("*.html"))
    if src_filter:
        files = [f for f in files if f.name.lower().startswith(src_filter)]
    total_files = len(files)

    print(f"Dataset: {SLIDES_DIR}")
    print(f"Files to validate: {total_files}")
    if fix_mode:
        print("Mode: AUTO-FIX enabled\n")
    else:
        print("Mode: audit only (use --fix to apply safe fixes)\n")

    # Aggregate stats
    issue_count_dist = defaultdict(int)   # {issue_count: file_count}
    category_totals  = defaultdict(int)   # {category: total_issues}
    source_stats     = defaultdict(lambda: {"files": 0, "issues": 0})
    worst_files      = []                 # (issue_count, path)
    files_fixed      = 0
    total_issues_all = 0

    for i, path in enumerate(files):
        # Source prefix (e.g. "bain", "ey", "deloitte")
        src = path.name.split("_")[0]
        source_stats[src]["files"] += 1

        n_issues, by_cat, issues_list = validate_file(path)
        total_issues_all += n_issues
        issue_count_dist[n_issues] += 1
        source_stats[src]["issues"] += n_issues
        for cat, cnt in by_cat.items():
            category_totals[cat] += cnt
        if n_issues > 0:
            worst_files.append((n_issues, path.name))

        if fix_mode and n_issues > 0:
            html = path.read_text(encoding="utf-8", errors="ignore")
            fixed_html, changes = autofix_slide(html)
            if changes:
                path.write_text(fixed_html, encoding="utf-8")
                files_fixed += 1

        # Progress every 100 files
        if (i + 1) % 100 == 0 or (i + 1) == total_files:
            print(f"  [{i+1:4d}/{total_files}] running issues so far: {total_issues_all}", end="\r")

    print()
    print()

    # -- Summary report --------------------------------------------------------
    clean = issue_count_dist.get(0, 0)
    dirty = total_files - clean
    print("=" * 62)
    print("DATASET VALIDATION REPORT")
    print("=" * 62)
    print(f"Total slides:      {total_files:>6}")
    print(f"Clean (0 issues):  {clean:>6}  ({100*clean/total_files:.1f}%)")
    print(f"With issues:       {dirty:>6}  ({100*dirty/total_files:.1f}%)")
    print(f"Total issues:      {total_issues_all:>6}")
    print()

    print("-- Issue distribution ----------------------------------")
    for n in sorted(issue_count_dist):
        bar = "#" * min(40, issue_count_dist[n])
        print(f"  {n:2d} issues: {issue_count_dist[n]:4d} files  {bar}")
    print()

    print("-- Issue type breakdown --------------------------------")
    for cat, cnt in sorted(category_totals.items(), key=lambda x: -x[1]):
        print(f"  {cat:<26} {cnt:>5} occurrences")
    print()

    print("-- By source -------------------------------------------")
    for src, stats in sorted(source_stats.items(), key=lambda x: -x[1]["issues"]):
        n_files = stats["files"]
        n_iss   = stats["issues"]
        rate    = n_iss / n_files if n_files else 0
        print(f"  {src:<18} {n_files:>4} slides  {n_iss:>5} issues  ({rate:.1f}/slide)")
    print()

    print("-- Worst 20 slides -------------------------------------")
    for n, name in sorted(worst_files, reverse=True)[:20]:
        print(f"  [{n:2d}] {name}")

    if fix_mode:
        print(f"\nAuto-fixed: {files_fixed} files updated in {SLIDES_DIR}")

    # Save JSON report
    report = {
        "total": total_files, "clean": clean, "dirty": dirty,
        "total_issues": total_issues_all,
        "by_category": dict(category_totals),
        "by_source": {k: dict(v) for k, v in source_stats.items()},
    }
    report_path = Path(__file__).parent / "dataset_validation_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"Full report saved -> {report_path.name}")

    # Save quality exclusion list — slide IDs (stem) that failed validation.
    # build_finetune_dataset.py reads this to gate training pairs.
    failed_ids = sorted(Path(name).stem for _, name in worst_files)
    excl_path = Path(__file__).parent / "quality_exclusions.json"
    excl_path.write_text(json.dumps({
        "excluded_slide_ids": failed_ids,
        "reason": "failed layout validation (see dataset_validation_report.json)",
        "total_excluded": len(failed_ids),
        "total_slides": total_files,
        "pass_rate_pct": round(100 * (total_files - len(failed_ids)) / total_files, 1),
    }, indent=2))
    print(f"Quality exclusions -> {excl_path.name}  ({len(failed_ids)} slides excluded, "
          f"{total_files - len(failed_ids)} pass)")


if __name__ == "__main__":
    main()
