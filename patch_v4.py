"""
patch_v4.py - Fix 7 layout issues in full_deck_v4.html

Slide 1  (idx 0): Pill widths too narrow for text - remove fixed width, reposition h2/h3
Slide 5  (idx 4): IT/Infra bar overflows SVG right edge - recompute group x positions
Slide 6  (idx 5): chart-wrap overlaps subtitle - push chart down 20px
Slide 7  (idx 6): Tiny red arrow SVG between columns - remove it
Slide 8  (idx 7): Legend outside viewBox, milestone labels inside bars - fix both
Slide 9  (idx 8): Axis label too close to tick numbers - move down
Slide 11 (idx 10): Headline overlaps card tops - push cards down 12px
"""
import re
from pathlib import Path

DECK = Path(__file__).parent.parent / "full_deck_v4.html"

def decode(raw):
    return (raw.replace("&amp;", "&").replace("&quot;", '"')
               .replace("&#60;", "<").replace("&#62;", ">"))

def encode(html):
    return (html.replace("&", "&amp;").replace('"', "&quot;")
               .replace("<", "&#60;").replace(">", "&#62;"))

def patch_slide(html, idx):
    if idx == 0:
        return fix_cover_pills(html)
    elif idx == 4:
        return fix_investment_bars(html)
    elif idx == 5:
        return fix_productivity_overlap(html)
    elif idx == 6:
        return fix_op_model_arrow(html)
    elif idx == 7:
        return fix_gantt_legend(html)
    elif idx == 8:
        return fix_risk_axis(html)
    elif idx == 10:
        return fix_case_study_overlap(html)
    return html


# ── Slide 1: pill widths ───────────────────────────────────────────────────────
def fix_cover_pills(html):
    # Remove explicit widths from h1/h2/h3, spread pills across available space
    # h1 stays at left:72, h2 moves to 278, h3 moves to 388
    html = re.sub(r'(\.h1\s*\{[^}]*?)width:\s*\d+px', r'\g<1>', html, flags=re.DOTALL)
    html = re.sub(r'(\.h2\s*\{[^}]*?)width:\s*\d+px', r'\g<1>', html, flags=re.DOTALL)
    html = re.sub(r'(\.h3\s*\{[^}]*?)width:\s*\d+px', r'\g<1>', html, flags=re.DOTALL)
    # Reposition h2 and h3
    html = re.sub(r'(\.h2\s*\{[^}]*?)left:\s*214px', r'\g<1>left:278px', html, flags=re.DOTALL)
    html = re.sub(r'(\.h3\s*\{[^}]*?)left:\s*313px', r'\g<1>left:388px', html, flags=re.DOTALL)
    print("  Slide 1: pill widths removed, h2/h3 repositioned")
    return html


# ── Slide 5: grouped bar overflow ─────────────────────────────────────────────
def fix_investment_bars(html):
    # New group x positions (spacing 88px):
    # Old: 90,185,280,375,470,565,660,755
    # New: 90,178,266,354,442,530,618,706
    # Shifts: 0,-7,-14,-21,-28,-35,-42,-49

    # For each group 2-8 (0-indexed 1-7), shift all x-values by delta
    # Elements per group: 2022-bar, 2025-bar, growth-text, label-text(s)

    old_positions = [185, 280, 375, 470, 565, 660, 755]
    new_positions = [178, 266, 354, 442, 530, 618, 706]

    for old_gx, new_gx in zip(old_positions, new_positions):
        delta = new_gx - old_gx
        # 2022 bar: rect x="<old_gx>"
        html = html.replace(f'rect x="{old_gx}"', f'rect x="{new_gx}"', 1)
        # 2025 bar: rect x="<old_gx+44>"
        old2 = old_gx + 44
        new2 = new_gx + 44
        html = html.replace(f'rect x="{old2}"', f'rect x="{new2}"', 1)
        # growth % text: x="<old_gx+62>"  (center of 2025 bar)
        old3 = old_gx + 44 + 18  # 44 offset + half of 36px bar
        new3 = new_gx + 44 + 18
        html = html.replace(f'text x="{old3}"', f'text x="{new3}"', 1)
        # function labels: two text elements at x="<old_gx+40>"
        old4 = old_gx + 40  # approx center of group
        new4 = new_gx + 40
        # Replace up to 2 occurrences (main + sub label)
        html = html.replace(f'text x="{old4}"', f'text x="{new4}"', 2)

    # Recompute label x for group 1 (stays at 90): labels were at x=130 → stays
    # Fix group 2 label from 225 to 218 (done via 185+40=225 → 178+40=218 above)

    # Move annotation box from x=484 to x=550 (closer to IT/Infra area, now at 706)
    html = html.replace('rect x="484"', 'rect x="556"', 1)
    # Annotation text lines at x=496 → x=568
    html = html.replace('<text x="496"', '<text x="568"', 2)

    print("  Slide 5: bar positions recomputed, IT/Infra now ends at x=786 (within 820)")
    return html


