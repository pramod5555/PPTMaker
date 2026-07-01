"""demo.py — Render 9 sample slides covering all major block types.

Run:
    python slide-dsl/demo.py

Output:
    slide-dsl/demo_output/slide_01.html  ... slide_09.html
    slide-dsl/demo_output/demo_deck.html  (combined viewer)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from renderer import render_slide

OUT = Path(__file__).parent / "demo_output"
OUT.mkdir(exist_ok=True)


SPECS = [

    # 1 ── Cover
    {
        "slide_type": "cover",
        "header": {
            "kicker": "Private Capital Series",
            "headline": "Private Capital in Transition:\nNavigating the New Normal",
            "sub": "Strategic Outlook 2024–2026"
        },
        "right_panel_text": "Confidential — For Discussion Purposes Only",
        "footer": {"source": "McKinsey Global Private Markets Review 2024", "page": 1}
    },

    # 2 ── Chapter divider
    {
        "slide_type": "chapter",
        "header": {
            "kicker": "Section 01",
            "headline": "Market Dynamics\nand Capital Flows"
        },
        "footer": {"page": 3}
    },

    # 3 ── KPI grid (left) + grouped bar chart (right)
    {
        "slide_type": "content",
        "header": {
            "kicker": "Market Overview",
            "headline": "Private Credit Reaches $2.1T AUM",
            "sub": "Four-year CAGR of 18%, driven by bank retreat from middle-market lending"
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "kpi-grid",
                "columns": 2,
                "items": [
                    {"stat": "$2.1T",  "label": "Total AUM",    "delta": "+18% CAGR (4yr)", "positive": True},
                    {"stat": "847",    "label": "Active Funds",  "delta": "+23 new in 2024", "positive": True},
                    {"stat": "12.4%",  "label": "Avg Net IRR",   "delta": "-0.8pp vs 2022",  "positive": False},
                    {"stat": "6.2x",   "label": "Avg MOIC",      "delta": "stable YoY",       "positive": None}
                ]
            },
            "right": {
                "type": "bar-chart",
                "title": "AUM by Strategy ($B)",
                "series": [
                    {"name": "Direct Lending", "values": [420, 580, 710, 890, 1050]},
                    {"name": "Distressed",      "values": [180, 210, 190, 240, 280]}
                ],
                "labels": ["2019", "2020", "2021", "2022", "2023"],
                "stacked": False,
                "show_values": True
            }
        },
        "footer": {"source": "Preqin 2024; McKinsey analysis", "page": 5}
    },

    # 4 ── Bullet list (left) + donut chart (right)
    {
        "slide_type": "content",
        "header": {
            "kicker": "Strategy Allocation",
            "headline": "Direct Lending Dominates at 58% of Total AUM",
            "sub": "Driven by superior risk-adjusted returns and structural tailwinds from bank regulation"
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "bullet-list",
                "title": "Key Structural Drivers",
                "items": [
                    {"text": "Banking sector retreat post-Basel III",
                     "sub": "Regulatory capital requirements raised cost of middle-market lending by 40–60bps"},
                    {"text": "Floating rate structures provide inflation hedge",
                     "sub": "SOFR + spread model benefits investors in rising rate environment"},
                    {"text": "Covenant-lite erosion in syndicated markets",
                     "sub": "Private credit retains stronger lender protections and direct management access"},
                    {"text": "Longer hold periods reward patient capital",
                     "sub": "Illiquidity premium of 100–150bps over equivalent public debt"}
                ]
            },
            "right": {
                "type": "donut-chart",
                "center_text": "$2.1T",
                "center_label": "Total AUM",
                "segments": [
                    {"label": "Direct Lending", "value": 58},
                    {"label": "Distressed",      "value": 23},
                    {"label": "Mezzanine",       "value": 11},
                    {"label": "Other",           "value": 8}
                ]
            }
        },
        "footer": {"source": "Preqin Q4 2024", "page": 7}
    },

    # 5 ── Multi-line chart (full width, area fill)
    {
        "slide_type": "content",
        "header": {
            "kicker": "Performance Trends",
            "headline": "Net IRR Has Compressed But Remains Above Public Market Equivalents",
            "sub": "10-year horizon returns by strategy, net of fees (%)"
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "line-chart",
                "labels": ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"],
                "series": [
                    {"name": "Direct Lending", "values": [13.2, 13.8, 14.1, 13.6, 12.9, 11.8, 13.4, 14.2, 12.4]},
                    {"name": "Distressed",     "values": [15.1, 16.2, 14.8, 13.9, 12.1, 17.3, 18.2, 14.1, 11.8]},
                    {"name": "S&P 500 PME",    "values": [11.2, 10.8, 12.1, 11.4, 13.2, 10.1, 15.2,  9.8, 11.6]}
                ],
                "y_label": "Net IRR (%)",
                "fmt": "decimal",
                "area": True
            }
        },
        "footer": {"source": "Cambridge Associates; Preqin 2024", "page": 9}
    },

    # 6 ── Horizontal bar (full width)
    {
        "slide_type": "content",
        "header": {
            "kicker": "Geographic Distribution",
            "headline": "North America Leads at 58% But APAC Share Growing Fastest",
            "sub": "AUM by geography, 2024 (% of total)"
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "bar-chart",
                "orientation": "horizontal",
                "series": [
                    {"label": "North America",  "value": 58},
                    {"label": "Europe",          "value": 27},
                    {"label": "Asia Pacific",    "value": 11},
                    {"label": "Rest of World",   "value": 4}
                ],
                "fmt": "percent",
                "show_values": True
            }
        },
        "footer": {"source": "Preqin 2024; McKinsey analysis", "page": 11}
    },

    # 7 ── Waterfall (full width)
    {
        "slide_type": "content",
        "header": {
            "kicker": "AUM Bridge",
            "headline": "Net New Commitments and Portfolio Appreciation Drive $360B Growth",
            "sub": "AUM movement 2022 to 2024 ($B)"
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "waterfall-chart",
                "title": "AUM Bridge 2022–2024 ($B)",
                "bars": [
                    {"label": "2022 AUM",          "value": 1720, "type": "start"},
                    {"label": "New Commitments",    "value":  620},
                    {"label": "Distributions",      "value": -380},
                    {"label": "Appreciation",       "value":  210},
                    {"label": "Fees & Expenses",    "value":  -70},
                    {"label": "FX Impact",          "value":  -20},
                    {"label": "2024 AUM",           "value": 2080, "type": "total"}
                ],
                "show_values": True
            }
        },
        "footer": {"source": "Preqin; company reports; McKinsey analysis", "page": 14}
    },

    # 8 ── Gantt chart (full width)
    {
        "slide_type": "content",
        "header": {
            "kicker": "Implementation Roadmap",
            "headline": "Three-Phase Transformation Delivers Full Operating Model in 18 Months",
            "sub": "Indicative timeline — subject to board approval Q1 2025"
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "gantt-chart",
                "x_labels": ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025", "Q1 2026", "Q2 2026"],
                "rows": [
                    {"label": "Diagnostic & Design",  "start": 0,   "end": 1.5, "bar_label": "6 wks"},
                    {"label": "Platform Selection",    "start": 0.5, "end": 2.0, "bar_label": "6 wks"},
                    {"label": "Pilot Launch",          "start": 2.0, "end": 3.5, "bar_label": "Pilot"},
                    {"label": "Investor Onboarding",   "start": 2.5, "end": 4.5},
                    {"label": "Full Scale Rollout",    "start": 4.0, "end": 6.0, "bar_label": "Scale"}
                ],
                "milestones": [
                    {"label": "Board Approval", "at": 1.0},
                    {"label": "Go-Live",         "at": 3.5}
                ]
            }
        },
        "footer": {"source": "McKinsey transformation office", "page": 17}
    },

    # 9 ── Process flow + table (sidebar)
    {
        "slide_type": "content",
        "header": {
            "kicker": "Investment Process",
            "headline": "Five-Step Process Ensures Consistent Underwriting Across All Strategies",
            "sub": "End-to-end deal cycle from origination to portfolio monitoring"
        },
        "layout": "sidebar-right",
        "content": {
            "main": {
                "type": "process-flow",
                "direction": "vertical",
                "steps": [
                    {"icon": "1", "label": "Origination",  "sub": "Direct sponsor relationships; proprietary pipeline of 200+ deals/year"},
                    {"icon": "2", "label": "Screening",    "sub": "Sector fit, leverage tolerance, minimum EBITDA $10M"},
                    {"icon": "3", "label": "Underwriting", "sub": "Full credit analysis, downside scenarios, peer benchmarking"},
                    {"icon": "4", "label": "IC Review",    "sub": "Investment committee unanimous approval required"},
                    {"icon": "5", "label": "Monitoring",   "sub": "Quarterly reporting, covenant tracking, board observer rights"}
                ]
            },
            "sidebar": {
                "type": "table",
                "headers": ["Metric", "2023"],
                "col_widths": [200, 170],
                "rows": [
                    ["Deals screened",    "847"],
                    ["IC submissions",    "112"],
                    ["Deals closed",       "43"],
                    ["Conversion rate",  "5.1%"],
                    ["Avg ticket size", "$180M"],
                    ["Avg LTV",          "48%"]
                ],
                "highlight_col": 1
            }
        },
        "footer": {"source": "Internal deal log; McKinsey analysis", "page": 20}
    },

]


def _srcdoc_encode(html: str) -> str:
    return html.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&#60;").replace(">", "&#62;")


def main():
    slide_htmls = []
    for i, spec in enumerate(SPECS):
        html  = render_slide(spec)
        fname = f"slide_{i+1:02d}.html"
        (OUT / fname).write_text(html, encoding="utf-8")
        slide_htmls.append(html)
        stype = spec.get("slide_type", "content")
        layout = spec.get("layout", "-")
        print(f"  {fname}  [{stype}/{layout}]  {len(html):,} chars")

    # Combined deck viewer
    deck = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Slide DSL Demo Deck</title>
<style>
body { margin: 0; background: #1a1a1a; padding: 30px; font-family: Arial, sans-serif; }
h1 { color: #fff; font-size: 16px; margin-bottom: 24px; font-weight: 400; opacity: 0.6; }
.wrap { margin: 0 auto 24px auto; width: 1280px; box-shadow: 0 4px 24px rgba(0,0,0,0.6); }
iframe { display: block; width: 1280px; height: 720px; border: none; }
.label { color: rgba(255,255,255,0.3); font-size: 11px; margin-bottom: 4px; }
</style>
</head>
<body>
<h1>Slide DSL — Demo Deck ({n} slides)</h1>
""".replace("{n}", str(len(SPECS)))

    for i, (spec, html) in enumerate(zip(SPECS, slide_htmls)):
        stype  = spec.get("slide_type", "content")
        layout = spec.get("layout", "")
        label  = f"Slide {i+1} — {stype}" + (f" / {layout}" if layout else "")
        deck += f'<div class="label">{label}</div>\n'
        deck += f'<div class="wrap"><iframe srcdoc="{_srcdoc_encode(html)}"></iframe></div>\n'

    deck += "</body></html>"
    deck_path = OUT / "demo_deck.html"
    deck_path.write_text(deck, encoding="utf-8")
    print(f"\nDeck viewer -> {deck_path}")
    print(f"Open in browser: file:///{deck_path.as_posix()}")


if __name__ == "__main__":
    main()
