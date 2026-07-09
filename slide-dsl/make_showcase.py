"""
make_showcase.py — Generate a Daimler Truck capability showcase deck.

Covers every block type, every layout, and all four slide types.
Run: python3 slide-dsl/make_showcase.py
"""
from __future__ import annotations
import sys, textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from renderer import render_slide

SLIDES = [

    # ── 1. COVER ────────────────────────────────────────────────────────────────
    {
        "slide_type": "cover",
        "header": {
            "kicker": "Daimler Truck AG",
            "headline": "PPTMaker: AI-Generated Consulting Decks at Scale",
            "sub": "Capability Showcase · All Chart Types · All Layouts",
        },
        "footer": {"page": 1},
    },

    # ── 2. CHAPTER — Financial Performance ──────────────────────────────────────
    {
        "slide_type": "chapter",
        "header": {
            "kicker": "Section 01",
            "headline": "Financial\nPerformance",
        },
        "footer": {"source": "Daimler Truck AG Annual Report 2024", "page": 2},
    },

    # ── 3. CONTENT — Line chart (full layout) ───────────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "REVENUE TREND",
            "headline": "Group revenue reached €55.9B in FY2024, up 3% vs. prior year",
            "sub": "Revenue in €B by segment, 2019–2024 · Source: Daimler Truck Annual Report",
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "line-chart",
                "title": "Group Revenue by Segment (€B)",
                "labels": ["2019", "2020", "2021", "2022", "2023", "2024"],
                "series": [
                    {"name": "Trucks NA",    "values": [17.2, 14.8, 16.4, 21.3, 23.1, 24.7]},
                    {"name": "Trucks EU",    "values": [12.4, 10.9, 11.8, 14.2, 15.6, 16.1]},
                    {"name": "Trucks Asia",  "values": [5.8,  5.1,  5.6,  7.1,  8.3,  8.9]},
                    {"name": "Buses",        "values": [3.9,  2.8,  3.2,  4.1,  4.8,  5.2]},
                    {"name": "Financial Svc","values": [0.9,  0.8,  0.9,  1.0,  1.0,  1.0]},
                ],
                "fmt": "auto",
                "show_points": True,
                "area": False,
            }
        },
        "footer": {"source": "Daimler Truck AG Annual Report 2024", "page": 3},
    },

    # ── 4. CONTENT — Vertical bar + KPI grid (two-column) ───────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "FY2024 RESULTS",
            "headline": "North America leads growth; group EBIT margin held at 9.1% despite headwinds",
            "sub": "FY2024 vs. FY2023 comparison across key financial metrics",
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "bar-chart",
                "orientation": "vertical",
                "title": "Revenue by Region (€B)",
                "labels": ["North America", "Europe", "Asia-Pac", "Lat Am", "Other"],
                "series": [
                    {"name": "FY2024", "values": [24.7, 16.1, 8.9, 4.1, 2.1]},
                    {"name": "FY2023", "values": [23.1, 15.6, 8.3, 3.8, 2.0]},
                ],
                "stacked": False,
                "show_values": True,
            },
            "right": {
                "type": "kpi-grid",
                "style": "accent",
                "columns": 2,
                "items": [
                    {"stat": "€55.9B",  "label": "Group Revenue",    "delta": "+3.1%",  "positive": True},
                    {"stat": "9.1%",    "label": "EBIT Margin",      "delta": "-0.2pp", "positive": False},
                    {"stat": "488k",    "label": "Units Sold",        "delta": "+1.8%",  "positive": True},
                    {"stat": "€3.6B",   "label": "Net Profit",        "delta": "+4.2%",  "positive": True},
                    {"stat": "€5.1B",   "label": "Free Cash Flow",    "delta": "+€0.3B", "positive": True},
                    {"stat": "103,000", "label": "Employees",         "delta": "+1.1%",  "positive": True},
                ],
            },
        },
        "footer": {"source": "Daimler Truck AG Annual Report 2024", "page": 4},
    },

    # ── 5. CONTENT — Donut + Table (two-column) ─────────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "PORTFOLIO MIX",
            "headline": "North America represents 44% of group revenue; Europe and Asia deliver balanced exposure",
            "sub": "Revenue share by geography and key market metrics, FY2024",
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "donut-chart",
                "center_text": "6",
                "center_label": "Regions",
                "show_legend": True,
                "segments": [
                    {"label": "North America", "value": 44},
                    {"label": "Europe",        "value": 29},
                    {"label": "Asia-Pacific",  "value": 16},
                    {"label": "Latin America", "value": 7},
                    {"label": "Middle East",   "value": 2},
                    {"label": "Africa",        "value": 2},
                ],
            },
            "right": {
                "type": "table",
                "headers": ["Region", "Revenue", "YoY", "Units", "Margin"],
                "rows": [
                    ["North America", "€24.7B", "+7%",  "224k", "11.2%"],
                    ["Europe",        "€16.1B", "+3%",  "138k",  "8.4%"],
                    ["Asia-Pacific",  "€8.9B",  "+7%",   "84k",  "7.8%"],
                    ["Latin America", "€4.1B",  "+8%",   "31k",  "6.2%"],
                    ["Middle East",   "€1.1B",  "+5%",    "6k",  "5.9%"],
                    ["Africa",        "€1.0B",  "+2%",    "5k",  "5.1%"],
                ],
                "highlight_col": 2,
            },
        },
        "footer": {"source": "Daimler Truck AG Annual Report 2024", "page": 5},
    },

    # ── 6. CHAPTER — Market Position ────────────────────────────────────────────
    {
        "slide_type": "chapter",
        "header": {
            "kicker": "Section 02",
            "headline": "Market Position\n& Competitive Landscape",
        },
        "footer": {"source": "Daimler Truck AG Investor Day 2024", "page": 6},
    },

    # ── 7. CONTENT — Waterfall chart (full layout) ──────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "EBIT BRIDGE",
            "headline": "Volume growth and pricing offset cost inflation to deliver €5.1B EBIT in FY2024",
            "sub": "EBIT walk FY2023 → FY2024 (€B) · Source: Daimler Truck AG Annual Report 2024",
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "waterfall-chart",
                "title": "EBIT Bridge FY2023 → FY2024 (€B)",
                "fmt": "auto",
                "bars": [
                    {"label": "FY2023 EBIT",       "value": 4.7,  "type": "start"},
                    {"label": "Volume / Mix",        "value": 0.9,  "type": "positive"},
                    {"label": "Pricing",             "value": 0.6,  "type": "positive"},
                    {"label": "Raw Material Costs",  "value": -0.4, "type": "negative"},
                    {"label": "Labour Inflation",    "value": -0.3, "type": "negative"},
                    {"label": "R&D Investment",      "value": -0.2, "type": "negative"},
                    {"label": "FX Effects",          "value": -0.1, "type": "negative"},
                    {"label": "Other",               "value": -0.1, "type": "negative"},
                    {"label": "FY2024 EBIT",         "value": 5.1,  "type": "total"},
                ],
            }
        },
        "footer": {"source": "Daimler Truck AG Annual Report 2024", "page": 7},
    },

    # ── 8. CONTENT — Scatter + Bullet list (two-column) ─────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "COMPETITIVE POSITION",
            "headline": "Daimler Truck leads peers on margin-to-scale; key differentiators are services and electrification",
            "sub": "Peer comparison: EBIT margin vs. revenue scale, FY2024",
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "scatter-chart",
                "title": "EBIT Margin vs. Revenue Scale (FY2024)",
                "x_label": "Revenue (€B)",
                "y_label": "EBIT Margin (%)",
                "x_range": [0, 70],
                "y_range": [0, 14],
                "quadrant_labels": ["Niche", "Premium", "Scale", "Leader"],
                "points": [
                    {"label": "Daimler Truck", "x": 55.9, "y": 9.1, "size": 10},
                    {"label": "Volvo Group",   "x": 47.5, "y": 8.6, "size": 9},
                    {"label": "PACCAR",        "x": 35.1, "y": 11.2,"size": 8},
                    {"label": "Traton",        "x": 44.3, "y": 7.4, "size": 9},
                    {"label": "Iveco Group",   "x": 15.6, "y": 4.8, "size": 6},
                    {"label": "CNH Industrial","x": 22.8, "y": 7.2, "size": 7},
                    {"label": "Hino Motors",   "x": 9.2,  "y": 3.1, "size": 5},
                ],
            },
            "right": {
                "type": "bullet-list",
                "title": "Key Competitive Advantages",
                "items": [
                    {"text": "Brand portfolio breadth",
                     "sub": "7 brands covering every truck segment from heavy-duty to buses across 6 continents"},
                    {"text": "North America profitability",
                     "sub": "Freightliner holds 39% US Class 8 market share; highest margin region at 11.2%"},
                    {"text": "Services & digital revenue",
                     "sub": "Omniplus & Fleetboard generating €2.8B in recurring high-margin service revenue"},
                    {"text": "Electrification lead",
                     "sub": "eActros, eCascadia and eCitaro — 3 production BEV models ahead of most peers"},
                    {"text": "Financial services",
                     "sub": "Daimler Truck Financial Services funds 48% of new vehicle purchases in NA"},
                ],
            },
        },
        "footer": {"source": "Company reports, Bloomberg, Daimler Truck Investor Day 2024", "page": 8},
    },

    # ── 9. CONTENT — Horizontal bar + Text block (sidebar-right) ────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "BRAND MARKET SHARES",
            "headline": "Freightliner and Mercedes-Benz Trucks anchor #1 positions in their respective core markets",
            "sub": "2024 market share in primary segment by brand",
        },
        "layout": "sidebar-right",
        "content": {
            "main": {
                "type": "bar-chart",
                "orientation": "horizontal",
                "title": "Market Share in Primary Segment (%)",
                "labels": [
                    "Freightliner (US Class 8)",
                    "MB Trucks (EU Heavy)",
                    "BharatBenz (India MD/HD)",
                    "Western Star (US Vocational)",
                    "Setra (EU Luxury Coach)",
                    "Thomas Built (US School Bus)",
                    "FUSO (Asia Light Duty)",
                ],
                "series": [
                    {"label": "", "value": 39},
                    {"label": "", "value": 28},
                    {"label": "", "value": 22},
                    {"label": "", "value": 18},
                    {"label": "", "value": 31},
                    {"label": "", "value": 45},
                    {"label": "", "value": 17},
                ],
                "show_values": True,
            },
            "sidebar": {
                "type": "text-block",
                "title": "Key Insight",
                "style": "callout",
                "body": (
                    "Daimler Truck's multi-brand strategy enables premium positioning "
                    "across distinct segments without cannibalisation. Thomas Built Buses "
                    "commands a dominant 45% share in US school buses — a segment ignored "
                    "by European competitors. The combined brand portfolio covers 94% of "
                    "global commercial vehicle demand by segment."
                ),
            },
        },
        "footer": {"source": "IHS Markit, Daimler Truck Market Intelligence 2024", "page": 9},
    },

    # ── 10. CHAPTER — Electrification & Future ──────────────────────────────────
    {
        "slide_type": "chapter",
        "header": {
            "kicker": "Section 03",
            "headline": "Electrification\n& Strategic Roadmap",
        },
        "footer": {"source": "Daimler Truck Strategy 2030", "page": 10},
    },

    # ── 11. CONTENT — Gantt + Process flow (two-column) ─────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "ELECTRIFICATION ROADMAP",
            "headline": "Full BEV lineup operational by 2027; hydrogen fuel cell trucks enter series production in 2028",
            "sub": "Product launch timeline by segment — 2024 to 2030",
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "gantt-chart",
                "title": "BEV & FCEV Launch Timeline",
                "x_labels": ["Q1'25","Q2'25","Q3'25","Q4'25","Q1'26","Q2'26","Q3'26","Q4'26"],
                "rows": [
                    {"label": "eActros 600 (EU)",     "start": 0.00, "end": 0.25, "bar_label": "Ramp-up"},
                    {"label": "eCascadia Gen2 (NA)",  "start": 0.12, "end": 0.50, "bar_label": "Launch"},
                    {"label": "eBharatBenz (India)",   "start": 0.25, "end": 0.62, "bar_label": "Pilot"},
                    {"label": "eEconic (Muni.)",       "start": 0.38, "end": 0.75, "bar_label": "Series"},
                    {"label": "GenH2 Truck (pilot)",   "start": 0.62, "end": 1.00, "bar_label": "SOP"},
                ],
                "milestones": [
                    {"label": "EU Zero-emission mandate", "at": 0.5},
                ],
            },
            "right": {
                "type": "process-flow",
                "direction": "vertical",
                "steps": [
                    {"icon": "1", "label": "Design & Engineer",
                     "sub": "Platform co-development with Volvo Group (HTWO JV for H₂ components)"},
                    {"icon": "2", "label": "Manufacture",
                     "sub": "Wörth, Portland, and Chennai plants converting to mixed BEV/ICE lines"},
                    {"icon": "3", "label": "Charge & Refuel",
                     "sub": "CharIN Megawatt Charging Standard; H₂ refuelling via Shell JV"},
                    {"icon": "4", "label": "Operate & Finance",
                     "sub": "Subscription model via DT Financial Services; guaranteed residuals"},
                    {"icon": "5", "label": "Service & Data",
                     "sub": "Remote diagnostics via Fleetboard; predictive maintenance AI"},
                ],
            },
        },
        "footer": {"source": "Daimler Truck Strategy 2030 / Investor Day Presentation", "page": 11},
    },

    # ── 12. CONTENT — Comparison matrix (full layout) ───────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "DRIVETRAIN COMPARISON",
            "headline": "Battery-electric leads on TCO by 2026; hydrogen offers superior range for long-haul",
            "sub": "Multi-criteria comparison across drivetrain options for Class 8 long-haul trucking",
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "comparison-matrix",
                "title": "Drivetrain Comparison — Class 8 Long-Haul (2026 Outlook)",
                "columns": ["Diesel ICE", "Battery Electric", "Hydrogen FCEV"],
                "rows": [
                    {"label": "Upfront Cost",         "values": ["€130k",   "€210k",    "€280k"],   "highlight": 0},
                    {"label": "TCO (10yr, 150k km/yr)","values": ["€980k",   "€870k",    "€940k"],   "highlight": 1},
                    {"label": "Range per Fill/Charge", "values": ["1,800 km","500–800 km","1,200 km"], "highlight": 0},
                    {"label": "Refuel / Charge Time",  "values": ["12 min",  "45–90 min", "20 min"],  "highlight": 0},
                    {"label": "CO₂ (g/tkm, EU mix)",   "values": ["95",      "18",        "12"],      "highlight": 2},
                    {"label": "Infrastructure Maturity","values": ["★★★★★",   "★★★☆☆",    "★★☆☆☆"],  "highlight": 0},
                    {"label": "DT Series-Production",  "values": ["Now",     "2024–25",  "2027–28"],  "highlight": 1},
                ],
                "style": "zebra",
            }
        },
        "footer": {"source": "Daimler Truck R&D, IEA Hydrogen Review 2024, McKinsey TCO Model", "page": 12},
    },

    # ── 13. CONTENT — Three-column KPIs ─────────────────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "SUSTAINABILITY SCORECARD",
            "headline": "Carbon intensity down 38% since 2019; on track for 2030 net-zero manufacturing target",
            "sub": "Key ESG metrics across environmental, social, and governance pillars · FY2024",
        },
        "layout": "three-column",
        "content": {
            "left": {
                "type": "kpi-grid",
                "style": "compact",
                "columns": 1,
                "items": [
                    {"stat": "−38%",   "label": "CO₂ Manufacturing Intensity vs. 2019", "delta": "−5pp YoY", "positive": True,  "icon": "🌱"},
                    {"stat": "42%",    "label": "Renewable Electricity in Production",  "delta": "+8pp",     "positive": True,  "icon": "⚡"},
                    {"stat": "€1.2B",  "label": "Green Capex (Climate Tech)",           "delta": "+22%",     "positive": True,  "icon": "♻"},
                    {"stat": "Net 0",  "label": "Manufacturing Target Year",            "delta": "2030",     "positive": True,  "icon": "🎯"},
                ],
            },
            "center": {
                "type": "kpi-grid",
                "style": "compact",
                "columns": 1,
                "items": [
                    {"stat": "103k",  "label": "Total Employees Worldwide",         "delta": "+1.1%",   "positive": True,  "icon": "👥"},
                    {"stat": "22%",   "label": "Women in Leadership Roles",         "delta": "+2pp",    "positive": True,  "icon": "📈"},
                    {"stat": "96%",   "label": "Employee Engagement Score",         "delta": "+1pp",    "positive": True,  "icon": "✅"},
                    {"stat": "€180M", "label": "Training Investment FY2024",        "delta": "+12%",    "positive": True,  "icon": "🎓"},
                ],
            },
            "right": {
                "type": "kpi-grid",
                "style": "compact",
                "columns": 1,
                "items": [
                    {"stat": "45%",  "label": "Independent Supervisory Board",     "delta": "+5pp",    "positive": True,  "icon": "🏛"},
                    {"stat": "€0",   "label": "Material Compliance Fines FY2024",  "delta": "Clean",   "positive": True,  "icon": "⚖"},
                    {"stat": "86/100","label": "CDP Climate Score",                 "delta": "+4pts",   "positive": True,  "icon": "🌍"},
                    {"stat": "AAA",  "label": "MSCI ESG Rating",                   "delta": "Upgrade", "positive": True,  "icon": "⭐"},
                ],
            },
        },
        "footer": {"source": "Daimler Truck Sustainability Report 2024 / MSCI / CDP", "page": 13},
    },

    # ── 14. CTA ──────────────────────────────────────────────────────────────────
    {
        "slide_type": "cta",
        "header": {
            "headline": "Driving the future of sustainable commercial transport — together.",
            "sub": "PPTMaker · AI-generated consulting decks for Daimler Truck AG",
        },
        "content": {
            "items": [
                "10+ chart types · 5 layout modes · Daimler Truck CI/CD brand compliance",
                "Azure GPT-4 pipeline: brief → outline → DSL spec → HTML deck",
                "Contact: ir@daimlertruck.com · daimlertruck.com",
            ]
        },
        "footer": {"source": "PPTMaker v1 · Daimler Truck AG Internal Tool", "page": 14},
    },
]


