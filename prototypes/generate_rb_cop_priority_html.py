from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "html_slides"
OUT.mkdir(exist_ok=True)

W, H = 1280, 720
BLUE = "#003f6b"
BAR = "#0b4774"
STEEL = "#6f8db1"
GOLD = "#d6b900"
GOLD_LIGHT = "#eadb73"
TEXT = "#242424"


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def css() -> str:
    return f"""
html, body {{ margin: 0; width: {W}px; height: {H}px; background: #fff; font-family: Calibri, Arial, sans-serif; }}
.slide {{ width: {W}px; height: {H}px; position: relative; overflow: hidden; background: #fff; color: {TEXT}; }}
.kicker {{ position:absolute; right:92px; top:48px; font-size:15px; color:{BLUE}; }}
.page {{ position:absolute; right:54px; top:48px; font-size:16px; color:#222; font-weight:700; }}
.section-mark {{ position:absolute; left:72px; top:96px; width:48px; height:6px; background:{GOLD}; }}
.letter {{ position:absolute; left:72px; top:124px; font-size:20px; color:{GOLD}; font-weight:800; }}
.headline {{ position:absolute; left:98px; top:124px; width:1020px; font-size:25px; line-height:1.18; font-weight:800; }}
.subhead {{ position:absolute; left:72px; top:170px; width:830px; font-size:15px; line-height:1.25; font-weight:800; }}
.source {{ position:absolute; left:72px; bottom:30px; font-size:12px; color:#444; }}
.callout {{ position:absolute; color:{GOLD}; font-family: Georgia, serif; font-size:22px; line-height:1.18; }}
.note {{ position:absolute; font-size:12px; color:#555; }}
.blue-panel {{ position:absolute; background:{STEEL}; color:#fff; box-sizing:border-box; padding:15px 18px; }}
.bar-label {{ position:absolute; font-size:14px; line-height:1.1; }}
.value {{ position:absolute; font-size:18px; font-weight:800; }}
.axis {{ position:absolute; height:1px; background:#222; }}
.mini-title {{ position:absolute; font-size:21px; font-weight:800; color:{BLUE}; }}
.tiny {{ font-size:11px; color:#555; }}
"""


def write(slide_id: str, body: str) -> None:
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{slide_id}</title>
  <style>{css()}</style>
</head>
<body>
  <div class="slide">
{body}
  </div>
