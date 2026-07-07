"""demo_dt_deck.py — 9-slide deck showcasing the DT brand palette and all major block types.

Demonstrates:
  - DT brand palette (Petrol + shades, Green/Red deltas, Yellow max-accent)
  - Yellow highlight rule: one bar / one scatter point per view
  - All key block types: KPI, bar, line, waterfall, gantt, scatter, comparison-matrix, process, donut

Run:
    python slide-dsl/demo_dt_deck.py

Output:
    slide-dsl/demo_output/dt_deck.html
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from renderer import render_slide

OUT = Path(__file__).parent / "demo_output"
OUT.mkdir(exist_ok=True)

SPECS = [

    # ── 1. Cover ──────────────────────────────────────────────────────────────
    {
        "slide_type": "cover",
        "header": {
            "kicker": "Strategic Review 2024",
            "headline": "Daimler Truck AG\nPerformance & Growth Outlook",
            "sub": "Executive Summary — Board Presentation Q4 2024"
        },
        "right_panel_text": "Confidential — For Internal Use Only",
        "footer": {"source": "Daimler Truck AG Management Accounts", "page": 1}
    },

    # ── 2. Chapter ────────────────────────────────────────────────────────────
    {
        "slide_type": "chapter",
        "header": {
            "kicker": "Section 01",
            "headline": "Financial Performance\nFY 2024"
        },
        "footer": {"page": 2}
    },

    # ── 3. KPI grid (accent style) + bar chart with yellow highlight ──────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "FY 2024 Results",
            "headline": "Revenue Grows 12% YoY; EBIT Margin Hits Record 9.8%",
            "sub": "All figures as reported; FX-adjusted growth +14.2%"
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "kpi-grid",
                "columns": 2,
                "style": "accent",
                "items": [
                    {"stat": "€55.8B",  "label": "Revenue",        "delta": "+12.1% YoY",     "positive": True},
                    {"stat": "9.8%",    "label": "EBIT Margin",     "delta": "Record high",    "positive": True},
                    {"stat": "€5.47B",  "label": "EBIT",            "delta": "+€620M vs 2023", "positive": True},
                    {"stat": "€3.2B",   "label": "Free Cash Flow",  "delta": "+€480M YoY",     "positive": True},
                ]
            },
            "right": {
                "type": "bar-chart",
                "orientation": "vertical",
                "title": "Revenue by Division (€B)",
                "series": [
                    {"label": "Trucks Europe", "value": 24.2},
                    {"label": "Trucks Americas", "value": 18.6, "highlight": True},
                    {"label": "Trucks Asia", "value": 7.8},
                    {"label": "Buses", "value": 3.4},
                    {"label": "Financial Services", "value": 1.8},
                ],
                "fmt": "auto",
                "show_values": True
            }
        },
        "footer": {"source": "Daimler Truck AG Annual Report 2024", "page": 3}
    },

    # ── 4. Waterfall — EBIT bridge ────────────────────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "EBIT Bridge",
            "headline": "Volume Growth and Pricing Drive €620M EBIT Expansion",
            "sub": "FY 2023 to FY 2024 bridge; management accounts basis"
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "waterfall-chart",
                "title": "EBIT Bridge FY2023 → FY2024 (€M)",
                "fmt": "auto",
                "bars": [
                    {"label": "FY 2023 EBIT",       "value": 4850,  "type": "start"},
                    {"label": "Volume Growth",        "value": 680,   "type": "positive"},
                    {"label": "Pricing & Mix",        "value": 420,   "type": "positive"},
                    {"label": "Raw Material Relief",  "value": 210,   "type": "positive"},
                    {"label": "Labour Cost Inflation","value": -380,  "type": "negative"},
                    {"label": "R&D Investment",       "value": -220,  "type": "negative"},
                    {"label": "FX Headwind",          "value": -90,   "type": "negative"},
                    {"label": "FY 2024 EBIT",         "value": 5470,  "type": "total"},
                ]
            }
        },
        "footer": {"source": "Daimler Truck AG Management Accounts", "page": 4}
    },

    # ── 5. Line chart — multi-series trend ───────────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "Revenue Trend",
            "headline": "Consistent Growth Across All Key P&L Lines Since 2020",
            "sub": "5-year CAGR: Revenue +9.4%, EBIT +18.2%, FCF +22.6%"
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "line-chart",
                "title": "5-Year Financial Trajectory (€B)",
                "labels": ["FY 2020", "FY 2021", "FY 2022", "FY 2023", "FY 2024"],
                "series": [
                    {"name": "Revenue (€B)",  "values": [35.7, 39.8, 45.6, 49.8, 55.8]},
                    {"name": "EBIT (€B)",     "values": [2.1,  3.4,  4.2,  4.85, 5.47]},
                    {"name": "FCF (€B)",      "values": [1.2,  1.9,  2.4,  2.72, 3.2]},
                ],
                "fmt": "auto",
                "show_points": True,
                "area": False
            }
        },
        "footer": {"source": "Daimler Truck AG Annual Reports 2020–2024", "page": 5}
    },

    # ── 6. Chapter ────────────────────────────────────────────────────────────
    {
        "slide_type": "chapter",
        "header": {
            "kicker": "Section 02",
            "headline": "Strategic Priorities\n2025–2027"
        },
        "footer": {"page": 6}
    },

    # ── 7. Gantt — transformation roadmap ────────────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "Transformation Roadmap",
            "headline": "Three-Year Electrification & Digital Programme Underway",
            "sub": "Six workstreams; €4.2B total investment committed"
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "gantt-chart",
                "title": "Strategic Programme Timeline 2025–2027",
                "x_labels": ["Q1 25","Q2 25","Q3 25","Q4 25",
                              "Q1 26","Q2 26","Q3 26","Q4 26",
                              "Q1 27","Q2 27","Q3 27","Q4 27"],
                "rows": [
                    {"label": "eTruck Platform (eActros 600)", "start": 0/12,  "end": 5/12,  "bar_label": "Volume ramp"},
                    {"label": "Charging Infrastructure",        "start": 1/12,  "end": 8/12,  "bar_label": "1,200 sites"},
                    {"label": "Battery Supply Chain",           "start": 0/12,  "end": 10/12, "bar_label": "3 supplier contracts"},
                    {"label": "Digital Services Platform",      "start": 2/12,  "end": 9/12,  "bar_label": "Fleet.OS v2"},
                    {"label": "Workforce Reskilling",           "start": 0/12,  "end": 1.0,   "bar_label": "8,400 employees"},
                    {"label": "Carbon Reporting (CSRD)",        "start": 3/12,  "end": 6/12,  "bar_label": "Full compliance"},
                ],
                "milestones": [
                    {"label": "eActros 600 SOP",    "at": 4/12},
                    {"label": "Fleet.OS Launch",    "at": 8/12},
                    {"label": "Net-Zero Milestone", "at": 11/12},
                ]
            }
        },
        "footer": {"source": "Daimler Truck AG Strategy Presentation Nov 2024", "page": 7}
    },

    # ── 8. Scatter — portfolio positioning with yellow highlight ──────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "Market Positioning",
            "headline": "eActros 600 Leads on Total Cost of Ownership vs. Competitors",
            "sub": "Competitive analysis based on publicly available fleet operator data"
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "scatter-chart",
                "title": "Electric Heavy-Duty Truck: Range vs. TCO Index (5-year fleet basis)",
                "points": [
                    {"label": "eActros 600",    "x": 500, "y": 82,  "size": 10, "highlight": True},
                    {"label": "Volvo FH Elec.", "x": 390, "y": 88,  "size": 8},
                    {"label": "Scania BEV",     "x": 350, "y": 91,  "size": 8},
                    {"label": "MAN eTruck",     "x": 270, "y": 94,  "size": 7},
                    {"label": "Freightliner eCascadia","x": 440, "y": 86,  "size": 8},
                    {"label": "Tesla Semi",     "x": 480, "y": 90,  "size": 9},
                    {"label": "Nikola Tre",     "x": 280, "y": 97,  "size": 6},
                    {"label": "BYD T10A",       "x": 200, "y": 95,  "size": 6},
                ],
                "x_label": "Range per charge (km)",
                "y_label": "TCO Index (lower = better, 100 = diesel baseline)",
                "x_range": [150, 550],
                "y_range": [75, 105],
                "quadrant_labels": [
                    "Short range\nHigh TCO",
                    "Long range\nHigh TCO",
                    "Short range\nLow TCO",
                    "Long range\nLow TCO"
                ]
            }
        },
        "footer": {"source": "Daimler Truck market analysis; fleet operator benchmarks", "page": 8}
    },

    # ── 9. Comparison matrix — strategic options ──────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "Strategic Options",
            "headline": "Battery JV with CATL Preferred Over Fully In-House Production",
            "sub": "Evaluated against five strategic criteria; IC-approved framework"
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "comparison-matrix",
                "title": "Battery Strategy Options Assessment",
                "style": "zebra",
                "columns": ["In-House Production", "JV with CATL", "Long-term Supply Agreement"],
                "rows": [
                    {"label": "Capital Required (5yr)",  "values": ["€4.8B",   "€1.6B",    "€0.3B"],      "highlight": 1},
                    {"label": "Time to Full Capacity",   "values": ["5–7 yrs", "2–3 yrs",  "Immediate"],  "highlight": 2},
                    {"label": "Technology Control",      "values": ["Full",    "Shared",    "None"],        "highlight": 0},
                    {"label": "Supply Security",         "values": ["High",    "High",      "Medium"],      "highlight": 0},
                    {"label": "Cost Competitiveness",    "values": ["Low",     "High",      "Medium"],      "highlight": 1},
                    {"label": "Recommendation",          "values": ["–",       "✓ Preferred","–"],          "highlight": 1},
                ]
            }
        },
        "footer": {"source": "Daimler Truck Strategy & Corporate Development", "page": 9}
    },

]


def build_deck(specs: list[dict]) -> str:
    slides_html = []
    for i, spec in enumerate(specs):
        html = render_slide(spec)
        # Extract body content from full HTML
        body_start = html.find("<body>") + 6
        body_end   = html.find("</body>")
        inner      = html[body_start:body_end].strip()
        slides_html.append(f'<div class="slide-frame" id="slide-{i+1}">{inner}</div>')

    nav_dots = "".join(
        f'<span class="dot {"active" if i==0 else ""}" onclick="goTo({i+1})"></span>'
        for i in range(len(specs))
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Daimler Truck — Strategic Review 2024</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#1a1a1a; display:flex; flex-direction:column;
        align-items:center; justify-content:center;
        min-height:100vh; font-family:Arial,sans-serif; }}
.deck-wrap {{ position:relative; width:1280px; }}
.slide-frame {{ display:none; width:1280px; height:720px; overflow:hidden; }}
.slide-frame.active {{ display:block; }}
.controls {{ display:flex; align-items:center; justify-content:center;
             gap:12px; margin-top:16px; }}
.btn {{ background:#00677F; color:#fff; border:none; padding:8px 24px;
        border-radius:4px; cursor:pointer; font-size:14px; font-weight:600; }}
.btn:hover {{ background:#004355; }}
.dot {{ width:10px; height:10px; border-radius:50%; background:#555;
        cursor:pointer; transition:background .2s; }}
.dot.active {{ background:#00677F; }}
.counter {{ color:#888; font-size:13px; min-width:60px; text-align:center; }}
</style>
</head>
<body>
<div class="deck-wrap">
{"".join(slides_html)}
</div>
<div class="controls">
  <button class="btn" onclick="prev()">&#8592; Prev</button>
  <div style="display:flex;gap:6px;align-items:center">{nav_dots}</div>
  <button class="btn" onclick="next()">Next &#8594;</button>
  <span class="counter" id="counter">1 / {len(specs)}</span>
</div>
<script>
let cur = 1;
const total = {len(specs)};
function goTo(n) {{
  document.querySelector('.slide-frame.active')?.classList.remove('active');
  document.querySelector('.dot.active')?.classList.remove('active');
  cur = Math.max(1, Math.min(n, total));
  document.getElementById('slide-' + cur).classList.add('active');
  document.querySelectorAll('.dot')[cur-1].classList.add('active');
  document.getElementById('counter').textContent = cur + ' / ' + total;
}}
function next() {{ goTo(cur + 1); }}
function prev() {{ goTo(cur - 1); }}
document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight' || e.key === ' ') next();
  if (e.key === 'ArrowLeft')  prev();
}});
goTo(1);
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("Rendering 9 slides...")
    deck_html = build_deck(SPECS)
    out = OUT / "dt_deck.html"
    out.write_text(deck_html, encoding="utf-8")
    print(f"Done -> {out}")
    print(f"Open:   file:///{out.as_posix()}")
