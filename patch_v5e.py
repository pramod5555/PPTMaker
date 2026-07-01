"""patch_v5e.py — Fix inappropriate yellow (#FFFF40) usages

All yellow landed on large chart bars/bubbles on light backgrounds = blinding/invisible.
Replace with appropriate petrol variants:

IDX 7 (Hold Period Roadmap / Gantt):
  ESG Compliance bar fill:    #FFFF40 -> #A6CAD8  (petrol 20%, lightest teal)
  ESG bar label text:         #FFFFFF -> #333333  (white-on-yellow -> dark-on-light-teal)
  ESG milestone diamond:      stroke #FFFF40 -> #A6CAD8

IDX 8 (IRR vs Risk scatter):
  Venture bubble fill:        #FFFF40 -> #79AEBF  (petrol 40%)
  Venture external label:     fill #FFFF40 -> #00677F  (petrol, readable on white)
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


def fix_idx7(html):
    changes = []

    # 1. ESG bar fill: big rect at y=426 width=540 fill=yellow -> petrol 20%
    old = '<rect x="540" y="426" width="540" height="28" rx="4" fill="#FFFF40"/>'
    new = '<rect x="540" y="426" width="540" height="28" rx="4" fill="#A6CAD8"/>'
    if old in html:
        html = html.replace(old, new)
        changes.append("ESG bar fill -> #A6CAD8")

    # 2. ESG bar label text: white-on-yellow -> dark-on-teal
    old = '<text x="810" y="444" font-size="11" font-weight="700" fill="#FFFFFF" text-anchor="middle" font-family="Arial, Helvetica, sans-serif">ESG certified</text>'
    new = '<text x="810" y="444" font-size="11" font-weight="700" fill="#333333" text-anchor="middle" font-family="Arial, Helvetica, sans-serif">ESG certified</text>'
    if old in html:
        html = html.replace(old, new)
        changes.append("ESG label text -> #333333")

    # 3. ESG diamond milestone stroke: yellow -> petrol 20%
    old = '<rect x="1076" y="436" width="8" height="8" fill="#FFFFFF" stroke="#FFFF40" transform="rotate(45 1080 440)"/>'
    new = '<rect x="1076" y="436" width="8" height="8" fill="#FFFFFF" stroke="#A6CAD8" transform="rotate(45 1080 440)"/>'
    if old in html:
        html = html.replace(old, new)
        changes.append("ESG diamond stroke -> #A6CAD8")

    print(f"  IDX 7: {', '.join(changes) if changes else 'NO MATCH — check patterns'}")
    return html


def fix_idx8(html):
    changes = []

    # 1. Venture bubble: yellow fill -> petrol 40%
    old = '<circle cx="612.5" cy="134" r="6.07" fill="#FFFF40"/>'
    new = '<circle cx="612.5" cy="134" r="6.07" fill="#79AEBF"/>'
    if old in html:
        html = html.replace(old, new)
        changes.append("Venture bubble -> #79AEBF")

    # 2. Venture external label: yellow text -> petrol (readable on white)
    old = '<text x="621" y="134" font-size="8" font-weight="700" fill="#FFFF40" text-anchor="start">Venture</text>'
    new = '<text x="621" y="134" font-size="8" font-weight="700" fill="#00677F" text-anchor="start">Venture</text>'
    if old in html:
        html = html.replace(old, new)
        changes.append("Venture label -> #00677F")

    print(f"  IDX 8: {', '.join(changes) if changes else 'NO MATCH — check patterns'}")
    return html


def main():
    deck = DECK.read_text(encoding="ascii", errors="ignore")
    matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))

    for idx, fix_fn in [(8, fix_idx8), (7, fix_idx7)]:
        m = matches[idx]
        html = decode(m.group(1))
        fixed = fix_fn(html)
        if fixed != html:
            deck = deck[:m.start()] + 'srcdoc="' + encode(fixed) + '"' + deck[m.end():]

    DECK.write_text(deck, encoding="ascii")

    # Verify no yellow remains
    remaining = [m.start() for m in re.finditer(r'#FFFF40', deck, re.IGNORECASE)]
    if remaining:
        print(f"\nWARNING: {len(remaining)} #FFFF40 still present in deck")
    else:
        print("\nVerified: no #FFFF40 remaining in deck")

if __name__ == "__main__":
    main()