</body>
</html>
"""
    (OUT / f"{slide_id}.html").write_text(html, encoding="utf-8")


def shell(page: int, letter: str, headline: str, body: str, subhead: str = "", source: str = "Source: VDMA and Roland Berger study") -> str:
    return "\n".join(
        [
            '<div class="kicker">Next Generation Manufacturing</div>',
            f'<div class="page">| {page}</div>',
            '<div class="section-mark"></div>',
            f'<div class="letter">{esc(letter)}</div>',
            f'<div class="headline">{esc(headline)}</div>',
            f'<div class="subhead">{esc(subhead)}</div>' if subhead else "",
            body,
            f'<div class="source">{esc(source)}</div>',
        ]
    )


def vertical_bar_chart(x: int, y: int, values: list[tuple[str, int, int]], scale: float, w: int = 34, gap: int = 98, plot_h: int = 252) -> str:
    bits = [f'<div class="axis" style="left:{x}px; top:{y+plot_h}px; width:{len(values)*gap+24}px;"></div>']
    for i, (label, n, pct) in enumerate(values):
        bx = x + 28 + i * gap
        h = int(pct * scale)
        top = y + plot_h - h
        bits.append(f'<div style="position:absolute; left:{bx}px; top:{top}px; width:{w}px; height:{h}px; background:{BAR};"></div>')
        bits.append(f'<div class="value" style="left:{bx-8}px; top:{top-26}px;">{n} <span style="font-weight:400;">[{pct}%]</span></div>')
        label_html = esc(label).replace("|", "<br>")
        bits.append(f'<div class="bar-label" style="left:{bx-8}px; top:{y+plot_h+14}px; width:118px;">{label_html}</div>')
    return "\n".join(bits)


def horizontal_bars(x: int, y: int, rows: list[tuple[str, int]], width: int, color: str = BAR, row_gap: int = 46, h: int = 18) -> str:
    bits = []
    for i, (label, value) in enumerate(rows):
        yy = y + i * row_gap
        bw = int(width * value / 100)
        bits.append(f'<div class="bar-label" style="left:{x}px; top:{yy-21}px; width:{width+150}px;">{esc(label)}</div>')
        bits.append(f'<div style="position:absolute; left:{x}px; top:{yy}px; width:{bw}px; height:{h}px; background:{color};"></div>')
        bits.append(f'<div class="value" style="left:{x+bw+8}px; top:{yy-3}px;">{value}%</div>')
    return "\n".join(bits)


def slide_009() -> None:
    body = shell(
        9,
        "B",
        "The surveyed companies are feeling high cost pressure on manufacturing and expect competition to intensify",
        "\n".join(
            [
                '<div style="position:absolute; left:72px; top:210px; width:430px; font-family:Georgia,serif; font-size:18px; line-height:1.28;">Cost and efficiency pressure is a constant in production. Eighty percent of participants agree that manufacturing is under pressure to further optimize costs and efficiency, while almost all respondents expect pressure to stay high or increase.</div>',
                '<div style="position:absolute; left:570px; top:205px; font-size:14px; font-weight:800;">Pressure to increase efficiency / reduce costs in manufacturing</div>',
                '<div style="position:absolute; left:570px; top:242px; color:#004477; font-weight:800;">N = 340</div>',
                vertical_bar_chart(570, 248, [("Disagree|completely", 2, 1), ("Disagree", 14, 4), ("Neither agree|nor disagree", 52, 15), ("Agree", 115, 34), ("Agree|completely", 157, 46)], 4.0, 28, 92, 214),
                '<div style="position:absolute; left:1015px; top:330px; color:#d1b100; font-size:18px; font-weight:800;">CEOs:<br>29%<br>COOs:<br>63%</div>',
                '<div style="position:absolute; left:570px; top:545px; font-size:14px; font-weight:800;">Expected change in coming years</div>',
                '<div style="position:absolute; left:570px; top:572px; color:#004477; font-weight:800;">N = 340</div>',
                vertical_bar_chart(570, 535, [("Decrease", 4, 1), ("No change", 117, 34), ("Increase", 219, 64)], 1.6, 30, 175, 105),
                '<div class="callout" style="left:72px; top:575px; width:430px;">Respondents expect cost pressure on production to increase in the future.</div>',
            ]
        ),
    )
    write("roland_berger_cop_vdma_studie_slide_009", body)


def slide_012() -> None:
    values = [
        ("Competitors follow completely different approaches", 22, 7),
        ("Less than half use similar approaches", 67, 22),
        ("Mixed picture", 78, 26),
        ("More than half follow similar approaches", 97, 32),
        ("Little room for differentiation", 37, 12),
    ]
    body = shell(
        12,
        "E",
        "Companies are seeing their competitors apply similar optimization levers - There is little room to differentiate",
        "\n".join(
            [
                '<div style="position:absolute; left:72px; top:185px; color:#004477; font-weight:800;">N = 301</div>',
                vertical_bar_chart(125, 210, values, 6.6, 26, 190),
                "".join(f'<div style="position:absolute; left:{118+i*190}px; top:459px; width:42px; height:42px; border-radius:50%; background:{GOLD}; color:#fff; text-align:center; line-height:42px; font-size:22px; font-weight:800;">{i+1}</div>' for i in range(5)),
                '<div class="callout" style="left:120px; top:610px; width:780px;">Some 13% of large companies agree with statements 1 and 2, whereas 42% of smaller companies agree.</div>',
            ]
        ),
    )
    write("roland_berger_cop_vdma_studie_slide_012", body)


def mini_relevance(x: int, y: int, points: list[tuple[int, int]], title: str) -> str:
    poly = " ".join(f"{70 + px*58},{42 + py*20}" for px, py in points)
    dots = "".join(f'<circle cx="{70 + px*58}" cy="{42 + py*20}" r="7" fill="{GOLD}"/>' for px, py in points)
    return f"""
<div style="position:absolute; left:{x}px; top:{y}px; width:392px; height:150px; background:{STEEL};">
<svg viewBox="0 0 392 150" width="392" height="150">
  <text x="155" y="24" font-size="13" fill="#fff" font-weight="800" letter-spacing="1">RELEVANCE</text>
  <text x="32" y="48" font-size="12" fill="#fff">low</text><text x="333" y="48" font-size="12" fill="#fff">high</text>
  <line x1="35" y1="64" x2="35" y2="130" stroke="#fff"/><line x1="338" y1="64" x2="338" y2="130" stroke="#fff"/>
  <line x1="35" y1="86" x2="338" y2="86" stroke="#fff" stroke-dasharray="1 2" opacity=".9"/>
  <line x1="35" y1="108" x2="338" y2="108" stroke="#fff" stroke-dasharray="1 2" opacity=".9"/>
  <line x1="97" y1="64" x2="97" y2="130" stroke="#fff" stroke-dasharray="1 2" opacity=".9"/><line x1="159" y1="64" x2="159" y2="130" stroke="#fff" stroke-dasharray="1 2" opacity=".9"/><line x1="221" y1="64" x2="221" y2="130" stroke="#fff" stroke-dasharray="1 2" opacity=".9"/><line x1="283" y1="64" x2="283" y2="130" stroke="#fff" stroke-dasharray="1 2" opacity=".9"/>
  <polyline points="{poly}" fill="none" stroke="{GOLD}" stroke-width="3"/>
  {dots}
