# Slide Generation Constraints
Derived from layout bugs found and patched across full_deck_v4.html (rounds 1–4).
These rules MUST be embedded in the generation system prompt and/or verified by validate_slides.py.

---

## 1. Subtitle z-index (CRITICAL)

**Rule:** Every `.sub` CSS class MUST include `z-index:1`.

**Why it breaks:** Chart divs (`chart-wrap`, `chart`, `insights`, etc.) come after `.sub` in DOM order
and have background fills (`#FAFAFA`, `#FFFFFF`). Later DOM elements paint on top of earlier ones
at the same z-index. Without `z-index:1`, the chart background covers subtitle text completely.

**Fix pattern:**
```css
.sub { position:absolute; z-index:1; top:Xpx; ... }
```

---

## 2. Chart must start below subtitle (CRITICAL)

**Rule:** Any element with a solid background (`chart-wrap`, `chart`, `insights`, column `col` divs)
must have its `top` value set BELOW the subtitle's bottom edge.

**Formula:**
```
chart.top >= sub.top + (sub.fontSize * sub.lineHeight) + 10
```
For a typical 12px subtitle with line-height 1.25: `chart.top >= sub.top + 25`.
For slides with both headline (16px) and subtitle (12px): chart must clear the subtitle end, not just the headline.

**Common mistake:** Setting `chart-wrap { top:86px }` when `sub { top:86px }` — they start at the same y.

**Reference fixes:** Slides 5, 6, 7, 9 in v4c patch — all charts moved down 20–54px.

---

## 3. position:absolute does NOT cascade to grandchildren

**Rule:** The slide-level rule `.slide > div { position:absolute }` ONLY reaches direct children of `.slide`.
Any nested element (child of a panel, row, or column div) that needs `left/top` layout MUST have
its own explicit `position:absolute` declaration.

**Elements that always need explicit `position:absolute`:**
- `.num-badge`, `.enabler-text` inside `.enabler`
- `.row > div` (badge, score, title inside a row)
- `.big`, `.small` inside `.row`
- Any icon or label div inside a panel container

**Wrong:**
```css
.num-badge { left:12px; top:12px; }  /* left/top silently ignored — no position set */
```
**Right:**
```css
.num-badge { position:absolute; left:12px; top:12px; }
```

---

## 4. Absolute coordinates relative to nearest positioned ancestor

**Rule:** `left/top` on a `position:absolute` child is measured from its nearest
`position:absolute/relative` ancestor — NOT from the slide.

**Common mistake:** Generating `.enabler { left:24px }` (default slide margin) when the enabler
should be inside a right column at x=840. The enabler's parent is `.slide`, so left:24 positions
it at the slide's left edge, not inside the column.

**Fix:** Use inline styles on each element to set absolute slide coordinates. Never use a CSS class
`left` value as a column position default — it applies to ALL instances of that class.

---

## 5. SVG horizontal grid lines must not enter the label/legend area

**Rule:** Horizontal grid lines (`<line y1="N" x2="maxWidth">`) must start at `x1` equal to the
width of the left label column, NOT at `x1="0"`.

**Formula:** `x1 = labelColumnWidth` (typically 150–200px for role/category labels).

**Wrong:** `<line x1="0" y1="94" x2="1152" y2="94" />`
**Right:** `<line x1="180" y1="94" x2="1152" y2="94" />`

**Why:** Lines starting at x=0 cut through row labels and legend items on the left side.

---

## 6. SVG vertical grid lines must not enter the header row

**Rule:** Vertical grid lines that span the chart height must start at `y1` equal to the
header row height, NOT at `y1="0"`.

**Formula:** `y1 = headerHeight` (sum of all header row heights, e.g., 50px for phase+quarter rows).

**Wrong:** `<line x1="420" y1="0" x2="420" y2="520" />`
**Right:** `<line x1="420" y1="50" x2="420" y2="520" />`

**Why:** Vertical lines from y=0 create visible column separators inside header boxes,
even when the header boxes have no stroke.

---

## 7. SVG section header boxes: no stroke

**Rule:** Phase/section header rects in Gantt or table charts must use `fill` only.
Do NOT add `stroke` to header rects — any stroke creates visible borders that render
as separating lines inside the header row.

**Wrong:** `<rect x="180" y="0" width="240" height="30" fill="#FAFAFA" stroke="#C41230" />`
**Right:** `<rect x="180" y="0" width="240" height="30" fill="#FAFAFA" />`

