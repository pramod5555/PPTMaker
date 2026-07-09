"""stress_two_col.py — Renders all two-column chart-pair combinations to a deck.

No API calls — all specs are hand-crafted with dense realistic data.
Run:  python slide-dsl/stress_two_col.py
"""
from __future__ import annotations
import sys, textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from renderer import render_slide

ROOT = Path(__file__).parent.parent
OUT  = ROOT / "slide-dsl" / "generated" / "stress_two_col.html"

SLIDES = [

# ── 1. Line + Line (many series — the original bug) ───────────────────────────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 01", "headline": "Dual Line Charts: 6-Series Bond Yield Trends vs Inflation Expectations"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "line-chart",
      "title": "Global Bond Yields 2018–2024",
      "labels": ["2018","2019","2020","2021","2022","2023","2024"],
      "series": [
        {"name": "US 10Y Treasury",        "values": [2.91, 2.14, 0.93, 1.52, 3.88, 3.97, 4.25]},
        {"name": "Eurozone 10Y Bund",      "values": [0.44, -0.19, -0.57, -0.18, 2.57, 2.56, 2.37]},
        {"name": "UK 10Y Gilt",            "values": [1.28, 0.82, 0.30, 0.97, 3.67, 3.68, 4.15]},
        {"name": "Japan 10Y JGB",          "values": [0.05, -0.01, 0.02, 0.07, 0.25, 0.63, 0.87]},
        {"name": "Australia 10Y Bond",     "values": [2.73, 1.37, 0.98, 1.67, 3.95, 4.32, 4.40]},
        {"name": "Canada 10Y Bond",        "values": [2.34, 1.70, 0.68, 1.43, 3.29, 3.65, 3.78]}
      ],
      "fmt": "decimal",
      "show_points": False
    },
    "right": {
      "type": "line-chart",
      "title": "5Y5Y Inflation Expectations 2018–2024",
      "labels": ["2018","2019","2020","2021","2022","2023","2024"],
      "series": [
        {"name": "US 5Y5Y Breakeven",      "values": [2.18, 2.10, 2.25, 2.52, 2.63, 2.48, 2.38]},
        {"name": "Eurozone 5Y5Y Swap",     "values": [1.72, 1.48, 1.55, 2.12, 2.56, 2.44, 2.29]},
        {"name": "UK 5Y5Y Swap",           "values": [3.51, 3.25, 3.18, 3.67, 4.02, 3.72, 3.55]},
        {"name": "Japan 5Y5Y Swap",        "values": [0.15, 0.22, 0.18, 0.38, 0.85, 1.12, 1.34]},
        {"name": "Australia 5Y5Y Swap",    "values": [2.40, 2.20, 2.35, 2.68, 2.85, 2.73, 2.60]},
        {"name": "Canada 5Y5Y Swap",       "values": [1.88, 1.75, 1.90, 2.30, 2.55, 2.48, 2.35]}
      ],
      "fmt": "decimal",
      "show_points": False
    }
  },
  "footer": {"source": "Bloomberg, ECB, Federal Reserve", "page": 1}
},

# ── 2. Bar + Bar (vertical, different series counts) ──────────────────────────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 02", "headline": "Dual Bar Charts: PE Fundraising vs Deployment by Strategy"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "bar-chart",
      "title": "Capital Raised by Strategy ($Bn) 2024",
      "orientation": "horizontal",
      "series": [
        {"label": "Buyout",           "value": 387},
        {"label": "Venture Capital",  "value": 213},
        {"label": "Growth Equity",    "value": 156},
        {"label": "Real Estate",      "value": 134},
        {"label": "Infrastructure",   "value": 118},
        {"label": "Credit",           "value": 97},
        {"label": "Secondaries",      "value": 84}
      ],
      "fmt": "auto",
      "show_values": True
    },
    "right": {
      "type": "bar-chart",
      "title": "Deal Count by Quarter 2022–2024",
      "orientation": "vertical",
      "stacked": False,
      "labels": ["Q1'22","Q2'22","Q3'22","Q4'22","Q1'23","Q2'23","Q3'23","Q4'23","Q1'24","Q2'24"],
      "series": [
        {"name": "Buyout",  "values": [312, 298, 275, 241, 227, 243, 261, 278, 289, 301]},
        {"name": "VC",      "values": [891, 874, 812, 736, 698, 721, 754, 780, 798, 815]},
        {"name": "Growth",  "values": [187, 176, 165, 148, 139, 152, 161, 169, 178, 184]}
      ],
      "fmt": "auto",
      "show_values": False
    }
  },
  "footer": {"source": "Preqin 2024 Global PE Report", "page": 2}
},

