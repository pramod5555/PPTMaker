from __future__ import annotations

from math import cos, pi, sin
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "html_slides"
OUT.mkdir(exist_ok=True)

CYAN = "#0aa8bd"
BLUE = "#166f9f"
GREY = "#8e959b"
LIGHT = "#d9dde2"
BLACK = "#000000"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def css() -> str:
    return """
html, body { margin:0; width:1280px; height:720px; background:#fff; font-family: Calibri, Arial, sans-serif; }
.slide { width: 1280px; height: 720px; position: relative; overflow: hidden; background:#fff; color:#000; }
.section { position:absolute; left:96px; top:32px; color:#8d949b; font-size:22px; font-weight:700; }
.title { position:absolute; left:96px; top:88px; width:1080px; font-size:40px; line-height:1.08; font-weight:300; letter-spacing:0; }
.subtitle { position:absolute; left:96px; top:205px; width:1000px; font-size:34px; line-height:1.08; color:#90979e; font-weight:300; }
.logo { position:absolute; right:70px; top:38px; font-size:22px; line-height:.85; text-align:right; }
.logo:after { content:"B"; display:inline-block; margin-left:8px; font-size:56px; font-weight:900; color:#a0a6aa; vertical-align:middle; }
.foot { position:absolute; left:96px; bottom:22px; width:980px; font-size:13px; }
.page { position:absolute; right:76px; bottom:22px; font-size:13px; color:#777; }
.axis { position:absolute; background:#000; }
.label { position:absolute; font-size:21px; line-height:1.1; }
.value { position:absolute; font-size:22px; font-weight:800; }
.small { position:absolute; font-size:13px; line-height:1.1; }
"""


def write(slide_id: str, body: str) -> None:
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{slide_id}</title>
  <style>{css()}</style>
