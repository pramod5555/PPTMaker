"""
Extract rich visual fidelity features from slide PNGs.

Phase 1 additions over the original:
  - color_tokens   : pixel-sampled semantic roles (rail, accent, panel, …)
  - layout_dims    : named fractional measurements from detected regions
  - text_density   : ink-pixel coverage in content region + low/medium/high
  - chart_region   : tightened plot-area bounding box when a chart is present
  - --priority all : process every slide in the dataset (not just consulting)
"""

from __future__ import annotations

import argparse
import colorsys
import csv
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from common import BASE_DIR, ensure_output_dir, load_dataset

FIDELITY_DIR = BASE_DIR / "fidelity"
OUT_DIR = ensure_output_dir()
SUMMARY_CSV = OUT_DIR / "fidelity_summary.csv"
SUMMARY_JSON = OUT_DIR / "fidelity_summary.json"


# ── low-level helpers ─────────────────────────────────────────────────────────

def bbox_norm(box: tuple[int, int, int, int] | None, w: int, h: int) -> dict[str, float] | None:
    if box is None:
        return None
    x0, y0, x1, y1 = box
    return {
        "x": round(x0 / w, 4),
        "y": round(y0 / h, 4),
        "w": round((x1 - x0) / w, 4),
        "h": round((y1 - y0) / h, 4),
    }


def abs_box(norm_box: dict[str, float] | None, w: int, h: int) -> tuple[int, int, int, int] | None:
    if not norm_box:
        return None
    return (
        int(norm_box["x"] * w),
        int(norm_box["y"] * h),
        int((norm_box["x"] + norm_box["w"]) * w),
        int((norm_box["y"] + norm_box["h"]) * h),
    )


def largest_components(mask: np.ndarray, min_area: int = 2000, limit: int = 8) -> list[tuple[int, int, int, int, int]]:
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps: list[tuple[int, int, int, int, int]] = []
    ys, xs = np.nonzero(mask)
    starts = list(zip(xs.tolist(), ys.tolist()))
    for sx, sy in starts:
        if seen[sy, sx] or not mask[sy, sx]:
            continue
        q: deque[tuple[int, int]] = deque([(sx, sy)])
        seen[sy, sx] = True
        area = 0
        x0 = x1 = sx
        y0 = y1 = sy
        while q:
            x, y = q.popleft()
            area += 1
            x0, x1 = min(x0, x), max(x1, x)
            y0, y1 = min(y0, y), max(y1, y)
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < width and 0 <= ny < height and not seen[ny, nx] and mask[ny, nx]:
                    seen[ny, nx] = True
                    q.append((nx, ny))
        if area >= min_area:
            comps.append((area, x0, y0, x1 + 1, y1 + 1))
    comps.sort(reverse=True)
    return comps[:limit]


