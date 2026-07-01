"""Fix slide 14 (geo risk matrix, index 13): headline wraps → sub overlap."""
import re
from pathlib import Path

deck_path = Path(__file__).parent.parent / "full_deck_v3.html"
deck = deck_path.read_text(encoding="utf-8", errors="ignore")
matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))

idx = 13  # slide 14
raw = matches[idx].group(1)
html = (raw.replace("&amp;", "&").replace("&quot;", '"')
           .replace("&#60;", "<").replace("&#62;", ">"))

print("GEOPOLITICS in slide:", "GEOPOLITICS" in html)

# Show current headline CSS
m = re.search(r'\.headline\{.*?\}', html, re.DOTALL)
if m:
    print("headline CSS:", repr(m.group(0)))

# Show current sub CSS
m2 = re.search(r'\.sub\{.*?\}', html, re.DOTALL)
if m2:
    print("sub CSS:", repr(m2.group(0)))

# Fix: reduce headline from 21px -> 16px (fits ~100 chars in 960px: 100*9.5=950 < 960)
html_fixed = re.sub(r'(\.headline\{[^}]*?)font-size:21px', r'\g<1>font-size:16px', html, flags=re.DOTALL)
# Move sub down to clear a single-line headline (16px*1.2=19px, ends at 32+19=51; sub at 60)
html_fixed = re.sub(r'(\.sub\{[^}]*?)top:\d+px', r'\g<1>top:60px', html_fixed, flags=re.DOTALL)

changed = html != html_fixed
print(f"Changed: {changed}")

if changed:
    safe = (html_fixed.replace("&", "&amp;").replace('"', "&quot;")
                      .replace("<", "&#60;").replace(">", "&#62;"))
    m = matches[idx]
    deck_new = deck[:m.start()] + 'srcdoc="' + safe + '"' + deck[m.end():]
    deck_ascii = deck_new.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
    deck_path.write_text(deck_ascii, encoding="ascii")
    print("Saved.")
else:
    loc21 = html.find("font-size:21px")
    print(f"font-size:21px at pos {loc21}")
    if loc21 >= 0:
        print(repr(html[max(0,loc21-300):loc21+50]))