# ── 3. Waterfall + Table (narrow table with long headers — original bug) ───────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 03", "headline": "Revenue Bridge vs Segment Performance Summary"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "waterfall-chart",
      "title": "FY2024 Revenue Bridge ($M)",
      "fmt": "auto",
      "bars": [
        {"label": "FY2023 Base",       "value": 4820, "type": "start"},
        {"label": "Volume Growth",     "value": 612,  "type": "positive"},
        {"label": "Pricing Impact",    "value": 284,  "type": "positive"},
        {"label": "FX Headwind",       "value": -198, "type": "negative"},
        {"label": "Portfolio Exits",   "value": -143, "type": "negative"},
        {"label": "Acquisitions",      "value": 521,  "type": "positive"},
        {"label": "Restructuring",     "value": -87,  "type": "negative"},
        {"label": "FY2024 Total",      "value": 5809, "type": "total"}
      ]
    },
    "right": {
      "type": "table",
      "headers": ["Segment", "2023 Revenue", "2024 Revenue", "YoY Growth", "EBITDA Margin", "Headcount"],
      "rows": [
        ["Enterprise Software", "$1,842M", "$2,156M", "+17.0%", "34.2%", "8,420"],
        ["Cloud Services",      "$1,124M", "$1,387M", "+23.4%", "28.7%", "4,210"],
        ["Professional Svcs",   "$892M",   "$1,021M", "+14.5%", "18.3%", "6,890"],
        ["Hardware & OEM",      "$612M",   "$798M",   "+30.4%", "22.1%", "2,340"],
        ["Maintenance",         "$350M",   "$447M",   "+27.7%", "61.4%", "1,120"]
      ],
      "highlight_col": 4
    }
  },
  "footer": {"source": "Company filings, internal analysis", "page": 3}
},

# ── 4. Donut + Bullet list ────────────────────────────────────────────────────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 04", "headline": "Portfolio Allocation vs Strategic Rationale"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "donut-chart",
      "center_text": "$4.7T",
      "center_label": "AUM",
      "show_legend": True,
      "segments": [
        {"label": "North American Buyout",          "value": 1645},
        {"label": "European Growth Equity",         "value": 987},
        {"label": "Asia Pacific Infrastructure",    "value": 763},
        {"label": "Global Credit Opportunities",    "value": 612},
        {"label": "Climate Transition Fund",        "value": 487},
        {"label": "Secondaries & Co-Invest",        "value": 206}
      ]
    },
    "right": {
      "type": "bullet-list",
      "title": "Portfolio Construction Rationale",
      "items": [
        {"text": "North American Buyout remains anchor strategy", "sub": "Strong deal flow in tech-enabled services; 14 platforms added in 2024 at 8.2x avg entry EBITDA"},
        {"text": "European Growth Equity allocation increased 12%", "sub": "Energy transition and B2B SaaS driving outsized deal activity; euro weakness creates entry opportunity"},
        {"text": "Asia Pacific Infrastructure de-risked", "sub": "Shifted from China exposure to SE Asia data centers and Australian renewables; IRR target 13–15%"},
        {"text": "Global Credit Opportunities buffer expanded", "sub": "Senior secured floating rate at 450bps spread; provides downside protection in rate volatility scenarios"},
        {"text": "Climate Transition Fund fully committed", "sub": "25 investments across wind, solar and grid storage; average DPI of 0.8x ahead of 5-year plan"}
      ]
    }
  },
  "footer": {"source": "Portfolio Management Team, Q4 2024 Review", "page": 4}
},

