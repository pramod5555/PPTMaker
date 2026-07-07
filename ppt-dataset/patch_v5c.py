"""patch_v5c.py — Layout consistency standardisation for full_deck_v5.html

Targets:
  Top accent bar:  left:0; top:0; width:1280px; height:4px; background:#00677F
  .kicker:         top:20px
  .headline:       top:40px
  .sub:            top:78px
  Divider .rule:   top:66px; left:64px; width:1152px; height:1px
  Footer source:   top:686px
  Page number:     font-weight:400  (normalise bold → regular)

Slides skipped: IDX 0 (cover), IDX 11 (CTA) — both have custom layouts.
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


# ── CSS class block patchers ──────────────────────────────────────────────────

def css_set(html, cls, prop, value, flags=re.DOTALL):
    """Replace `prop:Xunit` inside `.cls { ... }` block."""
    pattern = rf'(\.{re.escape(cls)}\s*\{{[^}}]*?){re.escape(prop)}:\s*[\w\-]+(?:px|em|%)?'
    return re.sub(pattern, rf'\g<1>{prop}:{value}', html, flags=flags)

def css_ensure(html, cls, prop, value):
    """Add `prop:value` to `.cls { }` if the prop is absent."""
    m = re.search(rf'\.{re.escape(cls)}\s*\{{([^}}]+)\}}', html, re.DOTALL)
    if m and re.escape(prop) not in m.group(1).replace('-', r'\-'):
        new_block = m.group(1).rstrip() + f'\n    {prop}:{value};'
        return html[:m.start()] + f'.{cls}{{{new_block}}}' + html[m.end():]
    return html

def has_css_class(html, cls):
    return bool(re.search(rf'\.{re.escape(cls)}\s*\{{', html))


# ── Top accent bar helpers ────────────────────────────────────────────────────

TOP_BAR_HTML = '<div style="position:absolute;left:0;top:0;width:1280px;height:4px;background:#00677F;"></div>\n  '

def fix_rule_top_css(html):
    """Standardise .rule-top or .top-grad CSS block to full-width at top:0."""
    for cls in ('rule-top', 'top-grad'):
        if not has_css_class(html, cls):
            continue
        html = css_set(html, cls, 'left', '0')
        html = css_set(html, cls, 'top', '0')
        html = css_set(html, cls, 'width', '1280px')
        html = css_set(html, cls, 'height', '4px')
    return html

def fix_rule_class(html):
    """
    .rule used as TOP BAR (top <= 50px) → move to top:0, full width.
    .rule used as DIVIDER (top > 50px) → standardise to top:66px, left:64px, width:1152px.
    """
    m = re.search(r'\.rule\s*\{([^}]+)\}', html, re.DOTALL)
    if not m:
        return html
    block = m.group(1)
    top_m = re.search(r'top:\s*(\d+)px', block)
    if not top_m:
        return html
    top_val = int(top_m.group(1))

    if top_val <= 50:
        # It's the top accent bar — pull it to y=0, full width
        block = re.sub(r'top:\s*\d+px',    'top:0',          block)
        block = re.sub(r'left:\s*\d+px',   'left:0',         block)
        block = re.sub(r'width:\s*\d+px',  'width:1280px',   block)
        block = re.sub(r'height:\s*\d+px', 'height:4px',     block)
    else:
        # It's a divider line below the headline
        block = re.sub(r'top:\s*\d+px',   'top:66px',    block)
        block = re.sub(r'left:\s*\d+px',  'left:64px',   block)
        block = re.sub(r'width:\s*\d+px', 'width:1152px', block)
        # Ensure thin height
        if 'height' not in block:
            block = block.rstrip() + '\n    height:1px;'
        else:
            block = re.sub(r'height:\s*\d+px', 'height:1px', block)

    return html[:m.start()] + '.rule{' + block + '}' + html[m.end():]

def inject_top_bar_if_missing(html):
    """Add a top accent bar div for slides that have neither .rule-top, .top-grad, nor a top .rule."""
    has_top_bar = (
        has_css_class(html, 'rule-top') or
        has_css_class(html, 'top-grad') or
        TOP_BAR_HTML.strip() in html
    )
    if has_top_bar:
        return html

    # Check if .rule exists and is used as top bar (top <= 50px)
    m = re.search(r'\.rule\s*\{([^}]+)\}', html, re.DOTALL)
    if m:
        top_m = re.search(r'top:\s*(\d+)px', m.group(1))
        if top_m and int(top_m.group(1)) <= 50:
            return html  # .rule IS the top bar

    # Inject after <div class="slide">
    html = re.sub(
        r'(<div class="slide">)',
        r'\1\n  ' + TOP_BAR_HTML.strip(),
        html, count=1
    )
    return html


# ── Header element position normalisation ────────────────────────────────────

def fix_header_positions(html):
    """Normalise kicker / headline / sub top positions."""
    if has_css_class(html, 'kicker'):
        html = css_set(html, 'kicker', 'top', '20px')
    if has_css_class(html, 'headline'):
        html = css_set(html, 'headline', 'top', '40px')
    if has_css_class(html, 'sub'):
        html = css_set(html, 'sub', 'top', '78px')
    return html


# ── Footer / page-number normalisation ───────────────────────────────────────

def fix_footer(html):
    """
    Standardise footer elements:
    - footer source text  → top:686px
    - page number         → font-weight:400  and position at top:686 / right:64px
    """
    # Source footer text (left-aligned): normalise top
    for cls in ('footer-left', 'footer-source', 'footer', 'footer-note'):
        if not has_css_class(html, cls):
            continue
        # Remove bottom-based positioning and replace with top:686px
        m = re.search(rf'\.{re.escape(cls)}\s*\{{([^}}]+)\}}', html, re.DOTALL)
        if not m:
            continue
        block = m.group(1)
        if 'bottom:' in block:
            block = re.sub(r'bottom:\s*[\w]+;?', 'top:686px;', block)
        elif 'top:' in block:
            block = re.sub(r'top:\s*\d+px', 'top:686px', block)
        else:
            block = block.rstrip() + '\n    top:686px;'
        html = html[:m.start()] + f'.{cls}{{{block}}}' + html[m.end():]

    # Page number (right-aligned): font-weight:400 and position
    for cls in ('footer-page', 'footer-right', 'slide-num', 'page-num'):
        if not has_css_class(html, cls):
            continue
        # Normalise font-weight
        if f'font-weight' in html:
            html = re.sub(
                rf'(\.{re.escape(cls)}\s*\{{[^}}]*?font-weight:\s*)\d+',
                r'\g<1>400',
                html, flags=re.DOTALL
            )
        m = re.search(rf'\.{re.escape(cls)}\s*\{{([^}}]+)\}}', html, re.DOTALL)
        if not m:
            continue
        block = m.group(1)
        # Standardise to right:64px and top:686px (remove bottom-based)
        if 'bottom:' in block:
            block = re.sub(r'bottom:\s*[\w]+;?', 'top:686px;', block)
        if 'top:' in block:
            block = re.sub(r'top:\s*\d+px', 'top:686px', block)
        else:
            block = block.rstrip() + '\n    top:686px;'
        html = html[:m.start()] + f'.{cls}{{{block}}}' + html[m.end():]

    # Also catch inline page-number divs near the bottom (top:67x or top:68x or top:69x)
    # that might have font-weight:700 → change to 400
    html = re.sub(
        r'(top:\s*6[6-9]\d[^;]*;[^"]*?font-weight:\s*)700',
        r'\g<1>400',
        html
    )
    # Standardise inline footer divs at top:67x/68x/69x to top:686
    def normalise_footer_top(m2):
        s = m2.group(0)
        top_m = re.search(r'top:\s*(\d+)px', s)
        if top_m:
            t = int(top_m.group(1))
            if 665 <= t <= 705 and t != 686:
                s = re.sub(r'top:\s*\d+px', 'top:686px', s)
        return s
    html = re.sub(r'top:\s*6[5-9]\d[^"]{0,200}', normalise_footer_top, html)

    return html


# ── Per-slide dispatcher ──────────────────────────────────────────────────────

def patch_slide(html, idx):
    log = []

    # 1. Top accent bar
    before = html
    html = fix_rule_top_css(html)
    html = fix_rule_class(html)
    html = inject_top_bar_if_missing(html)
    if html != before: log.append('top-bar fixed')

    # 2. Header positions
    before = html
    html = fix_header_positions(html)
    if html != before: log.append('header tops normalised')

    # 3. Footer
    before = html
    html = fix_footer(html)
    if html != before: log.append('footer normalised')

    return html, log


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    deck = DECK.read_text(encoding="ascii", errors="ignore")
    matches = list(re.finditer(r'srcdoc="([^"]*)"', deck, re.DOTALL))
    total = len(matches)
    print(f"Processing {total} slides in {DECK.name}")

    # Process in reverse index order so string positions stay valid
    for idx in sorted(range(total), reverse=True):
        if idx in (0, 11):
            print(f"  [{idx:2d}] SKIPPED (special layout)")
            continue
        m = matches[idx]
        html = decode(m.group(1))
        fixed, log = patch_slide(html, idx)
        if log:
            deck = deck[:m.start()] + 'srcdoc="' + encode(fixed) + '"' + deck[m.end():]
            print(f"  [{idx:2d}] {', '.join(log)}")
        else:
            print(f"  [{idx:2d}] no changes")

    DECK.write_text(deck, encoding="ascii")
    print("\nDone. Run validate_slides.py to confirm.")

if __name__ == "__main__":
    main()
