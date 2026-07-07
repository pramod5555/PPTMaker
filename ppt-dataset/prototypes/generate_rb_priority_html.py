from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "html_slides"
OUT.mkdir(exist_ok=True)

W, H = 1280, 720
RB_DARK = "#30343a"
RB_PURPLE = "#5a3a8e"
RB_LILAC = "#a994cf"
RB_BLUE = "#0b4f7a"
RB_PANEL = "#d9dde2"


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def base_css() -> str:
    return f"""
html, body {{ margin: 0; width: {W}px; height: {H}px; background: #fff; font-family: Calibri, Arial, sans-serif; }}
.slide {{ width: {W}px; height: {H}px; position: relative; overflow: hidden; background: #fff; color: #222; }}
.rail {{ position: absolute; left: 0; top: 0; width: 170px; height: 720px; background: {RB_DARK}; color: #fff; }}
.rail:after {{ content: ""; position: absolute; right: 0; top: 0; width: 3px; height: 720px; background: {RB_PURPLE}; }}
.rail-title {{ position: absolute; left: 12px; top: 34px; width: 135px; font-size: 25px; line-height: 1.12; font-weight: 800; }}
.hex {{ position: absolute; left: 21px; width: 70px; height: 62px; clip-path: polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%); border: 0; background: #747a82; }}
.hex.active {{ background: linear-gradient(135deg,#12a5c8,#314f7a); box-shadow: 0 0 0 5px {RB_LILAC}; }}
.n {{ position: absolute; left: 108px; width: 45px; font-size: 34px; line-height: 1; font-weight: 800; color: #858a91; }}
.n.active {{ color: {RB_LILAC}; }}
.rail-label {{ position: absolute; left: 108px; width: 58px; font-size: 15px; line-height: 1.05; font-weight: 700; color: #858a91; }}
.rail-label.active {{ color: {RB_LILAC}; }}
.gear {{ position: absolute; left: 60px; bottom: 35px; width: 66px; height: 66px; border-radius: 50%; border: 10px solid rgba(180,184,190,.35); opacity: .65; }}
.gear:before {{ content: ""; position: absolute; left: 18px; top: 18px; width: 22px; height: 22px; border-radius: 50%; background: rgba(180,184,190,.35); }}
.page {{ position: absolute; left: 10px; bottom: 8px; font-size: 13px; color: #fff; }}
.title {{ position: absolute; left: 206px; top: 28px; width: 990px; font-size: 32px; line-height: 1.08; font-weight: 800; letter-spacing: 0; }}
.subtitle {{ position: absolute; left: 206px; top: 136px; width: 790px; font-size: 24px; line-height: 1.16; color: #8b929a; font-weight: 300; }}
.chart-bg {{ position: absolute; background: radial-gradient(circle at 70% 25%, rgba(140,140,140,.2), transparent 12%), radial-gradient(circle at 40% 65%, rgba(140,140,140,.18), transparent 14%), linear-gradient(135deg, rgba(255,255,255,.9), rgba(230,232,235,.65)); }}
.panel {{ position: absolute; right: 0; top: 176px; width: 330px; height: 500px; background: {RB_PANEL}; box-sizing: border-box; padding: 16px 22px; font-size: 18px; line-height: 1.2; }}
.bullet {{ position: relative; margin: 0 0 14px 0; padding-left: 18px; }}
.bullet:before {{ content: ">"; position: absolute; left: 0; top: 0; }}
.foot {{ position: absolute; left: 206px; bottom: 20px; width: 740px; font-size: 12px; line-height: 1.25; }}
.logo {{ position: absolute; right: 34px; bottom: 22px; width: 82px; height: 22px; font-size: 10px; text-align: right; color: #333; }}
.logo:after {{ content: "B"; display: inline-block; margin-left: 6px; font-size: 28px; font-weight: 800; color: #98a0a8; vertical-align: middle; }}
.axis-label {{ position: absolute; font-size: 19px; font-weight: 800; color: #222; }}
.legend {{ position: absolute; font-size: 17px; color: #222; }}
.small-title {{ position: absolute; font-size: 19px; font-weight: 800; line-height: 1.12; }}
.note {{ font-size: 12px; }}
"""