</head>
<body><div class="slide">
{body}
</div></body>
</html>
"""
    (OUT / f"{slide_id}.html").write_text(html, encoding="utf-8")


def shell(page: int, section: str, title: str, subtitle: str, inner: str, foot: str) -> str:
    return "\n".join(
        [
            f'<div class="section">{esc(section)}</div>',
            f'<div class="logo">Roland<br>Berger</div>',
            f'<div class="title">{esc(title)}</div>',
            f'<div class="subtitle">{esc(subtitle)}</div>',
            inner,
            f'<div class="foot">{esc(foot)}</div>',
            f'<div class="page">| {page}</div>',
        ]
    )


def slide_011() -> None:
    rows = [
        ("Electricity (1873)", 46),
        ("Telephone (1876)", 35),
        ("Radio (1897)", 31),
        ("TV (1926)", 26),
        ("PC (1975)", 16),
        ("Mobile phone (1987)", 13),
        ("World Wide Web (1991)", 7),
        ("Facebook (2004)", 4),
    ]
    bits = ['<div class="axis" style="left:326px; top:300px; width:1px; height:375px;"></div>']
    for i, (label, val) in enumerate(rows):
        y = 312 + i * 48
        bits.append(f'<div class="label" style="left:96px; top:{y}px; width:220px;">{esc(label)}</div>')
        bits.append(f'<div style="position:absolute; left:327px; top:{y}px; width:{val*15}px; height:36px; background:{CYAN};"></div>')
        bits.append(f'<div class="value" style="left:{327+val*15+8}px; top:{y+5}px;">{val}</div>')
    write(
        "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_011",
        shell(
            11,
            "1. Power of innovation - Driver of economic prosperity",
            "Increasingly, innovations are reaching significant diffusion milestones faster",
            "Time from introducing a product to an adoption rate of 25% across US citizens [years]",
            "\n".join(bits),
            "Source: FAZ",
        ),
    )


def slide_012() -> None:
    regions = [
        ("North\nAmerica", 250, 360, 118, 374, 65, 99),
        ("Western\nEurope", 600, 350, 492, 365, 45, 92),
        ("Central &\nEastern Europe", 770, 385, 860, 350, 15, 92),
        ("Africa &\nMiddle East", 760, 530, 858, 500, 10, 71),
        ("Asia &\nPacific", 1080, 500, 1005, 462, 17, 81),
        ("Latin\nAmerica", 330, 585, 215, 530, 14, 80),
    ]
    bits = [
        '<div style="position:absolute; left:150px; top:340px; width:960px; height:290px; background:radial-gradient(ellipse at 20% 35%, #d9dde2 0 18%, transparent 19%),radial-gradient(ellipse at 48% 35%, #d9dde2 0 20%, transparent 21%),radial-gradient(ellipse at 75% 35%, #d9dde2 0 25%, transparent 26%),radial-gradient(ellipse at 37% 80%, #d9dde2 0 12%, transparent 13%),radial-gradient(ellipse at 62% 78%, #d9dde2 0 14%, transparent 15%); opacity:.9;"></div>',
        f'<div style="position:absolute; left:96px; top:650px; width:28px; height:18px; background:{BLUE};"></div><div class="label" style="left:132px; top:647px; font-size:16px;">2013</div>',
        f'<div style="position:absolute; left:220px; top:650px; width:28px; height:18px; background:{CYAN};"></div><div class="label" style="left:256px; top:647px; font-size:16px;">2021</div>',
    ]
    for label, x, y, lx, ly, v13, v21 in regions:
        h13, h21 = int(v13 * 1.7), int(v21 * 1.7)
        bits.append(f'<div class="label" style="left:{lx}px; top:{ly}px; font-size:28px; font-weight:800; white-space:pre-line;">{esc(label)}</div>')
        bits.append(f'<div style="position:absolute; left:{x}px; top:{y+95-h13}px; width:31px; height:{h13}px; background:{BLUE};"></div>')
        bits.append(f'<div style="position:absolute; left:{x+43}px; top:{y+95-h21}px; width:31px; height:{h21}px; background:{CYAN};"></div>')
        bits.append(f'<div class="value" style="left:{x-2}px; top:{y+70-h13}px; font-size:18px;">{v13}</div>')
        bits.append(f'<div class="value" style="left:{x+42}px; top:{y+70-h21}px; font-size:18px;">{v21}</div>')
        bits.append(f'<div class="axis" style="left:{x-8}px; top:{y+96}px; width:92px; height:1px;"></div>')
    write(
        "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_012",
        shell(
            12,
            "1. Power of innovation - Driver of economic prosperity",
            "Fast diffusion of technology is a global reality and not restricted to advanced economies",
            "Mobile smart devices and connections as share of total number of devices and connections, 2013 vs. 2021 [%]",
            "\n".join(bits),
            "Source: Cisco",
        ),
    )


def donut(cx: int, cy: int, r: int, vals: list[tuple[str, float, str]], title: str) -> str:
    total = sum(v for _, v, _ in vals)
    start = -90
    paths = []
    for _, val, color in vals:
        ang = val / total * 360
        end = start + ang
        large = 1 if ang > 180 else 0
        x1, y1 = cx + r * cos(start * pi / 180), cy + r * sin(start * pi / 180)
        x2, y2 = cx + r * cos(end * pi / 180), cy + r * sin(end * pi / 180)
        paths.append(f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {large},1 {x2:.1f},{y2:.1f} Z" fill="{color}"/>')
        start = end
    labels = []
    for i, (name, val, _) in enumerate(vals):
        labels.append(f'<text x="{cx + (180 if i % 2 else -240)}" y="{cy-120+i*38}" font-size="18">{esc(name)} <tspan font-weight="800">{val}</tspan></text>')
    return f"""
