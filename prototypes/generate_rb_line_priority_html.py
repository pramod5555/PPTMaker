from __future__ import annotations

from pathlib import Path

from generate_rb_priority_html import RB_BLUE, RB_LILAC, RB_PANEL, RB_PURPLE, base_css, esc, panel, rail, write

ROOT = Path(__file__).parent.parent


def polyline(points, color, width=3):
    pts = " ".join(f"{x},{y}" for x, y in points)
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'


def rb_shell(slide_id, active, page, title, subtitle, chart_html, panel_items, foot):
    panel_html = panel(panel_items) if panel_items else ""
    body = "\n".join([
        rail(active, page),
        f'<div class="title">{esc(title)}</div>',
        f'<div class="subtitle">{esc(subtitle)}</div>',
        chart_html,
        panel_html,
        f'<div class="foot">{esc(foot)}</div>',
        '<div class="logo">Roland<br>Berger</div>',
    ])
    write(slide_id, body)


def line_timeline_chart():
    series = [
        ([(80,340),(160,336),(240,320),(320,300),(400,278),(480,225),(560,145),(640,65)], "#0b4f7a", 4),
        ([(80,350),(160,348),(240,342),(320,326),(400,300),(480,250),(560,180),(640,120)], "#9cb6d4", 3),
        ([(80,358),(160,357),(240,352),(320,348),(400,330),(480,292),(560,250),(640,230)], "#7f6ab0", 3),
        ([(80,362),(160,360),(240,356),(320,354),(400,345),(480,320),(560,280),(640,240)], "#111111", 3),
        ([(80,365),(160,365),(240,362),(320,360),(400,352),(480,338),(560,312),(640,288)], "#4d2d78", 3),
        ([(80,368),(160,366),(240,365),(320,363),(400,360),(480,352),(560,345),(640,335)], "#6d93b8", 3),
    ]
    paths = "\n".join(polyline(*s) for s in series)
    eras = [("Industrial Revolution",110),("Age of steam & railways",195),("Age of steel, electricity & engineering",315),("Age of oil, cars & mass production",475),("Age of ICT",585),("Industry 4.0",665)]
    era_text = "".join(f'<text x="{x}" y="72" transform="rotate(-90 {x} 72)" font-size="18" fill="{RB_PURPLE}">{esc(t)}</text>' for t, x in eras)
    return f'''
<div class="chart-bg" style="left:206px; top:200px; width:760px; height:430px;"></div>
<div style="position:absolute; left:240px; top:185px; width:730px; height:430px;">
<svg viewBox="0 0 730 430" width="730" height="430">
  <rect x="80" y="42" width="100" height="330" fill="#e4e6e9" opacity=".8"/>
  <rect x="180" y="42" width="120" height="330" fill="#d5d7da" opacity=".8"/>
  <rect x="300" y="42" width="150" height="330" fill="#e4e6e9" opacity=".8"/>
  <rect x="450" y="42" width="170" height="330" fill="#d5d7da" opacity=".8"/>
  <rect x="620" y="42" width="58" height="330" fill="#c8ccd1" opacity=".9"/>
  <line x1="80" y1="42" x2="80" y2="372" stroke="#222"/>
  <line x1="80" y1="372" x2="680" y2="372" stroke="#222"/>
  {era_text}
  {paths}
  <text x="14" y="220" transform="rotate(-90 14 220)" font-size="18" font-weight="800">GDP per capita [USD '000]</text>
  <text x="80" y="394" font-size="16">1820</text><text x="200" y="394" font-size="16">1860</text><text x="340" y="394" font-size="16">1920</text><text x="500" y="394" font-size="16">1980</text><text x="640" y="394" font-size="16">2020</text>
</svg></div>
<div class="legend" style="left:235px; top:630px; font-size:13px;">Western Europe &nbsp;&nbsp; Western Anglophonic countries &nbsp;&nbsp; Asia (East) &nbsp;&nbsp; Latin America &nbsp;&nbsp; Middle East &nbsp;&nbsp; Sub-Sahara Africa</div>
'''