# ── Slide 6: chart-wrap overlaps subtitle ─────────────────────────────────────
def fix_productivity_overlap(html):
    # Move chart-wrap from top:86px → top:110px (below sub that ends at ~106px)
    html = re.sub(r'(\.chart-wrap\s*\{[^}]*?)top:\s*86px', r'\g<1>top:110px', html, flags=re.DOTALL)
    # Reduce height to compensate: 520→496px so bottom stays at 606px
    html = re.sub(r'(\.chart-wrap\s*\{[^}]*?)height:\s*520px', r'\g<1>height:496px', html, flags=re.DOTALL)
    # Move panel down too: top:86 → 110
    html = re.sub(r'(\.panel\s*\{[^}]*?)top:\s*86px', r'\g<1>top:110px', html, flags=re.DOTALL)
    html = re.sub(r'(\.panel\s*\{[^}]*?)height:\s*520px', r'\g<1>height:496px', html, flags=re.DOTALL)
    # Move panel-title: top:102 → 126
    html = re.sub(r'(\.panel-title\s*\{[^}]*?)top:\s*102px', r'\g<1>top:126px', html, flags=re.DOTALL)
    # Move insight blocks: block1 130→154, block2 280→304, block3 430→454
    html = re.sub(r'(\.block1\s*\{[^}]*?)top:\s*130px', r'\g<1>top:154px', html, flags=re.DOTALL)
    html = re.sub(r'(\.block2\s*\{[^}]*?)top:\s*280px', r'\g<1>top:304px', html, flags=re.DOTALL)
    html = re.sub(r'(\.block3\s*\{[^}]*?)top:\s*430px', r'\g<1>top:454px', html, flags=re.DOTALL)
    print("  Slide 6: chart-wrap moved to top:110px, panel/blocks adjusted")
    return html


# ── Slide 7: remove tiny red arrow SVG ────────────────────────────────────────
def fix_op_model_arrow(html):
    # Remove the 16x32px arrow SVG between columns
    pattern = r'<svg\s+style="left:424px;\s*top:284px;[^"]*"[^>]*>.*?</svg>'
    html, n = re.subn(pattern, '', html, count=1, flags=re.DOTALL)
    if n == 0:
        # Try alternate format
        pattern2 = r'<svg[^>]*left:424px[^>]*>.*?</svg>'
        html, n = re.subn(pattern2, '', html, count=1, flags=re.DOTALL)
    print(f"  Slide 7: arrow SVG {'removed' if n else 'not found - check manually'}")
    return html


# ── Slide 8: Gantt legend outside viewBox + milestone label positions ──────────
def fix_gantt_legend(html):
    # 1. Remove legend items from x:1140 area (7 items)
    old_legend = """    <!-- Legend -->
    <rect x="1140" y="50" width="8" height="8" fill="#C41230"/>
    <text x="1152" y="57" font-size="9" fill="#555555">Strategy</text>

    <rect x="1140" y="70" width="8" height="8" fill="#0D4D8C"/>
    <text x="1152" y="77" font-size="9" fill="#555555">Technology</text>

    <rect x="1140" y="90" width="8" height="8" fill="#1A1A1A"/>
    <text x="1152" y="97" font-size="9" fill="#555555">Leadership</text>

    <rect x="1140" y="110" width="8" height="8" fill="#888888"/>
    <text x="1152" y="117" font-size="9" fill="#555555">Pilots</text>

    <rect x="1140" y="130" width="8" height="8" fill="#B35C00"/>
    <text x="1152" y="137" font-size="9" fill="#555555">Risk</text>

    <rect x="1140" y="150" width="8" height="8" fill="#1B7A3E"/>
    <text x="1152" y="157" font-size="9" fill="#555555">Talent</text>

    <rect x="1140" y="170" width="8" height="8" fill="#555555"/>
    <text x="1152" y="177" font-size="9" fill="#555555">Review</text>"""

    new_legend = """    <!-- Legend (repositioned inside SVG at left margin) -->
    <rect x="5" y="62" width="8" height="8" fill="#C41230"/>
    <text x="17" y="69" font-size="8" fill="#555555">Strategy</text>

    <rect x="5" y="77" width="8" height="8" fill="#0D4D8C"/>
    <text x="17" y="84" font-size="8" fill="#555555">Technology</text>

    <rect x="5" y="92" width="8" height="8" fill="#1A1A1A"/>
    <text x="17" y="99" font-size="8" fill="#555555">Leadership</text>

    <rect x="5" y="107" width="8" height="8" fill="#888888"/>
    <text x="17" y="114" font-size="8" fill="#555555">Pilots</text>

    <rect x="5" y="122" width="8" height="8" fill="#B35C00"/>
    <text x="17" y="129" font-size="8" fill="#555555">Risk</text>

    <rect x="5" y="137" width="8" height="8" fill="#1B7A3E"/>
    <text x="17" y="144" font-size="8" fill="#555555">Talent</text>

    <rect x="5" y="152" width="8" height="8" fill="#555555"/>
    <text x="17" y="159" font-size="8" fill="#555555">Review</text>"""

    if old_legend in html:
        html = html.replace(old_legend, new_legend)
        print("  Slide 8: legend moved to x:5 (left margin)")
    else:
        # Fallback: just replace all x="1140" rect/text in legend area
        html = re.sub(r'(<rect x=")1140(" y="(?:50|70|90|110|130|150|170)" width="8")', lambda m: m.group(0).replace('x="1140"', 'x="5"'), html)
        html = re.sub(r'(<text x=")1152(" y="(?:57|77|97|117|137|157|177)")', lambda m: m.group(0).replace('x="1152"', 'x="17"'), html)
        print("  Slide 8: legend repositioned (fallback regex)")

    # 2. Fix milestone label y positions: all are 1px inside bar top, move 9px above
    # Pattern: milestone labels near top of each bar
    old_milestone_ys = [59, 119, 179, 239, 299, 359, 419, 479]
    new_milestone_ys = [50, 110, 170, 230, 290, 350, 410, 470]
    milestone_xs = [1134, 784, 425, 668, 549, 913, 1132, 1090]

    replacements = [
        (f'x="{mx}" y="{oy}"', f'x="{mx}" y="{ny}"')
        for mx, oy, ny in zip(milestone_xs, old_milestone_ys, new_milestone_ys)
    ]
    for old, new in replacements:
        if old in html:
            html = html.replace(old, new, 1)
        else:
            print(f"    WARNING: '{old}' not found in gantt slide")

    print("  Slide 8: milestone labels moved above bar tops")
    return html