</svg></div>
<div class="mini-title" style="left:{x-520}px; top:{y+20}px;">{esc(title)}</div>
"""


def trend_block(x: int, y: int, title: str, bullets: list[str], score: int) -> str:
    rows = "".join(f'<div style="position:absolute; left:{x}px; top:{y+72+i*24}px; width:550px; font-size:14px; border-bottom:1px dotted #888; padding-bottom:4px;">{esc(b)}</div>' for i, b in enumerate(bullets))
    squares = "".join(f'<span style="display:inline-block; width:11px; height:11px; margin-right:4px; background:{"#d6b900" if i < score else "#fff"}; border:1px solid #d6b900;"></span>' for i in range(4))
    return f"""
<div style="position:absolute; left:{x}px; top:{y}px; width:58px; height:58px; border-radius:50%; background:{BLUE};"></div>
<div style="position:absolute; left:{x+74}px; top:{y+14}px;">{squares}</div>
<div class="mini-title" style="left:{x+74}px; top:{y+36}px;">{esc(title)}</div>
{rows}
"""


def slide_014() -> None:
    body = shell(
        14,
        "F",
        "The survey reveals the most relevant trends: location matters, digitalization and sustainability",
        "\n".join(
            [
                trend_block(72, 190, "LOCATION MATTERS", ["Local-for-local production", "Higher awareness of product origin", "Local sourcing reduces supply chain risk", "De-risk end-to-end delivery"], 4),
                trend_block(72, 375, "SUSTAINABILITY", ["Reduce greenhouse gas emissions", "Circular economy and waste reduction", "Inclusive society and equal treatment", "Internal ESG reporting and KPIs", "Improve ESG ratings"], 3),
                mini_relevance(720, 190, [(3, 0), (3, 1), (4, 2), (5, 3)], " "),
                mini_relevance(720, 375, [(3, 0), (2, 1), (1, 2), (3, 3), (4, 4)], " "),
                '<div class="tiny" style="position:absolute; left:72px; top:650px;">Filled squares indicate high relevance of trend; white squares indicate lower relevance.</div>',
            ]
        ),
    )
    write("roland_berger_cop_vdma_studie_slide_014", body)


def slide_015() -> None:
    body = shell(
        15,
        "F",
        "Digitalization, populism and industry disruption create different relevance profiles",
        "\n".join(
            [
                trend_block(72, 185, "DIGITALIZATION", ["Digital interfaces across the lifecycle", "Smart factory and IIoT enable efficiency", "End-to-end data transfer", "Cybersecurity for equipment uptime"], 2),
                trend_block(72, 360, "POPULISM", ["Social media demands attention", "Transparency and awareness of fair pay", "Ethical behavior is rewarded or punished", "Political and social influence", "More frequent international crises"], 2),
                mini_relevance(720, 185, [(2, 0), (4, 1), (5, 2), (4, 3)], " "),
                mini_relevance(720, 360, [(1, 0), (3, 1), (0, 2), (2, 3), (4, 4)], " "),
            ]
        ),
    )
    write("roland_berger_cop_vdma_studie_slide_015", body)


def slide_016() -> None:
    body = shell(
        16,
        "G",
        "NGM enables companies to use production to differentiate themselves on the market",
        "\n".join(
            [
                '<div style="position:absolute; left:72px; top:190px; font-weight:800;">Percentage of survey participants who agree with the following statements</div>',
                horizontal_bars(72, 250, [("Rethink and reconfigure production", 59), ("Improve manufacturing competitiveness", 57), ("Government conditions support NGM", 32), ("Company is well positioned as pioneer", 24), ("Examples of successful NGM application", 14)], 720),
                '<div class="blue-panel" style="left:930px; top:218px; width:225px; height:230px; font-size:16px; line-height:1.18;">Companies with limited vertical integration see less opportunity, while larger companies see more opportunity to leverage this trend due to scale and stronger support.</div>',
                '<div class="callout" style="left:72px; top:520px; width:900px;">Companies can see the relevance and opportunities of NGM but are not yet positioned to apply it.</div>',
            ]
        ),
    )
    write("roland_berger_cop_vdma_studie_slide_016", body)


def panel_bars(x: int, y: int, title: str, rows: list[tuple[str, int]]) -> str:
    body = [f'<div class="blue-panel" style="left:{x}px; top:{y}px; width:480px; height:70px;"><div style="color:{GOLD}; font-size:19px; font-weight:800;">{esc(title)}</div><div style="font-size:13px; font-weight:800; margin-top:9px;">Which aspects need to be established to enable NGM? [in %]</div></div>']
    for i, (label, value) in enumerate(rows):
        yy = y + 112 + i * 28
        bw = int(280 * value / 100)
        body.append(f'<div style="position:absolute; left:{x}px; top:{yy-16}px; width:360px; font-size:12px;">{esc(label)}</div>')
        body.append(f'<div style="position:absolute; left:{x}px; top:{yy}px; width:{bw}px; height:13px; background:{GOLD};"></div>')
        body.append(f'<div style="position:absolute; left:{x+bw+8}px; top:{yy-3}px; font-size:15px; font-weight:800;">{value}%</div>')
    return "\n".join(body)


def slide_017() -> None:
    body = shell(
        17,
        "H",
        "The main demands on governments were analyzed on four different levels",
        "\n".join(
            [
                panel_bars(72, 160, "LEGAL LEVEL", [("Protection of intellectual property", 94), ("Low corruption", 80), ("De-bureaucratization", 70), ("Independent courts", 67), ("Human rights", 64), ("Freedom of the press", 36)]),
                panel_bars(660, 160, "TECHNICAL LEVEL", [("Internet bandwidth/mobile network", 91), ("Stable power grid", 81), ("Transportation infrastructure", 77), ("Communication systems", 45), ("Accepted IIoT standards", 45), ("Green energy", 43)]),
                panel_bars(72, 430, "TAX LEVEL", [("Low import/export duties", 84), ("Government-funded research", 52), ("Low income taxes", 38), ("Subsidies", 35)]),
                panel_bars(660, 430, "OTHER ASPECTS", [("Education and qualified talent", 93), ("Public safety", 85), ("Availability of properties", 43), ("Common platforms", 35), ("Incentives for shared services", 6)]),
            ]
        ),
    )
    write("roland_berger_cop_vdma_studie_slide_017", body)


def diverging_row(y: int, label: str, left1: int, left2: int, right1: int, right2: int, right3: int) -> str:
    scale = 4.2
    left_end = 520
    right_start = 750
    l1, l2 = int(left1 * scale), int(left2 * scale)
    r1, r2, r3 = int(right1 * scale), int(right2 * scale), int(right3 * scale)
    return f"""