def stacked_area_chart():
    return '''
<div class="chart-bg" style="left:206px; top:210px; width:760px; height:405px;"></div>
<div style="position:absolute; left:285px; top:195px; width:680px; height:410px;">
<svg viewBox="0 0 680 410" width="680" height="410">
  <line x1="70" y1="40" x2="70" y2="350" stroke="#222"/><line x1="70" y1="350" x2="650" y2="350" stroke="#222"/>
  <path d="M70 330 L150 330 L230 326 L310 322 L390 315 L470 302 L550 286 L650 270 L650 350 L70 350 Z" fill="#9fb7d0"/>
  <path d="M70 315 L150 312 L230 307 L310 300 L390 278 L470 240 L550 205 L650 160 L650 270 L550 286 L470 302 L390 315 L310 322 L230 326 L150 330 L70 330 Z" fill="#5d8ab0"/>
  <path d="M70 300 L150 296 L230 288 L310 270 L390 225 L470 175 L550 112 L650 70 L650 160 L550 205 L470 240 L390 278 L310 300 L230 307 L150 312 L70 315 Z" fill="#251346"/>
  <path d="M70 290 L150 286 L230 275 L310 255 L390 205 L470 155 L550 82 L650 30 L650 70 L550 112 L470 175 L390 225 L310 270 L230 288 L150 296 L70 300 Z" fill="#4d2d78"/>
  <path d="M70 270 L150 260 L230 252 L310 230 L390 188 L470 130 L550 62 L650 12 L650 30 L550 82 L470 155 L390 205 L310 255 L230 275 L150 286 L70 290 Z" fill="#a994cf"/>
  <text x="96" y="64" font-size="15">Electrical machinery</text><text x="96" y="88" font-size="15">Digital communication</text><text x="96" y="112" font-size="15">Computer technology</text><text x="96" y="136" font-size="15">Semiconductors</text>
  <text x="0" y="210" transform="rotate(-90 0 210)" font-size="18" font-weight="800">Number of global patents</text>
  <text x="70" y="378" font-size="16">1980</text><text x="250" y="378" font-size="16">1995</text><text x="445" y="378" font-size="16">2010</text><text x="620" y="378" font-size="16">2019</text>
  <text x="600" y="54" font-size="20" font-weight="800">600,000</text>
</svg></div>
'''


def hype_cycle(labels_left=True):
    labels = ""
    if labels_left:
        names = [("CeDeFi/CeDeX",120,286),("Decentralized Web",154,215),("Zero-Knowledge Proofs",178,170),("Stablecoins",248,70),("DeFi",318,88),("Smart Contracts",350,205),("Cryptocurrencies",508,302),("Blockchain Wallets",545,338)]
    else:
        names = [("Immersive Workspaces",145,286),("Knowledge Graphs",208,118),("Workplace Analytics",262,70),("Smart Workspace",322,95),("Employee Wellness",376,185),("Team Collaboration Devices",498,312),("Cloud Office",610,188)]
    for text, x, y in names:
        labels += f'<text x="{x}" y="{y}" font-size="12">{esc(text)}</text>'
    return f'''
<div class="chart-bg" style="left:206px; top:205px; width:760px; height:430px;"></div>
<div style="position:absolute; left:235px; top:185px; width:730px; height:430px;">
<svg viewBox="0 0 730 430" width="730" height="430">
  <line x1="55" y1="50" x2="55" y2="365" stroke="#222"/><line x1="55" y1="365" x2="690" y2="365" stroke="#222"/>
  <path d="M130 330 C175 290 190 150 245 105 C305 55 360 82 375 135 C395 205 360 270 392 305 C440 358 520 304 570 255 C610 218 650 210 690 215" fill="none" stroke="#777" stroke-width="3"/>
  <line x1="230" y1="50" x2="230" y2="365" stroke="#999" stroke-dasharray="4 4"/><line x1="320" y1="50" x2="320" y2="365" stroke="#999" stroke-dasharray="4 4"/><line x1="455" y1="50" x2="455" y2="365" stroke="#999" stroke-dasharray="4 4"/><line x1="610" y1="50" x2="610" y2="365" stroke="#999" stroke-dasharray="4 4"/>
  <g fill="{RB_PURPLE}"><circle cx="150" cy="285" r="7"/><circle cx="174" cy="212" r="7"/><circle cx="188" cy="170" r="7"/><circle cx="220" cy="135" r="7"/><circle cx="250" cy="95" r="7"/><circle cx="285" cy="82" r="7"/><circle cx="318" cy="90" r="7"/><circle cx="350" cy="205" r="7"/><circle cx="392" cy="305" r="7"/><circle cx="445" cy="318" r="7"/><circle cx="498" cy="302" r="7"/><circle cx="545" cy="278" r="7"/><circle cx="620" cy="225" r="7"/></g>
  {labels}
  <text x="26" y="220" transform="rotate(-90 26 220)" font-size="18" font-weight="800">Expectations</text><text x="380" y="410" font-size="18" font-weight="800">Time</text>
  <text x="128" y="400" font-size="13">Innovation Trigger</text><text x="225" y="400" font-size="13">Peak of Inflated Expectations</text><text x="348" y="400" font-size="13">Trough of Disillusionment</text><text x="500" y="400" font-size="13">Slope of Enlightenment</text><text x="610" y="400" font-size="13">Plateau of Productivity</text>
</svg></div>
'''