<text x="{cx-r-120}" y="335" font-size="40" font-weight="800">{title}</text>
<line x1="{cx-r-8}" y1="360" x2="{cx+r+150}" y2="360" stroke="#000" stroke-width="8"/>
<g>{''.join(paths)}<circle cx="{cx}" cy="{cy}" r="{int(r*.58)}" fill="#fff"/></g>
{''.join(labels)}
"""


def slide_019() -> None:
    vals06 = [("USA", 47.1, CYAN), ("Other countries", 22.5, "#80c9d6"), ("Japan", 12.8, LIGHT), ("China", 1.5, "#9cb6d4"), ("South Korea", 2.2, BLUE), ("EPO", 13.9, BLACK)]
    vals16 = [("USA", 39.5, CYAN), ("Other countries", 15.2, "#80c9d6"), ("Japan", 15.0, LIGHT), ("China", 7.6, "#9cb6d4"), ("South Korea", 6.0, BLUE), ("EPO", 16.7, BLACK)]
    inner = f'<svg viewBox="0 0 1280 720" width="1280" height="720">{donut(330, 490, 135, vals06, "2006")}{donut(900, 490, 135, vals16, "2016")}</svg>'
    write(
        "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_019",
        shell(
            19,
            "2. Life Sciences - Addressing major challenges of humanity",
            "Life Sciences markets are shifting - the US are losing share while Asian countries are gaining",
            "Selected PCT Life Sciences publications by filing office [% of global total]",
            inner,
            "Source: WIPO",
        ),
    )


def slide_024() -> None:
    years = [1985, 1990, 1995, 2000, 2005, 2010, 2015]
    bubbles = [
        (250, 640, 18, "mp3"),
        (360, 615, 34, "Search engine"),
        (470, 608, 42, "E-Commerce"),
        (610, 565, 58, "Smartphone"),
        (735, 525, 72, "Cloud"),
        (900, 460, 140, "Big Data"),
        (1070, 400, 270, "Smart everything"),
    ]
    bits = ['<div class="axis" style="left:116px; top:654px; width:1100px; height:2px; background:#00a7c8;"></div>']
    for i, yr in enumerate(years):
        x = 116 + i * 155
        bits.append(f'<div class="axis" style="left:{x}px; top:645px; width:1px; height:18px; background:#00a7c8;"></div><div class="value" style="left:{x-22}px; top:672px; font-size:22px;">{yr}</div>')
    bits.append('<div class="label" style="left:96px; top:372px; font-size:23px; font-weight:800;">Web 1.0</div><div class="label" style="left:560px; top:372px; font-size:23px; font-weight:800;">Web 2.0</div><div class="label" style="left:1135px; top:372px; font-size:23px; font-weight:800;">Web 3.0</div>')
    for x, y, r, name in bubbles:
        bits.append(f'<div style="position:absolute; left:{x-r}px; top:{y-r}px; width:{2*r}px; height:{2*r}px; border-radius:50%; background:{CYAN}; opacity:.35;"></div>')
        bits.append(f'<div class="small" style="left:{x-r//2}px; top:{y-6}px;">{esc(name)}</div>')
    write(
        "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_024",
        shell(
            24,
            "3. Digital Transformation - The digital economy is here",
            "Digital Transformation has changed everything and is set to continue",
            "Milestones in the digital evolution",
            "\n".join(bits),
            "Source: Roland Berger analysis",
        ),
    )


def slide_029() -> None:
    entries = [
        ("Roland Berger", "1.25", "EUR tn", "Europe"),
        ("European Commission", "> 1.0", "EUR tn", "Europe"),
        ("Cisco", "8.0", "USD tn", "Global"),
        ("Machina Research", "3.0", "USD tn", "Global"),
    ]
    bits = []
    base = 470
    for i, (name, val, unit, group) in enumerate(entries):
        x = 100 + i * 270
        h = [92, 76, 158, 82][i]
        color = CYAN if i < 2 else LIGHT
        bits.append(f'<div class="value" style="left:{x+96}px; top:282px; font-size:24px;">{esc(val)}</div>')
        bits.append(f'<div style="position:absolute; left:{x+45}px; top:{base-h}px; width:128px; height:{h}px; background:{color}; display:flex; align-items:center; justify-content:center; font-weight:800; color:{"#fff" if i<2 else BLUE}; text-align:center; font-size:12px;">{esc(name)}</div>')
        bits.append(f'<div class="axis" style="left:{x}px; top:{base}px; width:220px; height:1px;"></div>')
        bits.append(f'<div class="label" style="left:{x}px; top:{base+30}px; width:220px; font-size:20px; font-weight:800;">{esc(name)}</div>')
        bits.append(f'<div class="label" style="left:{x}px; top:{base+72}px; width:220px; font-size:18px;">{esc(val)} {esc(unit)} value creation<br>{esc(group)} forecast</div>')
    bits.append('<div class="value" style="left:96px; top:300px; font-size:34px;">Europe</div><div class="axis" style="left:96px; top:354px; width:520px; height:6px;"></div><div class="value" style="left:930px; top:300px; font-size:34px;">Global</div><div class="axis" style="left:688px; top:354px; width:520px; height:6px;"></div>')
    write(
        "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_029",
        shell(
            29,
            "3. Digital Transformation - The digital economy is here",
            "Digital Transformation/IoT is forecast to boost the global economy over next decades",
            "Economic value creation in Europe and globally with Digital Transformation/IoT",
            "\n".join(bits),
            "Source: Roland Berger, European Commission, Cisco, Machina Research",
        ),
    )


def main() -> None:
    slide_011()
    slide_012()
    slide_019()
    slide_024()
    slide_029()


if __name__ == "__main__":
    main()
