"""
slide-dsl/renderer.py
Converts a slide DSL spec (dict or JSON string) into a complete 1280x720 HTML slide.

Usage:
    from renderer import render_slide
    html = render_slide(spec_dict)
    html = render_slide(json_string)

Slide types:   cover | chapter | content | cta
Layouts:       full | two-column | three-column | sidebar-right | sidebar-left
Block types:   bar-chart | line-chart | scatter-chart | donut-chart |
               kpi-grid | bullet-list | table | text-block |
               gantt-chart | waterfall-chart | process-flow
"""

import json
import math
import html as _html

# ── Palette ────────────────────────────────────────────────────────────────────
PETROL      = "#00677F"
PETROL_DARK = "#004355"
PETROL_MED  = "#007A93"
PETROL_LT   = "#5097AB"
PETROL_LTR  = "#79AEBF"
PETROL_LTST = "#A6CAD8"
GREY_BG     = "#EFF7FA"
GREY_RULE   = "#DCE9ED"
GREY_TEXT   = "#1A1A1A"
GREY_SUB    = "#666666"

SERIES_COLORS = [PETROL, PETROL_LT, PETROL_LTR, PETROL_DARK, PETROL_MED, PETROL_LTST]

# ── Fixed slide geometry (1280x720) ────────────────────────────────────────────
SLIDE_W  = 1280
SLIDE_H  = 720
M_L      = 64
M_R      = 64
CON_X    = M_L
CON_Y    = 110    # content top — below header zone
CON_W    = SLIDE_W - M_L - M_R   # 1152
CON_H    = SLIDE_H - CON_Y - 34  # 576
FOOTER_Y = 686

# Column definitions: (x-offset from CON_X, width)
_COLS = {
    "full":          [{"dx": 0,   "w": 1152}],
    "two-column":    [{"dx": 0,   "w": 550},  {"dx": 602, "w": 550}],
    "three-column":  [{"dx": 0,   "w": 360},  {"dx": 396, "w": 360}, {"dx": 792, "w": 360}],
    "sidebar-right": [{"dx": 0,   "w": 720},  {"dx": 772, "w": 380}],
    "sidebar-left":  [{"dx": 0,   "w": 380},  {"dx": 432, "w": 720}],
}
_KEYS = {
    "full":          ["main"],
    "two-column":    ["left", "right"],
    "three-column":  ["left", "center", "right"],
    "sidebar-right": ["main", "sidebar"],
    "sidebar-left":  ["sidebar", "main"],
}

# ── HTML shell ─────────────────────────────────────────────────────────────────
_BASE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:1280px;height:720px;overflow:hidden;background:#fff;}}
.slide{{position:relative;width:1280px;height:720px;background:#fff;
        font-family:Arial,Helvetica,sans-serif;overflow:hidden;}}