def aviation_timeline():
    return '''
<div class="chart-bg" style="left:206px; top:205px; width:980px; height:430px;"></div>
<div style="position:absolute; left:206px; top:205px; width:980px; height:430px;">
<svg viewBox="0 0 980 430" width="980" height="430">
  <text x="0" y="28" font-size="24" font-weight="800" fill="#0b4f7a">Projected development in aviation technologies</text>
  <line x1="30" y1="75" x2="930" y2="75" stroke="#5f4c9a" stroke-width="3"/><polygon points="930,65 955,75 930,85" fill="#5f4c9a"/>
  <g fill="#5f4c9a"><circle cx="60" cy="75" r="12"/><circle cx="230" cy="75" r="12"/><circle cx="405" cy="75" r="12"/><circle cx="575" cy="75" r="12"/><circle cx="755" cy="75" r="12"/></g>
  <text x="20" y="120" font-size="17" font-weight="800">Today</text><text x="195" y="120" font-size="17" font-weight="800">2020-2025</text><text x="365" y="120" font-size="17" font-weight="800">2025-2030</text><text x="535" y="120" font-size="17" font-weight="800">2030-2035</text><text x="720" y="120" font-size="17" font-weight="800">2035-2050</text>
  <text x="0" y="150" font-size="16">Electric air taxi - first<tspan x="0" dy="20">manned flights</tspan></text>
  <text x="195" y="150" font-size="16">Electric air taxi enter<tspan x="195" dy="20">service for urban mobility</tspan><tspan x="195" dy="54"># of pax: 2</tspan><tspan x="195" dy="20">Range: 150 nm</tspan></text>
  <text x="365" y="150" font-size="16">Market entry of small<tspan x="365" dy="20">hybrid-electric aircraft</tspan><tspan x="365" dy="54"># of pax: 10-15</tspan><tspan x="365" dy="20">Range: 700 nm</tspan></text>
  <text x="535" y="150" font-size="16">Regional flights based on<tspan x="535" dy="20">hybrid-driven aircraft</tspan><tspan x="535" dy="54"># of pax: 50-100</tspan><tspan x="535" dy="20">Range: 850 nm</tspan></text>
  <text x="720" y="150" font-size="16">Battery-powered aircraft<tspan x="720" dy="20">on short-haul flights</tspan><tspan x="720" dy="54"># of pax: &lt;150</tspan><tspan x="720" dy="20">Range: 290 nm</tspan></text>
  <path d="M70 300 L285 300 L315 325 L285 350 L70 350 Z" fill="#005a91"/><path d="M420 300 L640 300 L670 325 L640 350 L420 350 Z" fill="#626fa8"/><path d="M745 300 L930 300 L960 325 L930 350 L745 350 Z" fill="#8062b2"/>
  <text x="95" y="320" font-size="17" fill="#fff" font-weight="800">Electric air taxi</text><text x="95" y="343" font-size="16" fill="#fff">2020-2025 CO2 reduction: 80-100%</text>
  <text x="445" y="320" font-size="17" fill="#fff" font-weight="800">Hybrid-electric aircraft</text><text x="445" y="343" font-size="16" fill="#fff">2025-2030 CO2 reduction: 10-40%</text>
  <text x="770" y="320" font-size="17" fill="#fff" font-weight="800">Fuel cell powered aircraft</text><text x="770" y="343" font-size="16" fill="#fff">from 2035, up to 100%</text>
</svg></div>
<div style="position:absolute; left:218px; bottom:66px; width:940px; background:#d9dde2; padding:10px 14px; font-size:17px; line-height:1.15;"><b>Electrified aviation</b> is a technological breakthrough that will transform aviation, while continuous developments in fuel efficiency and new engine architectures will improve aircraft performance.</div>
'''