def rail(active: int, page: int) -> str:
    rows = [(1, "Value of Innovation", 132), (2, "Frontier Technologies", 260), (3, "Humans & Machines", 386)]
    bits = [
        '<div class="rail">',
        '<div class="rail-title">Technology &amp;<br>Innovation</div>',
    ]
    for num, label, y in rows:
        active_cls = " active" if num == active else ""
        bits.append(f'<div class="hex{active_cls}" style="top:{y}px;"></div>')
        bits.append(f'<div class="n{active_cls}" style="top:{y+6}px;">{num}</div>')
        bits.append(f'<div class="rail-label{active_cls}" style="top:{y+45}px;">{esc(label)}</div>')
    bits.append('<div class="gear"></div>')
    bits.append(f'<div class="page">{page}</div>')
    bits.append("</div>")
    return "\n".join(bits)


def svg_scatter(points, labels, x0, x1, y0, y1, trend=True, arrows=False) -> str:
    width, height = 610, 390
    left, top = 75, 38
    plot_w, plot_h = 510, 300

    def px(x):
        return left + (x - x0) / (x1 - x0) * plot_w

    def py(y):
        return top + plot_h - (y - y0) / (y1 - y0) * plot_h

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#111" stroke-width="1.2"/>',
        f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#111" stroke-width="1.2"/>',
    ]
    for i in range(6):
        x = left + i * plot_w / 5
        parts.append(f'<line x1="{x:.1f}" y1="{top+plot_h}" x2="{x:.1f}" y2="{top+plot_h+7}" stroke="#111"/>')
    for i in range(6):
        y = top + i * plot_h / 5
        parts.append(f'<line x1="{left-7}" y1="{y:.1f}" x2="{left}" y2="{y:.1f}" stroke="#111"/>')
    if trend:
        parts.append(f'<line x1="{left+35}" y1="{top+plot_h-42}" x2="{left+plot_w-35}" y2="{top+52}" stroke="#111" stroke-width="1.2"/>')
    if arrows:
        parts.append('<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#4a2d78"/></marker></defs>')
    for x, y, kind in points:
        cx, cy = px(x), py(y)
        if kind == "tri":
            parts.append(f'<polygon points="{cx:.1f},{cy-8:.1f} {cx-8:.1f},{cy+7:.1f} {cx+8:.1f},{cy+7:.1f}" fill="{RB_BLUE}"/>')
        elif kind == "dia":
            parts.append(f'<rect x="{cx-7:.1f}" y="{cy-7:.1f}" width="14" height="14" transform="rotate(45 {cx:.1f} {cy:.1f})" fill="{RB_PURPLE}"/>')
        else:
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6.5" fill="{RB_LILAC}"/>')
    for text, x, y in labels:
        parts.append(f'<text x="{px(x)+8:.1f}" y="{py(y)+5:.1f}" font-family="Calibri,Arial,sans-serif" font-size="16" fill="#222">{esc(text)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def panel(bullets: list[str]) -> str:
    return '<div class="panel">' + "".join(f'<div class="bullet">{b}</div>' for b in bullets) + "</div>"


def write(slide_id: str, body: str) -> None:
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{slide_id}</title>
  <style>{base_css()}</style>
</head>
<body>
  <div class="slide">
{body}
  </div>
</body>
</html>
"""
    (OUT / f"{slide_id}.html").write_text(html, encoding="utf-8")


def rb_scatter(slide_id, page, title, subtitle, xlab, ylab, panel_items, points, labels, x0, x1, y0, y1, active=1):
    body = "\n".join([
        rail(active, page),
        f'<div class="title">{esc(title)}</div>',
        f'<div class="subtitle">{esc(subtitle)}</div>',
        '<div class="chart-bg" style="left:206px; top:205px; width:690px; height:430px;"></div>',
        f'<div style="position:absolute; left:230px; top:205px; width:650px; height:410px;">{svg_scatter(points, labels, x0, x1, y0, y1)}</div>',
        f'<div class="axis-label" style="left:475px; top:628px;">{esc(xlab)}</div>',
        f'<div class="axis-label" style="left:210px; top:360px; transform:rotate(-90deg); transform-origin:left top;">{esc(ylab)}</div>',
        '<div class="legend" style="left:300px; top:212px;">Emerging markets &amp; developing economies<br><span style="color:#3e286a;">▲</span> Advanced countries</div>',
        panel(panel_items),
        '<div class="foot">Sources: WIPO; World Bank; OECD; UN; Roland Berger</div>',
        '<div class="logo">Roland<br>Berger</div>',
    ])
    write(slide_id, body)


def main() -> None:
    rb_scatter(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_008",
        8,
        "Winning at innovation starts in the classroom - Becoming a future leader in innovation requires investment in education ...",
        "Global Innovation Index 2021 plotted against average PISA outcome 2018 (China = 100)",
        "PISA outcome",
        "Global Innovation Index",
        [
            "Innovation has several driving factors; an important one is its <b>educational base</b>.",
            "High quality human capital is required to think beyond the limits of existing technologies.",
            "Countries with better educational systems experience better abilities to innovate.",
            "Higher PISA outcomes are associated with a higher Global Innovation Index.",
        ],
        [(22,32,"circ"),(25,30,"circ"),(31,37,"circ"),(36,42,"circ"),(42,47,"circ"),(58,49,"tri"),(66,55,"tri"),(68,63,"tri"),(72,60,"tri"),(77,59,"tri"),(91,58,"tri"),(99,55,"circ"),(20,29,"circ"),(37,35,"circ"),(64,51,"tri"),(70,52,"tri"),(62,46,"tri"),(75,53,"tri")],
        [("Philippines",22,35),("Brazil",38,36),("US",66,61),("UK",72,60),("Switzerland",68,65),("South Korea",77,59),("China",91,55),("Indonesia",26,28)],
        0,100,25,70,
    )
    rb_scatter(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_009",
        9,
        "... as well as investment in R&D - A quintessential factor for best-in-class innovation, expenditure levels signal trust in future promise",
        "Global Innovation Index 2021 plotted against Gross Expenditure in R&D (GERD) 2019",
        "GERD as a percentage of GDP",
        "Global Innovation Index",
        [
            "Devoting capital to <b>R&amp;D</b> is essential for becoming more innovative.",
            "Innovation processes are resource consuming and subject to uncertainty.",
            "R&amp;D investment and innovation are positively correlated.",
            "Investment decisions signal expectations regarding innovation returns.",
        ],
        [(0.3,36,"circ"),(0.6,34,"circ"),(1.0,42,"circ"),(1.4,46,"tri"),(1.8,50,"tri"),(2.1,52,"tri"),(2.8,60,"tri"),(3.1,58,"tri"),(3.3,64,"tri"),(4.2,56,"tri"),(4.7,58,"tri"),(2.1,55,"circ"),(1.7,61,"tri"),(3.2,55,"tri"),(2.7,50,"tri"),(1.2,38,"circ"),(2.9,62,"tri"),(1.9,42,"tri")],
        [("Russia",0.3,35),("Chile",0.25,38),("Lithuania",1.0,42),("Norway",2.1,52),("China",2.0,55),("UK",1.7,61),("US",2.9,62),("Germany",3.1,58),("Japan",3.2,55),("South Korea",4.2,56)],
        0,5,30,70,
    )
    rb_scatter(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_011",
        11,
        "Technological innovation and prosperity are highly interconnected - Lack of either factor is mutually disadvantageous",
        "Global Innovation Index related to GDP per capita PPP, 2019 [USD]",
        "Global Innovation Index",
        "GDP per capita PPP [USD '000]",
        [
            "A nation's ability to innovate is an essential engine of productivity, growth and prosperity.",
            "The higher countries score on innovation, the higher their GDP per capita.",
            "China is an exception, having built innovation strength while GDP per capita remains lower.",
            "Developing countries lack skills, investments and institutions to close the gap.",
        ],
        [(31,15,"circ"),(33,12,"circ"),(36,18,"circ"),(38,14,"circ"),(42,32,"tri"),(46,45,"tri"),(48,41,"tri"),(50,55,"tri"),(52,68,"tri"),(55,50,"tri"),(58,87,"tri"),(60,103,"tri"),(61,60,"tri"),(66,70,"tri"),(56,17,"circ"),(45,94,"circ"),(33,65,"circ"),(42,70,"circ")],
        [("India",31,10),("Brazil",36,12),("China",56,17),("Singapore",58,87),("Luxembourg",60,120),("Switzerland",52,68),("US",55,62)],
        15,70,0,130,
    )

    # Slide 016: country trajectories.
    body16 = "\n".join([
        rail(1, 16),
        '<div class="title">For emerging countries, boosting innovation enables per capita GDP growth to become intrinsic and sustainable</div>',
        '<div class="subtitle">Global Innovation Index plotted against GDP per capita, 2011 and 2019 [index, USD]</div>',
        '<div class="chart-bg" style="left:206px; top:235px; width:600px; height:370px;"></div>',
        '<div style="position:absolute; left:245px; top:240px; width:560px; height:350px;"><svg viewBox="0 0 560 350" width="560" height="350"><defs><marker id="a" markerWidth="10" markerHeight="10" refX="9" refY="4" orient="auto"><path d="M0,0 L9,4 L0,8 Z" fill="#4a2d78"/></marker></defs><line x1="60" y1="36" x2="60" y2="305" stroke="#222"/><line x1="60" y1="305" x2="540" y2="305" stroke="#222"/><text x="0" y="20" font-size="19" font-weight="800">GDP per capita PPP [USD]</text><path d="M70 260 C110 220 140 200 165 200" stroke="#4a2d78" stroke-width="5" fill="none" marker-end="url(#a)"/><path d="M150 256 C180 230 210 246 240 246" stroke="#4a2d78" stroke-width="5" fill="none" marker-end="url(#a)"/><path d="M170 292 C190 264 205 266 220 246" stroke="#4a2d78" stroke-width="5" fill="none" marker-end="url(#a)"/><path d="M260 210 C305 155 350 125 390 110" stroke="#4a2d78" stroke-width="5" fill="none" marker-end="url(#a)"/><path d="M315 205 C390 205 435 170 470 108" stroke="#4a2d78" stroke-width="5" fill="none" marker-end="url(#a)"/><path d="M420 275 C480 270 520 240 535 205" stroke="#4a2d78" stroke-width="5" fill="none" marker-end="url(#a)"/><g fill="#4a2d78"><circle cx="70" cy="260" r="7"/><polygon points="165,195 157,211 173,211"/><circle cx="150" cy="256" r="7"/><polygon points="240,238 232,254 248,254"/><circle cx="170" cy="292" r="7"/><polygon points="220,238 212,254 228,254"/><circle cx="315" cy="205" r="7"/><polygon points="390,100 380,118 400,118"/><polygon points="470,98 460,116 480,116"/><circle cx="420" cy="275" r="7"/><polygon points="535,194 525,212 545,212"/></g><text x="80" y="300" font-size="17">Brazil</text><text x="198" y="282" font-size="17">India</text><text x="170" y="205" font-size="17">Mexico</text><text x="370" y="90" font-size="17">Turkey</text><text x="485" y="105" font-size="17">Russia</text><text x="500" y="185" font-size="17">China</text></svg></div>',
        panel([
            "Economic growth can be sustained by multiple factors, but finite resources limit long-term growth.",
            "Sustainable growth is achieved through technological progress and innovation.",
            "Emerging countries moved up along the prosperity-innovation scale as GII increased.",
            "Brazil appears as an exception, with less GII improvement and near-static GDP per capita.",
        ]),
        '<div class="axis-label" style="left:570px; top:626px;">Global Innovation Index</div>',
        '<div class="foot">Sources: WIPO; The World Bank; UN; Roland Berger</div>',
        '<div class="logo">Roland<br>Berger</div>',
    ])
    write("roland_berger_trend_compendium_2050_technology_and_innovation_slide_016", body16)

    # Slide 020: two scatter panels.
    body20 = "\n".join([
        rail(1, 20),
        '<div class="title">Historically, rates of adoption of innovations have been facilitated by globalization - Network effects strongly influence pace of adoption</div>',
        '<div class="subtitle">Globalization and network effects foster technology diffusion</div>',
        '<div class="chart-bg" style="left:206px; top:205px; width:690px; height:430px;"></div>',
        '<div class="small-title" style="left:206px; top:182px;">Trade Openness Index related to years until<br>adoption rate of 25% of US pop. [index, years]</div>',
        '<div class="small-title" style="left:578px; top:182px;">GII related to Internet adoption rate for<br>selected countries [index, %]</div>',
        f'<div style="position:absolute; left:205px; top:292px; width:340px; height:250px;">{svg_scatter([(8,21,"circ"),(12,16,"circ"),(16,13,"circ"),(20,6,"circ"),(26,4,"circ"),(30,2,"circ")],[("Microcomputer",8,21),("PC",12,16),("Mobile phone",16,13),("World Wide Web",18,8),("Facebook",26,4),("Tablets",30,2)],0,32,0,22,True)}</div>',
        f'<div style="position:absolute; left:575px; top:292px; width:340px; height:250px;">{svg_scatter([(28,54,"circ"),(30,72,"circ"),(34,80,"circ"),(38,85,"circ"),(42,90,"circ"),(45,78,"circ"),(48,87,"circ"),(50,92,"circ"),(56,70,"circ"),(58,96,"circ"),(60,94,"circ"),(62,95,"circ")],[("Indonesia",28,54),("Turkey",34,78),("Russia",34,85),("Germany",50,88),("China",56,70),("South Korea",58,98),("UK",60,96)],25,65,50,100,True)}</div>',
        panel([
            "Adoption of innovations is linked to networks and societal interaction.",
            "Globalization is one of the main drivers of faster technology adoption.",
            "Slowbalization may reduce the dynamics of technology adoption.",
            "Network effects accelerate diffusion to other technologies and markets.",
        ]),
        '<div class="foot">Sources: Pew Research; OurWorldInData; World Bank; ITU; WIPO; Roland Berger</div>',
        '<div class="logo">Roland<br>Berger</div>',
    ])
    write("roland_berger_trend_compendium_2050_technology_and_innovation_slide_020", body20)

    # Slide 053: risk landscape with paired cohorts and arrows.
    body53 = "\n".join([
        rail(3, 53),
        '<div class="title">The relationship of humans with machines is fraught with technological risk - Risk perception regarding innovations in the younger generation are higher</div>',
        '<div class="subtitle">Global risks landscape for technological risks</div>',
        '<div class="chart-bg" style="left:206px; top:215px; width:690px; height:405px;"></div>',
        '<div style="position:absolute; left:230px; top:218px; width:670px; height:390px;"><svg viewBox="0 0 670 390" width="670" height="390"><defs><marker id="ra" markerWidth="10" markerHeight="10" refX="9" refY="4" orient="auto"><path d="M0,0 L9,4 L0,8 Z" fill="#6f55a4"/></marker></defs><line x1="70" y1="45" x2="70" y2="315" stroke="#222"/><line x1="70" y1="315" x2="625" y2="315" stroke="#222"/><text x="0" y="18" font-size="18" font-weight="800">Impact</text><text x="575" y="355" font-size="18" font-weight="800">Likelihood</text><path d="M145 255 C195 180 270 160 330 130" stroke="#6f55a4" stroke-width="6" fill="none" marker-end="url(#ra)"/><path d="M385 268 C430 180 485 145 510 116" stroke="#6f55a4" stroke-width="6" fill="none" marker-end="url(#ra)"/><path d="M545 258 C570 180 600 150 612 125" stroke="#6f55a4" stroke-width="6" fill="none" marker-end="url(#ra)"/><path d="M545 190 C565 120 590 86 610 70" stroke="#6f55a4" stroke-width="6" fill="none" marker-end="url(#ra)"/><g fill="#6f55a4"><circle cx="110" cy="115" r="11"/><rect x="132" y="86" width="14" height="14" transform="rotate(45 139 93)"/><circle cx="330" cy="135" r="11"/><rect x="280" y="250" width="14" height="14" transform="rotate(45 287 257)"/><circle cx="450" cy="95" r="11"/><rect x="430" y="105" width="14" height="14" transform="rotate(45 437 112)"/><circle cx="485" cy="115" r="11"/><rect x="535" y="185" width="14" height="14" transform="rotate(45 542 192)"/><circle cx="610" cy="125" r="11"/><rect x="535" y="260" width="14" height="14" transform="rotate(45 542 267)"/><circle cx="610" cy="60" r="11"/></g><text x="100" y="150" font-size="15">IT infrastructure</text><text x="283" y="112" font-size="15">Adverse tech</text><text x="410" y="72" font-size="15">Cyber security</text><text x="475" y="150" font-size="15">Tech governance</text><text x="548" y="108" font-size="14">Digital inequality</text><text x="407" y="52" font-size="15">Digital power concentration</text></svg></div>',
        panel([
            "The global risks landscape reflects perceived likelihood and impact of technological risks.",
            "Younger generations perceive such risks to occur more likely and with higher impact.",
            "Differences are notable for adverse tech advances, tech governance failure and digital inequality.",
            "Breakdown of critical infrastructure and cybersecurity failure are exceptions.",
        ]),
        '<div class="foot">Sources: WEF; Roland Berger</div>',
        '<div class="logo">Roland<br>Berger</div>',
    ])
    write("roland_berger_trend_compendium_2050_technology_and_innovation_slide_053", body53)


if __name__ == "__main__":
    main()