<div style="position:absolute; left:{left_end-l1-l2}px; top:{y}px; width:{l1}px; height:18px; background:{GOLD_LIGHT};"></div>
<div style="position:absolute; left:{left_end-l2}px; top:{y}px; width:{l2}px; height:18px; background:{GOLD};"></div>
<div style="position:absolute; left:{left_end}px; top:{y-8}px; width:1px; height:34px; background:#222;"></div>
<div style="position:absolute; left:{right_start}px; top:{y-8}px; width:1px; height:34px; background:#222;"></div>
<div style="position:absolute; left:{right_start+38}px; top:{y}px; width:{r1}px; height:18px; background:{BAR};"></div>
<div style="position:absolute; left:{right_start+38+r1}px; top:{y}px; width:{r2}px; height:18px; background:{STEEL}; border-left:2px solid #fff;"></div>
<div style="position:absolute; left:{right_start+38+r1+r2}px; top:{y}px; width:{r3}px; height:18px; background:#b8c7d9; border-left:2px solid #fff;"></div>
<div style="position:absolute; left:548px; top:{y-16}px; width:170px; text-align:center; font-size:15px; line-height:1.05;">{esc(label)}</div>
<div class="value" style="left:{left_end-l1-l2-36}px; top:{y-3}px;">{left1+left2}</div>
<div class="value" style="left:{right_start+38+r1+r2+r3+8}px; top:{y-3}px;">{right1+right2+right3}</div>
"""


def slide_018() -> None:
    body = shell(
        18,
        "I",
        "How able are companies to cover their human resources needs?",
        "\n".join(
            [
                '<div style="position:absolute; left:72px; top:185px; width:980px; font-family:Georgia,serif; font-size:17px; line-height:1.28;">The majority of respondents are experiencing shortages of qualified workers overall, with IT experts and specialized engineers particularly affected.</div>',
                '<div style="position:absolute; left:72px; top:260px; color:#004477; font-weight:800;">N = 340 [in %]</div>',
                diverging_row(340, "IT EXPERTS, HIGHLY SPECIALIZED", 31, 33, 18, 10, 8),
                diverging_row(420, "ENGINEERS, HIGHLY SPECIALIZED", 24, 36, 21, 13, 6),
                diverging_row(500, "IT EXPERTS, GENERAL", 19, 41, 22, 13, 5),
                diverging_row(580, "SKILLED WORKERS", 16, 44, 22, 17, 1),
                '<div class="tiny" style="position:absolute; left:72px; top:660px;">Gold: shortage affecting business. Blue: demand and difficulty filling positions.</div>',
            ]
        ),
    )
    write("roland_berger_cop_vdma_studie_slide_018", body)


def dot_scale_row(y: int, label: str, tri: int, sq: int, circ: int, avg: int) -> str:
    x0 = 330
    scale = 7.6
    return f"""
