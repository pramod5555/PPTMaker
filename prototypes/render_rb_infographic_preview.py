from __future__ import annotations

from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont

from common import ensure_output_dir

OUT_DIR = ensure_output_dir()
PREVIEW_DIR = OUT_DIR / "rb_style_infographic_previews"
PX_W, PX_H = 2000, 1125

C = {
    "rail": "#30343A",
    "divider": "#6B3FA0",
    "ink": "#111216",
    "muted": "#8A8F96",
    "paper": "#FFFFFF",
    "panel": "#D9DDE2",
    "blue": "#06466D",
    "blue2": "#2D79A3",
    "lavender": "#A99BD1",
    "lightLavender": "#C8BFDF",
    "grid": "#D8D8D8",
    "footer": "#4A4F56",
    "saffron": "#F2A541",
}

POINTS = [
    (0.4, 34),
    (0.7, 39),
    (1.1, 42),
    (1.2, 46),
    (1.6, 51),
    (1.8, 55),
    (2.2, 58),
    (2.5, 54),
    (2.9, 63),
    (3.1, 60),
    (3.4, 68),
    (4.0, 66),
    (4.5, 70),
    (1.4, 48),
    (2.0, 52),
    (2.8, 57),
]
LABELS = {
    "US": (2.9, 63),
    "Germany": (3.1, 60),
    "Japan": (2.5, 54),
    "South Korea": (4.0, 66),
    "UK": (2.2, 58),
    "Estonia": (1.4, 48),
    "Lithuania": (1.1, 42),
}


def rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def font(size: int, bold: bool = False):
    for name in (["arialbd.ttf", "arial.ttf"] if bold else ["arial.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, color: str, bold: bool = False) -> None:
    draw.multiline_text(xy, value, fill=rgb(color), font=font(size, bold), spacing=6)


def wrapped_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    size: int,
    color: str,
    width: int,
    bold: bool = False,
) -> None:
    lines: list[str] = []
    for paragraph in value.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=width) or [""])
    draw.multiline_text(xy, "\n".join(lines), fill=rgb(color), font=font(size, bold), spacing=6)


def hexagon(cx: int, cy: int, r: int) -> list[tuple[int, int]]:
    return [
        (cx - r, cy),
        (cx - r // 2, cy - int(r * 0.86)),
        (cx + r // 2, cy - int(r * 0.86)),
        (cx + r, cy),
        (cx + r // 2, cy + int(r * 0.86)),
        (cx - r // 2, cy + int(r * 0.86)),
    ]


def map_point(x: float, y: float, box: tuple[int, int, int, int]) -> tuple[int, int]:
    x0, y0, w, h = box
    px = x0 + int((x / 5.0) * w)
    py = y0 + h - int(((y - 30) / 42) * h)
    return px, py


def draw_scatter(draw: ImageDraw.ImageDraw) -> None:
    box = (445, 305, 920, 570)
    x0, y0, w, h = box
    for i in range(6):
        x = x0 + int(i * w / 5)
        draw.line([x, y0, x, y0 + h], fill=rgb("#EFEFEF"), width=1)
        text(draw, (x - 10, y0 + h + 18), f"{i}", 24, C["ink"])
    for idx, val in enumerate(range(30, 71, 10)):
        y = y0 + h - int(((val - 30) / 42) * h)
        draw.line([x0, y, x0 + w, y], fill=rgb(C["grid"]), width=1)
        text(draw, (x0 - 50, y - 16), str(val), 24, C["ink"])
    draw.line([x0, y0 + h, x0 + w, y0 + h], fill=rgb(C["ink"]), width=3)
    draw.line([x0, y0, x0, y0 + h], fill=rgb(C["ink"]), width=3)
    draw.line([x0 + 55, y0 + h - 30, x0 + w - 70, y0 + 75], fill=rgb("#55595E"), width=3)
    for i, (x, y) in enumerate(POINTS):
        px, py = map_point(x, y, box)
        color = C["blue"] if i % 3 else C["lightLavender"]
        draw.ellipse([px - 9, py - 9, px + 9, py + 9], fill=rgb(color), outline=rgb(C["paper"]), width=2)
    for label, (x, y) in LABELS.items():
        px, py = map_point(x, y, box)
        text(draw, (px + 14, py - 14), label, 25, C["ink"])
    text(draw, (x0 + 20, y0 + 90), "R: 0.62", 26, C["ink"])
    text(draw, (x0 + 250, y0 + h + 85), "AI investment intensity as % of operating cost", 30, C["ink"], True)
    text(draw, (x0 - 112, y0 + 160), "Digital operating\nmaturity index", 29, C["ink"], True)


def render() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (PX_W, PX_H), rgb(C["paper"]))
    draw = ImageDraw.Draw(im)

    draw.rectangle([0, 0, 267, PX_H], fill=rgb(C["rail"]))
    draw.rectangle([267, 0, 273, PX_H], fill=rgb(C["divider"]))
    text(draw, (20, 55), "Digital\nOperations", 34, C["paper"], True)
    for idx, (num, label, y, active) in enumerate(
        [("1", "Value\nof AI", 260, True), ("2", "Control\nmodel", 455, False), ("3", "Scale\nplan", 650, False)]
    ):
        pts = hexagon(70, y, 48)
        draw.polygon(pts, fill=rgb(C["blue2"] if active else "#777B82"), outline=rgb(C["lavender"] if active else "#A8ADB3"))
        text(draw, (130, y - 36), num, 48, C["lavender"] if active else "#74787F", True)
        text(draw, (160, y - 18), label, 22, C["lavender"] if active else "#74787F", True if active else False)
    text(draw, (18, 1080), "9", 22, C["paper"])
    text(draw, (86, 970), "AI", 54, "#6F747B", True)

    text(
        draw,
        (325, 58),
        "... as AI investment intensity emerges as a decisive factor\nfor scalable productivity gains",
        42,
        C["ink"],
        True,
    )
    text(draw, (326, 168), "Illustrative banking benchmark plotted against AI investment intensity", 35, C["muted"])

    draw_scatter(draw)

    draw.rectangle([1455, 285, 1975, 1035], fill=rgb(C["panel"]))
    bullets = [
        ("Funding AI operations", "must connect to repeatable frontline workflows"),
        ("Productivity processes", "need controls for adoption, data quality, and auditability"),
        ("Higher investment intensity", "correlates with maturity, but execution quality explains dispersion"),
        ("At the operating level", "investment signals confidence in redesign and scaled learning"),
    ]
    y = 318
    for lead, body in bullets:
        text(draw, (1485, y), ">", 26, C["ink"])
        text(draw, (1525, y), lead, 26, C["ink"], True)
        wrapped_text(draw, (1525, y + 38), body, 25, C["ink"], 38)
        y += 175

    text(draw, (326, 1062), "1) Prototype benchmark created for slide-generation research; values are illustrative", 18, C["footer"])
    text(draw, (326, 1088), "Sources: synthetic benchmark set; ppt-dataset fidelity extractor", 18, C["footer"])
    text(draw, (1860, 1084), "Prototype", 18, C["footer"])

    path = PREVIEW_DIR / "slide_001.png"
    im.save(path)
    sheet = im.copy()
    sheet.thumbnail((512, 288))
    sheet.save(PREVIEW_DIR / "contact_sheet.png")
    print(f"Wrote previews to {PREVIEW_DIR}")


if __name__ == "__main__":
    render()