def dominant_palette(arr: np.ndarray, k: int = 8) -> list[dict[str, Any]]:
    sample = arr.reshape(-1, 3)
    if len(sample) > 120_000:
        idx = np.linspace(0, len(sample) - 1, 120_000).astype(int)
        sample = sample[idx]
    quant = (sample // 24) * 24
    counts = Counter(map(tuple, quant.tolist()))
    total = sum(counts.values()) or 1
    colors = []
    for (r, g, b), count in counts.most_common(k):
        colors.append({"hex": f"#{int(r):02X}{int(g):02X}{int(b):02X}", "share": round(count / total, 4)})
    return colors


# ── region detectors ──────────────────────────────────────────────────────────

def detect_left_rail(arr: np.ndarray) -> tuple[int, int, int, int] | None:
    h, w, _ = arr.shape
    max_x = int(w * 0.24)
    gray = arr[:, :max_x].mean(axis=2)
    dark_cols = (gray < 92).mean(axis=0)
    candidates = np.where(dark_cols > 0.78)[0]
    if len(candidates) < w * 0.035:
        return None
    end = int(candidates.max()) + 1
    if end < w * 0.055:
        return None
    return (0, 0, end, h)


def detect_vertical_divider(arr: np.ndarray, rail: tuple[int, int, int, int] | None) -> tuple[int, int, int, int] | None:
    if rail is None:
        return None
    h, w, _ = arr.shape
    x_start = max(0, rail[2] - 10)
    x_end = min(w, rail[2] + 18)
    crop = arr[:, x_start:x_end]
    if crop.size == 0:
        return None
    r, g, b = crop[:, :, 0], crop[:, :, 1], crop[:, :, 2]
    sat = crop.max(axis=2) - crop.min(axis=2)
    mask = ((b > r) | (r > g)) & (sat > 35)
    cols = mask.mean(axis=0)
    if cols.max() < 0.35:
        return None
    x = x_start + int(cols.argmax())
    return (x, 0, min(w, x + 5), h)


def detect_right_panel(arr: np.ndarray, rail: tuple[int, int, int, int] | None) -> tuple[int, int, int, int] | None:
    h, w, _ = arr.shape
    left_limit = int(w * 0.48)
    if rail:
        left_limit = max(left_limit, rail[2] + int(w * 0.25))
    crop = arr[int(h * 0.18) : int(h * 0.92), left_limit:w]
    if crop.size == 0:
        return None
    mean = crop.mean(axis=2)
    saturation = crop.max(axis=2) - crop.min(axis=2)
    mask = (mean > 150) & (mean < 238) & (saturation < 26)
    comps = largest_components(mask, min_area=max(1200, int(w * h * 0.002)), limit=5)
    if not comps:
        return None
    area, x0, y0, x1, y1 = comps[0]
    bw, bh = x1 - x0, y1 - y0
    if bw < w * 0.08 or bh < h * 0.12:
        return None
    return (x0 + left_limit, y0 + int(h * 0.18), x1 + left_limit, y1 + int(h * 0.18))


def detect_title_and_subtitle(
    arr: np.ndarray, rail: tuple[int, int, int, int] | None
) -> tuple[tuple[int, int, int, int] | None, tuple[int, int, int, int] | None]:
    h, w, _ = arr.shape
    x0 = rail[2] + int(w * 0.025) if rail else int(w * 0.05)
    x1 = int(w * 0.92)
    crop = arr[: int(h * 0.26), x0:x1]
    if crop.size == 0:
        return None, None
    gray = crop.mean(axis=2)
    dark = gray < 155
    row_density = dark.mean(axis=1)
    rows = np.where(row_density > 0.018)[0]
    if len(rows) == 0:
        return None, None
    first = int(rows.min())
    groups: list[tuple[int, int]] = []
    start = prev = first
    for r in rows[1:]:
        r = int(r)
        if r - prev > 8:
            groups.append((start, prev))
            start = r
        prev = r
    groups.append((start, prev))
    title_group = groups[0]
    title_box = (x0, max(0, title_group[0] - 4), x1, min(h, title_group[1] + 8))
    subtitle_box = None
    if len(groups) > 1:
        sub = groups[1]
        subtitle_box = (x0, max(0, sub[0] - 4), x1, min(h, sub[1] + 8))
    else:
        grey = (gray > 120) & (gray < 205)
        grey_rows = np.where(grey.mean(axis=1) > 0.045)[0]
        grey_rows = grey_rows[grey_rows > title_group[1] + 8]
        if len(grey_rows):
            subtitle_box = (x0, int(grey_rows.min()), x1, min(h, int(grey_rows.max()) + 8))
    return title_box, subtitle_box


def detect_footer(arr: np.ndarray, rail: tuple[int, int, int, int] | None) -> tuple[int, int, int, int] | None:
    h, w, _ = arr.shape
    x0 = rail[2] + int(w * 0.02) if rail else int(w * 0.04)
    crop = arr[int(h * 0.84) : h, x0:w]
    gray = crop.mean(axis=2)
    nonwhite = gray < 235
    rows = np.where(nonwhite.mean(axis=1) > 0.01)[0]
    if len(rows) == 0:
        return None
    y0 = int(h * 0.84) + int(rows.min())
    y1 = int(h * 0.84) + int(rows.max()) + 1
    if y1 - y0 < h * 0.008:
        return None
    return (x0, y0, w, y1)


def detect_content_region(
    arr: np.ndarray,
    rail: tuple[int, int, int, int] | None,
    right_panel: tuple[int, int, int, int] | None,
    title: tuple[int, int, int, int] | None,
    footer: tuple[int, int, int, int] | None,
) -> tuple[int, int, int, int] | None:
    h, w, _ = arr.shape
    x0 = rail[2] + int(w * 0.03) if rail else int(w * 0.05)
    x1 = right_panel[0] - int(w * 0.025) if right_panel else int(w * 0.9)
    y0 = (title[3] + int(h * 0.035)) if title else int(h * 0.18)
    y1 = (footer[1] - int(h * 0.025)) if footer else int(h * 0.88)
    if x1 <= x0 or y1 <= y0:
        return None
    crop = arr[y0:y1, x0:x1]
    gray = crop.mean(axis=2)
    nonwhite = gray < 242
    cols = np.where(nonwhite.mean(axis=0) > 0.01)[0]
    rows = np.where(nonwhite.mean(axis=1) > 0.01)[0]
    if len(cols) == 0 or len(rows) == 0:
        return (x0, y0, x1, y1)
    return (x0 + int(cols.min()), y0 + int(rows.min()), x0 + int(cols.max()) + 1, y0 + int(rows.max()) + 1)


# ── Phase 1: color tokens ─────────────────────────────────────────────────────

def _hex_brightness(hex_color: str) -> float:
    v = hex_color.lstrip("#")
    r, g, b = int(v[0:2], 16) / 255, int(v[2:4], 16) / 255, int(v[4:6], 16) / 255
    return 0.299 * r + 0.587 * g + 0.114 * b


def _hex_saturation(hex_color: str) -> float:
    v = hex_color.lstrip("#")
    r, g, b = int(v[0:2], 16) / 255, int(v[2:4], 16) / 255, int(v[4:6], 16) / 255
    _, s, _ = colorsys.rgb_to_hsv(r, g, b)
    return s


def _median_hex(arr: np.ndarray, box: tuple[int, int, int, int] | None) -> str | None:
    """Median RGB colour of an absolute-pixel bounding box."""
    if box is None:
        return None
    x0, y0, x1, y1 = box
    crop = arr[max(0, y0):max(0, y1), max(0, x0):max(0, x1)]
    if crop.size == 0:
        return None
    med = np.median(crop.reshape(-1, 3), axis=0).astype(int)
    return f"#{int(med[0]):02X}{int(med[1]):02X}{int(med[2]):02X}"


def extract_color_tokens(
    arr: np.ndarray,
    parts: dict[str, Any],
    palette: list[dict[str, Any]],
    w: int,
    h: int,
) -> dict[str, str | None]:
    """
    Map pixel-sampled regions and the dominant palette to semantic colour roles.

    Roles
    -----
    background  : brightest dominant colour (usually the slide's white/off-white)
    rail        : median of the left navigation rail region
    divider     : median of the vertical accent divider
    panel       : median of the right insight panel region
    accent      : most-saturated entry in the dominant palette
    text_primary: median of the darkest pixels in the title region
    """
    # background: brightest palette entry
    background = max((c["hex"] for c in palette), key=_hex_brightness, default=None)

    # Pixel-sampled region colours
    rail_color = _median_hex(arr, abs_box(parts.get("left_rail"), w, h))
    divider_color = _median_hex(arr, abs_box(parts.get("vertical_divider"), w, h))
    panel_color = _median_hex(arr, abs_box(parts.get("right_panel"), w, h))

    # accent: most-saturated non-neutral colour in palette.
    # k=8 quantisation misses narrow accent stripes — fall back to region samples.
    saturated = [c["hex"] for c in palette if _hex_saturation(c["hex"]) > 0.12]
    accent = max(saturated, key=_hex_saturation) if saturated else None
    if accent is None:
        candidates = [c for c in [divider_color, rail_color, panel_color] if c and _hex_saturation(c) > 0.12]
        if candidates:
            accent = max(candidates, key=_hex_saturation)

    # text_primary: median of dark pixels in title region
    text_primary: str | None = None
    title_box = abs_box(parts.get("title_region"), w, h)
    if title_box:
        x0, y0, x1, y1 = title_box
        crop = arr[y0:y1, x0:x1]
        if crop.size > 0:
            gray = crop.mean(axis=2)
            dark_pixels = crop[gray < 100]
            if len(dark_pixels) >= 30:
                med = np.median(dark_pixels, axis=0).astype(int)
                text_primary = f"#{int(med[0]):02X}{int(med[1]):02X}{int(med[2]):02X}"

    return {
        "background": background,
        "rail": rail_color,
        "divider": divider_color,
        "panel": panel_color,
        "accent": accent,
        "text_primary": text_primary,
    }


# ── Phase 1: layout_dims ──────────────────────────────────────────────────────

def extract_layout_dims(parts: dict[str, Any]) -> dict[str, float]:
    """
    Named fractional measurements derived directly from detected regions.
    Provides generation-ready slot dimensions (fractions of slide W/H).
    """
    dims: dict[str, float] = {}

    rail = parts.get("left_rail")
    if rail:
        dims["rail_w"] = round(rail["w"], 4)
        # content starts just after the rail + divider gap
        dims["content_x"] = round(rail["x"] + rail["w"], 4)
    else:
        dims["content_x"] = 0.0

    title = parts.get("title_region")
    if title:
        dims["title_y"] = round(title["y"], 4)
        dims["title_h"] = round(title["h"], 4)

    subtitle = parts.get("subtitle_region")
    if subtitle:
        dims["subtitle_y"] = round(subtitle["y"], 4)
        dims["subtitle_h"] = round(subtitle["h"], 4)

    content = parts.get("main_content_region")
    if content:
        dims["content_y"] = round(content["y"], 4)
        dims["content_w"] = round(content["w"], 4)
        dims["content_h"] = round(content["h"], 4)
        dims["content_x_end"] = round(content["x"] + content["w"], 4)

    panel = parts.get("right_panel")
    if panel:
        dims["panel_x"] = round(panel["x"], 4)
        dims["panel_y"] = round(panel["y"], 4)
        dims["panel_w"] = round(panel["w"], 4)
        dims["panel_h"] = round(panel["h"], 4)

    footer = parts.get("footer_region")
    if footer:
        dims["footer_y"] = round(footer["y"], 4)
        dims["footer_h"] = round(footer["h"], 4)

    return dims


# ── Phase 1: text density ─────────────────────────────────────────────────────

def estimate_text_density(
    arr: np.ndarray, content_box: tuple[int, int, int, int] | None
) -> dict[str, Any]:
    """
    Estimate ink-pixel coverage in the main content region.

    Returns
    -------
    ink_fraction : float  — dark-pixel share (0–1)
    category     : str    — "low" / "medium" / "high"
    """
    if content_box is None:
        return {"ink_fraction": 0.0, "category": "low"}
    x0, y0, x1, y1 = content_box
    crop = arr[max(0, y0):y1, max(0, x0):x1]
    if crop.size == 0:
        return {"ink_fraction": 0.0, "category": "low"}
    gray = crop.mean(axis=2)
    ink = float((gray < 130).mean())
    if ink < 0.025:
        category = "low"
    elif ink < 0.065:
        category = "medium"
    else:
        category = "high"
    return {"ink_fraction": round(ink, 4), "category": category}


# ── Phase 1: chart region ─────────────────────────────────────────────────────

def detect_chart_region(
    arr: np.ndarray,
    content_box: tuple[int, int, int, int] | None,
    has_chart: bool,
) -> tuple[int, int, int, int] | None:
    """
    Within the content region, tighten to the chart's plot-area bounding box.

    Strategy: look for an L-shaped axis structure — a dark row near the bottom
    of the content area (x-axis) and a dark column near the left (y-axis).
    Falls back to the full content_box if no clear structure is found.
    """
    if not has_chart or content_box is None:
        return None

    x0, y0, x1, y1 = content_box
    crop = arr[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]
    if ch < 40 or cw < 40:
        return content_box

    gray = crop.mean(axis=2)
    # Use 150 threshold: chart axis lines are medium-grey after JPEG compression.
    dark = (gray < 150).astype(np.float32)

    row_dark = dark.mean(axis=1)   # darkness per row
    col_dark = dark.mean(axis=0)   # darkness per col

    # X-axis line: last sustained-dark row in the bottom 60 % of content
    x_axis_row = None
    for r in range(int(ch * 0.4), ch):
        if row_dark[r] >= 0.25:
            x_axis_row = r

    # Y-axis line: first sustained-dark column in the left 35 % of content
    y_axis_col = None
    for c in range(int(cw * 0.35)):
        if col_dark[c] >= 0.25:
            y_axis_col = c

    if x_axis_row is None or y_axis_col is None:
        return content_box

    # Plot area: above x_axis_row, right of y_axis_col, clipped to content
    plot_x0 = x0 + y_axis_col
    plot_y0 = y0 + 4
    plot_x1 = x1 - 4
    plot_y1 = y0 + x_axis_row

    # Sanity: plot must occupy a reasonable fraction of the content box
    if (plot_x1 - plot_x0) < cw * 0.2 or (plot_y1 - plot_y0) < ch * 0.15:
        return content_box

    return (int(plot_x0), int(plot_y0), int(plot_x1), int(plot_y1))


# ── recipe + scoring ──────────────────────────────────────────────────────────

def infer_recipe(label: dict[str, Any], parts: dict[str, Any]) -> str:
    pieces = []
    if parts.get("left_rail"):
        pieces.append("left_nav_rail")
    pieces.append("title_stack")
    layout = label.get("layout_type", "")
    chart = label.get("chart_type", "none")
    if chart == "scatter" or layout == "scatter_bubble_chart":
        pieces.append("scatter_evidence_field")
    elif chart != "none":
        pieces.append(f"{chart}_chart_field")
    else:
        pieces.append("content_field")
    if parts.get("right_panel"):
        pieces.append("right_insight_panel")
    if parts.get("footer"):
        pieces.append("source_footer")
    return " + ".join(pieces)


def style_anchor_score(slide: dict[str, Any], parts: dict[str, Any], whitespace: float) -> float:
    label = slide["label"]
    score = 0.0
    if label.get("source_company") == "Roland Berger":
        score += 2.0
    elif label.get("source_company") in {"BCG", "Accenture"}:
        score += 1.0
    score += max(0, float(label.get("estimated_quality_score", 0)) - 3)
    if label.get("chart_type") in {"scatter", "bar", "line", "mixed"}:
        score += 0.9
    if parts.get("left_rail"):
        score += 0.8
    if parts.get("right_panel"):
        score += 0.9
    if 0.55 <= whitespace <= 0.88:
        score += 0.4
    return round(score, 2)


def is_priority(slide: dict[str, Any], mode: str) -> bool:
    label = slide["label"]
    source = label.get("source_company")
    if mode == "all":
        return True
    if mode == "roland":
        return source == "Roland Berger"
    if mode == "consulting":
        return source in {"Roland Berger", "BCG", "Accenture"}
    if mode == "gold-candidates":
        return source in {"Roland Berger", "BCG", "Accenture"} and int(label.get("estimated_quality_score", 0)) >= 4
    raise ValueError(mode)


# ── main extraction ───────────────────────────────────────────────────────────

def extract_one(slide: dict[str, Any]) -> dict[str, Any]:
    image_path = BASE_DIR / slide["image_path"]
    image = Image.open(image_path).convert("RGB")
    arr = np.array(image)
    h, w, _ = arr.shape

    # ── region detection ──────────────────────────────────────────────────────
    rail = detect_left_rail(arr)
    divider = detect_vertical_divider(arr, rail)
    right_panel = detect_right_panel(arr, rail)
    title, subtitle = detect_title_and_subtitle(arr, rail)
    footer = detect_footer(arr, rail)
    content = detect_content_region(arr, rail, right_panel, title, footer)

    gray = arr.mean(axis=2)
    whitespace = round(float((gray > 242).mean()), 4)

    parts = {
        "left_rail": bbox_norm(rail, w, h),
        "vertical_divider": bbox_norm(divider, w, h),
        "title_region": bbox_norm(title, w, h),
        "subtitle_region": bbox_norm(subtitle, w, h),
        "main_content_region": bbox_norm(content, w, h),
        "right_panel": bbox_norm(right_panel, w, h),
        "footer_region": bbox_norm(footer, w, h),
    }

    palette = dominant_palette(arr)
    label = slide["label"]

    # ── Phase 1 additions ─────────────────────────────────────────────────────
    color_tokens = extract_color_tokens(arr, parts, palette, w, h)
    layout_dims = extract_layout_dims(parts)

    has_chart = label.get("chart_type", "none") not in {"none", None, ""}
    chart_box = detect_chart_region(arr, content, has_chart)
    chart_region_norm = bbox_norm(chart_box, w, h)

    text_density = estimate_text_density(arr, content)

    recipe = infer_recipe(label, parts)
    anchor_score = style_anchor_score(slide, parts, whitespace)

    return {
        "slide_id": slide["slide_id"],
        "image_path": slide["image_path"],
        "dimensions": {"width": w, "height": h},
        "source_company": label.get("source_company"),
        "label": label,
        "fidelity": {
            "regions": parts,
            "chart_region": chart_region_norm,
            "has_left_nav_rail": parts["left_rail"] is not None,
            "has_right_insight_panel": parts["right_panel"] is not None,
            "has_footer": parts["footer_region"] is not None,
            "whitespace_share": whitespace,
            "dominant_palette": palette,
            "color_tokens": color_tokens,
            "layout_dims": layout_dims,
            "text_density": text_density,
            "design_recipe": recipe,
            "style_anchor_score": anchor_score,
        },
    }


# ── entrypoint ────────────────────────────────────────────────────────────────

_SUMMARY_FIELDS = [
    "slide_id", "source_company", "layout_type", "chart_type", "slide_purpose",
    "estimated_quality_score", "style_anchor_score",
    "has_left_nav_rail", "has_right_insight_panel",
    "whitespace_share", "design_recipe",
    # Phase 1 additions
    "ink_fraction", "text_density_category",
    "color_bg", "color_rail", "color_accent", "color_panel", "color_text",
    "rail_w", "content_x", "content_y", "content_w", "content_h",
    "panel_x", "panel_w", "title_y", "title_h",
    "image_path",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract fidelity features from slide PNGs.")
    parser.add_argument(
        "--priority",
        choices=["roland", "consulting", "gold-candidates", "all"],
        default="all",
        help="Which slides to process (default: all)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Cap at N slides (0 = no cap)")
    args = parser.parse_args()

    FIDELITY_DIR.mkdir(exist_ok=True)
    dataset = load_dataset()
    slides = [s for s in dataset["slides"] if s.get("label") and is_priority(s, args.priority)]
    if args.limit:
        slides = slides[: args.limit]

    print(f"Processing {len(slides)} slides ({args.priority}) …")

    rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    errors: list[str] = []

    for i, slide in enumerate(slides, 1):
        try:
            record = extract_one(slide)
        except Exception as exc:
            errors.append(f"{slide['slide_id']}: {exc}")
            print(f"  ERROR {slide['slide_id']}: {exc}")
            continue

        out_file = FIDELITY_DIR / f"{slide['slide_id']}.json"
        out_file.write_text(json.dumps(record, indent=2), encoding="utf-8")

        fid = record["fidelity"]
        ct = fid["color_tokens"]
        ld = fid["layout_dims"]
        td = fid["text_density"]

        rows.append({
            "slide_id": record["slide_id"],
            "source_company": record["source_company"],
            "layout_type": record["label"].get("layout_type"),
            "chart_type": record["label"].get("chart_type"),
            "slide_purpose": record["label"].get("slide_purpose"),
            "estimated_quality_score": record["label"].get("estimated_quality_score"),
            "style_anchor_score": fid["style_anchor_score"],
            "has_left_nav_rail": fid["has_left_nav_rail"],
            "has_right_insight_panel": fid["has_right_insight_panel"],
            "whitespace_share": fid["whitespace_share"],
            "design_recipe": fid["design_recipe"],
            "ink_fraction": td["ink_fraction"],
            "text_density_category": td["category"],
            "color_bg": ct.get("background"),
            "color_rail": ct.get("rail"),
            "color_accent": ct.get("accent"),
            "color_panel": ct.get("panel"),
            "color_text": ct.get("text_primary"),
            "rail_w": ld.get("rail_w"),
            "content_x": ld.get("content_x"),
            "content_y": ld.get("content_y"),
            "content_w": ld.get("content_w"),
            "content_h": ld.get("content_h"),
            "panel_x": ld.get("panel_x"),
            "panel_w": ld.get("panel_w"),
            "title_y": ld.get("title_y"),
            "title_h": ld.get("title_h"),
            "image_path": record["image_path"],
        })
        summaries.append(record)

        if i % 50 == 0 or i == len(slides):
            print(f"  {i}/{len(slides)} done")

    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: float(r["style_anchor_score"] or 0), reverse=True))

    SUMMARY_JSON.write_text(json.dumps(summaries, indent=2), encoding="utf-8")

    print(f"\nExtracted {len(rows)} slides  ({len(errors)} errors)")
    print(f"Wrote {FIDELITY_DIR}/  ({len(rows)} JSON files)")
    print(f"Wrote {SUMMARY_CSV}")
    print(f"Wrote {SUMMARY_JSON}")

    if rows:
        print("\nTop style anchors:")
        for row in sorted(rows, key=lambda r: float(r["style_anchor_score"] or 0), reverse=True)[:10]:
            print(f"  {row['style_anchor_score']:>5}  {row['slide_id'][:60]}  {row['design_recipe']}")

    if errors:
        print(f"\n{len(errors)} errors:")
        for e in errors[:10]:
            print(f"  {e}")


if __name__ == "__main__":
    main()
