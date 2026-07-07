from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import ensure_output_dir

OUT_DIR = ensure_output_dir()
PREVIEW_DIR = OUT_DIR / "sample_prompt_genai_banking_previews"
PX_W, PX_H = 1920, 1080

C = {
    "black": "#111216",
    "charcoal": "#252A31",
    "ink": "#20242B",
    "muted": "#6C7480",
    "pale": "#F7F6F2",
    "paper": "#FFFFFF",
    "grid": "#E7E2DA",
    "teal": "#168C9B",
    "cyan": "#35B6C7",
    "plum": "#6B3FA0",
    "saffron": "#F2A541",
    "green": "#6CBF84",
}

USE_CASES = [
    ("Contact center copilot", 88),
    ("Credit memo assistant", 76),
    ("KYC document review", 71),
    ("Collections next action", 63),
    ("Marketing personalization", 54),
]
ADOPTION = {
    "labels": ["M0", "M1", "M2", "M3", "M4", "M5", "M6"],
    "ops": [0, 8, 19, 33, 48, 61, 72],
    "risk": [0, 5, 13, 24, 34, 43, 51],
}
ALLOCATION = [("Platform + security", 34), ("Workflow build", 28), ("Change + training", 22), ("Measurement", 16)]
PORTFOLIO = [("Contact center", 72, 84, 28), ("Credit memo", 64, 77, 22), ("KYC review", 58, 69, 20), ("Collections", 45, 61, 16), ("Marketing", 68, 56, 14)]
ROADMAP = {
    "labels": ["Weeks 1-2", "Weeks 3-6", "Weeks 7-10", "Weeks 11-13"],
    "foundation": [80, 35, 15, 10],
    "pilots": [20, 55, 45, 25],
    "scale": [0, 10, 40, 65],
}


def rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (["arialbd.ttf", "arial.ttf"] if bold else ["arial.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, color: str, bold: bool = False) -> None:
    draw.multiline_text(xy, value, fill=rgb(color), font=font(size, bold), spacing=6)


def line_chart(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x, y, w, h = box
    draw.rectangle([x, y, x + w, y + h], outline=rgb(C["grid"]))
    for i in range(5):
        yy = y + h - int(i * h / 4)
        draw.line([x, yy, x + w, yy], fill=rgb(C["grid"]))
    def plot(vals, color):
        pts = []
        for i, val in enumerate(vals):
            px = x + int(i * w / 6)
            py = y + h - int(val / 80 * h)
            pts.append((px, py))
        draw.line(pts, fill=rgb(color), width=5)
        for px, py in pts:
            draw.ellipse([px - 6, py - 6, px + 6, py + 6], fill=rgb(color))
    plot(ADOPTION["ops"], C["teal"])
    plot(ADOPTION["risk"], C["saffron"])


def render() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    pages: list[Path] = []
    for n in range(1, 7):
        bg = C["black"] if n in {1, 6} else C["pale"] if n in {2, 4} else C["paper"]
        im = Image.new("RGB", (PX_W, PX_H), rgb(bg))
        draw = ImageDraw.Draw(im)

        if n == 1:
            draw.rectangle([0, 0, 318, PX_H], fill=rgb(C["charcoal"]))
            text(draw, (98, 115), "90", 76, C["cyan"], True)
            text(draw, (116, 218), "days", 24, "#BFC9D4")
            text(draw, (432, 145), "GenAI in\nMid-Market\nBanking", 74, C["paper"], True)
            text(draw, (438, 465), "Value capture plan for service, risk, and credit workflows", 28, "#CBD5DD")
            draw.rectangle([438, 550, 632, 556], fill=rgb(C["teal"]))
        elif n == 2:
            text(draw, (94, 74), "Prioritize customer-service and credit workflows first", 44, C["ink"], True)
            text(draw, (96, 148), "They combine visible P&L impact, manageable controls, and enough repeat volume for fast learning.", 20, C["muted"])
            max_v = 100
            for i, (label, value) in enumerate(USE_CASES):
                y = 300 + i * 80
                draw.rectangle([120, y, 120 + int(value / max_v * 620), y + 34], fill=rgb(C["plum"]))
                text(draw, (765, y - 4), f"{label} ({value})", 20, C["ink"])
            text(draw, (1150, 300), "The first wave should prove three things", 26, C["ink"], True)
            for i, word in enumerate(["Impact", "Control", "Repeatability"]):
                draw.rectangle([1160, 370 + i * 125, 1172, 430 + i * 125], fill=rgb(C["teal"] if i != 1 else C["saffron"]))
                text(draw, (1210, 360 + i * 125), word, 24, C["ink"], True)
        elif n == 3:
            text(draw, (100, 76), "Adoption becomes real when pilots are embedded into weekly work", 42, C["ink"], True)
            line_chart(draw, (120, 230, 1120, 600))
            text(draw, (1390, 285), "72%", 68, C["teal"], True)
            text(draw, (1395, 380), "weekly active users\nin operations by month 6", 21, C["muted"])
        elif n == 4:
            text(draw, (94, 74), "The 90-day budget should over-invest in controls and workflow fit", 42, C["ink"], True)
            start = 0
            colors = [C["teal"], C["plum"], C["saffron"], C["green"]]
            for i, (label, value) in enumerate(ALLOCATION):
                width = int(value / 100 * 720)
                draw.rectangle([130 + start, 330, 130 + start + width, 480], fill=rgb(colors[i]))
                text(draw, (130 + start, 510), f"{value}%", 26, colors[i], True)
                text(draw, (130 + start, 555), label, 18, C["muted"])
                start += width
            text(draw, (1020, 280), "Expected operating movement", 28, C["ink"], True)
            impacts = [("Call handling time", "-18%"), ("Manual review hours", "-26%"), ("First-contact resolution", "+12%"), ("Cycle time to decision", "-21%")]
            for i, (label, value) in enumerate(impacts):
                text(draw, (1020, 350 + i * 75), label, 20, C["ink"])
                text(draw, (1450, 345 + i * 75), value, 28, C["teal"] if "-" in value else C["saffron"], True)
        elif n == 5:
            text(draw, (100, 76), "A portfolio lens prevents the pilot list from becoming a wish list", 42, C["ink"], True)
            x0, y0, w, h = 130, 240, 1040, 610
            draw.rectangle([x0, y0, x0 + w, y0 + h], outline=rgb(C["grid"]))
            for label, xval, yval, size in PORTFOLIO:
                px = x0 + int((xval - 35) / 45 * w)
                py = y0 + h - int((yval - 45) / 45 * h)
                r = size
                draw.ellipse([px - r, py - r, px + r, py + r], fill=rgb(C["teal"]), outline=rgb(C["paper"]), width=3)
                text(draw, (px + r + 8, py - 10), label, 16, C["ink"])
            text(draw, (1240, 270), "Bubble size indicates\nrelative 90-day benefit pool.", 22, C["muted"])
        else:
            text(draw, (110, 86), "The operating model shifts from foundation to scale by week 10", 42, C["paper"], True)
            labels = ROADMAP["labels"]
            series = [("foundation", C["charcoal"]), ("pilots", C["teal"]), ("scale", C["saffron"])]
            for i, label in enumerate(labels):
                x = 180 + i * 260
                bottom = 800
                for key, color in series:
                    value = ROADMAP[key][i]
                    hh = int(value / 100 * 420)
                    draw.rectangle([x, bottom - hh, x + 110, bottom], fill=rgb(color), outline=rgb(C["black"]))
                    bottom -= hh
                text(draw, (x - 8, 830), label, 18, "#BAC5CE")
            text(draw, (1280, 300), "Decision gates", 28, C["paper"], True)
            for i, gate in enumerate(["security pattern approved", "two workflows live", "weekly benefit signal", "scale backlog funded"]):
                draw.rectangle([1280, 370 + i * 75, 1294, 420 + i * 75], fill=rgb(C["teal"] if i < 2 else C["saffron"]))
                text(draw, (1320, 370 + i * 75), gate, 20, "#C6CFD8")

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
