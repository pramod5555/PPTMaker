"""validate_slides.py
Run against any deck HTML to catch known layout bug patterns BEFORE manual review.
Usage:
    python validate_slides.py full_deck_v4.html
    python validate_slides.py full_deck_v4.html --fix   (auto-apply safe fixes)
"""
import re
import sys
from pathlib import Path


def decode(raw):
    return (raw.replace("&amp;", "&").replace("&quot;", '"')
               .replace("&#60;", "<").replace("&#62;", ">"))

def encode(html):
    return (html.replace("&", "&amp;").replace('"', "&quot;")
               .replace("<", "&#60;").replace(">", "&#62;"))

# ─────────────────────────────────────────────────────────────────────────────
# Individual checks — each returns list of issue strings, empty = pass
# ─────────────────────────────────────────────────────────────────────────────

def check_sub_zindex(html, idx):
    """CONSTRAINT 1 & 12: .sub must have z-index:1"""
    issues = []
    sub = re.search(r'\.sub\s*\{([^}]+)\}', html)
    if sub and 'z-index' not in sub.group(1):
        issues.append("sub missing z-index:1")
    return issues

def check_chart_clears_sub(html, idx):
    """CONSTRAINT 2: chart top must be >= sub.top + 25"""
    issues = []
    sub = re.search(r'\.sub\s*\{[^}]*?top:\s*(\d+)px', html)
    if not sub:
        return issues
    sub_top = int(sub.group(1))
    # Find chart top (any of these class names)
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

def check_position_absolute_on_children(html, idx):
    """CONSTRAINT 3: common nested elements must have position:absolute"""
    issues = []
    needs_absolute = ['.num-badge', '.enabler-text', '.big', '.small']
    for cls in needs_absolute:
        key = cls.lstrip('.')
        m = re.search(r'\.' + key + r'\s*\{([^}]+)\}', html)
        if m and 'left' in m.group(1) and 'position' not in m.group(1):
            issues.append(f"{cls} uses left/top without position:absolute")
    return issues

def check_svg_hgrid_lines(html, idx):
    """CONSTRAINT 5: horizontal SVG grid lines must not start at x1=0"""
    issues = []
    bad = re.findall(r'<line x1="0" y1="\d+" x2="\d+" y2="\d+"', html)
    if bad:
        issues.append(f"{len(bad)} horizontal grid lines start at x1=0 (cut through label column)")
    return issues

def check_svg_vgrid_lines(html, idx):
    """CONSTRAINT 6: vertical SVG grid lines must not start at y1=0 if a header row exists"""
    issues = []
    # Detect if slide has a header row (phase or quarter rects at y=0)
    has_header = bool(re.search(r'<rect[^>]+y="0"[^>]+height="\d+"[^>]*/>', html))
    if not has_header:
        return issues
    bad = re.findall(r'<line x1="(\d+)" y1="0" x2="\1" y2="\d+"', html)
    if bad:
        issues.append(f"{len(bad)} vertical grid lines start at y1=0 inside header area")
    return issues

def check_header_rect_stroke(html, idx):
    """CONSTRAINT 7: phase/section header rects must not have stroke"""
    issues = []
    # Header rects: y=0 with height <= 40 and a stroke
    bad = re.findall(
        r'<rect[^>]+y="0"[^>]+height="\d{1,2}"[^>]+stroke="[^n][^>]+"',
        html
    )
    if bad:
        issues.append(f"{len(bad)} header rect(s) have stroke (creates visual dividers)")
    return issues