# ── 5. Line + Bar (mixed types) ───────────────────────────────────────────────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 05", "headline": "Revenue Growth Rate vs Absolute Deal Volume"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "line-chart",
      "title": "YoY Revenue Growth by Cohort 2019–2024",
      "labels": ["2019","2020","2021","2022","2023","2024"],
      "series": [
        {"name": "Cohort 2017 (Mature)",   "values": [8.2,  -2.1, 12.4, 9.8,  7.1,  6.3]},
        {"name": "Cohort 2019 (Growth)",   "values": [None, 18.3, 34.7, 28.2, 19.4, 14.8]},
        {"name": "Cohort 2021 (Early)",    "values": [None,None,None, 41.3, 31.2, 24.7]},
        {"name": "Portfolio Average",      "values": [8.2,  4.1,  22.1, 18.7, 15.2, 12.8]}
      ],
      "fmt": "percent",
      "area": False,
      "show_points": True
    },
    "right": {
      "type": "bar-chart",
      "title": "Deal Volume by Sector ($Bn) 2024",
      "orientation": "vertical",
      "stacked": True,
      "labels": ["Q1","Q2","Q3","Q4"],
      "series": [
        {"name": "Technology",    "values": [12.4, 15.7, 13.2, 18.9]},
        {"name": "Healthcare",    "values": [8.1,  9.3,  8.7,  11.2]},
        {"name": "Industrials",   "values": [6.2,  7.1,  6.8,  8.4]},
        {"name": "Consumer",      "values": [4.3,  5.2,  4.9,  6.1]},
        {"name": "Financial Svcs","values": [3.8,  4.4,  4.1,  5.3]}
      ],
      "fmt": "auto",
      "show_values": False
    }
  },
  "footer": {"source": "Internal portfolio data, Pitchbook 2024", "page": 5}
},

# ── 6. Scatter + Bullet ───────────────────────────────────────────────────────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 06", "headline": "Portfolio Positioning: Risk-Return vs Strategic Priorities"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "scatter-chart",
      "title": "IRR vs Risk Score by Asset",
      "x_label": "Risk Score (1–10)",
      "y_label": "Net IRR (%)",
      "x_range": [1, 10],
      "y_range": [0, 35],
      "quadrant_labels": ["Low Risk / High Return", "High Risk / High Return", "Low Risk / Low Return", "High Risk / Low Return"],
      "points": [
        {"label": "Asset A",  "x": 2.1, "y": 18.4, "size": 8},
        {"label": "Asset B",  "x": 3.4, "y": 22.7, "size": 10},
        {"label": "Asset C",  "x": 4.8, "y": 28.3, "size": 14},
        {"label": "Asset D",  "x": 5.2, "y": 15.1, "size": 7},
        {"label": "Asset E",  "x": 6.7, "y": 31.4, "size": 12},
        {"label": "Asset F",  "x": 7.3, "y": 12.8, "size": 6},
        {"label": "Asset G",  "x": 8.1, "y": 24.6, "size": 11},
        {"label": "Asset H",  "x": 3.9, "y": 19.2, "size": 9},
        {"label": "Asset I",  "x": 5.8, "y": 8.7,  "size": 5},
        {"label": "Asset J",  "x": 2.6, "y": 14.3, "size": 8}
      ]
    },
    "right": {
      "type": "bullet-list",
      "title": "Key Observations",
      "items": [
        {"text": "Cluster in moderate-risk / high-return quadrant", "sub": "Assets B, C, H grouped at 3–5 risk score with 19–28% IRR; represents core outperformance thesis"},
        {"text": "Two outliers in high-risk zone require monitoring", "sub": "Assets F and I show 6.7–8.1 risk with below-target IRR of 12.8% and 8.7% respectively"},
        {"text": "Asset C best risk-adjusted return in portfolio", "sub": "28.3% IRR at 4.8 risk score; tech-enabled logistics buyout; exit process initiated Q3 2025"},
        {"text": "Low-risk anchor positions delivering steady returns", "sub": "Assets A and J at sub-3 risk with 14–18% IRR; infrastructure assets providing portfolio stability"},
        {"text": "Portfolio average IRR 20.1% vs 18% target", "sub": "Outperformance driven by technology sector multiples expansion; review risk model assumptions"}
      ]
    }
  },
  "footer": {"source": "Portfolio Risk Team, Q4 2024", "page": 6}
},

