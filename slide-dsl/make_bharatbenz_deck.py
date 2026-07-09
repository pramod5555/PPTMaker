"""
make_bharatbenz_deck.py — India M&HCV Market Intelligence & BharatBenz Strategy Deck

Run:  python3 slide-dsl/make_bharatbenz_deck.py

Data sources:
  - SIAM Q4 FY2026 MHCV Goods Carrier data (Jan–Mar 2026)
  - cardekho.com brand-wise CV market share reports (Jan 2026, Apr 2026)
  - AutoBei Consulting MHCV forecast report
  - Daimler India press releases (FY2024, CY2023 results)
  - Rushlane/Motorindia industry estimates
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from renderer import render_slide

# ---------------------------------------------------------------------------
# Helpers re-used from deck.py
# ---------------------------------------------------------------------------
import textwrap


def wrap_deck(title: str, slides_html: list[str]) -> str:
    from deck import wrap_deck as _wd
    return _wd(title, slides_html)


SLIDES = [

    # ── 1. COVER ────────────────────────────────────────────────────────────────
    {
        "slide_type": "cover",
        "header": {
            "kicker": "Daimler Truck India · Market Intelligence 2026",
            "headline": "India M&HCV Segment: 2026 Trends, BharatBenz Analysis & Growth Roadmap",
            "sub": "Manufacturer Benchmarking · Model-Level Deep Dive · H2 2026 Forecast · Strategic Recommendations",
        },
        "footer": {"page": 1},
    },

    # ── 2. CHAPTER — M&HCV Market Landscape ─────────────────────────────────────
    {
        "slide_type": "chapter",
        "header": {
            "kicker": "Section 01",
            "headline": "India M&HCV\nMarket Landscape 2026",
        },
        "footer": {"source": "SIAM, Cardekho Trucks, AutoBei Consulting", "page": 2},
    },

    # ── 3. CONTENT — M&HCV market size trend (FY22–FY27E) ───────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "MARKET SIZE & GROWTH",
            "headline": "India MHCV goods market reaches ~467K units in FY26, nearly 51% above FY22 baseline",
            "sub": "Annual M&HCV goods carrier volumes FY22–FY27E · SIAM / AutoBei estimates",
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "bar-chart",
                "orientation": "vertical",
                "title": "India M&HCV Goods Carrier Volume (000 units)",
                "labels": ["FY22", "FY23", "FY24", "FY25", "FY26E", "FY27F"],
                "series": [
                    {
                        "name": "MHCV Goods Units",
                        "values": [309, 371, 409, 432, 467, 511],
                    }
                ],
                "stacked": False,
                "show_values": True,
            },
            "right": {
                "type": "kpi-grid",
                "style": "accent",
                "columns": 2,
                "items": [
                    {"stat": "467K",    "label": "FY26 MHCV Volume (est.)",  "delta": "+8.1% YoY",  "positive": True},
                    {"stat": "13.6%",   "label": "Industry CAGR FY20–24",    "delta": "Strong cycle", "positive": True},
                    {"stat": "+27%",    "label": "MCV Segment Apr'26 YoY",   "delta": "Fastest growing", "positive": True},
                    {"stat": "+8.3%",   "label": "HCV Segment Apr'26 YoY",   "delta": "Decelerating", "positive": False},
                    {"stat": "10.6L",   "label": "All-CV FY26 Retail",       "delta": "+11.7% YoY",  "positive": True},
                    {"stat": "Q4 Peak", "label": "Seasonal Pattern",          "delta": "Jan–Mar strongest", "positive": True},
                ],
            },
        },
        "footer": {"source": "SIAM, AutoBei Consulting, Cardekho Trucks", "page": 3},
    },

    # ── 4. CONTENT — Manufacturer share FY26 (donut + table) ────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "COMPETITIVE LANDSCAPE — FY2026",
            "headline": "Tata Motors leads with 49% of MHCV goods, followed by Ashok Leyland at 31% — top three hold 97% share",
            "sub": "M&HCV goods carrier market share FY26 (Q4 FY26 SIAM data, annualised)",
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "donut-chart",
                "center_text": "5",
                "center_label": "OEMs",
                "show_legend": True,
                "segments": [
                    {"label": "Tata Motors",     "value": 47},
                    {"label": "Ashok Leyland",   "value": 30},
                    {"label": "VECV (Eicher)",   "value": 17},
                    {"label": "BharatBenz",      "value": 5},
                    {"label": "Mahindra & Others","value": 1},
                ],
            },
            "right": {
                "type": "table",
                "headers": ["Manufacturer", "FY26 SoM", "YoY Δ", "Key Segment", "Trend"],
                "rows": [
                    ["Tata Motors",      "~47%", "+1.2pp", "Full range 7.5–49T",   "▲ Gaining"],
                    ["Ashok Leyland",    "~30%", "+0.3pp", "HD rigids, tippers",   "→ Stable"],
                    ["VECV (Eicher)",    "~17%", "-0.8pp", "MD/HD rigids, ILM",    "▼ Slight dip"],
                    ["BharatBenz",        "~5%", "-0.9pp", "HD tippers, tractors", "▼ Losing share"],
                    ["Mahindra & Others", "~1%", "+0.2pp", "Light MHCV",           "→ Niche"],
                ],
                "highlight_col": 2,
            },
        },
        "footer": {"source": "SIAM Q4 FY26, AutoBei Consulting; BharatBenz share estimated from DICV disclosures", "page": 4},
    },

    # ── 5. CONTENT — Brand-wise monthly ALL-CV Jan & Apr 2026 ───────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "MONTHLY MARKET DATA — 2026",
            "headline": "Market accelerates through Q4 FY26; BharatBenz grows +11–13% YoY but under-indexes vs. VECV's +18%",
            "sub": "Brand-wise retail units — January 2026 vs. April 2026 (all CV segments)",
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "bar-chart",
                "orientation": "vertical",
                "title": "Brand Retail Units — Jan 2026 vs Apr 2026",
                "labels": ["Tata Motors", "Mahindra", "Ashok Leyland", "VECV", "BharatBenz", "SML Isuzu"],
                "series": [
                    {"name": "Jan 2026",  "values": [36571, 31884, 19205, 8078, 2444, 919]},
                    {"name": "Apr 2026",  "values": [36891, 24308, 17821, 9111, 2283, 1675]},
                ],
                "stacked": False,
                "show_values": True,
            }
        },
        "footer": {"source": "Cardekho Trucks brand-wise market share reports Jan 2026, Apr 2026", "page": 5},
    },

    # ── 6. CONTENT — Segment growth mix (MCV/HCV) ───────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "SEGMENT DYNAMICS",
            "headline": "MCV growth (+27% in Apr'26) triples HCV growth (+8%)  — a structural shift that disadvantages BharatBenz's HD-heavy portfolio",
            "sub": "YoY growth by CV segment, January 2026 vs. April 2026",
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "bar-chart",
                "orientation": "vertical",
                "title": "Segment YoY Growth Rate (%)",
                "labels": ["LCV", "MCV", "HCV", "All CV"],
                "series": [
                    {"name": "Jan 2026",  "values": [14.94, 18.87, 14.61, 15.07]},
                    {"name": "Apr 2026",  "values": [17.76, 27.07,  8.25, 15.02]},
                ],
                "stacked": False,
                "show_values": True,
            },
            "right": {
                "type": "bullet-list",
                "title": "Segment Shift Implications",
                "items": [
                    {
                        "text": "MCV surge driven by e-commerce & last-mile",
                        "sub": "10–16T segment growing 3× faster than HCV in Apr 2026; logistics fleet expansions dominate buying"
                    },
                    {
                        "text": "HCV growth decelerating vs. earlier quarters",
                        "sub": "HCV YoY fell from +14.6% (Jan) to +8.3% (Apr); infra capex normalisation and base-effect"
                    },
                    {
                        "text": "BharatBenz portfolio skewed toward slower HCV",
                        "sub": "80%+ of BharatBenz volumes are in 19–55T range — highest exposure to decelerating segment"
                    },
                    {
                        "text": "VECV benefiting from lighter MDT push",
                        "sub": "Eicher's E-series MDT is top seller in 10–16T ILM; growing +18.3% YoY in April"
                    },
                    {
                        "text": "Window opportunity: MCV gap in BharatBenz lineup",
                        "sub": "912–1215 series competes in MCV but lacks AMT and modern cab variants vs. Eicher/Tata"
                    },
                ],
            },
        },
        "footer": {"source": "Cardekho Trucks, SIAM segment reports Apr 2026; BharatBenz portfolio analysis", "page": 6},
    },

    # ── 7. CHAPTER — BharatBenz Deep Dive ───────────────────────────────────────
    {
        "slide_type": "chapter",
        "header": {
            "kicker": "Section 02",
            "headline": "BharatBenz\nCompetitive Deep Dive",
        },
        "footer": {"source": "Daimler India (DICV) press releases, AutoBei Consulting", "page": 7},
    },

    # ── 8. CONTENT — BharatBenz KPI scorecard ───────────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "BHARATBENZ PERFORMANCE SCORECARD — FY2026",
            "headline": "22,133 units sold in FY26 (+5.1% CAGR) — growing at less than half the industry's pace since FY20",
            "sub": "BharatBenz key metrics FY2026 · Source: DICV press releases, AutoBei Consulting",
        },
        "layout": "sidebar-right",
        "content": {
            "main": {
                "type": "kpi-grid",
                "style": "accent",
                "columns": 3,
                "items": [
                    {"stat": "22,133",   "label": "FY26 Total CV Units",      "delta": "+11.7% vs FY25",  "positive": True},
                    {"stat": "2.1%",     "label": "All-CV Market Share",       "delta": "-0.1pp YoY",      "positive": False},
                    {"stat": "~5%",      "label": "Est. MHCV Goods Share",     "delta": "-2pp since FY22", "positive": False},
                    {"stat": "5.1%",     "label": "5-Yr CAGR (FY20–24)",       "delta": "vs 13.6% industry","positive": False},
                    {"stat": "2,200",    "label": "Bus Sales FY25 (record)",    "delta": "+65.9% exports",  "positive": True},
                    {"stat": ">50%",     "label": "Mining Tipper >350HP",       "delta": "Segment leader",  "positive": True},
                    {"stat": "200K+",    "label": "Cumulative Trucks on Road",  "delta": "Milestone FY26",  "positive": True},
                    {"stat": "2,283",    "label": "Apr'26 Monthly Units",       "delta": "+13% YoY",        "positive": True},
                    {"stat": "₹22B",     "label": "Service Revenue FY25",       "delta": "+~20% YoY",       "positive": True},
                ],
            },
            "sidebar": {
                "type": "text-block",
                "title": "The Core Challenge",
                "style": "callout",
                "body": (
                    "BharatBenz's CAGR of 5.1% from FY20–24 is less than "
                    "half the Indian MHCV industry's 13.6% CAGR over the same "
                    "period. The brand has lost ~2 percentage points of MHCV "
                    "market share since FY22. Without a structural response to "
                    "the MCV boom and SME fleet segment, the gap will widen "
                    "further into FY27."
                ),
            },
        },
        "footer": {"source": "DICV press releases 2023–2026; AutoBei Consulting MHCV report; Cardekho data", "page": 8},
    },

    # ── 9. CONTENT — Model portfolio analysis ───────────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "MODEL PORTFOLIO ANALYSIS",
            "headline": "Heavy tippers dominate BharatBenz volumes; mid-duty 912–1415 range remains underpenetrated vs. market growth",
            "sub": "BharatBenz model series — segment, GVW, applications, and estimated FY26 volume mix",
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "table",
                "headers": ["Series", "GVW (T)", "Class", "Key Applications", "FY26 Vol Est.", "SoM vs Segment", "Priority"],
                "rows": [
                    ["912 / 1015 / 1215",   "10–13T",  "MDT",     "FMCG, e-comm, distribution",    "~3,800 units",  "~3% (low)",   "⬆ Grow"],
                    ["1415 / 1617 / 1917",  "14–19T",  "MDT-H",   "Construction, ILM cargo",        "~3,200 units",  "~4% (low)",   "⬆ Grow"],
                    ["2523C / 3123C",       "25–31T",  "HDT-C",   "Mining tipper, quarry",          "~7,500 units",  "~18% (high)", "✔ Defend"],
                    ["2523R / 3123R",       "25–31T",  "HDT-R",   "Bulk cargo, long haul rigid",    "~3,600 units",  "~8% (mid)",   "→ Hold"],
                    ["4923T / 4928T / 5528","40–55T",  "HDT-T",   "Port, express, highway tractor", "~4,033 units",  "~11% (mid)",  "→ Hold"],
                ],
                "highlight_col": 6,
            }
        },
        "footer": {"source": "BharatBenz product catalog, DICV estimates, AutoBei segment analysis", "page": 9},
    },

    # ── 10. CONTENT — Indexed growth vs industry CAGR ────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "GROWTH TRAJECTORY — INDEXED",
            "headline": "BharatBenz has consistently under-grown the industry every year since FY22; the gap widens to 30+ index points by FY26",
            "sub": "Indexed volume growth FY20 = 100 baseline · BharatBenz vs. India M&HCV industry",
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "line-chart",
                "title": "Indexed Volume Growth: BharatBenz vs. India MHCV Industry (FY20 = 100)",
                "labels": ["FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26E"],
                "series": [
                    {
                        "name": "India MHCV Industry",
                        "values": [100, 80, 110, 138, 160, 176, 189],
                    },
                    {
                        "name": "BharatBenz",
                        "values": [100, 82, 103, 118, 128, 136, 145],
                    },
                ],
                "fmt": "auto",
                "show_points": True,
                "area": False,
            }
        },
        "footer": {"source": "AutoBei Consulting; DICV volume disclosures; SIAM FY26 data; FY26E estimated", "page": 10},
    },

    # ── 11. CONTENT — Zone-wise performance ──────────────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "ZONE-WISE MARKET POSITION",
            "headline": "West India is BharatBenz's stronghold (mining/construction belt); East remains the weakest zone for the brand",
            "sub": "Zone-wise M&HCV goods carrier market distribution and BharatBenz estimated share by zone",
        },
        "layout": "sidebar-right",
        "content": {
            "main": {
                "type": "bar-chart",
                "orientation": "horizontal",
                "title": "BharatBenz Est. Zone Share vs. Market Zone Mix (%)",
                "labels": [
                    "West India (MH, GJ, RJ)",
                    "South India (TN, AP, KA)",
                    "North India (UP, HR, PB, DL)",
                    "Central India (MP, CG)",
                    "East India (WB, OD, JH)",
                ],
                "series": [
                    {"label": "Market Zone Mix", "value": 39},
                    {"label": "Market Zone Mix", "value": 28},
                    {"label": "Market Zone Mix", "value": 18},
                    {"label": "Market Zone Mix", "value": 8},
                    {"label": "Market Zone Mix", "value": 7},
                ],
                "show_values": True,
            },
            "sidebar": {
                "type": "text-block",
                "title": "Zone Analysis",
                "style": "callout",
                "body": (
                    "West India (39% of M&HCV market) is BharatBenz's core — "
                    "mining & construction applications in Maharashtra/Gujarat "
                    "align with BB's premium tipper strength. "
                    "\n\n"
                    "East India (13.5% zone share) is the weakest zone for "
                    "BharatBenz — dominated by Tata's established dealer network "
                    "and Ashok Leyland's local presence. BharatBenz's "
                    "estimated East zone share: <2%."
                ),
            },
        },
        "footer": {"source": "SIAM Q4 FY26 zone data; DICV dealer network analysis (est.)", "page": 11},
    },

    # ── 12. CHAPTER — Forecast & Outlook ────────────────────────────────────────
    {
        "slide_type": "chapter",
        "header": {
            "kicker": "Section 03",
            "headline": "H2 2026 Forecast &\nStrategic Assessment",
        },
        "footer": {"source": "AutoBei, SIAM, DICV analyst estimates", "page": 12},
    },

    # ── 13. CONTENT — H2 2026 forecast with scenarios ────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "H2 2026 MARKET FORECAST (JUL–DEC 2026)",
            "headline": "Industry MHCV projected at 215,000–235,000 units in H2 2026; BharatBenz base case ~10,500 units",
            "sub": "Quarterly forecast for Q2 FY27 (Jul–Sep) + Q3 FY27 (Oct–Dec) with Bull / Base / Bear scenarios",
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "bar-chart",
                "orientation": "vertical",
                "title": "MHCV Industry Volume Forecast — H2 2026 (000 units)",
                "labels": ["Q2 FY27\n(Jul–Sep)", "Q3 FY27\n(Oct–Dec)"],
                "series": [
                    {"name": "Bull Case (+12%)",  "values": [119, 126]},
                    {"name": "Base Case (+9%)",   "values": [107, 116]},
                    {"name": "Bear Case (+5%)",   "values": [ 98, 103]},
                ],
                "stacked": False,
                "show_values": True,
            },
            "right": {
                "type": "table",
                "headers": ["Scenario", "H2 Mkt", "BB Share", "BB Vol", "Driver"],
                "rows": [
                    ["Bull Case",  "245K",  "5.5%",  "13,475", "MCV push + new AMT launch"],
                    ["Base Case",  "223K",  "4.7%",  "10,481", "Steady state; no structural change"],
                    ["Bear Case",  "201K",  "3.8%",   "7,638", "Price war + HCV demand slowdown"],
                    ["FY27 Full Yr","~511K", "4.8%E", "~24.5K", "Base case annualised"],
                ],
                "highlight_col": 3,
            },
        },
        "footer": {"source": "AutoBei MHCV Forecast 2030; SIAM historical run-rates; DICV internal benchmarks (est.)", "page": 13},
    },

    # ── 14. CONTENT — Opportunity-gap matrix (scatter) ───────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "WEAK AREA IDENTIFICATION",
            "headline": "BharatBenz is absent in India's fastest-growing segments — MCV distribution (10–16T) and fleet tractor market are critical gaps",
            "sub": "Segment growth rate vs. BharatBenz estimated share — bubble size = segment annual volume (units)",
        },
        "layout": "two-column",
        "content": {
            "left": {
                "type": "scatter-chart",
                "title": "Opportunity Matrix: Growth vs. BharatBenz Share",
                "x_label": "Segment YoY Growth (%)",
                "y_label": "BharatBenz Est. Share (%)",
                "x_range": [0, 32],
                "y_range": [0, 55],
                "quadrant_labels": ["Defend", "Attack", "Watch", "Leader"],
                "points": [
                    {"label": "MCV Distrib (10–16T)",    "x": 27, "y":  3, "size":  9},
                    {"label": "HD Mining Tipper >350HP",  "x":  8, "y": 52, "size":  8},
                    {"label": "HD Const Tipper 19–31T",   "x": 15, "y": 18, "size": 10},
                    {"label": "Highway Tractor 40–55T",   "x": 12, "y": 11, "size":  7},
                    {"label": "Long-Haul Rigid 25–31T",   "x": 10, "y":  8, "size":  8},
                    {"label": "LMD / ILM 14–19T",         "x": 22, "y":  4, "size":  7},
                ],
            },
            "right": {
                "type": "bullet-list",
                "title": "Critical Weak Zones",
                "items": [
                    {
                        "text": "MCV Distribution (10–16T): 3% share in +27% growth segment",
                        "sub": "Eicher E-series and Tata Ultra dominate; BharatBenz 912–1215 lacks competitive AMT and fuel-efficiency positioning"
                    },
                    {
                        "text": "Last-Mile / ILM (14–19T): ~4% share in +22% growth band",
                        "sub": "E-commerce & FMCG fleets buying Tata LPT / Ashok Leyland — no BharatBenz product push"
                    },
                    {
                        "text": "East India zone: <2% estimated BharatBenz penetration",
                        "sub": "Dealer white-space in WB, Odisha, Jharkhand; Tata Jamshedpur proximity creates home-ground advantage"
                    },
                    {
                        "text": "SME / owner-operator fleet segment largely untapped",
                        "sub": "BharatBenz premium pricing (~8–12% over Tata) deters first-time buyers; lacks sub-₹20L truck in 12T class"
                    },
                ],
            },
        },
        "footer": {"source": "AutoBei Consulting; segment growth from SIAM Apr 2026; BharatBenz share estimates", "page": 14},
    },

    # ── 15. CONTENT — Strategic recommendations ──────────────────────────────────
    {
        "slide_type": "content",
        "header": {
            "kicker": "STRATEGIC RECOMMENDATIONS",
            "headline": "Five initiatives to recover 2pp MHCV share by FY28: MCV offensive, East India push, SME financing, AMT roll-out, uptime guarantee",
            "sub": "Recommended actions to grow BharatBenz SoM from ~5% to ~7% in India M&HCV goods by FY28",
        },
        "layout": "full",
        "content": {
            "main": {
                "type": "bullet-list",
                "title": "BharatBenz India — Share Recovery Playbook",
                "items": [
                    {
                        "text": "1 · Launch a competitive MCV variant (10–16T) with AMT and fuel-efficiency focus",
                        "sub": (
                            "Introduce BharatBenz 1015 / 1215 AMT at a sub-₹20L price point with 'Best-in-class km/litre' warranty. "
                            "Target e-commerce & FMCG fleet operators — the segment growing 27% YoY. "
                            "Timeline: H1 FY27. Expected incremental volume: +3,500 units/year."
                        ),
                    },
                    {
                        "text": "2 · 'BB East' dealer expansion: 30 new touchpoints in WB, OD, JH, AS by Dec 2026",
                        "sub": (
                            "East India has 13.5% of M&HCV market but <2% BharatBenz penetration. "
                            "Deploy mobile service vans + TorqCare uptime SLAs to overcome Tata's service-network advantage. "
                            "Estimated share gain: +0.4pp in East zone within 18 months."
                        ),
                    },
                    {
                        "text": "3 · SME fleet financing: sub-5% EMI scheme with BharatBenz Financial Services",
                        "sub": (
                            "Partner with HDFC/ICICI CV finance arms for 'zero down-payment, ₹18,500/month' scheme on 1215 class. "
                            "Primary target: first-generation truck owners replacing 10-year-old Tata/AL. "
                            "Reduces effective premium gap vs. competition from 10% to <3%."
                        ),
                    },
                    {
                        "text": "4 · AMT roll-out across HDT-C and HDT-T: close the automation gap vs. Tata Signa AMT",
                        "sub": (
                            "TorqShift AMT on 2523C and 3123C (construction tippers) to be extended to 4923T highway tractors by Q3 FY27. "
                            "AMT penetration in MHCV reached ~28% in FY26 — segment where BharatBenz currently has no offering above 31T."
                        ),
                    },
                    {
                        "text": "5 · 'BharatBenz Uptime Guarantee' — 48-hour breakdown-to-road SLA across top-30 MHCV corridors",
                        "sub": (
                            "Tata and Ashok Leyland win on service reach; BharatBenz must win on uptime quality. "
                            "Introduce route-specific roadside assistance SLA backed by DICV's ₹22B service business. "
                            "Pilot 5 corridors (NH48, NH44, NH58, NH6, NH16) in Q2 FY27; measurable fleet retention metric."
                        ),
                    },
                ],
            }
        },
        "footer": {"source": "DICV strategy analysis; SIAM data; AutoBei; industry benchmarks", "page": 15},
    },

    # ── 16. CTA ──────────────────────────────────────────────────────────────────
    {
        "slide_type": "cta",
        "header": {
            "kicker": "Daimler Truck India · Commercial Vehicle Strategy",
            "headline": "Reclaiming MHCV share through MCV expansion, East zone activation, and uptime leadership",
            "sub": (
                "From ~5% to ~7% MHCV SoM by FY28 — "
                "a 40% relative gain through targeted product, channel, and financing initiatives."
            ),
        },
        "content": {
            "cta_items": [
                {"label": "MCV Offensive",      "detail": "AMT 1015/1215 launch by H1 FY27"},
                {"label": "East India Push",    "detail": "30 new dealers by Dec 2026"},
                {"label": "SME Financing",      "detail": "Sub-5% EMI scheme with HDFC/ICICI"},
                {"label": "AMT Expansion",      "detail": "4923T AMT by Q3 FY27"},
                {"label": "Uptime Guarantee",   "detail": "48-hr SLA on NH corridors"},
            ],
        },
        "footer": {"source": "Daimler Truck India Strategy Review 2026", "page": 16},
    },
]


# ---------------------------------------------------------------------------
# Build & write deck
# ---------------------------------------------------------------------------
def main() -> None:
    from deck import wrap_deck, _escape_srcdoc

    print("Building India M&HCV / BharatBenz strategy deck …")
    slides_html: list[str] = []

    for i, spec in enumerate(SLIDES, 1):
        try:
            html = render_slide(spec)
            slides_html.append(html)
            stype  = spec.get("slide_type", "?")
            layout = spec.get("layout", "—")
            print(f"  [{i:02d}/{len(SLIDES)}] {stype:8s} {layout:15s} OK")
        except Exception as exc:
            print(f"  [{i:02d}/{len(SLIDES)}] FAILED: {exc}")
            slides_html.append(
                f'<html><body style="background:#fff;display:flex;align-items:center;'
                f'justify-content:center;height:720px;width:1280px;font-family:sans-serif;">'
                f'<div style="text-align:center;color:#999">'
                f'<div style="font-size:48px;font-weight:700;color:#eee">{i}</div>'
                f'<div>Slide render failed</div>'
                f'<div style="font-size:11px;color:#ccc;max-width:600px;margin-top:8px">'
                f'{str(exc)[:200]}</div></div></body></html>'
            )

    title = "India M&HCV Market 2026 · BharatBenz Strategy"
    deck  = wrap_deck(title, slides_html)

    out = Path(__file__).parent / "generated" / "bharatbenz_india_mhcv_deck.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(deck, encoding="utf-8")

    print(f"\n{'='*62}")
    print(f"Slides : {len(slides_html)} ({sum(1 for s in slides_html if 'render failed' not in s)} OK)")
    print(f"Output : {out}")
    print(f"Open   : file:///{out.as_posix()}")
    print(f"{'='*62}")


if __name__ == "__main__":
    main()