def _esc_srcdoc(html: str) -> str:
    return html.replace("&", "&amp;").replace('"', "&quot;")


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


DECK_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: #0d0d0d;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
#topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    height: 44px;
    background: #1a1a1a;
    border-bottom: 1px solid #333;
    flex-shrink: 0;
}
#topbar h1 {
    font-size: 13px;
    font-weight: 600;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 60%;
}
#counter { font-size: 12px; color: #888; white-space: nowrap; }
#stage {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
}
.slide-frame {
    display: none;
    width: 1280px;
    height: 720px;
    border: none;
    box-shadow: 0 8px 40px rgba(0,0,0,0.6);
    border-radius: 4px;
    transform-origin: center center;
}
.slide-frame.active { display: block; }
#bottombar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    height: 52px;
    background: #1a1a1a;
    border-top: 1px solid #333;
    flex-shrink: 0;
}
.nav-btn {
    background: #2a2a2a;
    color: #ccc;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 7px 20px;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s;
}
.nav-btn:hover  { background: #3a3a3a; color: #fff; }
.nav-btn:active { background: #444; }
.nav-btn:disabled { opacity: 0.3; cursor: default; }
#dots { display: flex; gap: 6px; align-items: center; }
.dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #444;
    cursor: pointer;
    transition: background 0.15s;
}
.dot.active { background: #00677F; }
.dot:hover  { background: #666; }
"""

DECK_JS = """
const frames  = Array.from(document.querySelectorAll('.slide-frame'));
const dots    = Array.from(document.querySelectorAll('.dot'));
const counter = document.getElementById('counter');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
let current   = 0;

function scaleFrames() {
    const stage = document.getElementById('stage');
    const sw = stage.clientWidth  - 40;
    const sh = stage.clientHeight - 40;
    const scale = Math.min(sw / 1280, sh / 720, 1);
    frames.forEach(f => { f.style.transform = `scale(${scale})`; });
}

function goto(idx) {
    frames[current].classList.remove('active');
    dots[current].classList.remove('active');
    current = Math.max(0, Math.min(idx, frames.length - 1));
    frames[current].classList.add('active');
    dots[current].classList.add('active');
    counter.textContent = `${current + 1} / ${frames.length}`;
    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === frames.length - 1;
}

dots.forEach((d, i) => d.addEventListener('click', () => goto(i)));
prevBtn.addEventListener('click', () => goto(current - 1));
nextBtn.addEventListener('click', () => goto(current + 1));

document.addEventListener('keydown', e => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goto(current + 1);
    if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   goto(current - 1);
});

window.addEventListener('resize', scaleFrames);
scaleFrames();
goto(0);
"""


def main():
    title = "PPTMaker · Daimler Truck Showcase Deck"
    n = len(SLIDES)

    slides_html = []
    for i, spec in enumerate(SLIDES):
        try:
            h = render_slide(spec)
            slides_html.append(h)
            st = spec.get("slide_type", "?")
            print(f"  [{i+1:2d}/{n}] OK  — {st}")
        except Exception as e:
            print(f"  [{i+1:2d}/{n}] ERR — {e}")
            slides_html.append(
                f'<!DOCTYPE html><html><body style="background:#fff;display:flex;'
                f'align-items:center;justify-content:center;height:720px;font-family:sans-serif;">'
                f'<div style="color:#999;text-align:center;"><div style="font-size:48px;font-weight:700;'
                f'color:#eee;">{i+1}</div><div>Render error</div>'
                f'<div style="font-size:11px;margin-top:8px;color:#ccc;max-width:500px">{e}</div></div>'
                f'</body></html>'
            )

    frames_html = "\n".join(
        f'<iframe class="slide-frame" srcdoc="{_esc_srcdoc(h)}" sandbox="allow-same-origin"></iframe>'
        for h in slides_html
    )
    dots_html = "\n".join(
        f'<div class="dot" title="Slide {i+1}"></div>'
        for i in range(n)
    )

    deck = textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{_esc(title)}</title>
        <style>{DECK_CSS}</style>
        </head>
        <body>
        <div id="topbar">
          <h1>{_esc(title)}</h1>
          <span id="counter">1 / {n}</span>
        </div>
        <div id="stage">
        {frames_html}
        </div>
        <div id="bottombar">
          <button class="nav-btn" id="prevBtn">&larr; Prev</button>
          <div id="dots">{dots_html}</div>
          <button class="nav-btn" id="nextBtn">Next &rarr;</button>
        </div>
        <script>{DECK_JS}</script>
        </body>
        </html>
    """)

    out = Path(__file__).parent / "generated" / "dt_showcase_deck.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(deck, encoding="utf-8")
    print(f"\nDeck ({n} slides) → {out}")
    print(f"Open: file:///{out.as_posix()}")


if __name__ == "__main__":
    main()
