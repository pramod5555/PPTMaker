"""patch_v5a.py — Round-1 layout fixes for full_deck_v5.html

Fixes:
  idx  2  Exec Summary    — "4%" bar label to left of bar; bullet-3 crowds bullet-2
  idx  4  Value Creation  — "AI-ENABLED LEVERS" covered by first data row dot/line
  idx  5  Capital Scatter — small/grey bubble labels invisible (white on #CCCCCC)
  idx  8  IRR vs Risk     — same bubble label issue for small/light fill bubbles
  idx  9  LP Priorities   — all rows collapse (position:absolute children w/o positioned parent)
                          — SVG "Impact" y-axis label overlaps tick numbers
  idx 10  Case Studies    — headline at top:58 overlaps with card at top:72
"""
import re
from pathlib import Path

DECK = Path(__file__).parent.parent / "full_deck_v5.html"

def decode(raw):
    return (raw.replace("&amp;","&").replace("&quot;",'"')
               .replace("&#60;","<").replace("&#62;",">"))

def encode(html):
    return (html.replace("&","&amp;").replace('"',"&quot;")
               .replace("<","&#60;").replace(">","&#62;"))


# ── idx 2: Exec Summary ──────────────────────────────────────────────────────────
def fix_s2(html):
    # 1. "4%" label div at left:1047 is BEFORE the bar start (bar starts at SVG x=80
    #    offset by svg left:972 = page x=1052, bar 4%*2.8=11.2px → ends at 1063).
    #    Move label from 1047 to 1068 (5px past bar end).
    html = html.replace(
        'left:1047px;top:375px;width:18px;font-size:9px;line-height:12px;font-weight:700;color:#1A1A1A;">4%',
        'left:1068px;top:375px;width:18px;font-size:9px;line-height:12px;font-weight:700;color:#1A1A1A;">4%'
    )
    # 2. Bullet-2 text wraps to 2 lines (~33px tall), bottom at ~483.
    #    Bullet-3 at top:488 gives only 5px gap. Push bullet-3 to top:520.
    html = html.replace(
        'style="left:64px;top:488px;height:24px;"',
        'style="left:64px;top:520px;height:24px;"'
    )
    print("  IDX 2: '4%' label -> left:1068; bullet-3 -> top:520")
    return html


# ── idx 4: Value Creation dot-plot ───────────────────────────────────────────────
def fix_s4(html):
    # "AI-ENABLED LEVERS" text at y=24 is covered by first data row (y=20, r=9 dots).
    # White mask rect at y=12 height=14 (y=12..26) should mask the dashed box line,
    # but the connector (y=20) draws ON TOP of the mask text.
    # Fix: raise mask to y=2 height=14 and raise text to y=12.
    html = html.replace(
        '<rect x="301" y="12" width="98" height="14" fill="#FAFAFA"/>',
        '<rect x="300" y="2" width="124" height="14" fill="#FAFAFA"/>'
    )
    html = html.replace(
        '<text x="304" y="24" font-size="8" font-weight="700" fill="#C41230">AI-ENABLED LEVERS</text>',
        '<text x="304" y="12" font-size="8" font-weight="700" fill="#C41230">AI-ENABLED LEVERS</text>'
    )
    print("  IDX 4: AI-ENABLED LEVERS label -> y=12 (above first data row at y=20)")
    return html


# ── idx 5: Capital Allocation scatter ────────────────────────────────────────────
def fix_s5(html):
    changes = []
    # Traditional Retail (r=14, fill=#CCCCCC) — white text on light grey = invisible
    for line in ['Traditional', 'Retail']:
        old = f'text-anchor="middle" font-size="8" font-weight="700" fill="#FFFFFF">{line}</text>'
        new = f'text-anchor="middle" font-size="8" font-weight="700" fill="#333333">{line}</text>'
        if old in html:
            html = html.replace(old, new)
            changes.append(f"Trad Retail '{line}' -> dark fill")

    # Energy (r=12, fill=#CCCCCC) — same: white invisible on grey
    html = html.replace(
        'text-anchor="middle" font-size="8" font-weight="700" fill="#FFFFFF">Energy</text>',
        'text-anchor="middle" font-size="8" font-weight="700" fill="#333333">Energy</text>'
    )
    changes.append("Energy label -> dark fill")

    # Financial Svcs (r=10, fill=#555555) — too small for 2-line internal text
    # Replace both lines with single external label to the right of bubble
    html = re.sub(
        r'<text x="187" y="295"[^>]*fill="#FFFFFF">Financial</text>\s*'
        r'<text x="187" y="304"[^>]*fill="#FFFFFF">Svcs</text>',
        '<text x="200" y="297" text-anchor="start" font-size="8" font-weight="700" fill="#555555">Fin Svcs</text>',
        html
    )
    changes.append("Financial Svcs -> external label right")

    # Real Estate (r=10, fill=#CCCCCC) — tiny + light fill
    html = re.sub(
        r'<text x="165" y="399"[^>]*fill="#FFFFFF">Real</text>\s*'
        r'<text x="165" y="408"[^>]*fill="#FFFFFF">Estate</text>',
        '<text x="153" y="396" text-anchor="end" font-size="8" font-weight="700" fill="#555555">Real Estate</text>',
        html
    )
    changes.append("Real Estate -> external label left")

    print(f"  IDX 5: bubble label fixes: {'; '.join(changes)}")
    return html