def roadmap_space():
    bars = [
        ("Centimeter positioning by Multi-GNSS", 102, 72, 250, "#5b3b87"),
        ("Space traffic / debris removal", 270, 38, 275, "#5b3b87"),
        ("GEO/MEO comms", 108, 116, 205, "#5b3b87"),
        ("24/7 monitoring from GEO", 282, 108, 260, "#5b3b87"),
        ("LEO mega constellation", 132, 214, 245, "#5b3b87"),
        ("LEO manned platform", 238, 176, 380, "#5b3b87"),
        ("Reusable space transportation", 296, 292, 235, "#5b3b87"),
        ("Space passenger services", 540, 280, 170, "#5b3b87"),
        ("Internet in developing countries", 104, 384, 300, "#005a91"),
        ("Entertainment using space", 360, 374, 225, "#005a91"),
        ("Space tourism", 610, 372, 120, "#005a91"),
        ("Automatic drive / delivery", 98, 426, 245, "#005a91"),
        ("Disaster emergency response", 325, 426, 220, "#005a91"),
    ]
    bar_html = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="28" fill="{c}" opacity=".96"/><text x="{x+8}" y="{y+19}" font-size="13" fill="#fff" font-weight="800">{esc(t)}</text>' for t,x,y,w,c in bars)
    return f'''
<div style="position:absolute; left:214px; top:190px; width:710px; height:395px;">
<svg viewBox="0 0 780 470" width="710" height="428">
  <line x1="58" y1="32" x2="58" y2="445" stroke="#222"/><line x1="58" y1="445" x2="745" y2="445" stroke="#222"/>
  <path d="M58 330 C220 322 360 310 500 292 C615 276 685 254 735 230 L735 292 C630 314 500 338 58 356 Z" fill="#97b1ce" opacity=".95"/>
  <path d="M58 405 C230 388 440 370 735 315 L735 372 C500 426 260 440 58 445 Z" fill="#97b1ce" opacity=".95"/>
  <path d="M58 368 L735 330 L735 350 L58 418 Z" fill="#d6cce6" opacity=".9"/>
  {bar_html}
  <text x="92" y="464" font-size="19" font-weight="800">2020</text><text x="300" y="464" font-size="19" font-weight="800">2030</text><text x="510" y="464" font-size="19" font-weight="800">2040</text><text x="700" y="464" font-size="19" font-weight="800">2050</text>
  <text x="26" y="116" transform="rotate(-90 26 116)" font-size="17" font-weight="800">GEO utilization</text><text x="26" y="248" transform="rotate(-90 26 248)" font-size="17" font-weight="800">LEO utilization</text><text x="26" y="398" transform="rotate(-90 26 398)" font-size="17" font-weight="800">On the earth</text>
</svg></div>
'''


