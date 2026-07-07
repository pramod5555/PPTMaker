"""
audit_fix_v3.py — Scan all slides in full_deck_v3.html for headline overflow
and fix automatically without API calls.

Overflow formula: text_chars × font_size × 0.55 > container_width
Arial average char width ≈ 0.55 × font-size in px.
"""
import re
from pathlib import Path
from html import unescape

DECK = Path(__file__).parent.parent / "full_deck_v3.html"
AVG_CHAR_RATIO = 0.55  # Arial average char width / font-size

def decode_srcdoc(raw: str) -> str:
    return (raw.replace("&amp;", "&").replace("&quot;", '"')
               .replace("&#60;", "<").replace("&#62;", ">"))

def encode_srcdoc(html: str) -> str:
    return (html.replace("&", "&amp;").replace('"', "&quot;")
               .replace("<", "&#60;").replace(">", "&#62;"))

def get_css_prop(css_block: str, prop: str) -> str | None:
    m = re.search(rf'{re.escape(prop)}:\s*([^;}}]+)', css_block)
    return m.group(1).strip() if m else None

def px(val: str | None) -> int:
    if not val: return 0
    return int(re.sub(r'[^\d]', '', val) or 0)

def strip_tags(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html)

def text_len(html: str) -> int:
    return len(unescape(strip_tags(html)).strip())

def will_overflow(chars: int, font_px: int, width_px: int) -> bool:
    return chars * font_px * AVG_CHAR_RATIO > width_px

def fit_font_size(chars: int, width_px: int, start: int = 21) -> int:
    for fs in range(start, 10, -1):
        if not will_overflow(chars, fs, width_px):
            return fs
    return 12

def fix_slide(html: str, slide_num: int) -> tuple[str, list[str]]:
    fixes = []

    # Find all CSS class blocks
    headline_m = re.search(r'(\.headline\{[^}]+\})', html, re.DOTALL)
    sub_m      = re.search(r'(\.sub\{[^}]+\})',      html, re.DOTALL)

    if not headline_m:
        return html, fixes

    h_css    = headline_m.group(1)
    font_px  = px(get_css_prop(h_css, 'font-size'))
    width_px = px(get_css_prop(h_css, 'width')) or 960
    h_top    = px(get_css_prop(h_css, 'top'))
    lh_raw   = get_css_prop(h_css, 'line-height') or '1.2'
    lh       = float(lh_raw) if lh_raw.replace('.', '').isdigit() else 1.2

    # Find headline element content
    body_m = re.search(r'class="headline"[^>]*>(.*?)<', html, re.DOTALL)
    chars  = text_len(body_m.group(1)) if body_m else 0

    if chars == 0 or font_px == 0:
        return html, fixes

    overflows = will_overflow(chars, font_px, width_px)

    if overflows:
        new_fs = fit_font_size(chars, width_px, font_px)
        fixes.append(f"Slide {slide_num}: headline {chars}ch x {font_px}px overflows {width_px}px -> reduce to {new_fs}px")

        html = html.replace(
            h_css,
            re.sub(rf'font-size:{font_px}px', f'font-size:{new_fs}px', h_css)
        )

        # Recalculate safe sub top: headline_top + 1 line height + 8px
        line_height_px = int(new_fs * lh)
        safe_sub_top   = h_top + line_height_px + 8

        if sub_m:
            s_css    = sub_m.group(1)
            cur_top  = px(get_css_prop(s_css, 'top'))
            if cur_top < safe_sub_top:
                new_s_css = re.sub(rf'top:{cur_top}px', f'top:{safe_sub_top}px', s_css)
                html = html.replace(s_css, new_s_css)
                fixes.append(f"  sub top: {cur_top}px -> {safe_sub_top}px")
    else:
        fixes.append(f"Slide {slide_num}: headline {chars}ch x {font_px}px -> OK ({int(chars*font_px*AVG_CHAR_RATIO)}/{width_px}px)")

    return html, fixes

def main():
    deck = DECK.read_text(encoding="utf-8", errors="ignore")
    matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))
    print(f"Auditing {len(matches)} slides in {DECK.name}\n")

    total_fixes = 0
    for i, m in enumerate(matches):
        raw  = m.group(1)
        html = decode_srcdoc(raw)
        html_fixed, fixes = fix_slide(html, i + 1)

        for f in fixes:
            print(f)

        if html_fixed != html:
            total_fixes += 1
            safe = encode_srcdoc(html_fixed)
            deck = deck[:m.start()] + 'srcdoc="' + safe + '"' + deck[m.end():]
            # Re-find matches after replacement (positions shift)
            matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))

    if total_fixes:
        deck_ascii = deck.encode("ascii", errors="xmlcharrefreplace").decode("ascii")
        DECK.write_text(deck_ascii, encoding="ascii")
        print(f"\n{total_fixes} slide(s) fixed -> {DECK.name}")
    else:
        print("\nAll slides clean — no fixes needed.")

if __name__ == "__main__":
    main()
