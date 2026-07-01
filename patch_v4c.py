"""patch_v4c.py - Fix round-3 layout issues in full_deck_v4.html

Fixes:
  idx 4  (slide 5)  Investment Architecture  - push chart below subtitle
  idx 5  (slide 6)  Productivity dot-plot    - push chart below subtitle
  idx 6  (slide 7)  Operating Model          - push columns/content below subtitle
  idx 7  (slide 8)  Gantt                    - remove red borders from phase headers
  idx 8  (slide 9)  Risk vs Reward           - push chart/panel below headline+subtitle
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


# ── Slide 5 (idx 4): push chart-wrap and right-panel down below subtitle ────────
def fix_s4(html):
    # sub ends at top:103 + ~15px ≈ 118px; move both panels to top:128
    html = re.sub(
        r'(\.chart-wrap\s*\{[^}]*?)top:\s*86px',
        r'\g<1>top:128px', html, flags=re.DOTALL
    )
    html = re.sub(
        r'(\.right-panel\s*\{[^}]*?)top:\s*86px',
        r'\g<1>top:128px', html, flags=re.DOTALL
    )
    print("  Slide 5: chart-wrap + right-panel moved to top:128px")
    return html


# ── Slide 6 (idx 5): push .chart down below subtitle ────────────────────────────
def fix_s5(html):
    # sub is at top:86px (1 line, ~12px) → ends at ~102px; move chart to top:112
    html = re.sub(
        r'(\.chart\s*\{[^}]*?)top:\s*86px',
        r'\g<1>top:112px', html, flags=re.DOTALL
    )
    print("  Slide 6: .chart moved to top:112px")
    return html


# ── Slide 7 (idx 6): shift all column content down 20px below subtitle ──────────
def fix_s6(html):
    # sub at top:76px + ~15px = 91px; cols were at 86px (5px gap) → move to 106px
    # CSS: .bottom 606→626, .timeline 466→486
    html = re.sub(
        r'(\.bottom\s*\{[^}]*?)top:\s*606px',
        r'\g<1>top:626px', html, flags=re.DOTALL
    )
    html = re.sub(
        r'(\.timeline\s*\{[^}]*?)top:\s*466px',
        r'\g<1>top:486px', html, flags=re.DOTALL
    )

    # Body inline top values: only shift below </style> to avoid touching CSS values
    style_end = html.find('</style>') + len('</style>')
    head = html[:style_end]
    body = html[style_end:]

    # Ordered so longer strings don't partially match shorter ones
    shifts = [
        ('top:408px', 'top:428px'),  # enabler 4
        ('top:324px', 'top:344px'),  # enabler 3
        ('top:320px', 'top:340px'),  # SVG icons
        ('top:258px', 'top:278px'),  # bullet 4
        ('top:240px', 'top:260px'),  # enabler 2
        ('top:222px', 'top:242px'),  # bullet 3
        ('top:186px', 'top:206px'),  # bullet 2
        ('top:156px', 'top:176px'),  # enabler 1
        ('top:150px', 'top:170px'),  # bullet 1
        ('top:120px', 'top:140px'),  # col titles
        ('top:102px', 'top:122px'),  # col badges
        ('top:86px',  'top:106px'),  # col background boxes
    ]
    for old, new in shifts:
        body = body.replace(old, new)

    print("  Slide 7: all layout elements shifted down 20px; .bottom->626, .timeline->486")
    return head + body


# ── Slide 8 (idx 7): remove red borders from Foundation/Scale/Optimize phase headers
def fix_s7(html):
    # Scale and Optimize have stroke="#C41230"; change to match Foundation's grey
    html = html.replace(
        'width="240" height="30" fill="#FAFAFA" stroke="#C41230"',
        'width="240" height="30" fill="#FAFAFA" stroke="#E8E8E8"'
    )
    print("  Slide 8: Scale + Optimize phase header borders changed to #E8E8E8")
    return html


# ── Slide 9 (idx 8): push chart-wrap + insights panel + all right-side rows down ─
def fix_s8(html):
    # Headline at top:84 (ends ~104), sub at top:115 (ends ~130); chart/panel → top:140
    html = re.sub(
        r'(\.chart-wrap\s*\{[^}]*?)top:\s*86px',
        r'\g<1>top:140px', html, flags=re.DOTALL
    )
    html = re.sub(
        r'(\.insights\s*\{[^}]*?)top:\s*86px',
        r'\g<1>top:140px', html, flags=re.DOTALL
    )
    # Trim insights height so bottom aligns with row content (~606px)
    html = re.sub(
        r'(\.insights\s*\{[^}]*?)height:\s*520px',
        r'\g<1>height:466px', html, flags=re.DOTALL
    )
    # Shift panel-title and rows +54px (all are direct children of .slide)
    shifts = [
        (r'(\.panel-title\s*\{[^}]*?)top:\s*102px', r'\g<1>top:156px'),
        (r'(\.row1\s*\{[^}]*?)top:\s*134px',        r'\g<1>top:188px'),
        (r'(\.row2\s*\{[^}]*?)top:\s*238px',        r'\g<1>top:292px'),
        (r'(\.row3\s*\{[^}]*?)top:\s*342px',        r'\g<1>top:396px'),
        (r'(\.row4\s*\{[^}]*?)top:\s*446px',        r'\g<1>top:500px'),
    ]
    for pat, repl in shifts:
        html = re.sub(pat, repl, html, flags=re.DOTALL)

    print("  Slide 9: chart+insights moved to top:140; panel-title+rows shifted +54px")
    return html


# ── Dispatch + main ───────────────────────────────────────────────────────────────
def patch_slide(html, idx):
    if idx == 4: return fix_s4(html)
    if idx == 5: return fix_s5(html)
    if idx == 6: return fix_s6(html)
    if idx == 7: return fix_s7(html)
    if idx == 8: return fix_s8(html)
    return html

def main():
    deck = DECK.read_text(encoding="utf-8", errors="ignore")
    print(f"Patching {DECK.name}")
    targets = {4, 5, 6, 7, 8}
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
