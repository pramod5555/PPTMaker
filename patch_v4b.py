"""patch_v4b.py - Fix round-2 layout issues in full_deck_v4.html"""
import re
from pathlib import Path

DECK = Path(__file__).parent.parent / "full_deck_v4.html"

def decode(raw):
    return (raw.replace("&amp;","&").replace("&quot;",'"')
               .replace("&#60;","<").replace("&#62;",">"))

def encode(html):
    return (html.replace("&","&amp;").replace('"',"&quot;")
               .replace("<","&#60;").replace(">","&#62;"))

def patch_slide(html, idx):
    if idx == 4: return fix_s4(html)
    if idx == 5: return fix_s5(html)
    if idx == 6: return fix_s6(html)
    if idx == 7: return fix_s7(html)
    if idx == 8: return fix_s8(html)
    if idx == 9: return fix_s9(html)
    return html

# ── Slide 5 (idx 4): subtitle z-index + annotation box overflow ───────────────
def fix_s4(html):
    html = re.sub(r'(\.sub\s*\{)', r'\1z-index:1;', html)
    # Move annotation box from x=556 to x=440, widen to 230
    html = html.replace('rect x="556" y="40" width="200"', 'rect x="440" y="40" width="230"')
    html = html.replace('text x="568" y="58"', 'text x="452" y="58"')
    html = html.replace('text x="568" y="74"', 'text x="452" y="74"')
    print("  Slide 5: sub z-index added; annotation box moved to x=440")
    return html

# ── Slide 6 (idx 5): subtitle z-index + panel-title/metric overlap ────────────
def fix_s5(html):
    html = re.sub(r'(\.sub\s*\{)', r'\1z-index:1;', html)
    html = html.replace('.block-border1{top:130px;', '.block-border1{top:148px;')
    html = html.replace('.metric1{top:132px;', '.metric1{top:150px;')
    html = html.replace('.copy1{top:178px;}', '.copy1{top:196px;}')
    print("  Slide 6: sub z-index; metric1 moved to 150px, copy1 to 196px")
    return html

# ── Slide 7 (idx 6): enabler left pos + num-badge/enabler-text position ──────
def fix_s6(html):
    html = re.sub(r'(\.sub\s*\{)', r'\1z-index:1;', html)
    html = re.sub(r'(\.num-badge\s*\{)', r'\1position:absolute;', html)
    html = re.sub(r'(\.enabler-text\s*\{)', r'\1position:absolute;', html)
    # Fix each enabler left from CSS 24px to inline 840px
    html = re.sub(
        r'<div class="enabler" style="top:(\d+)px;">',
        lambda m: f'<div class="enabler" style="top:{m.group(1)}px;left:840px;">',
        html
    )
    # Fix timeline left position
    html = html.replace(
        '<div class="timeline">',
        '<div class="timeline" style="left:840px;">'
    )
    print("  Slide 7: enablers moved to left:840px; num-badge/enabler-text have position:absolute")
    return html

# ── Slide 8 (idx 7): Gantt horizontal lines don't cut through label area ──────
def fix_s7(html):
    # Change horizontal lines starting at x=0 to start at x=180 (bar area only)
    html = re.sub(
        r'<line x1="0" y1="(\d+)" x2="1152" y2="\1"',
        lambda m: f'<line x1="180" y1="{m.group(1)}" x2="1152" y2="{m.group(1)}"',
        html
    )
    print("  Slide 8: horizontal grid lines now start at x=180 (skip label/legend area)")
    return html

# ── Slide 9 (idx 8): subtitle z-index on risk/reward ─────────────────────────
def fix_s8(html):
    html = re.sub(r'(\.sub\s*\{)', r'\1z-index:1;', html)
    print("  Slide 9: sub z-index added")
    return html

# ── Slide 10 (idx 9): board priorities — add position:absolute to all layout elements
def fix_s9(html):
    extra = """
  .left-panel>.row{position:absolute;}
  .row>div{position:absolute;}
  .right-panel>div{position:absolute;box-sizing:border-box;}
  .right-panel>svg{position:absolute;}
"""
    html = html.replace('</style>', extra + '</style>', 1)
    print("  Slide 10: added position:absolute to .row, .row>div, .right-panel children")
    return html

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    deck = DECK.read_text(encoding="utf-8", errors="ignore")
    print(f"Patching {DECK.name}")
    targets = {4, 5, 6, 7, 8, 9}
    changed = 0
    for i in sorted(targets, reverse=True):
        matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))
        if i >= len(matches):
            print(f"  idx {i}: out of range")
            continue
        m = matches[i]
        html = decode(m.group(1))
        fixed = patch_slide(html, i)
        if fixed != html:
            changed += 1
            deck = deck[:m.start()] + 'srcdoc="' + encode(fixed) + '"' + deck[m.end():]
    if changed:
        out = deck.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
        DECK.write_text(out, encoding="ascii")
        print(f"\n{changed} slides patched -> {DECK.name}")
    else:
        print("\nNo changes.")

if __name__ == "__main__":
    main()
