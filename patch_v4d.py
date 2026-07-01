"""patch_v4d.py - Fix round-4 layout issues in full_deck_v4.html

Fixes:
  idx 2  (slide 3)  CEO Priority Shift  - '74' label invisible on red bar
  idx 5  (slide 6)  Productivity        - legend + axis cramped at bottom
  idx 7  (slide 8)  Gantt               - remove horizontal separator in header
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


# ── Slide 3 (idx 2): "74" label on red bar invisible (same colour as bar) ───────
def fix_s2(html):
    # Bar ends at x=213.2; text at text-anchor="end" x=217 puts "7" over the bar
    # Switch to left-align starting just past bar end at x=215
    html = html.replace(
        'x="217" y="41" text-anchor="end" font-family="Arial, Helvetica, sans-serif" font-size="9" font-weight="700" fill="#C41230">74',
        'x="215" y="41" font-family="Arial, Helvetica, sans-serif" font-size="9" font-weight="700" fill="#C41230">74'
    )
    print("  Slide 3: '74' label repositioned to left-align at x=215 (past bar end)")
    return html


# ── Slide 6 (idx 5): legend + axis cramped at bottom of dot-plot ────────────────
def fix_s5(html):
    # Current: legend cy=490, axis ticks y=504, axis title y=518, SVG height=520
    # Target:  legend cy=510, axis ticks y=524, axis title y=538, SVG height=550
    # Also update chart div height to match

    # Legend circles (cy=490 -> cy=510)
    html = html.replace(' cy="490" r="7" fill="#E8E8E8"', ' cy="510" r="7" fill="#E8E8E8"')
    html = html.replace(' cy="490" r="9" fill="#C41230"', ' cy="510" r="9" fill="#C41230"')

    # Legend text labels (y=494 -> y=514)
    html = html.replace(
        '"490" font-size="10" fill="#555555">Without AI',
        '"510" font-size="10" fill="#555555">Without AI'
    )
    html = html.replace(
        '"494" font-size="10" fill="#555555">Without AI',
        '"514" font-size="10" fill="#555555">Without AI'
    )
    html = html.replace(
        '"490" font-size="10" fill="#555555">With AI augmentation',
        '"510" font-size="10" fill="#555555">With AI augmentation'
    )
    html = html.replace(
        '"494" font-size="10" fill="#555555">With AI augmentation',
        '"514" font-size="10" fill="#555555">With AI augmentation'
    )

    # Axis tick labels (y=504 -> y=524)
    for tick in ['0%', '15%', '30%', '45%', '60%']:
        html = html.replace(
            f'y="504" font-size="9" fill="#888888" text-anchor="middle">{tick}',
            f'y="524" font-size="9" fill="#888888" text-anchor="middle">{tick}'
        )

    # Axis title (y=518 -> y=538)
    html = html.replace(
        'y="518" font-size="10" fill="#555555" text-anchor="middle">Productivity improvement',
        'y="538" font-size="10" fill="#555555" text-anchor="middle">Productivity improvement'
    )

    # SVG height 520 -> 550
    html = re.sub(
        r'(<svg\s[^>]*?)height="520"([^>]*viewBox="0 0 780 )520"',
        r'\g<1>height="550"\g<2>550"',
        html
    )
    # Chart div height 520 -> 550
    html = re.sub(
        r'(\.chart\s*\{[^}]*?)height:\s*520px',
        r'\g<1>height:550px', html, flags=re.DOTALL
    )

    print("  Slide 6: legend+axis pushed down 20px; SVG + div height -> 550px")
    return html


# ── Slide 8 (idx 7): remove y=30 separator line inside header area ───────────────
def fix_s7(html):
    # This line runs between the phase-header row and the quarter-label row
    html = html.replace(
        '<line x1="180" y1="30" x2="1152" y2="30" stroke="#E8E8E8"/>',
        ''
    )
    print("  Slide 8: removed y=30 phase/quarter separator line")
    return html


# ── Dispatch + main ───────────────────────────────────────────────────────────────
def patch_slide(html, idx):
    if idx == 2: return fix_s2(html)
    if idx == 5: return fix_s5(html)
    if idx == 7: return fix_s7(html)
    return html

def main():
    deck = DECK.read_text(encoding="utf-8", errors="ignore")
    print(f"Patching {DECK.name}")
    targets = {2, 5, 7}
    changed = 0
    for i in sorted(targets, reverse=True):
        matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))
        if i >= len(matches):
            print(f"  idx {i}: out of range"); continue
        m = matches[i]
        html = decode(m.group(1))
        fixed = patch_slide(html, i)
        if fixed != html:
            changed += 1
            deck = deck[:m.start()] + 'srcdoc="' + encode(fixed) + '"' + deck[m.end():]
        else:
            print(f"  idx {i}: NO CHANGE (check patterns)")
    if changed:
        out = deck.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
        DECK.write_text(out, encoding="ascii")
        print(f"\n{changed} slides patched -> {DECK.name}")
    else:
        print("\nNo changes applied.")

if __name__ == "__main__":
    main()