def check_label_color_vs_bar(html, idx):
    """CONSTRAINT 8: text-anchor=end labels must not share fill with the bar they anchor against"""
    issues = []
    rects = []
    for m in re.finditer(r'<rect x="([\d.]+)"[^>]+width="([\d.]+)"[^>]+fill="(#[0-9A-Fa-f]{6})"', html):
        x, w, fill = float(m.group(1)), float(m.group(2)), m.group(3)
        if fill not in ('#FAFAFA', '#FFFFFF', '#F0F0F0', '#E8E8E8'):
            rects.append((x, x + w, fill))
    # Only flag text-anchor="end" labels — these extend LEFT into the bar
    for m in re.finditer(r'<text x="([\d.]+)"[^>]*text-anchor="end"[^>]*fill="(#[0-9A-Fa-f]{6})"[^>]*>[\d.%]+<', html):
        tx, tfill = float(m.group(1)), m.group(2)
        for (rx, rx_end, rfill) in rects:
            # text-anchor=end: text extends LEFT from tx; overlaps bar if tx > rx and tx < rx_end+5
            if rfill == tfill and tx > rx and tx < rx_end + 5:
                issues.append(
                    f"text-anchor=end label fill={tfill} at x={tx:.0f} overlaps bar "
                    f"(bar {rx:.0f}-{rx_end:.0f} same fill) — label invisible"
                )
    return issues

def check_svg_bottom_clearance(html, idx):
    """CONSTRAINT 9: axis title must have >= 10px clearance before SVG height"""
    issues = []
    svgs = re.finditer(r'<svg[^>]+height="(\d+)"[^>]*viewBox="0 0 \d+ \1"', html)
    for svg_m in svgs:
        svgh = int(svg_m.group(1))
        # find the last y or cy value in this SVG block (rough — scan next 8000 chars)
        block_start = svg_m.start()
        block = html[block_start:block_start + 8000]
        y_vals = [int(v) for v in re.findall(r'\b(?:y|cy)="(\d+)"', block) if int(v) <= svgh]
        if not y_vals:
            continue
        last_y = max(y_vals)
        if svgh - last_y < 10:
            issues.append(
                f"SVG height={svgh} but last element at y={last_y} "
                f"(only {svgh - last_y}px clearance — content likely clipped)"
            )
    return issues

def check_annotation_box_overflow(html, idx):
    """CONSTRAINT 11: annotation rects must not exceed SVG viewBox width"""
    issues = []
    svgs = re.finditer(r'<svg[^>]+viewBox="0 0 (\d+) \d+"', html)
    for svg_m in svgs:
        vw = int(svg_m.group(1))
        block = html[svg_m.start():svg_m.start() + 8000]
        for rm in re.finditer(r'<rect x="([\d.]+)"[^>]+width="([\d.]+)"', block):
            rx, rw = float(rm.group(1)), float(rm.group(2))
            if rx + rw > vw + 1:
                issues.append(
                    f"rect x={rx:.0f} width={rw:.0f} extends to {rx+rw:.0f} "
                    f"(SVG viewBox width={vw}) — annotation overflow"
                )
    return issues


# ─────────────────────────────────────────────────────────────────────────────
# Auto-fix: safe mechanical corrections (add z-index, fix grid line origins)
# ─────────────────────────────────────────────────────────────────────────────