</style>
</head>
<body><div class="slide">
{body}
</div></body></html>"""


# ── Utility helpers ────────────────────────────────────────────────────────────
def _e(s):
    return _html.escape(str(s))

def _d(left, top, w, h, style="", inner=""):
    return (f'<div style="position:absolute;left:{left}px;top:{top}px;'
            f'width:{w}px;height:{h}px;{style}">{inner}</div>')

def _nice_max(v, n=5):
    """Return the tightest axis ceiling >= v that divides into n nice intervals."""
    if v <= 0: return 10
    raw = v / n
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    # Walk up nice factors until the resulting max covers v
    for f in (1, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10):
        candidate = f * mag * n
        if candidate >= v:
            return candidate
    return 10 * mag * n

def _fmt(v, mode="auto"):
    if mode == "percent":  return f"{v:.0f}%"
    if mode == "currency":
        a = abs(v)
        if a == 0:        return "$0"
        if a < 1:         return f"${v:.2f}"
        if a < 10:        return f"${v:.1f}"
        if a < 1_000:     return f"${v:,.0f}"
        if a < 1_000_000: return f"${v/1_000:.1f}K"
        if a < 1_000_000_000: return f"${v/1_000_000:.1f}M"
        return f"${v/1_000_000_000:.1f}B"
    if mode == "decimal":  return f"{v:.1f}"
    if v >= 1_000_000:     return f"{v/1_000_000:.1f}M"
    if v >= 1_000:         return f"{v:,.0f}"
    if v == int(v):        return str(int(v))
    return f"{v:.2f}"

def _svg(w, h, inner, overflow="visible"):
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'style="overflow:{overflow};">{inner}</svg>')

def _txt(x, y, text, size=11, weight=400, fill=GREY_TEXT,
         anchor="start", font="Arial,Helvetica,sans-serif"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'font-family="{font}">{_e(str(text))}</text>')


# ── Entry point ────────────────────────────────────────────────────────────────
def render_slide(spec) -> str:
    if isinstance(spec, str):
        spec = json.loads(spec)
    accent = spec.get("theme", {}).get("accent", PETROL)
    stype  = spec.get("slide_type", "content")
    if stype == "cover":
        body = _cover(spec, accent)
    elif stype == "chapter":
        body = _chapter(spec, accent)
    elif stype == "cta":
        body = _cta(spec, accent)
    else:
        body = _content(spec, accent)
    return _BASE.format(body=body)


# ── Cover ──────────────────────────────────────────────────────────────────────
def _cover(spec, accent):
    h = spec.get("header", {})
    f = spec.get("footer", {})
    panel_w = 800
    right_bg = spec.get("theme", {}).get("cover_right_bg", PETROL_DARK)
    p = []

    # Left white panel + top bar
    p.append(_d(0, 0, panel_w, SLIDE_H, f"background:#fff;"))
    p.append(_d(0, 0, panel_w, 4, f"background:{accent};"))

    oy = 160
    if h.get("kicker"):
        p.append(_d(M_L, oy, panel_w - M_L - 40, 20,
            f"font-size:11px;font-weight:700;color:{accent};text-transform:uppercase;letter-spacing:1.5px;",
            _e(h["kicker"])))
        oy += 30
    if h.get("headline"):
        text = _e(h["headline"]).replace("\n", "<br>")
        hl   = h["headline"]
        fs   = 38 if len(hl) <= 55 else (30 if len(hl) <= 90 else (24 if len(hl) <= 130 else 20))
        # lines × line-height × fs, clamp so sub still fits above footer
        n_lines  = max(1, len(hl) // max(int((panel_w - M_L - 40) / (fs * 0.58)), 1) + 1)
        hl_h     = min(int(n_lines * fs * 1.3) + 10, SLIDE_H - oy - 120)
        p.append(_d(M_L, oy, panel_w - M_L - 40, hl_h,
            f"font-size:{fs}px;font-weight:700;color:#1A1A1A;line-height:1.3;overflow:hidden;",
            text))
        oy += hl_h + 16
    if h.get("sub"):
        sub_y = min(oy, SLIDE_H - 120)
        p.append(_d(M_L, sub_y, panel_w - M_L - 40, 44,
            "font-size:14px;color:#666;overflow:hidden;",
            _e(h["sub"])))

    # Right dark panel
    p.append(_d(panel_w, 0, SLIDE_W - panel_w, SLIDE_H, f"background:{right_bg};"))
    if spec.get("right_panel_text"):
        p.append(_d(panel_w + 30, SLIDE_H - 80, SLIDE_W - panel_w - 60, 40,
            "font-size:12px;color:rgba(255,255,255,0.5);",
            _e(spec["right_panel_text"])))

    # Footer
    if f.get("source"):
        p.append(_d(M_L, FOOTER_Y, 700, 16,
            "font-size:9px;color:#999;", _e(f["source"])))
    if f.get("page") is not None:
        p.append(_d(SLIDE_W - M_R - 50, FOOTER_Y, 50, 16,
            "font-size:11px;color:#999;text-align:right;", str(f["page"])))
    return "\n".join(p)


# ── Chapter divider ────────────────────────────────────────────────────────────
def _chapter(spec, accent):
    h = spec.get("header", {})
    f = spec.get("footer", {})
    bg = spec.get("theme", {}).get("bg", PETROL_DARK)
    p = []
    p.append(_d(0, 0, SLIDE_W, SLIDE_H, f"background:{bg};"))
    if h.get("kicker"):
        p.append(_d(M_L, 230, 300, 20,
            "font-size:13px;font-weight:700;color:rgba(255,255,255,0.45);text-transform:uppercase;letter-spacing:2px;",
            _e(h["kicker"])))
    p.append(_d(M_L, 252, 70, 3, f"background:{accent};"))
    if h.get("headline"):
        text = _e(h["headline"]).replace("\n", "<br>")
        p.append(_d(M_L, 262, 900, 160,
            "font-size:42px;font-weight:700;color:#fff;line-height:1.2;", text))
    if f.get("page") is not None:
        p.append(_d(SLIDE_W - M_R - 50, FOOTER_Y, 50, 16,
            "font-size:11px;color:rgba(255,255,255,0.3);text-align:right;", str(f["page"])))
    return "\n".join(p)


# ── CTA / closing ──────────────────────────────────────────────────────────────
def _cta(spec, accent):
    h = spec.get("header", {})
    f = spec.get("footer", {})
    bg = spec.get("theme", {}).get("bg", "#002E3D")
    p = []
    p.append(_d(0, 0, SLIDE_W, SLIDE_H, f"background:{bg};"))
    p.append(_d(0, 0, SLIDE_W, 4, f"background:{accent};"))
    if h.get("headline"):
        p.append(_d(M_L, 270, 1000, 100,
            "font-size:34px;font-weight:700;color:#fff;line-height:1.3;", _e(h["headline"])))
    if h.get("sub"):
        p.append(_d(M_L, 380, 750, 50,
            "font-size:15px;color:rgba(255,255,255,0.65);", _e(h["sub"])))
    for i, item in enumerate(spec.get("content", {}).get("items", [])):
        p.append(_d(M_L, 450 + i * 28, 650, 24,
            "font-size:13px;color:rgba(255,255,255,0.8);", _e(item)))
    if f.get("source"):
        p.append(_d(M_L, FOOTER_Y, 700, 16,
            "font-size:9px;color:rgba(255,255,255,0.3);", _e(f["source"])))
    return "\n".join(p)


# ── Content slide ──────────────────────────────────────────────────────────────
def _content(spec, accent):
    h       = spec.get("header", {})
    f       = spec.get("footer", {})
    layout  = spec.get("layout", "full")
    content = spec.get("content", {})
    p = []

    # Top accent bar
    p.append(_d(0, 0, SLIDE_W, 4, f"background:{accent};"))

    # Header zone
    oy_hdr = 4  # start below top accent bar
    if h.get("kicker"):
        p.append(_d(M_L, oy_hdr + 12, CON_W, 16,
            f"font-size:10px;font-weight:700;color:{accent};text-transform:uppercase;"
            "letter-spacing:1px;overflow:hidden;white-space:nowrap;",
            _e(h["kicker"])))
        oy_hdr += 28
    else:
        oy_hdr += 16
    if h.get("headline"):
        hl = h["headline"]
        # Smaller font for long headlines so they fit in 2 lines comfortably
        fs = 20 if len(hl) <= 70 else (18 if len(hl) <= 95 else 16)
        p.append(_d(M_L, oy_hdr, CON_W, 42,
            f"font-size:{fs}px;font-weight:700;color:#1A1A1A;line-height:1.25;"
            "overflow:hidden;",
            _e(hl)))
        oy_hdr += 46
    # Divider rule
    p.append(_d(M_L, oy_hdr, CON_W, 1, f"background:{GREY_RULE};"))
    oy_hdr += 6
    if h.get("sub"):
        p.append(_d(M_L, oy_hdr, CON_W, 22,
            "font-size:12px;color:#666;overflow:hidden;white-space:nowrap;",
            _e(h["sub"])))

    # Column layout
    cols = _COLS.get(layout, _COLS["full"])
    keys = _KEYS.get(layout, ["main"])
    for col, key in zip(cols, keys):
        block = content.get(key)
        if not block:
            continue
        bx = CON_X + col["dx"]
        p.append(render_block(block, bx, CON_Y, col["w"], CON_H, accent))

    # Footer
    if f.get("source"):
        p.append(_d(M_L, FOOTER_Y, 780, 16,
            "font-size:9px;color:#999;overflow:hidden;white-space:nowrap;",
            _e(f["source"])))
    if f.get("page") is not None:
        p.append(_d(SLIDE_W - M_R - 50, FOOTER_Y, 50, 16,
            "font-size:11px;font-weight:400;color:#666;text-align:right;",
            str(f["page"])))
    return "\n".join(p)


# ── Block dispatcher ───────────────────────────────────────────────────────────
def render_block(block: dict, x: int, y: int, w: int, h: int,
                 accent: str = PETROL) -> str:
    btype = block.get("type", "text-block")
    fn = {
        "bar-chart":       render_bar_chart,
        "line-chart":      render_line_chart,
        "scatter-chart":   render_scatter_chart,
        "donut-chart":     render_donut_chart,
        "kpi-grid":        render_kpi_grid,
        "bullet-list":     render_bullet_list,
        "table":           render_table,
        "text-block":      render_text_block,
        "gantt-chart":        render_gantt,
        "waterfall-chart":    render_waterfall,
        "process-flow":       render_process_flow,
        "comparison-matrix":  render_comparison_matrix,
    }.get(btype)
    if fn:
        return fn(block, x, y, w, h, accent)
    return _d(x, y, w, 40, "border:1px dashed #ccc;color:#999;font-size:11px;"
              "display:flex;align-items:center;justify-content:center;",
              f"[unsupported: {btype}]")


# ══════════════════════════════════════════════════════════════════════════════
# Chart renderers
# ══════════════════════════════════════════════════════════════════════════════

# ── Bar chart ──────────────────────────────────────────────────────────────────
def render_bar_chart(block, x, y, w, h, accent=PETROL):
    """
    orientation: "vertical" (default) | "horizontal"
    Single-series:  series: [{label, value}]
    Multi-series:   series: [{name, values:[...]}], labels: [...]
    stacked: bool
    fmt: "auto"|"percent"|"currency"|"decimal"
    show_values: bool (default True)
    title: str
    """
    if block.get("orientation") == "horizontal":
        return _bar_h(block, x, y, w, h, accent)
    return _bar_v(block, x, y, w, h, accent)


def _series_mode(block):
    s = block.get("series", [])
    if not s:
        return "single", []
    if isinstance(s[0].get("values"), list):
        lbls = block.get("labels", [str(i) for i in range(len(s[0]["values"]))])
        return "multi", lbls, s
    return "single", s


def _bar_v(block, x, y, w, h, accent):
    title     = block.get("title", "")
    fmt       = block.get("fmt", "auto")
    show_vals = block.get("show_values", True)
    stacked   = block.get("stacked", False)

    T, B, L, R = (22 if title else 4), 38, 48, 6
    cw, ch = w - L - R, h - T - B
    cx, cy = L, T

    mode, *rest = _series_mode(block)
    if mode == "single":
        s_raw  = rest[0]
        labels = [s["label"] for s in s_raw]
        series = [{"name": "", "values": [s["value"] for s in s_raw],
                   "color": accent}]
    else:
        labels, s_raw = rest
        series = [{"name": s.get("name", ""), "values": s["values"],
                   "color": SERIES_COLORS[i % len(SERIES_COLORS)]}
                  for i, s in enumerate(s_raw)]

    n, ns = len(labels), len(series)
    all_v = [v for s in series for v in s["values"]]
    if stacked:
        col_sums = [sum(s["values"][i] for s in series) for i in range(n)]
        y_max = _nice_max(max(col_sums))
    else:
        y_max = _nice_max(max(all_v)) if all_v else 10
    y_min = 0

    def vy(v): return cy + ch - (v - y_min) / (y_max - y_min) * ch

    slot = cw / n
    if stacked or ns == 1:
        bw = slot * 0.72   # single-series: slightly wider bars
        def bx_fn(i, si): return cx + i * slot + (slot - bw) / 2
    else:
        bw = slot * 0.72 / ns
        def bx_fn(i, si): return cx + i * slot + (slot - bw * ns) / 2 + si * bw

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    for k in range(6):
        gv = y_min + k * (y_max - y_min) / 5
        gy = vy(gv)
        ln.append(f'<line x1="{cx}" y1="{gy:.1f}" x2="{cx+cw}" y2="{gy:.1f}" stroke="{GREY_RULE}" stroke-width="1"/>')
        ln.append(_txt(cx - 4, gy + 4, _fmt(gv, fmt), 9, 400, GREY_SUB, "end"))

    ln.append(f'<line x1="{cx}" y1="{vy(0):.1f}" x2="{cx+cw}" y2="{vy(0):.1f}" stroke="#999" stroke-width="1.5"/>')

    for si, s in enumerate(series):
        stack = [0] * n
        for i, v in enumerate(s["values"][:n]):
            bx = bx_fn(i, si)
            if stacked:
                bot, top = vy(stack[i]), vy(stack[i] + v)
                stack[i] += v
            else:
                bot, top = vy(0), vy(v)
            bh = bot - top
            ln.append(f'<rect x="{bx:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(bh, 1):.1f}" fill="{s["color"]}" rx="1"/>')
            if show_vals and v > 0:
                if stacked:
                    # inside label when segment is tall enough; skip if too thin
                    if bh >= 16:
                        lbl_y = top + bh / 2 + 4
                        lbl_c = "#fff" if si == 0 else "rgba(255,255,255,0.85)"
                        ln.append(_txt(bx + bw / 2, lbl_y, _fmt(v, fmt), 9, 700, lbl_c, "middle"))
                else:
                    ln.append(_txt(bx + bw / 2, top - 3, _fmt(v, fmt), 9, 400, GREY_TEXT, "middle"))

    for i, lbl in enumerate(labels):
        lx = cx + i * slot + slot / 2
        ln.append(_txt(lx, cy + ch + 14, lbl, 10, 400, GREY_SUB, "middle"))

    if ns > 1:
        leg_y = cy + ch + 26
        for si, s in enumerate(series):
            if not s["name"]: continue
            lx = cx + si * max(cw // ns, 80)
            ln.append(f'<rect x="{lx}" y="{leg_y}" width="10" height="10" fill="{s["color"]}"/>')
            ln.append(_txt(lx + 13, leg_y + 9, s["name"], 9, 400, GREY_SUB))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


def _bar_h(block, x, y, w, h, accent):
    title     = block.get("title", "")
    fmt       = block.get("fmt", "auto")
    show_vals = block.get("show_values", True)

    mode, *rest = _series_mode(block)
    if mode == "single":
        items = rest[0]
    else:
        lbls, s_raw = rest
        items = [{"label": l, "value": s_raw[0]["values"][i]}
                 for i, l in enumerate(lbls)]

    T, B, L, R = (22 if title else 4), 4, 120, 55
    cw, ch = w - L - R, h - T - B
    cx, cy = L, T

    n   = len(items)
    all_v = [s["value"] for s in items]
    x_max = _nice_max(max(all_v)) if all_v else 10

    slot = ch / n
    bh   = slot * 0.65

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    for k in range(5):
        gx = cx + k * cw / 4
        ln.append(f'<line x1="{gx:.1f}" y1="{cy}" x2="{gx:.1f}" y2="{cy+ch}" stroke="{GREY_RULE}" stroke-width="1"/>')
        ln.append(_txt(gx, cy + ch + 14, _fmt(k * x_max / 4, fmt), 9, 400, GREY_SUB, "middle"))

    for i, s in enumerate(items):
        by = cy + i * slot + (slot - bh) / 2
        bw_px = s["value"] / x_max * cw
        color = SERIES_COLORS[i % len(SERIES_COLORS)]

        ln.append(f'<rect x="{cx}" y="{by:.1f}" width="{max(bw_px, 1):.1f}" height="{bh:.1f}" fill="{color}" rx="2"/>')
        ln.append(_txt(cx - 6, by + bh / 2 + 4, s["label"], 10, 400, GREY_TEXT, "end"))
        if show_vals:
            ln.append(_txt(cx + bw_px + 4, by + bh / 2 + 4,
                           _fmt(s["value"], fmt), 10, 700, color))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── Line chart ─────────────────────────────────────────────────────────────────
def render_line_chart(block, x, y, w, h, accent=PETROL):
    """
    labels: ["Q1 2020", ...]
    series: [{name, values:[...]}]
    fmt: str
    show_points: bool (default True)
    title: str
    area: bool — fill area under line (default False)
    """
    labels      = block.get("labels", [])
    series_raw  = block.get("series", [])
    fmt         = block.get("fmt", "auto")
    show_pts    = block.get("show_points", True)
    title       = block.get("title", "")
    area        = block.get("area", False)

    T, B, L, R = (22 if title else 8), 36, 48, 8
    cw, ch = w - L - R, h - T - B
    cx, cy = L, T

    series = [{"name": s.get("name", ""), "values": s["values"],
               "color": SERIES_COLORS[i % len(SERIES_COLORS)]}
              for i, s in enumerate(series_raw)]

    all_v = [v for s in series for v in s["values"]]
    y_max = _nice_max(max(all_v)) if all_v else 10
    y_min = 0
    n     = max(len(labels), 1)

    def px(i, v):
        px_x = cx + i * cw / (n - 1) if n > 1 else cx + cw / 2
        px_y = cy + ch - (v - y_min) / (y_max - y_min) * ch
        return px_x, px_y

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    for k in range(6):
        gv = y_min + k * (y_max - y_min) / 5
        gy = cy + ch - k * ch / 5
        ln.append(f'<line x1="{cx}" y1="{gy:.1f}" x2="{cx+cw}" y2="{gy:.1f}" stroke="{GREY_RULE}" stroke-width="1"/>')
        ln.append(_txt(cx - 4, gy + 4, _fmt(gv, fmt), 9, 400, GREY_SUB, "end"))

    for s in series:
        pts  = [px(i, v) for i, v in enumerate(s["values"][:n])]
        path = "M " + " L ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
        if area:
            close = f" L {pts[-1][0]:.1f},{cy+ch} L {pts[0][0]:.1f},{cy+ch} Z"
            ln.append(f'<path d="{path}{close}" fill="{s["color"]}" opacity="0.12"/>')
        ln.append(f'<path d="{path}" stroke="{s["color"]}" stroke-width="2.5" fill="none"/>')
        if show_pts:
            for px_x, px_y in pts:
                ln.append(f'<circle cx="{px_x:.1f}" cy="{px_y:.1f}" r="4" fill="{s["color"]}" stroke="#fff" stroke-width="1.5"/>')

    for i, lbl in enumerate(labels):
        lx, _ = px(i, 0)
        ln.append(_txt(lx, cy + ch + 14, lbl, 10, 400, GREY_SUB, "middle"))

    if len(series) > 1:
        leg_y = cy + ch + 26
        for si, s in enumerate(series):
            lx = cx + si * max(cw // len(series), 80)
            ln.append(f'<rect x="{lx}" y="{leg_y}" width="20" height="3" fill="{s["color"]}"/>')
            ln.append(_txt(lx + 25, leg_y + 6, s["name"], 9, 400, GREY_SUB))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── Scatter / bubble chart ─────────────────────────────────────────────────────
def render_scatter_chart(block, x, y, w, h, accent=PETROL):
    """
    points: [{label, x, y, size: float, color: hex}]
    x_label / y_label: axis labels
    x_range / y_range: [min, max]
    quadrant_labels: [TL, TR, BL, BR]
    title: str
    """
    points   = block.get("points", [])
    x_label  = block.get("x_label", "")
    y_label  = block.get("y_label", "")
    x_range  = block.get("x_range")
    y_range  = block.get("y_range")
    qlabels  = block.get("quadrant_labels")
    title    = block.get("title", "")

    T, B, L, R = (22 if title else 8), 36, 48, 8
    cw, ch = w - L - R, h - T - B
    cx, cy = L, T

    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    x_min, x_max = (x_range or [min(xs, default=0), _nice_max(max(xs, default=10))])
    y_min, y_max = (y_range or [0, _nice_max(max(ys, default=10))])

    def to_px(px_v, py_v):
        return (cx + (px_v - x_min) / (x_max - x_min) * cw,
                cy + ch - (py_v - y_min) / (y_max - y_min) * ch)

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    for k in range(5):
        gy = cy + k * ch / 4
        gx = cx + k * cw / 4
        ln.append(f'<line x1="{cx}" y1="{gy:.1f}" x2="{cx+cw}" y2="{gy:.1f}" stroke="{GREY_RULE}" stroke-width="1"/>')
        ln.append(f'<line x1="{gx:.1f}" y1="{cy}" x2="{gx:.1f}" y2="{cy+ch}" stroke="{GREY_RULE}" stroke-width="1"/>')

    if qlabels:
        mx, my = to_px((x_min + x_max) / 2, (y_min + y_max) / 2)
        ln.append(f'<line x1="{mx:.1f}" y1="{cy}" x2="{mx:.1f}" y2="{cy+ch}" stroke="#aaa" stroke-width="1" stroke-dasharray="4 3"/>')
        ln.append(f'<line x1="{cx}" y1="{my:.1f}" x2="{cx+cw}" y2="{my:.1f}" stroke="#aaa" stroke-width="1" stroke-dasharray="4 3"/>')
        # Place quadrant labels at the mid-top and mid-bottom of each quadrant
        # so they stay clear of extreme-corner bubbles and the center boundary
        tl_cx = (cx + mx) / 2
        tr_cx = (mx + cx + cw) / 2
        ql_positions = [
            (tl_cx, cy + 14,      "middle"),   # TL: mid-top of top-left quadrant
            (tr_cx, cy + 14,      "middle"),   # TR: mid-top of top-right quadrant
            (tl_cx, cy + ch - 8,  "middle"),   # BL: mid-bottom of bottom-left quadrant
            (tr_cx, cy + ch - 8,  "middle"),   # BR: mid-bottom of bottom-right quadrant
        ]
        for ql, (qx, qy, anchor) in zip(qlabels, ql_positions):
            ln.append(_txt(qx, qy, ql, 9, 400, GREY_SUB, anchor))

    for p in points:
        px2, py2 = to_px(p["x"], p["y"])
        r     = p.get("size", 6)
        color = p.get("color") or accent
        ln.append(f'<circle cx="{px2:.1f}" cy="{py2:.1f}" r="{r}" fill="{color}" opacity="0.85"/>')
        if p.get("label"):
            ln.append(_txt(px2 + r + 3, py2 + 4, p["label"], 9, 400, GREY_TEXT))

    ln.append(f'<line x1="{cx}" y1="{cy+ch}" x2="{cx+cw}" y2="{cy+ch}" stroke="#999" stroke-width="1.5"/>')
    ln.append(f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+ch}" stroke="#999" stroke-width="1.5"/>')

    if x_label:
        ln.append(_txt(cx + cw / 2, cy + ch + 28, x_label, 10, 400, GREY_SUB, "middle"))
    if y_label:
        mid = cy + ch / 2
        ln.append(f'<text x="12" y="{mid:.1f}" text-anchor="middle" font-size="10" fill="{GREY_SUB}" '
                  f'transform="rotate(-90,12,{mid:.1f})" font-family="Arial,Helvetica,sans-serif">{_e(y_label)}</text>')

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── Donut chart ────────────────────────────────────────────────────────────────
def render_donut_chart(block, x, y, w, h, accent=PETROL):
    """
    segments: [{label, value, color: hex}]
    center_text / center_label: text shown in donut hole
    show_legend: bool (default True)
    fmt: "percent"|"auto"
    """
    segs         = block.get("segments", [])
    center_text  = block.get("center_text", "")
    center_label = block.get("center_label", "")
    show_leg     = block.get("show_legend", True)
    fmt          = block.get("fmt", "percent")

    if not segs:
        return ""

    leg_w = 160 if show_leg else 0
    chart_w = w - leg_w
    r_out = min(chart_w, h) // 2 - 10
    r_in  = int(r_out * 0.58)
    cx2   = chart_w // 2
    cy2   = h // 2

    total = sum(s.get("value", 0) for s in segs)
    if total == 0: return ""

    ln    = []
    start = -math.pi / 2

    for i, seg in enumerate(segs):
        v     = seg.get("value", 0)
        color = seg.get("color") or SERIES_COLORS[i % len(SERIES_COLORS)]
        sweep = (v / total) * 2 * math.pi
        end   = start + sweep

        x1, y1 = cx2 + r_out * math.cos(start), cy2 + r_out * math.sin(start)
        x2, y2 = cx2 + r_out * math.cos(end),   cy2 + r_out * math.sin(end)
        ix1, iy1 = cx2 + r_in * math.cos(end),  cy2 + r_in * math.sin(end)
        ix2, iy2 = cx2 + r_in * math.cos(start), cy2 + r_in * math.sin(start)

        large = 1 if sweep > math.pi else 0
        d = (f"M {x1:.1f} {y1:.1f} A {r_out} {r_out} 0 {large} 1 {x2:.1f} {y2:.1f} "
             f"L {ix1:.1f} {iy1:.1f} A {r_in} {r_in} 0 {large} 0 {ix2:.1f} {iy2:.1f} Z")
        ln.append(f'<path d="{d}" fill="{color}"/>')

        if sweep > 0.3:
            mid  = start + sweep / 2
            lr   = (r_out + r_in) / 2
            lx   = cx2 + lr * math.cos(mid)
            ly   = cy2 + lr * math.sin(mid)
            pct  = f"{v / total * 100:.0f}%"
            ln.append(f'<text x="{lx:.1f}" y="{ly+4:.1f}" text-anchor="middle" font-size="11" '
                      f'font-weight="700" fill="#fff" font-family="Arial,Helvetica,sans-serif">{pct}</text>')
        start = end

    if center_text:
        ln.append(f'<text x="{cx2}" y="{cy2-2}" text-anchor="middle" font-size="20" font-weight="700" '
                  f'fill="{accent}" font-family="Arial,Helvetica,sans-serif">{_e(center_text)}</text>')
    if center_label:
        ln.append(f'<text x="{cx2}" y="{cy2+16}" text-anchor="middle" font-size="9" fill="{GREY_SUB}" '
                  f'font-family="Arial,Helvetica,sans-serif">{_e(center_label)}</text>')

    if show_leg:
        lx0 = chart_w + 10
        for i, seg in enumerate(segs):
            ly  = max(h // 2 - len(segs) * 14, 10) + i * 30
            if ly > h - 20: break
            color = seg.get("color") or SERIES_COLORS[i % len(SERIES_COLORS)]
            ln.append(f'<rect x="{lx0}" y="{ly}" width="12" height="12" fill="{color}" rx="2"/>')
            ln.append(_txt(lx0 + 16, ly + 10, seg.get("label", ""), 10, 400, GREY_TEXT))
            v   = seg.get("value", 0)
            pct = f"{v / total * 100:.1f}%"
            ln.append(_txt(lx0 + 16, ly + 22, pct, 9, 400, GREY_SUB))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── KPI / stat callout grid ────────────────────────────────────────────────────
def render_kpi_grid(block, x, y, w, h, accent=PETROL):
    """
    columns: 1-4 (default 2)
    style: "default" | "accent" | "compact" | "borderless"
    items: [{stat, label, delta, positive: True|False|None, icon: str}]
    """
    items  = block.get("items", [])
    n_cols = min(block.get("columns", 2), 4)
    n_rows = math.ceil(len(items) / n_cols) if items else 1
    style  = block.get("style", "default")

    gap    = 12
    card_w = (w - gap * (n_cols - 1)) // n_cols
    card_h = (h - gap * (n_rows - 1)) // n_rows

    # Accent cards have fixed content height; cap and center vertically so they
    # don't stretch to fill the full column with empty whitespace.
    if style == "accent":
        eff_card_h = min(card_h, 160)
        total_grid_h = n_rows * eff_card_h + gap * (n_rows - 1)
        y_start = y + max(0, (h - total_grid_h) // 2)
    else:
        eff_card_h = card_h
        y_start = y

    stat_fs = min(38, max(20, eff_card_h // 5))

    p = []
    for i, item in enumerate(items):
        col, row = i % n_cols, i // n_cols
        cx2 = x + col * (card_w + gap)
        cy2 = y_start + row * (eff_card_h + gap)

        stat  = _e(str(item.get("stat", "")))
        label = _e(str(item.get("label", "")))
        delta = item.get("delta", "")
        pos   = item.get("positive", None)
        icon  = _e(str(item.get("icon", "")))

        if style == "accent":
            # Colored stat band + tight white body; card shrinks to its content
            hdr_h   = max(14, int(eff_card_h * 0.55))
            label_h = 22
            body_pad = 10  # top+bottom padding inside white section
            vis_h = hdr_h + body_pad + label_h + (18 if delta else 0) + body_pad
            # full card bg (white, sized to content)
            p.append(_d(cx2, cy2, card_w, vis_h,
                f"background:#fff;border-radius:6px;border:1px solid {GREY_RULE};overflow:hidden;"))
            # accent header band
            p.append(_d(cx2, cy2, card_w, hdr_h,
                f"background:{accent};border-radius:6px 6px 0 0;"))
            # stat — vertically centered in header band
            stat_y = cy2 + (hdr_h - stat_fs) // 2
            p.append(_d(cx2 + 12, stat_y, card_w - 24, stat_fs + 2,
                f"font-size:{stat_fs}px;font-weight:700;color:#fff;line-height:1;", stat))
            # label
            body_y = cy2 + hdr_h + body_pad
            p.append(_d(cx2 + 12, body_y, card_w - 24, label_h,
                "font-size:11px;color:#444;line-height:1.3;overflow:hidden;", label))
            # delta sits immediately below label
            if delta:
                dc = ("#2E7D32" if pos else "#C62828") if pos is not None else "#888"
                p.append(_d(cx2 + 12, body_y + label_h + 4, card_w - 24, 14,
                    f"font-size:10px;font-weight:700;color:{dc};", _e(str(delta))))

        elif style == "compact":
            # Left accent bar, no card background — just a clean row
            p.append(_d(cx2, cy2 + 4, 3, card_h - 8, f"background:{accent};border-radius:2px;"))
            p.append(_d(cx2 + 14, cy2, card_w - 14, int(card_h * 0.5),
                f"font-size:{min(stat_fs, 28)}px;font-weight:700;color:{accent};line-height:1;", stat))
            p.append(_d(cx2 + 14, cy2 + int(card_h * 0.52), card_w - 14, int(card_h * 0.3),
                "font-size:11px;color:#555;line-height:1.4;", label))
            if delta:
                dc = ("#2E7D32" if pos else "#C62828") if pos is not None else "#888"
                p.append(_d(cx2 + 14, cy2 + int(card_h * 0.82), card_w - 14, 14,
                    f"font-size:10px;font-weight:700;color:{dc};", _e(str(delta))))

        elif style == "borderless":
            # No card chrome — just stat + label floating on slide background
            p.append(_d(cx2, cy2, card_w, int(card_h * 0.48),
                f"font-size:{stat_fs}px;font-weight:700;color:{accent};line-height:1;", stat))
            p.append(_d(cx2, cy2 + int(card_h * 0.50), card_w, int(card_h * 0.35),
                "font-size:11px;color:#666;line-height:1.4;", label))
            p.append(_d(cx2, cy2 + card_h - 2, card_w, 1, f"background:{GREY_RULE};"))
            if delta:
                dc = ("#2E7D32" if pos else "#C62828") if pos is not None else "#888"
                p.append(_d(cx2, cy2 + int(card_h * 0.86), card_w, 14,
                    f"font-size:10px;font-weight:700;color:{dc};", _e(str(delta))))

        else:  # default
            p.append(_d(cx2, cy2, card_w, card_h,
                f"background:{GREY_BG};border-radius:6px;"))
            p.append(_d(cx2, cy2, card_w, 3,
                f"background:{accent};border-radius:6px 6px 0 0;"))
            if icon:
                p.append(_d(cx2 + card_w - 36, cy2 + 8, 28, 16,
                    f"font-size:9px;font-weight:700;color:{accent};background:#fff;"
                    f"border-radius:3px;text-align:center;padding:2px 4px;", icon))
            stat_top  = max(14, int(card_h * 0.12))
            label_top = max(stat_top + stat_fs + 8, int(card_h * 0.48))
            delta_top = int(card_h * 0.82)
            p.append(_d(cx2 + 14, cy2 + stat_top, card_w - 28, int(card_h * 0.36),
                f"font-size:{stat_fs}px;font-weight:700;color:{accent};line-height:1;", stat))
            p.append(_d(cx2 + 14, cy2 + label_top, card_w - 28, int(card_h * 0.30),
                "font-size:11px;color:#555;line-height:1.4;", label))
            if delta:
                dc = ("#2E7D32" if pos else "#C62828") if pos is not None else "#888"
                p.append(_d(cx2 + 14, cy2 + delta_top, card_w - 28, 14,
                    f"font-size:10px;font-weight:700;color:{dc};", _e(str(delta))))

    return "\n".join(p)


# ── Bullet list ────────────────────────────────────────────────────────────────
def render_bullet_list(block, x, y, w, h, accent=PETROL):
    """
    title: str (optional section title)
    items: [{text, sub}] or ["plain string", ...]
    spacing: int (px between items, default 10)
    """
    title   = block.get("title", "")
    items   = block.get("items", [])
    spacing = block.get("spacing", 10)

    p  = []
    oy = y

    if title:
        p.append(_d(x, oy, w, 20,
            f"font-size:13px;font-weight:700;color:{accent};", _e(title)))
        oy += 28

    for item in items:
        if isinstance(item, str):
            text, sub = item, ""
        else:
            text = item.get("text", "")
            sub  = item.get("sub", "")

        p.append(_d(x, oy + 5, 7, 7, f"background:{accent};border-radius:50%;"))
        p.append(_d(x + 16, oy, w - 16, 20,
            "font-size:13px;color:#1A1A1A;font-weight:600;line-height:1.45;", _e(text)))
        oy += 22

        if sub:
            p.append(_d(x + 16, oy, w - 16, 32,
                "font-size:11px;color:#666;line-height:1.45;", _e(sub)))
            oy += 36
        oy += spacing

        if oy > y + h - 20:
            break

    return "\n".join(p)


# ── Table ──────────────────────────────────────────────────────────────────────
def render_table(block, x, y, w, h, accent=PETROL):
    """
    headers: ["Col A", "Col B", ...]
    rows: [[v1, v2, ...], ...]
    col_widths: [int, ...] — optional, overrides equal distribution
    highlight_col: int — column index to accent
    """
    headers     = block.get("headers", [])
    rows        = block.get("rows", [])
    hl_col      = block.get("highlight_col")
    col_widths  = block.get("col_widths")

    n_cols = len(headers)
    if n_cols == 0: return ""

    if col_widths:
        cws = col_widths
    else:
        cws = [w // n_cols] * n_cols

    hdr_h  = 32
    row_h  = min(28, (h - hdr_h) // max(len(rows), 1))

    p = []
    for ci, hdr in enumerate(headers):
        hx  = x + sum(cws[:ci])
        bg  = accent if ci == hl_col else PETROL_DARK
        p.append(_d(hx, y, cws[ci] - 1, hdr_h, f"background:{bg};"))
        p.append(_d(hx + 8, y + 8, cws[ci] - 16, hdr_h - 8,
            "font-size:11px;font-weight:700;color:#fff;overflow:hidden;white-space:nowrap;",
            _e(str(hdr))))

    for ri, row in enumerate(rows):
        ry   = y + hdr_h + ri * row_h
        if ry + row_h > y + h: break
        rbg  = GREY_BG if ri % 2 == 0 else "#fff"
        for ci, val in enumerate(row[:n_cols]):
            cx2 = x + sum(cws[:ci])
            bg  = rbg
            ts  = f"font-size:11px;color:#333;"
            if ci == hl_col:
                bg = "#EFF7FA"
                ts = f"font-size:11px;font-weight:700;color:{accent};"
            p.append(_d(cx2, ry, cws[ci] - 1, row_h,
                f"background:{bg};border-bottom:1px solid {GREY_RULE};"))
            p.append(_d(cx2 + 8, ry + 6, cws[ci] - 16, row_h - 6,
                ts + "overflow:hidden;white-space:nowrap;", _e(str(val))))

    return "\n".join(p)


# ── Text block ─────────────────────────────────────────────────────────────────
def render_text_block(block, x, y, w, h, accent=PETROL):
    """
    title: str
    body: str (paragraph text)
    size: font-size in px (default 13)
    style: "default" | "callout" | "pull-quote"
    """
    title = block.get("title", "")
    body  = block.get("body", block.get("text", ""))
    size  = block.get("size", 13)
    style = block.get("style", "default")
    p     = []
    oy    = y

    if style == "callout":
        # Tinted box with left accent bar
        p.append(_d(x, y, w, h, f"background:{GREY_BG};border-radius:6px;border-left:4px solid {accent};"))
        x, w = x + 16, w - 24
        oy = y + 14

    elif style == "pull-quote":
        # Large opening quote mark + italic body
        p.append(_d(x, y - 8, 32, 40,
            f"font-size:52px;font-weight:900;color:{PETROL_LTST};line-height:1;", "“"))
        x, oy = x + 8, y + 28

    if title:
        p.append(_d(x, oy, w, 22,
            f"font-size:14px;font-weight:700;color:{accent};", _e(title)))
        oy += 30

    if body:
        fs   = size if style == "default" else size
        clr  = "#333" if style != "pull-quote" else "#444"
        p.append(_d(x, oy, w, h - (oy - y) - (14 if style == "callout" else 0),
            f"font-size:{fs}px;color:{clr};line-height:1.65;", _e(body)))

    return "\n".join(p)


# ── Comparison matrix ──────────────────────────────────────────────────────────
def render_comparison_matrix(block, x, y, w, h, accent=PETROL):
    """
    Side-by-side labeled comparison rows — the "2-column matrix" pattern.

    Schema:
      { "type": "comparison-matrix",
        "columns": ["Option A", "Option B"],
        "rows": [
          { "label": "Cost",  "values": ["Low", "High"] },
          { "label": "Speed", "values": ["Fast", "Slow"], "highlight": 0 }
        ],
        "style": "default | zebra | bordered"
      }
    highlight: 0-based index of winning/preferred column per row
    """
    cols  = block.get("columns", [])
    rows  = block.get("rows", [])
    style = block.get("style", "zebra")
    title = block.get("title", "")

    if not cols or not rows:
        return ""

    n_cols = len(cols)
    p      = []
    oy     = y

    if title:
        p.append(_d(x, oy, w, 20,
            f"font-size:13px;font-weight:700;color:{accent};", _e(title)))
        oy += 26

    label_w = max(130, w // (n_cols + 2))
    col_w   = (w - label_w) // n_cols
    hdr_h   = 30
    avail_h = h - (oy - y) - hdr_h
    # Fill height but cap rows at 90px so short-content rows don't look hollow
    row_h   = max(36, min(90, avail_h // max(len(rows), 1)))
    text_h  = row_h - 12

    # ── Column headers ──
    p.append(_d(x, oy, w, hdr_h, f"background:{accent};border-radius:4px 4px 0 0;"))
    for ci, ch in enumerate(cols):
        cx2 = x + label_w + ci * col_w
        p.append(_d(cx2, oy + 6, col_w - 8, hdr_h - 12,
            "font-size:11px;font-weight:700;color:#fff;text-align:center;", _e(str(ch))))
    oy += hdr_h

    # ── Rows ──
    for ri, row in enumerate(rows):
        ry        = oy + ri * row_h
        highlight = row.get("highlight", None)
        values    = row.get("values", [])

        # Row background
        if style == "zebra":
            row_bg = GREY_BG if ri % 2 == 0 else "#fff"
        else:
            row_bg = "#fff"
        p.append(_d(x, ry, w, row_h, f"background:{row_bg};"))
        # Row separator
        p.append(_d(x, ry + row_h - 1, w, 1, f"background:{GREY_RULE};"))

        # Row label (bold, left column)
        p.append(_d(x + 10, ry + 6, label_w - 14, text_h,
            "font-size:11px;font-weight:600;color:#1A1A1A;line-height:1.4;"
            "overflow:hidden;", _e(str(row.get("label", "")))))

        # Value cells
        for ci, val in enumerate(values[:n_cols]):
            cx2   = x + label_w + ci * col_w
            is_hl = (ci == highlight)
            if is_hl:
                # Light accent tint background + accent bold text
                p.append(_d(cx2 + 2, ry + 1, col_w - 4, row_h - 2,
                    f"background:{accent}18;border-radius:3px;"))
                clr, fw = accent, "700"
            else:
                clr, fw = "#444", "400"
            p.append(_d(cx2 + 8, ry + 6, col_w - 16, text_h,
                f"font-size:10.5px;font-weight:{fw};color:{clr};"
                f"line-height:1.4;overflow:hidden;", _e(str(val))))

    return "\n".join(p)


# ── Gantt chart ────────────────────────────────────────────────────────────────
def render_gantt(block, x, y, w, h, accent=PETROL):
    """
    x_labels: ["Q1", "Q2", ...] — time columns
    rows: [{label, start: float, end: float, bar_label: str, color: hex}]
    milestones: [{label, at: float}]
    title: str
    """
    title      = block.get("title", "")
    x_labels   = block.get("x_labels", [])
    rows       = block.get("rows", [])
    milestones = block.get("milestones", [])

    n_col = len(x_labels)
    n_row = len(rows)
    if n_col == 0 or n_row == 0: return ""

    T, B, L = (22 if title else 4), 10, 130
    hdr_h   = 22
    ms_h    = 20 if milestones else 0   # space for milestone labels at bottom
    cx, cy  = L, T + hdr_h
    cw      = w - L - 6
    ch      = h - T - hdr_h - B - ms_h
    row_h   = ch / n_row                # fill available height — no cap
    col_w   = cw / n_col

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    # Column headers + vertical rules
    for i, lbl in enumerate(x_labels):
        hx  = cx + i * col_w + col_w / 2
        ln.append(_txt(hx, T + hdr_h - 6, lbl, 9, 700, GREY_TEXT, "middle"))
        gx = cx + i * col_w
        ln.append(f'<line x1="{gx:.1f}" y1="{cy}" x2="{gx:.1f}" y2="{cy + n_row * row_h}" stroke="{GREY_RULE}" stroke-width="1"/>')

    # Row bars
    for ri, row in enumerate(rows):
        ry   = cy + ri * row_h
        bar_y = ry + row_h * 0.22
        bar_h = row_h * 0.56

        ln.append(_txt(cx - 6, ry + row_h / 2 + 4, row.get("label", ""), 9, 400, GREY_TEXT, "end"))

        if ri % 2 == 0:
            ln.append(f'<rect x="{cx}" y="{ry}" width="{cw}" height="{row_h}" fill="{GREY_BG}"/>')

        s, e    = row.get("start", 0), row.get("end", 1)
        color   = row.get("color") or SERIES_COLORS[ri % len(SERIES_COLORS)]
        bx_r    = cx + s * col_w
        bw_r    = (e - s) * col_w
        ln.append(f'<rect x="{bx_r:.1f}" y="{bar_y:.1f}" width="{max(bw_r, 2):.1f}" height="{bar_h:.1f}" fill="{color}" rx="3"/>')

        if row.get("bar_label"):
            ln.append(_txt(bx_r + bw_r / 2, bar_y + bar_h / 2 + 4,
                           row["bar_label"], 9, 700, "#fff", "middle"))

    # Milestones
    for ms in milestones:
        mx  = cx + ms["at"] * col_w
        my0 = cy - 4
        ln.append(f'<polygon points="{mx},{my0-6} {mx+5},{my0} {mx},{my0+6} {mx-5},{my0}" fill="{accent}"/>')
        if ms.get("label"):
            ln.append(_txt(mx, cy + n_row * row_h + 14, ms["label"], 9, 400, accent, "middle"))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── Waterfall chart ────────────────────────────────────────────────────────────
def render_waterfall(block, x, y, w, h, accent=PETROL):
    """
    bars: [{label, value, type: "start"|"positive"|"negative"|"total"}]
    fmt: str
    show_values: bool
    title: str
    """
    bars      = block.get("bars", [])
    fmt       = block.get("fmt", "auto")
    show_vals = block.get("show_values", True)
    title     = block.get("title", "")

    T, B, L, R = (22 if title else 4), 38, 50, 8
    cw, ch = w - L - R, h - T - B
    cx, cy = L, T

    running  = 0
    computed = []
    all_y    = []
    for b in bars:
        v     = b.get("value", 0)
        btype = b.get("type", "positive" if v >= 0 else "negative")
        if btype == "start":
            sy, ey = 0, v
            running = v
        elif btype == "total":
            sy, ey = 0, v
        else:
            sy, ey = running, running + v
            running = ey
        computed.append({"label": b.get("label", ""), "value": v,
                         "type": btype, "sy": sy, "ey": ey})
        all_y.extend([sy, ey])

    y_max = _nice_max(max(all_y)) if all_y else 10

    # Smart y-axis floor: if all non-zero running values sit above 15% of y_max,
    # zoom in so the bridge bars are visible instead of tiny slivers at the top.
    running_vals = [b["ey"] for b in computed]
    running_vals += [b["sy"] for b in computed if b["sy"] > 0]
    running_min = min(running_vals) if running_vals else 0
    if running_min > 0.15 * y_max:
        raw_floor = running_min * 0.92
        mag = 10 ** math.floor(math.log10(raw_floor)) if raw_floor > 0 else 1
        y_min = math.floor(raw_floor / mag) * mag
    else:
        y_min = min(0, min(all_y)) if all_y else 0

    def vy(v): return cy + ch - (v - y_min) / (y_max - y_min) * ch

    n    = len(computed)
    slot = cw / n
    bw   = slot * 0.6

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    for k in range(5):
        gv = y_min + k * (y_max - y_min) / 4
        gy = vy(gv)
        ln.append(f'<line x1="{cx}" y1="{gy:.1f}" x2="{cx+cw}" y2="{gy:.1f}" stroke="{GREY_RULE}" stroke-width="1"/>')
        ln.append(_txt(cx - 4, gy + 4, _fmt(gv, fmt), 9, 400, GREY_SUB, "end"))

    # Zero baseline only if 0 is visible in the y range
    if y_min <= 0 <= y_max:
        ln.append(f'<line x1="{cx}" y1="{vy(0):.1f}" x2="{cx+cw}" y2="{vy(0):.1f}" stroke="#999" stroke-width="1.5"/>')
    # Always show the chart floor axis
    ln.append(f'<line x1="{cx}" y1="{cy+ch:.1f}" x2="{cx+cw}" y2="{cy+ch:.1f}" stroke="{GREY_RULE}" stroke-width="1"/>')

    prev_ey = None
    for i, b in enumerate(computed):
        bx  = cx + i * slot + (slot - bw) / 2
        # Start/total bars draw from the chart floor (y_min) when axis is zoomed
        sy_draw = y_min if (b["type"] in ("start", "total") and y_min > 0) else b["sy"]
        top = vy(max(sy_draw, b["ey"]))
        bot = vy(min(sy_draw, b["ey"]))
        bh  = max(bot - top, 2)

        color = (PETROL_DARK if b["type"] == "total" else
                 PETROL_MED  if b["type"] == "start"  else
                 PETROL_LT   if b["value"] >= 0        else "#C62828")

        if prev_ey is not None and b["type"] not in ("start", "total"):
            ln.append(f'<line x1="{bx - (slot-bw)/2:.1f}" y1="{prev_ey:.1f}" '
                      f'x2="{bx:.1f}" y2="{prev_ey:.1f}" stroke="#aaa" stroke-width="1" stroke-dasharray="3 2"/>')

        ln.append(f'<rect x="{bx:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{color}"/>')

        if b["type"] not in ("start", "total"):
            prev_ey = vy(b["ey"])

        if show_vals:
            sign = "+" if b["value"] > 0 and b["type"] not in ("start", "total") else ""
            ln.append(_txt(bx + bw / 2, top - 4, f"{sign}{_fmt(b['value'], fmt)}", 9, 400, GREY_TEXT, "middle"))

        ln.append(_txt(bx + bw / 2, cy + ch + 14, b["label"], 9, 400, GREY_SUB, "middle"))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── Process flow ───────────────────────────────────────────────────────────────
def render_process_flow(block, x, y, w, h, accent=PETROL):
    """
    steps: [{icon, label, sub}]
    direction: "horizontal" (default) | "vertical"
    """
    steps = block.get("steps", [])
    if not steps: return ""

    direction = block.get("direction", "horizontal")
    n = len(steps)
    p = []

    if direction == "horizontal":
        # Timeline layout: horizontal connector line + badges + text below
        step_w   = w // n
        badge_r  = 20           # badge radius
        badge_d  = badge_r * 2
        line_y   = y + badge_r  # vertical position of the timeline line
        text_y   = line_y + badge_r + 18  # text starts below badges

        # Full-width connector line (behind badges)
        p.append(_d(x, line_y - 1, w, 2, f"background:{accent};opacity:0.25;"))

        for i, step in enumerate(steps):
            cx_step = x + i * step_w + step_w // 2  # center x of this step
            bx      = cx_step - badge_r
            col_w2  = step_w - 16

            # Connector segment — solid line from this badge to next
            if i < n - 1:
                line_start = cx_step + badge_r
                line_end   = x + (i + 1) * step_w + step_w // 2 - badge_r
                p.append(_d(line_start, line_y - 1, line_end - line_start, 2,
                    f"background:{accent};opacity:0.5;"))
                # Arrowhead at midpoint
                mid = (line_start + line_end) // 2
                p.append(_d(mid - 5, line_y - 6, 0, 0,
                    f"border-top:6px solid transparent;border-bottom:6px solid transparent;"
                    f"border-left:9px solid {accent};width:0;height:0;opacity:0.6;"))

            # Badge circle
            p.append(_d(bx, line_y - badge_r, badge_d, badge_d,
                f"background:{accent};border-radius:50%;font-size:13px;font-weight:700;"
                f"color:#fff;text-align:center;line-height:{badge_d}px;",
                _e(step.get("icon", str(i + 1)))))

            # Label — centered under badge
            lx = x + i * step_w + 8
            p.append(_d(lx, text_y, col_w2, 34,
                "font-size:12px;font-weight:700;color:#1A1A1A;line-height:1.3;"
                "text-align:center;",
                _e(step.get("label", ""))))

            # Sub text — centered, flows for remaining space
            if step.get("sub"):
                sub_y = text_y + 38
                sub_h = max(60, h - (sub_y - y) - 8)
                p.append(_d(lx, sub_y, col_w2, sub_h,
                    "font-size:10.5px;color:#555;line-height:1.55;overflow:hidden;"
                    "text-align:center;",
                    _e(step["sub"])))
    else:
        step_h = min((h - 10) // n, 110)
        for i, step in enumerate(steps):
            sy2 = y + i * step_h + 5
            sx2 = x
            p.append(_d(sx2, sy2, w, step_h - 6,
                f"background:{GREY_BG};border-radius:6px;border-left:4px solid {accent};"))
            p.append(_d(sx2 + 12, sy2 + 8, 28, 28,
                f"background:{accent};border-radius:50%;font-size:13px;font-weight:700;"
                f"color:#fff;text-align:center;line-height:28px;",
                _e(step.get("icon", str(i + 1)))))
            p.append(_d(sx2 + 50, sy2 + 8, w - 70, 22,
                "font-size:12px;font-weight:700;color:#1A1A1A;", _e(step.get("label", ""))))
            if step.get("sub"):
                p.append(_d(sx2 + 50, sy2 + 30, w - 70, 50,
                    "font-size:11px;color:#666;line-height:1.4;", _e(step["sub"])))

    return "\n".join(p)