# ── 7. KPI Grid + Table ───────────────────────────────────────────────────────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 07", "headline": "Fund Performance KPIs vs Peer Benchmarking"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "kpi-grid",
      "columns": 2,
      "style": "accent",
      "items": [
        {"stat": "21.4%",   "label": "Net IRR (Fund IV)",    "delta": "+3.2pp vs Fund III", "positive": True},
        {"stat": "1.87x",   "label": "TVPI Multiple",        "delta": "+0.14x vs vintage avg", "positive": True},
        {"stat": "$4.7Bn",  "label": "Total Equity Value",   "delta": "+$620M YoY",         "positive": True},
        {"stat": "0.61x",   "label": "DPI (Realised)",       "delta": "On track for 0.8x target", "positive": None},
        {"stat": "3.2yrs",  "label": "Avg Holding Period",   "delta": "Below 4yr fund avg", "positive": True},
        {"stat": "94%",     "label": "Capital Deployed",     "delta": "2 platforms remaining", "positive": None}
      ]
    },
    "right": {
      "type": "table",
      "headers": ["Fund", "Vintage", "Net IRR", "TVPI", "DPI", "Strategy"],
      "rows": [
        ["Fund IV (Ours)",      "2021", "21.4%", "1.87x", "0.61x", "Buyout"],
        ["Peer A Fund VI",      "2021", "18.2%", "1.71x", "0.54x", "Buyout"],
        ["Peer B Fund V",       "2021", "19.7%", "1.79x", "0.58x", "Buyout"],
        ["Peer C Growth III",   "2021", "24.3%", "2.01x", "0.47x", "Growth"],
        ["Vintage 2021 Median", "2021", "17.8%", "1.68x", "0.51x", "Buyout"],
        ["Top Quartile Bench.", "2021", "22.1%", "1.92x", "0.65x", "Buyout"]
      ],
      "highlight_col": 0
    }
  },
  "footer": {"source": "Preqin Benchmarks Q3 2024, Internal data", "page": 7}
},

# ── 8. Gantt + KPI Grid ───────────────────────────────────────────────────────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 08", "headline": "Digital Transformation Roadmap vs Progress Metrics"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "gantt-chart",
      "title": "8-Quarter Transformation Roadmap",
      "x_labels": ["Q1 '24", "Q2 '24", "Q3 '24", "Q4 '24", "Q1 '25", "Q2 '25", "Q3 '25", "Q4 '25"],
      "rows": [
        {"label": "Core ERP Migration",     "start": 0.00, "end": 0.38, "bar_label": "Phase 1"},
        {"label": "Data Lake Build-out",    "start": 0.13, "end": 0.56, "bar_label": "Foundation"},
        {"label": "AI/ML Platform",         "start": 0.38, "end": 0.75, "bar_label": "Deploy"},
        {"label": "Workforce Reskilling",   "start": 0.20, "end": 0.88, "bar_label": "Ongoing"},
        {"label": "Customer Portal v2",     "start": 0.56, "end": 0.88, "bar_label": "Launch"},
        {"label": "Legacy Decommission",    "start": 0.75, "end": 1.00, "bar_label": "Shutdown"}
      ],
      "milestones": [
        {"label": "ERP Go-Live",    "at": 0.38},
        {"label": "AI Launch",      "at": 0.75},
        {"label": "Full Migration", "at": 1.00}
      ]
    },
    "right": {
      "type": "kpi-grid",
      "columns": 2,
      "style": "compact",
      "items": [
        {"stat": "67%",    "label": "Milestones On Track",  "delta": "+8pp vs last qtr", "positive": True},
        {"stat": "$34M",   "label": "Budget Spent to Date", "delta": "vs $38M plan",     "positive": True},
        {"stat": "1,240",  "label": "Staff Retrained",      "delta": "of 1,800 target",  "positive": None},
        {"stat": "18%",    "label": "Process Automation",   "delta": "+6pp this quarter","positive": True},
        {"stat": "4.2/5",  "label": "Change Readiness Score","delta": "Survey n=320",    "positive": None},
        {"stat": "Q3 '26", "label": "Full Go-Live Target",  "delta": "1 qtr ahead",      "positive": True}
      ]
    }
  },
  "footer": {"source": "Transformation PMO Dashboard, July 2025", "page": 8}
},

