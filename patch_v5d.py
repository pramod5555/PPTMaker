"""patch_v5d.py — Follow-up consistency fixes after patch_v5c

Fixes:
  IDX 1  .eyebrow top:16 → 20px,  .title top:34 → 40px
  IDX 2  Remove duplicate injected top bar (original inline bar already existed)
  IDX 4  .title top:68 → 40px  (class name differs from .headline)
  IDX 5  .head  top:62 → 40px  (class name differs from .headline)
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

def css_set(html, cls, prop, value):
    pattern = rf'(\.{re.escape(cls)}\s*\{{[^}}]*?){re.escape(prop)}:\s*[\w\-]+(?:px|em|%)?'
    return re.sub(pattern, rf'\g<1>{prop}:{value}', html, flags=re.DOTALL)


def fix_idx1(html):
    html = css_set(html, 'eyebrow', 'top', '20px')
    html = css_set(html, 'title',   'top', '40px')
    return html

def fix_idx2(html):
    # Remove the duplicate injected bar (has position:absolute and height:4px)
    # Keep the original inline bar (no position:absolute, height:3px)
    dup = '<div style="position:absolute;left:0;top:0;width:1280px;height:4px;background:#00677F;"></div>\n  '
    html = html.replace(dup, '', 1)
    return html

def fix_idx4(html):
    return css_set(html, 'title', 'top', '40px')

def fix_idx5(html):
    return css_set(html, 'head', 'top', '40px')


FIXES = {1: fix_idx1, 2: fix_idx2, 4: fix_idx4, 5: fix_idx5}

def main():
    deck = DECK.read_text(encoding="ascii", errors="ignore")
    matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))

    for idx in sorted(FIXES, reverse=True):
        m = matches[idx]
        html = decode(m.group(1))
        fixed = FIXES[idx](html)
        if fixed != html:
            deck = deck[:m.start()] + 'srcdoc="' + encode(fixed) + '"' + deck[m.end():]
            print(f"  [{idx}] fixed")
        else:
            print(f"  [{idx}] NO CHANGE")

    DECK.write_text(deck, encoding="ascii")
    print("Done.")

if __name__ == "__main__":
    main()