**Exception:** The OUTER border of the chart container div is acceptable.

---

## 8. SVG value labels: never same color as the bar

**Rule:** A value label (`<text fill="#COLOR">`) positioned at or overlapping a bar rect
with `fill="#COLOR"` will be invisible. Either:
- (a) Position the label PAST the bar end with `text-anchor="start"` at `x = barEnd + 2`
- (b) Use contrasting fill: `fill="#FFFFFF"` for labels inside dark/colored bars

**Wrong:** Bar fills `#C41230`, label at bar end with `fill="#C41230"` and `text-anchor="end"` —
the label partially overlaps the bar and vanishes.

**Right (option a):** `<text x="215" text-anchor="start" fill="#C41230">74</text>` where bar ends at x=213.

**Right (option b):** `<text x="210" text-anchor="end" fill="#FFFFFF">74</text>` inside the bar.

---

## 9. SVG legend and axis must have clear space at bottom

**Rule:** The bottom region of an SVG must be budgeted explicitly:
```
lastDataElementCy           = (computed from data)
legendCirclesCy             = lastDataElementCy + 30   (minimum 30px gap)
legendLabelY                = legendCirclesCy + 5
axisTick_y                  = legendLabelY + 20
axisTitle_y                 = axisTick_y + 14
svgHeight                   = axisTitle_y + 14         (14px buffer below title)
```

**Common mistake:** Setting `svgHeight=520` with axis title at `y=518` — 2px margin means
the title is clipped in many render engines.

---

## 10. Multi-column layouts: always use inline left positions

**Rule:** In multi-column slide layouts where columns are direct `.slide` children,
every column and its associated elements must have `left` set via INLINE STYLE, not a CSS class.

**Why:** A CSS class like `.col { left:24px }` applies to ALL columns. The first column
wants `left:64px`, the second `left:440px`, the third `left:816px`. Using a class default
means every column renders at the same x position, stacked on top of each other.

**Right:**
```html
<div class="col" style="left:64px; top:106px;">...</div>
<div class="col" style="left:440px; top:106px;">...</div>
<div class="col" style="left:816px; top:106px;">...</div>
```

---

## 11. Annotation/callout boxes must not overflow chart width

**Rule:** Annotation boxes (callout rects + text) inside SVG charts must be sized and
positioned so they don't extend beyond the SVG viewBox width.

**Check:** `boxX + boxWidth <= svgViewBoxWidth`

**Common mistake:** Box at x=556 width=200 extends to x=756. If the IT/Infra bar is the
tallest at the chart's right edge, the box overflows the chart container's right boundary.

**Fix:** Either widen the SVG, or position the box to the left of the annotated element.

---

## 12. Subtitle visibility when chart or panel uses same top

**General pattern to check for every slide with a subtitle:**
1. Does any sibling div come AFTER `.sub` in DOM order? → That div paints over sub.
2. Does that sibling have a background fill? → Sub text is hidden.
3. If yes to both: add `z-index:1` to `.sub` AND ensure chart `top` > sub bottom edge.

Both fixes together are required. `z-index:1` alone makes the text paint on top of the
chart fill, but the text then floats awkwardly over chart content. The `top` offset
eliminates the overlap entirely.

---

## Generation Prompt Addition (paste into system prompt)

```
SLIDE LAYOUT RULES — follow all of these exactly:

1. CSS: .sub { z-index:1; } — always, on every slide with a subtitle.

2. Chart top clearance: chart-wrap/chart/insights top >= sub.top + 25px minimum.
   Never position a chart div at the same top as the subtitle.

3. position:absolute on every child that uses left/top: .num-badge, .enabler-text,
   .row > div, .big, .small, icon divs — always declare position:absolute explicitly.

4. Multi-column layouts: set left: via inline style on each column div.
   Never use a CSS class to set column x-position (applies to all columns equally).

5. SVG horizontal grid lines: x1 = label column width (not 0).
   SVG vertical grid lines: y1 = header row height (not 0).

6. SVG section header rects: fill only, no stroke.

7. SVG value labels on bars: if label color == bar fill color, the label is invisible.
   Use fill="#FFFFFF" for labels over colored bars, or position past bar end with text-anchor="start".

8. SVG bottom budget: last data element + 30px gap + legend + 20px + axis ticks +
   14px + axis title + 14px = svgHeight. Never place axis title within 10px of svgHeight.

9. Annotation box bounds: boxX + boxWidth must not exceed svgViewBoxWidth.
```