def xr_bar():
    return f'''
<div style="position:absolute; left:206px; top:210px; width:760px; height:415px;">
  <div style="position:absolute; left:0; top:0; width:500px; height:330px; background:linear-gradient(135deg,rgba(91,45,142,.18),rgba(91,45,142,.45)); border-radius:8px;"></div>
  <div style="position:absolute; left:16px; top:16px; width:455px; font-size:20px; line-height:1.15;"><b>Extended reality (XR)</b> is used as a term for any immersive reality that could include all senses and future interactions.</div>
  <div style="position:absolute; left:26px; top:108px; width:445px; height:185px; border-radius:8px; background:rgba(66,38,112,.88); color:#fff; padding:16px; box-sizing:border-box; font-size:20px; line-height:1.18;"><b>Mixed reality (MR)</b> combines VR and AR systems, creating a hybrid environment.<br><br><span style="display:inline-block;width:190px;"><b>Augmented reality</b><br>adds virtual objects to the physical world.</span><span style="display:inline-block;width:190px;margin-left:20px;"><b>Virtual reality</b><br>creates a fully digital simulated environment.</span></div>
  <div style="position:absolute; left:560px; top:35px; width:180px; height:290px;"><div style="position:absolute; left:20px; bottom:0; width:58px; height:16px; background:{RB_BLUE};"></div><div style="position:absolute; left:112px; bottom:0; width:58px; height:255px; background:{RB_BLUE};"></div><div style="position:absolute; left:20px; bottom:22px; font-size:21px; font-weight:800;">19</div><div style="position:absolute; left:108px; bottom:260px; font-size:21px; font-weight:800;">1,006</div><div style="position:absolute; left:17px; bottom:-34px; font-size:20px;">2018</div><div style="position:absolute; left:106px; bottom:-34px; font-size:20px;">2030</div></div>
</div>
'''


def governance_dilemma():
    return f'''
<div style="position:absolute; left:206px; top:205px; width:740px; height:430px;">
<svg viewBox="0 0 740 430" width="740" height="430">
  <rect x="0" y="110" width="740" height="255" fill="#eee" opacity=".55"/>
  <line x1="230" y1="80" x2="230" y2="250" stroke="#222"/><line x1="230" y1="250" x2="600" y2="250" stroke="#222"/>
  <text x="180" y="105" font-size="18" font-weight="800">High</text><text x="182" y="240" font-size="18" font-weight="800">Low</text><text x="545" y="260" font-size="17" font-weight="800">Time after innovation</text>
  <path d="M280 238 C350 175 430 155 500 80" stroke="#0b69a3" stroke-width="4" fill="none" stroke-dasharray="12 10"/><path d="M270 90 C360 130 420 200 505 235" stroke="#9bb6d3" stroke-width="4" fill="none" stroke-dasharray="12 10"/>
  <line x1="340" y1="80" x2="340" y2="250" stroke="#222" stroke-width="3"/><line x1="430" y1="80" x2="430" y2="250" stroke="#222" stroke-width="3"/>
  <text x="292" y="56" font-size="16" fill="#8b929a">Optimal period to regulate new technology</text>
  <circle cx="130" cy="325" r="74" fill="#8062b2" opacity=".95"/><text x="84" y="291" font-size="18" fill="#fff" font-weight="800">Collingridge</text><text x="96" y="316" font-size="18" fill="#fff" font-weight="800">Dilemma:</text><text x="98" y="343" font-size="13" fill="#fff">When should</text><text x="92" y="361" font-size="13" fill="#fff">new technology</text><text x="101" y="379" font-size="13" fill="#fff">be regulated?</text>
  <path d="M176 300 C218 232 282 205 350 190" stroke="#8062b2" stroke-width="12" fill="none"/><polygon points="350,170 395,190 356,220" fill="#8062b2"/>
  <rect x="210" y="285" width="520" height="115" rx="8" fill="#b7a6d4" opacity=".82"/><text x="300" y="320" font-size="20" font-weight="800">Governance of innovation and technology</text><text x="315" y="346" font-size="18">mitigating negative impact on society</text>
  <rect x="130" y="395" width="580" height="35" rx="4" fill="#4d2d78"/><text x="185" y="419" font-size="18" fill="#fff" font-weight="800">Anticipation</text><text x="335" y="419" font-size="18" fill="#fff" font-weight="800">Inclusion</text><text x="500" y="419" font-size="18" fill="#fff" font-weight="800">Directionality</text>
</svg></div>
'''


