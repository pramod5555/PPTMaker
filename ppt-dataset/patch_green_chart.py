"""Direct CSS patch: fix slide 8 (green chart) headline wrap + sub overlap."""
import re
from pathlib import Path

deck_path = Path(__file__).parent.parent / "full_deck_v3.html"
deck = deck_path.read_text(encoding="utf-8", errors="ignore")

matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))
print(f"Slides in deck: {len(matches)}")

idx = 7  # slide 8 (0-based)
raw = matches[idx].group(1)

# Decode srcdoc encoding
html = (raw.replace("&amp;", "&")
           .replace("&quot;", '"')
           .replace("&#60;", "<")
           .replace("&#62;", ">"))

print(f"Slide 8 has 'GREEN TRANSITION': {'GREEN TRANSITION' in html}")
print(f"Slide 8 has '.headline' class: {'.headline' in html}")

# Find and show the current headline CSS block
m = re.search(r'\.headline\{.*?\}', html, re.DOTALL)
if m:
    print("Current .headline CSS:", repr(m.group(0)[:200]))

# Fix 1: reduce headline font-size from 20px → 17px
html_fixed = re.sub(
    r'(\.headline\{[^}]*?)font-size:20px',
    r'\g<1>font-size:17px',
    html,
    flags=re.DOTALL
)

# Fix 2: move .sub top from 68px → 62px (headline at 17px×1.2=20px tall, ends at top:52; sub at 62 = 10px gap)
html_fixed = re.sub(
    r'(\.sub\{[^}]*?)top:68px',
    r'\g<1>top:62px',
    html_fixed,
    flags=re.DOTALL
)

changed = html != html_fixed
print(f"Changes made: {changed}")

if changed:
    # Re-encode for srcdoc
    safe = (html_fixed
            .replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&#60;")
            .replace(">", "&#62;"))

    m = matches[idx]
    deck_new = deck[:m.start()] + 'srcdoc="' + safe + '"' + deck[m.end():]
    deck_ascii = deck_new.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
    deck_path.write_text(deck_ascii, encoding="ascii")
    print("Saved -> full_deck_v3.html")
else:
    # Debug: show what's around font-size in the html
    loc = html.find("font-size:20px")
    print(f"'font-size:20px' found at pos {loc}")
    if loc >= 0:
        print("Context:", repr(html[max(0,loc-200):loc+50]))