def autofix(html, idx, issues):
    """Apply safe automatic fixes for the most common, unambiguous patterns."""
    changed = []

    # Fix 1: add z-index:1 to .sub if missing
    if any("sub missing z-index" in i for i in issues):
        before = html
        html = re.sub(r'(\.sub\s*\{)', r'\1z-index:1;', html)
        if html != before:
            changed.append("added z-index:1 to .sub")

    # Fix 2: horizontal grid lines starting at x1=0
    if any("horizontal grid lines start at x1=0" in i for i in issues):
        # Determine label column width from first vertical grid line or default 180
        vline = re.search(r'<line x1="(\d+)" y1="\d+" x2="\1" y2="\d+"', html)
        label_w = vline.group(1) if vline else "180"
        before = html
        html = re.sub(
            r'<line x1="0" y1="(\d+)" x2="(\d+)" y2="\1"',
            lambda m: f'<line x1="{label_w}" y1="{m.group(1)}" x2="{m.group(2)}" y2="{m.group(1)}"',
            html
        )
        if html != before:
            changed.append(f"shifted horizontal grid lines to x1={label_w}")

    # Fix 3: vertical grid lines starting at y1=0 when header rects exist
    if any("vertical grid lines start at y1=0" in i for i in issues):
        # Determine header height from tallest y=0 rect
        header_rects = re.findall(r'<rect[^>]+y="0"[^>]+height="(\d+)"', html)
        header_h = max(int(h) for h in header_rects) if header_rects else 50
        before = html
        html = re.sub(
            r'(<line x1="(\d+)" )y1="0"( x2="\2" y2="\d+")',
            lambda m: m.group(0).replace('y1="0"', f'y1="{header_h}"'),
            html
        )
        if html != before:
            changed.append(f"shifted vertical grid lines to y1={header_h}")

    # Fix 4: remove stroke from header rects (y=0, height <= 40)
    if any("header rect" in i and "stroke" in i for i in issues):
        before = html
        html = re.sub(
            r'(<rect[^>]+y="0"[^>]+height="\d{1,2}"[^>]+) stroke="[^"]+"',
            r'\1',
            html
        )
        if html != before:
            changed.append("removed stroke from header rects")

    # Fix 5: chart clearance — push chart/chart-wrap/col top down to clear subtitle
    for issue in issues:
        m = re.search(
            r'([\w\-\\b]+) top:(\d+) too close to sub top:(\d+) \(need >= (\d+)\)',
            issue
        )
        if m:
            cls_raw  = m.group(1)           # e.g. "chart-wrap" or "chart\b"
            cur_top  = m.group(2)
            req_top  = m.group(4)
            # Build CSS regex that matches the class name (strip \b word boundary marker)
            cls_name = cls_raw.replace(r'\b', '')
            pattern  = (r'(\.' + re.escape(cls_name) +
                        r'[\w\-]*\s*\{[^}]*?)top:\s*' + re.escape(cur_top) + r'px')
            before = html
            html = re.sub(pattern, rf'\g<1>top:{req_top}px', html, flags=re.DOTALL)
            if html != before:
                changed.append(f".{cls_name} top pushed {cur_top}px -> {req_top}px")

    return html, changed


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

ALL_CHECKS = [
    check_sub_zindex,
    check_chart_clears_sub,
    check_position_absolute_on_children,
    check_svg_hgrid_lines,
    check_svg_vgrid_lines,
    check_header_rect_stroke,
    check_label_color_vs_bar,
    check_svg_bottom_clearance,
    check_annotation_box_overflow,
]

def validate_deck(deck_path: Path, apply_fixes: bool = False):
    deck = deck_path.read_text(encoding="utf-8", errors="ignore")
    matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))
    print(f"Validating {deck_path.name} — {len(matches)} slides\n")

    total_issues = 0
    total_fixes = 0

    for idx, m in enumerate(matches):
        html = decode(m.group(1))
        slide_issues = []
        for check in ALL_CHECKS:
            slide_issues.extend(check(html, idx))

        if slide_issues:
            total_issues += len(slide_issues)
            print(f"  Slide idx {idx} — {len(slide_issues)} issue(s):")
            for issue in slide_issues:
                print(f"    FAIL: {issue}")

            if apply_fixes:
                fixed_html, changes = autofix(html, idx, slide_issues)
                if changes:
                    total_fixes += len(changes)
                    for c in changes:
                        print(f"    AUTO-FIXED: {c}")
                    # Re-query matches for correct byte positions after each replacement
                    matches_fresh = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))
                    mf = matches_fresh[idx]
                    deck = deck[:mf.start()] + 'srcdoc="' + encode(fixed_html) + '"' + deck[mf.end():]
        else:
            print(f"  Slide idx {idx} — OK")

    print(f"\nTotal issues found: {total_issues}")
    if apply_fixes:
        print(f"Total auto-fixes applied: {total_fixes}")
        if total_fixes:
            out = deck.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
            deck_path.write_text(out, encoding="ascii")
            print(f"Saved {deck_path.name}")

    return total_issues


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_slides.py <deck.html> [--fix]")
        sys.exit(1)
    path = Path(sys.argv[1])
    fix = "--fix" in sys.argv
    issues = validate_deck(path, apply_fixes=fix)
    sys.exit(0 if issues == 0 else 1)
