from __future__ import annotations

from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import BASE_DIR, ensure_output_dir, load_dataset

OUT_DIR = ensure_output_dir()
PREVIEW_DIR = OUT_DIR / "pptxgenjs_deck_v03_previews"
PX_W, PX_H = 1920, 1080

C = {
    "black": "#111216",
    "charcoal": "#252A31",
    "ink": "#1F2328",
    "muted": "#6B7280",
    "pale": "#F7F6F2",
    "paper": "#FFFFFF",
    "grid": "#D8D4CC",
    "teal": "#1B8A8F",
    "cyan": "#35B6C7",
    "plum": "#6B3FA0",
    "violet": "#B100FF",
    "green": "#7BC06F",
    "saffron": "#F2A541",
}


def rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ["arialbd.ttf", "arial.ttf"] if bold else ["arial.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, color: str, bold: bool = False) -> None:
    draw.multiline_text(xy, value, fill=rgb(color), font=font(size, bold), spacing=6)


def count_by(slides: list[dict], key: str) -> Counter:
    return Counter(slide["label"].get(key, "unknown") for slide in slides)


def paste_slide(im: Image.Image, filename: str, box: tuple[int, int, int, int]) -> None:
    src = Image.open(BASE_DIR / "slides" / filename).convert("RGB")
    x, y, w, h = box
    src.thumbnail((w, h))
    ox = x + (w - src.width) // 2
    oy = y + (h - src.height) // 2
    im.paste(src, (ox, oy))


def bar(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, value: int, max_value: int, color: str) -> None:
    width = int((value / max_value) * 520) if max_value else 0
    draw.rectangle([x, y, x + width, y + 26], fill=rgb(color))
    text(draw, (x + width + 14, y - 2), f"{label.replace('_', ' ')} ({value})", 18, C["ink"])


def render() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    dataset = load_dataset()
    slides = dataset["slides"]
    total = len(slides)
    source = count_by(slides, "source_company")
    layout = count_by(slides, "layout_type")
    chart = count_by(slides, "chart_type")
    density = count_by(slides, "text_density")
    remaining = max(0, 641 - total)
    pages: list[Path] = []

    for n in range(1, 7):
        bg = C["black"] if n in {1, 6} else C["pale"] if n in {2, 4} else C["paper"]
        im = Image.new("RGB", (PX_W, PX_H), rgb(bg))
        draw = ImageDraw.Draw(im)

        if n == 1:
            draw.rectangle([0, 0, 338, PX_H], fill=rgb(C["charcoal"]))
            for i, color in enumerate([C["teal"], C["saffron"], C["plum"]]):
                draw.rounded_rectangle([90, 130 + i * 112, 140, 180 + i * 112], radius=10, fill=rgb(color))
            text(draw, (435, 145), "Slide Dataset\nPrototype v0.3", 76, C["paper"], True)
            text(draw, (438, 390), "A complete labeled corpus with style-anchor controls for generation", 28, "#CED7DE")
            draw.rectangle([438, 478, 640, 484], fill=rgb(C["teal"]))
            text(draw, (1440, 165), str(total), 62, C["cyan"], True)
            text(draw, (1444, 245), "audited labels now available", 20, "#C8D0D8")
            text(draw, (1440, 390), str(remaining), 62, C["saffron"], True)
            text(draw, (1444, 470), "slides still queued", 20, "#C8D0D8")

        elif n == 2:
            text(draw, (94, 74), "The corpus is now fully labeled and ready for controlled generation", 42, C["ink"], True)
            text(draw, (96, 146), "The final tranche completes coverage, while quality gating keeps report pages from steering style too much.", 20, C["muted"])
            metrics = [(str(total), "labeled slides"), (str((total + 4) // 5), "labeled batches"), (str(source["Roland Berger"]), "Roland Berger anchors"), (f"{round(total / 641 * 100)}%", "corpus labeled")]
            for i, (num, label) in enumerate(metrics):
                x = 112 + i * 436
                text(draw, (x, 250), num, 62, C["plum"] if i != 3 else C["teal"], True)
                text(draw, (x + 4, 335), label, 18, C["muted"])
            max_source = max(source.values())
            for i, (label, value) in enumerate(source.most_common(6)):
                bar(draw, 126, 490 + i * 56, label, value, max_source, C["plum"])
            max_density = max(density.values())
            for i, (label, value) in enumerate(density.most_common()):
                x = 1110 + i * 180
                h = int((value / max_density) * 250)
                draw.rectangle([x, 770 - h, x + 90, 770], fill=rgb([C["teal"], C["saffron"], C["plum"]][i % 3]))
                text(draw, (x, 795), label, 16, C["muted"])

        elif n == 3:
            text(draw, (100, 76), "The best style anchors are still consulting-native", 42, C["ink"], True)
            text(draw, (102, 150), "Use World Bank and IMF for robustness, but sample visual direction from Roland Berger, BCG, and Accenture.", 20, C["muted"])
            refs = [
                ("Roland Berger", "roland_berger_trend_compendium_2050_technology_and_innovation_slide_008.png", "data evidence / scatter", C["teal"]),
                ("BCG", "bcg_how-cpg-retail-leaders-maximize-ai-roi_slide_005.png", "structured analysis", C["green"]),
                ("Accenture", "accenture_Accenture-Banking-Top-10-Trends-2024_slide_005.png", "visual narrative", C["violet"]),
            ]
            for i, (name, filename, tag, color) in enumerate(refs):
                x = 108 + i * 588
                paste_slide(im, filename, (x, 235, 500, 288))
                text(draw, (x, 560), name, 24, C["ink"], True)
                draw.rectangle([x, 604, x + 132, 610], fill=rgb(color))
                text(draw, (x, 640), tag, 18, C["muted"])

        elif n == 4:
            text(draw, (94, 74), "Layout labels are already expressive enough for retrieval", 42, C["ink"], True)
            evidence = layout["two_col_chart"] + layout["full_width_chart"] + layout["scatter_bubble_chart"] + layout["comparison_table"]
            frameworks = layout["process_flow_timeline"] + layout["icon_grid"] + layout["mixed_layout"]
            narrative = layout["title_slide"] + layout["section_divider"] + layout["three_col_text"] + layout["appendix"]
            for i, (name, value, color) in enumerate([("Evidence", evidence, C["teal"]), ("Framework", frameworks, C["plum"]), ("Narrative", narrative, C["saffron"])]):
                x = 115 + i * 584
                text(draw, (x, 250), str(value), 62, color, True)
                text(draw, (x, 340), name, 26, C["ink"], True)
                draw.rectangle([x, 390, x + 140, 396], fill=rgb(color))
            max_layout = max(layout.values())
            for i, (label, value) in enumerate(layout.most_common(8)):
                bar(draw, 120, 545 + i * 48, label, value, max_layout, C["teal"])
            max_chart = max(chart.values())
            for i, (label, value) in enumerate(chart.most_common(6)):
                x = 1110 + i * 110
                h = int((value / max_chart) * 220)
                draw.rectangle([x, 820 - h, x + 60, 820], fill=rgb([C["plum"], C["teal"], C["saffron"]][i % 3]))
                text(draw, (x - 8, 845), label, 14, C["muted"])

        elif n == 5:
            text(draw, (100, 78), "A practical generator starts with intent, then style memory", 42, C["ink"], True)
            steps = [("1", "Brief", "topic, audience, decision, message"), ("2", "Retrieve", "layout + chart + density neighbors"), ("3", "Author", "editable pptxgenJS shapes and charts"), ("4", "Score", "QC labels, legibility, visual distance")]
            for i, (num, title, desc) in enumerate(steps):
                y = 220 + i * 156
                draw.rounded_rectangle([120, y, 184, y + 64], radius=12, fill=rgb(C["plum"] if i < 2 else C["teal"]))
                text(draw, (146, y + 14), num, 24, C["paper"], True)
                text(draw, (232, y - 2), title, 28, C["ink"], True)
                text(draw, (232, y + 48), desc, 19, C["muted"])
            draw.rounded_rectangle([1160, 200, 1630, 680], radius=12, fill=rgb(C["black"]))
            text(draw, (1210, 270), "Prompt pack", 24, C["paper"], True)
            for i, label in enumerate(["layout_type", "chart_type", "text_density", "palette", "references"]):
                text(draw, (1210, 345 + i * 54), label, 18, "#D7DEE6")
                draw.rectangle([1480, 358 + i * 54, 1555 + i * 28, 364 + i * 54], fill=rgb(C["teal"] if i % 2 == 0 else C["saffron"]))

        else:
            text(draw, (120, 90), "Next sprint", 44, C["paper"], True)
            text(draw, (122, 164), "Move from complete labels to ranked generated slide variants", 20, "#BAC5CE")
            next_items = [
                ("Lock source weights", "Favor consulting-native slides for style; keep report pages as background data."),
                ("Add human audit marks", "Keep draft labels, but flag subjective layout calls before final training use."),
                ("Generate 3 variants per prompt", "Use retrieval packs and compare native chart structure."),
                ("Score presentation quality", "Combine schema checks, render checks, and manual preference."),
            ]
            for i, (title, body) in enumerate(next_items):
                x = 132 + (i % 2) * 858
                y = 300 + (i // 2) * 252
                draw.rectangle([x, y, x + 12, y + 122], fill=rgb(C["saffron"] if i % 2 else C["teal"]))
                text(draw, (x + 38, y - 2), title, 26, C["paper"], True)
                text(draw, (x + 38, y + 58), body, 19, "#C4CED7")
            text(draw, (132, 920), "Decision: keep pptxgenJS for generated decks; use Python only for data prep and preview artifacts.", 20, C["paper"], True)

        path = PREVIEW_DIR / f"slide_{n:03d}.png"
        im.save(path)
        pages.append(path)

    thumbs = []
    for path in pages:
        thumb = Image.open(path).convert("RGB")
        thumb.thumbnail((384, 216))
        thumbs.append(thumb)
    sheet = Image.new("RGB", (384 * len(thumbs), 216), rgb("#EFEFEF"))
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, (384 * i, 0))
    sheet.save(PREVIEW_DIR / "contact_sheet.png")
    print(f"Wrote previews to {PREVIEW_DIR}")


if __name__ == "__main__":
    render()
