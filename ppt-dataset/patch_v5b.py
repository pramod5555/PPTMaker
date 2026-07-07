"""patch_v5b.py — Full palette swap for full_deck_v5.html

New palette (from user-provided color reference):
  Primary accent:  #00677F  (Petrol)
  Accent dark:     #004355  (Petrol +40K)
  Accent medium:   #007A93  (Petrol 80%)
  Accent light:    #5097AB  (Petrol 60%)
  Accent lighter:  #79AEBF  (Petrol 40%)
  Accent lightest: #A6CAD8  (Petrol 20%)
  Highlight:       #FFFF40  (Yellow — SVG fills only, not text)

Mapping from old Bain-red palette:
  #C41230 (red)      → #00677F (petrol)
  #8B0000 (dark red) → #004355 (dark petrol)
  #1B7A3E (green)    → #007A93 (petrol 80%)
  #0D4D8C (blue)     → #5097AB (petrol 60%)
  #B35C00 (orange text) → #007A93 (petrol 80%)
  #B35C00 (orange SVG fills) → #FFFF40 (yellow)
  #5C2D91 (purple)   → #79AEBF (petrol 40%)
  Cover right panel  → #004355 (dark petrol background)
  CTA dark bg        → #002E3D (very dark petrol)
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


def fix_cover(html):
    # Right dark panel → dark petrol instead of near-black grey
    html = html.replace(
        'left:717px;top:0;width:563px;height:720px;background:#1A1A1A;',
        'left:717px;top:0;width:563px;height:720px;background:#004355;'
    )
    # Also update the divider line colour from grey to white (subtle on dark petrol)
    html = html.replace(
        'left:717px;top:0;width:1px;height:720px;background:#E6E6E6;',
        'left:717px;top:0;width:1px;height:720px;background:#00677F;'
    )
    return html


def global_swap(deck: str) -> str:
    """Apply ordered colour swaps to the raw deck string."""

    # ── Step 1: context-specific replacements BEFORE catch-all ──────────────
    # Orange text/background → petrol (yellow on white would be invisible)
    ctx_swaps = [
        ('color:#B35C00',      'color:#007A93'),
        ('color:#b35c00',      'color:#007a93'),
        ('background:#B35C00', 'background:#007A93'),
        ('background:#b35c00', 'background:#007a93'),
        # border accents with orange → petrol
        ('border:#B35C00',         'border:#007A93'),
        ('border-left:3px solid #B35C00', 'border-left:3px solid #007A93'),
        ('border-left:4px solid #B35C00', 'border-left:4px solid #007A93'),
        # Dark slide backgrounds → very dark petrol
        ('background:#0A0A0A', 'background:#002E3D'),
        ('background:#0a0a0a', 'background:#002e3d'),
        # FAFAFA with slight petrol tint on card/chart backgrounds
        ('#FAFAFA', '#EFF7FA'),
        ('#fafafa', '#eff7fa'),
    ]
    for old, new in ctx_swaps:
        deck = deck.replace(old, new)

    # ── Step 2: catch-all hex colour replacements ────────────────────────────
    hex_swaps = [
        # Primary accent: red → petrol
        ('#C41230', '#00677F'),
        ('#c41230', '#00677f'),
        # Dark accent: dark red → dark petrol
        ('#8B0000', '#004355'),
        ('#8b0000', '#004355'),
        # Green → petrol 80%
        ('#1B7A3E', '#007A93'),
        ('#1b7a3e', '#007a93'),
        # Blue → petrol 60%
        ('#0D4D8C', '#5097AB'),
        ('#0d4d8c', '#5097ab'),
        # Orange remaining (SVG fills = chart bars/bubbles) → yellow
        ('#B35C00', '#FFFF40'),
        ('#b35c00', '#ffff40'),
        # Purple → petrol 40%
        ('#5C2D91', '#79AEBF'),
        ('#5c2d91', '#79aebf'),
        # Rules/borders: E8 grey → cool grey with petrol tint
        ('#E8E8E8', '#DCE9ED'),
        ('#e8e8e8', '#dce9ed'),
        # Chart gridlines: F0F0F0 → very light petrol tint
        ('#F0F0F0', '#EAF3F6'),
        ('#f0f0f0', '#eaf3f6'),
    ]
    for old, new in hex_swaps:
        deck = deck.replace(old, new)

    return deck


def main():
    deck = DECK.read_text(encoding="ascii", errors="ignore")
    original_len = len(deck)

    # 1. Fix cover slide first (before global swap changes colours)
    matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))
    m0 = matches[0]
    h0 = decode(m0.group(1))
    h0_fixed = fix_cover(h0)
    deck = deck[:m0.start()] + 'srcdoc="' + encode(h0_fixed) + '"' + deck[m0.end():]

    # 2. Global palette swap
    deck = global_swap(deck)

    # 3. Save
    DECK.write_text(deck, encoding="ascii")

    # 4. Verification
    print("Palette swap complete:")
    print(f"  Red #C41230 removed:   {'#C41230' not in deck and '#c41230' not in deck}")
    print(f"  Petrol #00677F present: {'#00677F' in deck or '#00677f' in deck}")
    print(f"  Yellow #FFFF40 present: {'#FFFF40' in deck or '#ffff40' in deck}")
    print(f"  Cover dark petrol:      {'#004355' in deck}")
    print(f"  CTA dark petrol:        {'#002E3D' in deck or '#002e3d' in deck}")
    print(f"  File size delta: {len(deck) - original_len:+d} bytes")

if __name__ == "__main__":
    main()