<div style="position:absolute; left:72px; top:{y-12}px; width:210px; font-size:14px; line-height:1.1; color:#fff; text-align:right;">{esc(label)}</div>
<div style="position:absolute; left:{x0}px; top:{y}px; width:760px; border-top:2px dotted #fff;"></div>
<div style="position:absolute; left:{x0+avg*scale}px; top:{y-16}px; width:4px; height:32px; background:#fff;"></div>
<div style="position:absolute; left:{x0+tri*scale}px; top:{y-11}px; width:0; height:0; border-left:12px solid transparent; border-right:12px solid transparent; border-bottom:22px solid {BLUE};"></div>
<div style="position:absolute; left:{x0+sq*scale}px; top:{y-12}px; width:24px; height:24px; background:#ffdd17;"></div>
<div style="position:absolute; left:{x0+circ*scale}px; top:{y-13}px; width:26px; height:26px; border-radius:50%; background:#fff;"></div>
"""


def slide_019() -> None:
    body = "\n".join(
        [
            '<div style="position:absolute; left:0; top:0; width:1280px; height:720px; background:#6f8db1;"></div>',
            '<div style="position:absolute; left:72px; top:45px; width:100px; height:2px; background:#fff;"></div>',
            '<div style="position:absolute; left:186px; top:38px; color:#fff; font-size:24px; letter-spacing:10px; font-weight:800;">EXCURSUS</div>',
            '<div class="kicker" style="color:#003f6b;">Next Generation Manufacturing</div><div class="page">| 19</div>',
            '<div style="position:absolute; left:72px; top:140px; width:1020px; color:#fff; font-size:30px; line-height:1.18; font-weight:800;">Differences in how sectors are affected within the industry - Comparison of survey results for selected VDMA industry groups</div>',
            '<div style="position:absolute; left:72px; top:250px; width:500px; color:#fff; font-size:17px; line-height:1.28;">Industry groups show different preconditions. Power transmission faces strong cost pressure; robotics and automation are most affected by shortages; machine tool manufacturers appear better prepared.</div>',
            '<div style="position:absolute; left:660px; top:250px; width:480px; color:#fff; font-size:17px; line-height:1.28;">The comparison shows where selected sectors differ from the survey average across cost pressure, shortage impact, NGM opportunities and preparedness.</div>',
            '<div style="position:absolute; left:72px; top:430px; width:1000px; color:#fff; font-size:18px; font-weight:800;">Responses by VDMA industry group in comparison with survey average</div>',
            dot_scale_row(485, "Cost pressure and future trend", 64, 80, 56, 70),
            dot_scale_row(540, "Expected shortage of skilled workers", 50, 43, 77, 55),
            dot_scale_row(595, "Chances to rethink production with NGM", 47, 75, 66, 62),
            dot_scale_row(650, "Company already well prepared", 42, 18, 28, 22),
            '<div style="position:absolute; left:72px; bottom:28px; color:#fff; font-size:12px;">Triangle: machine tools; square: power transmission; circle: robotics and automation; vertical mark: survey average. Source: VDMA and Roland Berger study</div>',
        ]
    )
    write("roland_berger_cop_vdma_studie_slide_019", body)


def main() -> None:
    slide_009()
    slide_012()
    slide_014()
    slide_015()
    slide_016()
    slide_017()
    slide_018()
    slide_019()


if __name__ == "__main__":
    main()