def simple_map():
    return '''
<div style="position:absolute; left:206px; top:205px; width:760px; height:430px;">
<svg viewBox="0 0 760 430" width="760" height="430">
  <g fill="#d6d9de"><ellipse cx="150" cy="150" rx="110" ry="70"/><ellipse cx="385" cy="130" rx="150" ry="70"/><ellipse cx="560" cy="165" rx="150" ry="80"/><ellipse cx="255" cy="285" rx="85" ry="115"/><ellipse cx="455" cy="290" rx="100" ry="120"/><ellipse cx="650" cy="320" rx="72" ry="55"/></g>
  <g fill="none" stroke-width="2"><path d="M80 160 C135 120 180 155 220 140 C245 160 260 175 285 165" stroke="#4d2d78"/><path d="M335 145 C390 105 438 150 500 125 C548 145 600 142 650 170" stroke="#00669c"/><path d="M390 170 C420 230 438 280 470 335" stroke="#a994cf"/><path d="M545 185 C585 225 615 245 650 260" stroke="#7aa0c8"/><path d="M160 248 C190 310 230 352 275 365" stroke="#9bb6d3"/></g>
  <g fill="#fff" stroke="#4d2d78"><circle cx="90" cy="160" r="4"/><circle cx="150" cy="145" r="4"/><circle cx="225" cy="142" r="4"/></g>
  <g fill="#fff" stroke="#00669c"><circle cx="350" cy="145" r="4"/><circle cx="415" cy="128" r="4"/><circle cx="500" cy="128" r="4"/><circle cx="620" cy="162" r="4"/></g>
  <g fill="#fff" stroke="#9bb6d3"><circle cx="180" cy="255" r="4"/><circle cx="230" cy="330" r="4"/><circle cx="275" cy="365" r="4"/></g>
  <text x="70" y="132" font-size="13">Los Angeles</text><text x="180" y="132" font-size="13">New York</text><text x="355" y="118" font-size="13">London</text><text x="425" y="112" font-size="13">Berlin</text><text x="580" y="152" font-size="13">Beijing</text><text x="620" y="184" font-size="13">Shanghai</text><text x="250" y="378" font-size="13">Buenos Aires</text>
</svg></div>
'''