# ── 9. Donut + Line ───────────────────────────────────────────────────────────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 09", "headline": "Revenue Mix Shift vs Long-Term Trend by Segment"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "donut-chart",
      "center_text": "78%",
      "center_label": "Recurring",
      "show_legend": True,
      "segments": [
        {"label": "SaaS Subscriptions",     "value": 42},
        {"label": "Managed Services",       "value": 21},
        {"label": "Support Contracts",      "value": 15},
        {"label": "Professional Services",  "value": 13},
        {"label": "Hardware One-Time",      "value": 9}
      ]
    },
    "right": {
      "type": "line-chart",
      "title": "Recurring Revenue Growth 2020–2024 (%)",
      "labels": ["2020","2021","2022","2023","2024"],
      "series": [
        {"name": "SaaS Subscriptions",    "values": [28.4, 41.2, 35.8, 29.3, 24.7]},
        {"name": "Managed Services",      "values": [12.1, 18.7, 22.4, 19.8, 16.2]},
        {"name": "Support Contracts",     "values": [5.3,  8.1,  9.7,  8.4,  7.1]},
        {"name": "Total Recurring Rev.",  "values": [20.8, 31.4, 27.6, 23.1, 19.4]}
      ],
      "fmt": "percent",
      "area": False,
      "show_points": True
    }
  },
  "footer": {"source": "Company IR filings, Q4 2024 Earnings", "page": 9}
},

# ── 10. Bar + Waterfall (stacked bar + waterfall) ─────────────────────────────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 10", "headline": "Headcount Evolution vs Cost Bridge Impact"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "bar-chart",
      "title": "Headcount by Function 2021–2024",
      "orientation": "vertical",
      "stacked": True,
      "labels": ["2021","2022","2023","2024"],
      "series": [
        {"name": "Engineering",      "values": [1820, 2140, 2380, 2610]},
        {"name": "Sales & Marketing","values": [940,  1080, 1210, 1340]},
        {"name": "Operations",       "values": [720,  810,  870,  940]},
        {"name": "G&A",              "values": [380,  420,  460,  490]},
        {"name": "Product",          "values": [280,  320,  370,  410]}
      ],
      "fmt": "auto",
      "show_values": False
    },
    "right": {
      "type": "waterfall-chart",
      "title": "FY2024 Total Staff Cost Bridge ($M)",
      "fmt": "auto",
      "bars": [
        {"label": "FY2023 Base",        "value": 312, "type": "start"},
        {"label": "Headcount Growth",   "value": 48,  "type": "positive"},
        {"label": "Annual Salary Raise", "value": 27,  "type": "positive"},
        {"label": "Bonus Accrual",      "value": 18,  "type": "positive"},
        {"label": "Attrition Savings",  "value": -22, "type": "negative"},
        {"label": "AI Automation",      "value": -14, "type": "negative"},
        {"label": "Restructuring Cost", "value": 11,  "type": "positive"},
        {"label": "FY2024 Total",       "value": 380, "type": "total"}
      ]
    }
  },
  "footer": {"source": "HR Analytics, Finance Q4 2024", "page": 10}
},

# ── 11. Table + Donut (narrow table — 8 cols) ─────────────────────────────────
{
  "slide_type": "content",
  "header": {"kicker": "STRESS 11", "headline": "Country Risk Scores vs Portfolio Geographic Mix"},
  "layout": "two-column",
  "content": {
    "left": {
      "type": "table",
      "headers": ["Country", "Political Risk", "Credit Rating", "FX Volatility", "Inflation Rate", "GDP Growth", "Market Score", "Allocation"],
      "rows": [
        ["United States", "Low",    "AAA", "Low",    "3.1%", "+2.8%", "9.2/10", "34%"],
        ["Germany",       "Low",    "AAA", "Medium", "2.4%", "+1.2%", "8.7/10", "18%"],
        ["United Kingdom","Medium", "AA",  "Medium", "3.8%", "+1.4%", "7.9/10", "12%"],
        ["Japan",         "Low",    "A+",  "Low",    "2.9%", "+1.1%", "7.6/10", "10%"],
        ["Brazil",        "High",   "BB-", "High",   "4.6%", "+3.1%", "5.4/10", "8%"],
        ["India",         "Medium", "BBB-","Medium", "5.1%", "+6.8%", "7.1/10", "11%"],
        ["Australia",     "Low",    "AAA", "Medium", "3.3%", "+2.2%", "8.9/10", "7%"]
      ],
      "highlight_col": 7
    },
    "right": {
      "type": "donut-chart",
      "center_text": "7",
      "center_label": "Markets",
      "show_legend": True,
      "segments": [
        {"label": "United States", "value": 34},
        {"label": "Germany",       "value": 18},
        {"label": "India",         "value": 11},
        {"label": "UK",            "value": 12},
        {"label": "Japan",         "value": 10},
        {"label": "Brazil",        "value": 8},
        {"label": "Australia",     "value": 7}
      ]
    }
  },
  "footer": {"source": "Moody's, World Bank, Internal Risk Model", "page": 11}
},

]