# ── Slide 9: axis label overlap ───────────────────────────────────────────────
def fix_risk_axis(html):
    # Move "Implementation Risk" from y:478 to y:496
    html = html.replace(
        'x="400" y="478" font-size="10" fill="#555555" text-anchor="middle">Implementation Risk',
        'x="400" y="496" font-size="10" fill="#555555" text-anchor="middle">Implementation Risk'
    )
    # Also move x-axis tick numbers up slightly for cleaner separation: 473→474 (minor)
    # Not needed - just moving the label is sufficient
    print("  Slide 9: Implementation Risk label moved to y:496")
    return html


# ── Slide 11: headline overlaps card tops ─────────────────────────────────────
def fix_case_study_overlap(html):
    # Move .card top from 72px to 86px (+14)
    html = re.sub(r'(\.card\s*\{[^}]*?)top:\s*72px', r'\g<1>top:86px', html, flags=re.DOTALL)

    # Shift all internal elements +14px using inline style top values
    # Elements at: 88,108,136,152,232,252,360,384,482 (left card)
    # and: 88,108,136,152,232,252,360,384,482 (right card - same relative positions)
    shifts = {
        'top:88px': 'top:102px',   # tag
        'top:108px': 'top:122px',  # title
        'top:136px': 'top:150px',  # mini-rule
        'top:152px': 'top:166px',  # challenge
        'top:232px': 'top:246px',  # section-label / approach
        'top:252px': 'top:266px',  # bullets
        'top:360px': 'top:374px',  # results label
        'top:384px': 'top:398px',  # metric row 1
        'top:482px': 'top:496px',  # metric row 2
    }
    for old, new in shifts.items():
        # replace all occurrences (affects both left and right cards)
        html = html.replace(old, new)

    print("  Slide 11: cards and content moved down 14px, headline no longer overlaps")
    return html


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    deck = DECK.read_text(encoding="utf-8", errors="ignore")
    print(f"Patching slides in {DECK.name}")
    print()

    targets = {0, 4, 5, 6, 7, 8, 10}
    changed = 0

    # Process in REVERSE index order so that replacing a later slide does not
    # shift the byte positions of earlier slides (deck grows/shrinks from the end).
    for i in sorted(targets, reverse=True):
        matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))
        if i >= len(matches):
            print(f"  Slide {i+1}: index out of range (only {len(matches)} slides)")
            continue
        m = matches[i]
        raw = m.group(1)
        html = decode(raw)
        html_fixed = patch_slide(html, i)

        if html_fixed != html:
            changed += 1
            safe = encode(html_fixed)
            deck = deck[:m.start()] + 'srcdoc="' + safe + '"' + deck[m.end():]

    if changed:
        deck_ascii = deck.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
        DECK.write_text(deck_ascii, encoding="ascii")
        print(f"\n{changed} slides patched -> {DECK.name}")
    else:
        print("\nNo changes made.")

if __name__ == "__main__":
    main()