def main():
    rb_shell(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_021",
        1, 21,
        "Technology has been changing our world for centuries - Prosperity first arose in places of technological inventions and innovations",
        "Development of technological breakthroughs and GDP per capita [USD]",
        line_timeline_chart(),
        [
            "The global economy has been transformed since the Industrial Revolution.",
            "Breakthroughs brought new and previously unknown prosperity.",
            "Western European and Anglophonic countries show exponential growth paths.",
            "Prosperity and technological breakthrough regions correspond.",
        ],
        "Sources: UNCTAD; University of Groningen/Maddison Project Database; Roland Berger",
    )
    rb_shell(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_022",
        1, 22,
        "Patents in selected industries foretell the next technology wave - Current trends depict an explosion of patents related to digitalization",
        "Global patents in selected industries, 1980-2019",
        stacked_area_chart(),
        [
            "Breakthrough technologies related to Industry 4.0 and digitalization exploded since the mid-1990s.",
            "Patents closely related to Industry 4.0 have seen a tenfold increase.",
            "Digitalization has initiated a patent push in medical and environmental technology and transport.",
            "Older breakthrough technologies are reaching a plateau of innovation.",
        ],
        "Sources: WIPO; NBER; Roland Berger",
    )
    rb_shell(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_033",
        2, 33,
        "Most blockchain applications will fully penetrate the market in well under a decade - Decentralization will make trade more efficient",
        "The Gartner Hype Cycle for blockchain applications, 2021",
        hype_cycle(True),
        [
            "The Hype Cycle assigns key stages to the life cycle of blockchain applications.",
            "Blockchain penetration makes activities more decentralized and trading more efficient.",
            "Decentralized finance is an example of peer-to-peer services built on Ethereum.",
            "CeDeFi combines centralized finance with decentralized finance.",
        ],
        "Sources: Gartner; Etherium; 101blockchain; Roland Berger",
    )
    rb_shell(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_043",
        2, 43,
        "Electric vehicles are common today, but the aviation sector faces major challenges in decarbonization and electrification",
        "Timeline of electric/electrified aviation",
        aviation_timeline(),
        [],
        "Sources: IATA; Roland Berger",
    )
    rb_shell(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_044",
        2, 44,
        "Getting from A to B like never before: Visionaries in the hyperloop sector project a worldwide hyperloop network in 2050",
        "A futuristic global hyperloop network transporting travelers and freight",
        simple_map(),
        [
            "Hyperloop is an ultra-high-speed ground transportation system using sealed, low-pressure pods.",
            "An 88,500 km network could move passengers and freight across regions.",
            "This could create large revenue opportunities and reduce emissions if powered by renewable energy.",
        ],
        "Sources: Zeleros; Interesting Engineering; Roland Berger",
    )
    rb_shell(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_046",
        2, 46,
        "Human activities utilizing space assets will see continuous growth to 2050 - Space activities depend on orbital distances to Earth and commercial appeal",
        "Projected evolution of space activities up to geostationary orbit",
        roadmap_space(),
        [
            "Different current activities and planned endeavors depend on altitude and distance from Earth.",
            "Transportation, robotics and spacecraft architecture are essential for future exploration.",
            "Commercial and scientific utilization will include manufacturing, recycling and assembly in space.",
        ],
        "Sources: Satellite Today; JSASS; Roland Berger",
    )
    rb_shell(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_050",
        2, 50,
        "Our immersive future: The concept of extended reality merges physical and digital worlds ...",
        "The many realities that extend, mix and augment our future lives",
        xr_bar(),
        [
            "Extended reality has the potential to affect large parts of the economy.",
            "Virtual products can disrupt retail and advertising personalization.",
            "Education and training become important XR use cases.",
            "Progress depends on AI, devices, cloud systems and 5G.",
        ],
        "Sources: Bloomberg; Prescient & Strategic Intelligence; Ionos; Huawei; Roland Berger",
    )
    rb_shell(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_056",
        3, 56,
        "Workplaces have experienced a push to digitalization due to the pandemic - Other innovations are yet to impact our working life",
        "Gartner Hype Cycle for the Digital Workplace in 2020",
        hype_cycle(False),
        [
            "Workplace digitalization experienced an extraordinary push during the pandemic.",
            "Many digital workplace technologies remain in inflated expectations.",
            "Several surviving innovations should enhance productivity in the near to midterm.",
            "Cloud technologies and enterprise social networking have moved toward maturity.",
        ],
        "Sources: Gartner; Roland Berger",
    )
    rb_shell(
        "roland_berger_trend_compendium_2050_technology_and_innovation_slide_061",
        3, 61,
        "Future implications of technological advances regarding humanity are not entirely foreseeable - Regulators face a double-bind dilemma",
        "Innovation governance suffers from the Collingridge Dilemma",
        governance_dilemma(),
        [
            "Regulators face a double-bind quandary: information is weak early, control is hard later.",
            "New technologies carry ethical, economic, environmental and health-related implications.",
            "Early restrictions may hinder deployment, while late corrections can be costly.",
            "Governance requires anticipation, inclusion and directionality.",
        ],
        "Sources: OECD; Roland Berger",
    )


if __name__ == "__main__":
    main()