# ── Deck wrapper ───────────────────────────────────────────────────────────────
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
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 20px; height: 44px;
    background: #1a1a1a; border-bottom: 1px solid #333; flex-shrink: 0;
}
#topbar h1 { font-size: 13px; font-weight: 600; color: #fff; }
#counter   { font-size: 12px; color: #888; }
#stage {
    flex: 1; display: flex; align-items: center; justify-content: center;
    position: relative; overflow: hidden;
}
.slide-frame {
    display: none; width: 1280px; height: 720px;
    border: none; box-shadow: 0 8px 40px rgba(0,0,0,0.6);
    border-radius: 4px; transform-origin: center center;
}
.slide-frame.active { display: block; }
#bottombar {
    display: flex; align-items: center; justify-content: center; gap: 16px;
    height: 52px; background: #1a1a1a; border-top: 1px solid #333; flex-shrink: 0;
}
.nav-btn {
    background: #2a2a2a; color: #ccc; border: 1px solid #444;
    border-radius: 6px; padding: 7px 20px; font-size: 13px; cursor: pointer;
}
.nav-btn:hover { background: #3a3a3a; color: #fff; }
.nav-btn:disabled { opacity: 0.3; cursor: default; }
#dots { display: flex; gap: 6px; align-items: center; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: #444; cursor: pointer; }
.dot.active { background: #00677F; }
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
    const sw = stage.clientWidth  - 40, sh = stage.clientHeight - 40;
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
scaleFrames(); goto(0);
"""


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def _escape_srcdoc(html: str) -> str:
    return html.replace("&", "&amp;").replace('"', "&quot;")


def build_deck(specs: list[dict]) -> str:
    n = len(specs)
    frames = []
    for i, spec in enumerate(specs):
        try:
            html = render_slide(spec)
        except Exception as exc:
            html = f"<html><body style='display:flex;align-items:center;justify-content:center;height:720px;font-family:sans-serif;'><div style='color:#999;text-align:center;'><b>Slide {i+1} failed</b><br><code>{str(exc)[:200]}</code></div></body></html>"
        frames.append(
            f'<iframe class="slide-frame" srcdoc="{_escape_srcdoc(html)}" sandbox="allow-same-origin"></iframe>'
        )

    dots = "\n".join(f'<div class="dot" title="Slide {i+1}"></div>' for i in range(n))

    return textwrap.dedent(f"""\
        <!DOCTYPE html><html lang="en"><head>
        <meta charset="UTF-8">
        <title>Two-Column Stress Test</title>
        <style>{DECK_CSS}</style>
        </head><body>
        <div id="topbar">
          <h1>Two-Column Combined Layout Stress Test — 11 Scenarios</h1>
          <span id="counter">1 / {n}</span>
        </div>
        <div id="stage">
        {"".join(frames)}
        </div>
        <div id="bottombar">
          <button class="nav-btn" id="prevBtn">&larr; Prev</button>
          <div id="dots">{dots}</div>
          <button class="nav-btn" id="nextBtn">Next &rarr;</button>
        </div>
        <script>{DECK_JS}</script>
        </body></html>
    """)


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    deck_html = build_deck(SLIDES)
    OUT.write_text(deck_html, encoding="utf-8")
    print(f"Stress test deck: {OUT}")
    print(f"Open: file:///{OUT.as_posix()}")