# ── idx 8: IRR vs Risk scatter ────────────────────────────────────────────────────
def fix_s8(html):
    changes = []
    # AI Buyout (r=8.59, fill=#C41230) — 2-line "AI/Buy" inside 17px diameter bubble
    html = html.replace(
        '<text x="186.5" y="79.5" font-size="8" font-weight="700" fill="#FFFFFF" text-anchor="middle">AI</text>',
        ''
    )
    html = html.replace(
        '<text x="186.5" y="88.5" font-size="8" font-weight="700" fill="#FFFFFF" text-anchor="middle">Buy</text>',
        '<text x="196" y="77" font-size="8" font-weight="700" fill="#C41230" text-anchor="start">AI Buyout</text>'
    )
    changes.append("AI Buyout -> external right")

    # HC AI (r=6.97, fill=#C41230) — very tiny 2-line "HC/AI"
    html = html.replace(
        '<text x="222" y="127" font-size="8" font-weight="700" fill="#FFFFFF" text-anchor="middle">HC</text>',
        ''
    )
    html = html.replace(
        '<text x="222" y="136" font-size="8" font-weight="700" fill="#FFFFFF" text-anchor="middle">AI</text>',
        '<text x="231" y="124" font-size="8" font-weight="700" fill="#C41230" text-anchor="start">HC AI</text>'
    )
    changes.append("HC AI -> external right")

    # Infra AI (r=7.83, fill=#0D4D8C) — tiny 2-line "Infra/AI"
    html = html.replace(
        '<text x="151" y="193.5" font-size="8" font-weight="700" fill="#FFFFFF" text-anchor="middle">Infra</text>',
        ''
    )
    html = html.replace(
        '<text x="151" y="202.5" font-size="8" font-weight="700" fill="#FFFFFF" text-anchor="middle">AI</text>',
        '<text x="161" y="191" font-size="8" font-weight="700" fill="#0D4D8C" text-anchor="start">Infra AI</text>'
    )
    changes.append("Infra AI -> external right")

    # Venture (r=6.07, fill=#B35C00) — extremely tiny, move "Vent" outside
    html = html.replace(
        '<text x="612.5" y="136.5" font-size="8" font-weight="700" fill="#FFFFFF" text-anchor="middle">Vent</text>',
        '<text x="621" y="134" font-size="8" font-weight="700" fill="#B35C00" text-anchor="start">Venture</text>'
    )
    changes.append("Venture -> external right")

    # Real Assets (r=12.79, fill=#E8E8E8) — near-white fill, labels hard to see at this size
    html = html.replace(
        '<text x="257.5" y="284" font-size="8" font-weight="700" fill="#1A1A1A" text-anchor="middle">Real</text>',
        ''
    )
    html = html.replace(
        '<text x="257.5" y="293" font-size="8" font-weight="700" fill="#1A1A1A" text-anchor="middle">Ast</text>',
        '<text x="272" y="287" font-size="8" font-weight="700" fill="#888888" text-anchor="start">Real Assets</text>'
    )
    changes.append("Real Assets -> external right")

    print(f"  IDX 8: {'; '.join(changes)}")
    return html


# ── idx 9: LP Priorities ──────────────────────────────────────────────────────────
def fix_s9(html):
    # ROOT CAUSE: .list is position:absolute (from .slide > div rule).
    # .row has no position set → static block flow inside .list.
    # BUT .row > div (badge, score-circle, title, desc, trend) have position:absolute →
    # they are positioned relative to .list (not their parent .row).
    # All 6 rows' children stack at the same coordinates inside .list.
    # FIX: Add position:relative to .row so absolute children anchor to their row.
    # Also remove inline top/left from .row divs (top:88px would add double spacing
    # on top of natural flow when position:relative is set).
    html = re.sub(
        r'(\.row\s*\{)',
        r'\1\n    position:relative;',
        html
    )
    # Remove top/left inline style from row divs (they now flow naturally)
    html = re.sub(
        r'(<div class="row") style="left:0;\s*top:\d+px;"',
        r'\1',
        html
    )
    # Fix SVG Impact y-axis label: "Impact" rotated at x=15 overlaps tick labels (x=6-18)
    html = html.replace(
        'x="15" y="132" transform="rotate(-90 15 132)"',
        'x="3" y="132" transform="rotate(-90 3 132)"'
    )
    print("  IDX 9: .row position:relative added; row inline styles removed; Impact label x=3")
    return html


# ── idx 10: Case Studies ──────────────────────────────────────────────────────────
def fix_s10(html):
    # Headline at top:58 (line-height:19 → ends at ~77px).
    # .card top:72 starts inside headline area. Move to 90px.
    before = html
    html = re.sub(
        r'(\.card\s*\{[^}]*?)top:\s*72px',
        r'\g<1>top:90px',
        html, flags=re.DOTALL
    )
    if html == before:
        # Fallback: try inline style version
        html = html.replace('style="top:72px', 'style="top:90px')
    print("  IDX 10: .card top: 72px -> 90px")
    return html


# ── Dispatch ─────────────────────────────────────────────────────────────────────
def patch_slide(html, idx):
    if idx == 2:  return fix_s2(html)
    if idx == 4:  return fix_s4(html)
    if idx == 5:  return fix_s5(html)
    if idx == 8:  return fix_s8(html)
    if idx == 9:  return fix_s9(html)
    if idx == 10: return fix_s10(html)
    return html

def main():
    deck = DECK.read_text(encoding="utf-8", errors="ignore")
    print(f"Patching {DECK.name}")
    targets = {2, 4, 5, 8, 9, 10}
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
