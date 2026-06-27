from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import ensure_output_dir

OUT_DIR = ensure_output_dir()
PREVIEW_DIR = OUT_DIR / "html_corpus_ai_banking_sample_previews"
PX_W, PX_H = 1920, 1080

C = {
    "black": "#050505",
    "ink": "#111111",
    "grey": "#8D949B",
    "paleGrey": "#D9DDE2",
    "teal": "#0AA8BD",
    "teal2": "#80C9D6",
    "darkBlue": "#166F9F",
    "paper": "#FFFFFF",
    "panel": "#F2F4F6",
    "grid": "#E1E5EA",
    "purple": "#5B2D8E",
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
    draw.multiline_text(xy, value, fill=rgb(color), font=font(size, bold), spacing=8)


def header(draw: ImageDraw.ImageDraw, section: str, title: str, subtitle: str) -> None:
    text(draw, (144, 46), section, 26, C["grey"], True)
    text(draw, (144, 132), title, 50, C["black"])
    text(draw, (144, 306), subtitle, 36, C["grey"])
    text(draw, (1700, 58), "Corpus\nsample", 20, C["ink"])
    text(draw, (1790, 78), "B", 58, "#A0A6AA", True)


def footer(draw: ImageDraw.ImageDraw, n: int, anchor: str) -> None:
    text(draw, (144, 1026), f"Design anchor: {anchor}", 13, "#444444")
    text(draw, (1800, 1026), f"| {n:02d}", 13, "#777777")


def render() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    pages: list[Path] = []

    for n in range(1, 8):
        bg = C["black"] if n == 7 else C["paper"]
        im = Image.new("RGB", (PX_W, PX_H), rgb(bg))
        draw = ImageDraw.Draw(im)

        if n == 1:
            draw.rectangle([0, 0, 26, PX_H], fill=rgb(C["teal"]))
            draw.rectangle([26, 0, 32, PX_H], fill=rgb(C["purple"]))
            text(draw, (136, 94), "HTML/CSS corpus sample", 26, C["grey"], True)
            text(draw, (136, 170), "AI-native banking platforms", 66, C["black"])
            text(draw, (136, 260), "where value scales first", 58, C["black"])
            text(draw, (140, 392), "A generated sample deck using the newly processed Roland Berger HTML/CSS\nslide conversions as layout memory", 28, C["grey"])
            draw.line([140, 500, 470, 500], fill=rgb(C["black"]), width=7)
            tags = [("011", "diffusion bars"), ("012", "regional comparison"), ("019", "dual donut shift"), ("024", "bubble timeline"), ("029", "market value comparison")]
            for i, (num, label) in enumerate(tags):
                x = 1120 + (i % 2) * 310
                y = 620 + (i // 2) * 84
                text(draw, (x, y), num, 28, C["teal"], True)
                text(draw, (x + 70, y + 5), label, 18, C["grey"])
            footer(draw, 1, "html_slides/*priority Roland Berger conversions")

        elif n == 2:
            header(draw, "1. Adoption velocity - From pilots to institutional workflows", "AI platforms are reaching diffusion thresholds faster", "Time from first deployment to 25% weekly active workflow coverage [months]")
            rows = [("Core analytics dashboards", 46), ("RPA workflow scripts", 35), ("Cloud data lake", 31), ("Document AI", 26), ("GenAI knowledge assistant", 16), ("Credit memo copilot", 13), ("Service AI copilot", 7), ("Agentic queue orchestration", 4)]
            draw.line([490, 450, 490, 965], fill=rgb(C["black"]), width=2)
            for i, (label, value) in enumerate(rows):
                y = 466 + i * 68
                text(draw, (144, y + 4), label, 24, C["black"])
                w = int(value / 46 * 995)
                draw.rectangle([494, y, 494 + w, y + 38], fill=rgb(C["teal"]))
                text(draw, (510 + w, y + 2), str(value), 24, C["black"], True)
            text(draw, (1160, 930), "Read: platformized AI compresses the path from experiment to workflow coverage.", 19, C["grey"])
            footer(draw, 2, "slide_011.html")

        elif n == 3:
            header(draw, "2. Deployment footprint - Readiness is uneven by market", "AI readiness is uneven by market", "Indexed AI banking platform readiness by region [0-100]")
            regions = [("North America", 76, 86), ("Europe", 63, 78), ("Asia-Pacific", 68, 84), ("Middle East", 52, 70), ("Latin America", 45, 61)]
            text(draw, (150, 455), "2024", 34, C["black"], True)
            draw.line([265, 482, 860, 482], fill=rgb(C["black"]), width=8)
            text(draw, (1020, 455), "2028 target", 34, C["black"], True)
            draw.line([1220, 482, 1780, 482], fill=rgb(C["black"]), width=8)
            for i, (label, now, target) in enumerate(regions):
                y = 545 + i * 76
                text(draw, (150, y), label, 22, C["black"])
                draw.rectangle([380, y, 380 + now * 5, y + 24], fill=rgb(C["teal2"]))
                text(draw, (400 + now * 5, y - 2), str(now), 20, C["black"], True)
                text(draw, (1020, y), label, 22, C["black"])
                draw.rectangle([1250, y, 1250 + target * 5, y + 24], fill=rgb(C["teal"]))
                text(draw, (1270 + target * 5, y - 2), str(target), 20, C["black"], True)
            footer(draw, 3, "slide_012.html")

        elif n == 4:
            header(draw, "3. Value pools - Economics shift as platforms mature", "Value pools shift as platforms mature", "Illustrative banking AI value pool split [% of total]")
            colors = [C["teal"], C["teal2"], C["paleGrey"], C["darkBlue"]]
            for cx, title, vals in [(500, "2024", [58, 18, 16, 8]), (1340, "2028", [34, 24, 28, 14])]:
                text(draw, (cx - 230, 452), title, 38, C["black"], True)
                start = -90
                total = sum(vals)
                for val, color in zip(vals, colors):
                    end = start + 360 * val / total
                    draw.pieslice([cx - 190, 520, cx + 190, 900], start, end, fill=rgb(color))
                    start = end
                draw.ellipse([cx - 105, 605, cx + 105, 815], fill=rgb(C["paper"]))
            for i, label in enumerate(["Efficiency", "Risk controls", "Revenue growth", "New propositions"]):
                x = 520 + i * 250
                draw.rectangle([x, 945, x + 20, 965], fill=rgb(colors[i]))
                text(draw, (x + 30, 942), label, 17, C["ink"])
            footer(draw, 4, "slide_019.html")

        elif n == 5:
            header(draw, "4. Platform evolution - The operating system gets broader", "The operating system gets broader", "Milestones in AI-native banking platform evolution")
            draw.line([170, 940, 1780, 940], fill=rgb(C["teal"]), width=4)
            for i, year in enumerate([2024, 2025, 2026, 2027, 2028, 2029]):
                x = 170 + i * 290
                draw.line([x, 926, x, 954], fill=rgb(C["teal"]), width=2)
                text(draw, (x - 40, 978), str(year), 21, C["black"], True)
            bubbles = [("Service copilot", 290, 820, 62), ("Document AI", 455, 760, 96), ("Credit assistant", 650, 700, 126), ("Risk controls", 865, 620, 156), ("Customer 360", 1075, 505, 196), ("Agentic queueing", 1315, 370, 258), ("Smart operating model", 1510, 190, 360)]
            for label, x, y, r in bubbles:
                draw.ellipse([x, y, x + r, y + r], fill=(*rgb(C["teal"]),))
                text(draw, (x + int(r * 0.2), y + int(r * 0.48)), label, max(13, int(r / 16)), C["black"])
            footer(draw, 5, "slide_024.html")

        elif n == 6:
            header(draw, "5. Economic prize - Platform value scales across three benefit pools", "Platform value scales across benefit pools", "Illustrative annualized value creation potential [INR bn]")
            groups = [("Efficiency", [("Service", 18, C["teal"]), ("Ops", 12, C["teal"])]), ("Risk + credit", [("Credit", 21, C["paleGrey"]), ("Fraud", 15, C["paleGrey"])]), ("Growth", [("Next best", 14, C["teal2"]), ("Pricing", 9, C["teal2"])])]
            for gi, (group, entries) in enumerate(groups):
                gx = 160 + gi * 555
                text(draw, (gx, 455), group, 36, C["black"], True)
                draw.line([gx, 520, gx + 425, 520], fill=rgb(C["black"]), width=8)
                for i, (label, val, color) in enumerate(entries):
                    h = int(val / 28 * 245)
                    x = gx + 70 + i * 170
                    draw.rectangle([x, 790 - h, x + 104, 790], fill=rgb(color))
                    text(draw, (x + 28, 752 - h), str(val), 25, C["black"], True)
                    text(draw, (x - 6, 825), label, 18, C["black"], True)
            text(draw, (1660, 535), "89", 62, C["teal"], True)
            text(draw, (1660, 620), "total illustrative\nannualized\nvalue pool", 20, C["grey"])
            footer(draw, 6, "slide_029.html")

        else:
            draw.rectangle([0, 0, 24, PX_H], fill=rgb(C["teal"]))
            text(draw, (130, 130), "What the new HTML/CSS corpus adds", 60, C["paper"])
            text(draw, (132, 245), "The generator can now retrieve concrete infographic structures, not just generic chart labels.", 28, "#C7D0D8")
            points = [("Layout memory", "fixed 1280x720 object positions"), ("Chart grammar", "bars, donuts, timelines, market comparisons"), ("Density cues", "where titles, captions, values, and footers sit"), ("Next bridge", "convert HTML patterns into reusable PPTX recipes")]
            for i, (title, body) in enumerate(points):
                y = 390 + i * 115
                draw.rectangle([138, y, 152, y + 60], fill=rgb(C["teal"] if i < 2 else C["purple"]))
                text(draw, (180, y - 4), title, 26, C["paper"], True)
                text(draw, (470, y - 4), body, 24, "#C7D0D8")

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
