"""synthesize.py — Generate synthetic DSL training pairs for underrepresented block types.

Targets 900+ pairs covering missing combinations:
  kpi-grid+bar, kpi-grid+line, kpi-grid+donut, waterfall, gantt,
  scatter, comparison-matrix, process+kpi, three-column mixes, etc.

Run:
    python slide-dsl/synthesize.py                  # generates ~900 pairs
    python slide-dsl/synthesize.py --validate       # render-test every spec
    python slide-dsl/synthesize.py --preview 5      # print 5 samples
"""

from __future__ import annotations
import argparse
import json
import math
import random
import sys
from pathlib import Path

ROOT    = Path(__file__).parent.parent
OUT_DIR = Path(__file__).parent / "dsl_finetune"

random.seed(42)

# ── Shared system prompt (must match build_dsl_dataset.py / generate.py) ──────
SYSTEM_PROMPT = """\
You are a consulting slide generator. Given a plain-English description, return a JSON spec \
for a 1280×720 slide following the schema below. Return ONLY valid JSON — no markdown, no commentary.

SCHEMA:
{
  "slide_type": "cover | chapter | content | cta",
  "header": { "kicker": "", "headline": "", "sub": "" },
  "layout": "full | two-column | three-column | sidebar-right | sidebar-left",
  "content": { "main|left|right|center|sidebar": <BLOCK> },
  "footer": { "source": "", "page": 0 }
}

BLOCKS:
  bar-chart:          { "type":"bar-chart", "orientation":"vertical|horizontal",
                        "series":[{"label":"","value":0}],
                        "series":[{"name":"","values":[]}], "labels":[],
                        "stacked":false, "fmt":"auto|percent|currency", "show_values":true, "title":"" }
  line-chart:         { "type":"line-chart", "labels":[], "series":[{"name":"","values":[]}],
                        "fmt":"auto|decimal|percent", "show_points":true, "area":false, "title":"" }
  scatter-chart:      { "type":"scatter-chart", "points":[{"label":"","x":0,"y":0,"size":6}],
                        "x_label":"", "y_label":"", "x_range":[0,100], "y_range":[0,100],
                        "quadrant_labels":["TL","TR","BL","BR"], "title":"" }
  donut-chart:        { "type":"donut-chart", "segments":[{"label":"","value":0}],
                        "center_text":"", "center_label":"", "show_legend":true }
  kpi-grid:           { "type":"kpi-grid", "columns":2, "style":"default|accent|compact|borderless",
                        "items":[{"stat":"","label":"","delta":"","positive":null,"icon":""}] }
  bullet-list:        { "type":"bullet-list", "title":"", "items":[{"text":"","sub":""}] }
  table:              { "type":"table", "headers":[], "rows":[[]], "highlight_col":0 }
  text-block:         { "type":"text-block", "title":"", "body":"", "style":"default|callout|pull-quote" }
  comparison-matrix:  { "type":"comparison-matrix", "title":"",
                        "columns":["Option A","Option B"],
                        "rows":[{"label":"","values":["",""],"highlight":0}],
                        "style":"zebra|bordered|default" }
  gantt-chart:        { "type":"gantt-chart", "x_labels":[], "title":"",
                        "rows":[{"label":"","start":0.0,"end":1.0,"bar_label":""}],
                        "milestones":[{"label":"","at":0.0}] }
  waterfall-chart:    { "type":"waterfall-chart", "title":"", "fmt":"auto",
                        "bars":[{"label":"","value":0,"type":"start|positive|negative|total"}] }
  process-flow:       { "type":"process-flow", "direction":"horizontal|vertical",
                        "steps":[{"icon":"1","label":"","sub":""}] }

STYLE RULES:
- Consulting tone: precise, data-driven, no filler text.
- Kicker: short uppercase label (e.g. "Section 02", "Key Insight").
- Headline: declarative statement of the main finding.
- Sub: one-line context or methodology note.
- Footer source: citation in plain text."""

# ── Data pools ─────────────────────────────────────────────────────────────────
FUND_NAMES  = ["Summit Capital","Meridian Partners","Apex Private Equity","Vertex Capital",
               "Pinnacle Growth Fund","Alderton Equity","Blue Crest Partners","Harbor Hill Capital",
               "Crestview Advisors","Stonefield Partners","Lakewood Private Equity","Bridgeway Capital"]
COMPANIES   = ["NovaTech","PulseAI","ClearPath Systems","RapidScale","Orbis Platforms",
               "DataVault","Nexus Analytics","CloudBridge","Sentinel Health","Meridian Digital"]
BANKS       = ["First Continental Bank","Pacific Regional","Sterling Financial","Cascade Bank",
               "Northern Trust Corp","Heritage Bancorp","Atlas Financial Group"]
SECTORS     = ["Technology","Healthcare","Consumer","Industrials","Financial Services",
               "Energy","Real Estate","Infrastructure","Media","Business Services"]
GEOGRAPHIES = ["North America","Europe","Asia-Pacific","Latin America","Middle East & Africa"]
QUARTERS    = ["Q1 2022","Q2 2022","Q3 2022","Q4 2022",
               "Q1 2023","Q2 2023","Q3 2023","Q4 2023",
               "Q1 2024","Q2 2024","Q3 2024","Q4 2024"]
YEARS       = ["2019","2020","2021","2022","2023","2024"]
STRATEGIES  = ["Buyout","Growth Equity","Venture","Real Assets","Credit","Infrastructure"]

def _r(a, b):      return round(random.uniform(a, b), 1)
def _ri(a, b):     return random.randint(a, b)
def _rc(pool):     return random.choice(pool)
def _pct(v):       return f"{v:.1f}%"
def _bn(v):        return f"${v:.1f}B"
def _mn(v):        return f"${v:.0f}M"
def _x(v):         return f"{v:.1f}x"
def _delta(v, pos=None):
    sign = "+" if v >= 0 else ""
    if pos is None: pos = v >= 0
    return f"{sign}{v:.1f}%", pos

# ── Coherent company/fund profiles ─────────────────────────────────────────────
# Each profile pins all metrics to internally consistent values so the model
# learns that fund size → IRR range, revenue growth → margin profile, etc.

_FUND_PROFILES = [
    # (aum_B, irr, moic, cos, irr_target, new_cos)
    (4.2,  28.4, 2.6, 14, 20,  3),
    (2.8,  22.1, 2.1, 10, 18,  2),
    (11.3, 17.8, 1.9, 31,  16, 5),
    (6.8,  19.3, 2.0,  8,  18, 2),
    (18.5, 14.6, 1.7, 42,  14, 6),
    (3.2,  31.2, 3.1, 12,  22, 2),
    (8.5,  16.4, 1.8, 22,  15, 4),
    (1.4,  34.8, 3.4,  6,  25, 1),
    (24.0, 13.1, 1.6, 48,  12, 7),
    (5.6,  24.7, 2.4, 18,  20, 3),
    (0.9,  38.2, 3.8,  5,  28, 2),
    (14.2, 15.8, 1.8, 36,  15, 5),
]

# (rev_M, ebitda_margin, rev_growth, prior_rev_M, market_growth, headcount)
_COMPANY_PROFILES = [
    (268,  29.1, 37, 196, 12, 1420),
    (124,  18.4, 58,  78,  8,  680),
    (840,  24.8, 14, 737, 6, 4800),
    (312,  16.2, 68, 186, 22, 1860),
    (1240, 32.1,  9,1138,  5, 6200),
    ( 58,  11.3, 42,  41, 15,  320),
    (440,  28.6, 22, 361, 9, 2100),
    (186,  21.4, 31, 142, 11,  940),
    (620,  19.8, 18, 525, 7, 3100),
    ( 92,  14.7, 51,  61, 18,  480),
]

# (arr_M, nrr, growth, cac_K, gm, churn, months_payback)
_SAAS_PROFILES = [
    (124, 124, 58, 28,  82, 2.8, 11),
    (312, 118, 68, 42,  79, 3.4, 14),
    ( 48, 134, 94, 18,  86, 1.8,  8),
    (680, 112, 42, 65,  77, 4.1, 18),
    ( 22, 141,128, 12,  88, 1.2,  6),
    (186, 108, 34, 84,  74, 5.2, 22),
    ( 94, 128, 81, 22,  83, 2.1,  9),
    (450, 105, 28, 95,  71, 6.4, 28),
    ( 16, 138,145, 8,   91, 0.9,  4),
    (248, 121, 52, 38,  80, 3.0, 13),
]

# (deal_ev_M, ev_ebitda, irr_target, hold_yr, leverage)
_DEAL_PROFILES = [
    (420,  8.4, 26, 5.0, "4.2x"),
    (1850, 11.2, 19, 4.5, "5.1x"),
    (280,  7.8, 31, 4.0, "3.8x"),
    (680,  9.6, 22, 5.5, "4.6x"),
    (3200, 13.4, 16, 5.0, "5.8x"),
    (140,  6.2, 34, 3.5, "3.4x"),
    (920,  10.8, 20, 4.8, "4.9x"),
    (2400, 12.1, 17, 5.2, "5.4x"),
]

# (tam_B, cagr, pen_pct, players, pen_prior)
_MARKET_PROFILES = [
    (42,  18.4, 28, 12, 18),
    (8.6, 32.1, 14,  6,  7),
    (210, 9.2,  62, 18, 48),
    (3.2, 44.8,  8,  4,  3),
    (85,  14.6, 38, 22, 28),
    (18,  28.3, 21,  8, 12),
    (320, 7.1,  71, 31, 58),
    (6.4, 51.2, 11,  3,  5),
]

# ── Block generators ───────────────────────────────────────────────────────────

def _kpi_fund():
    p = _rc(_FUND_PROFILES)
    aum, irr, moic, cos, irr_target, new_cos = p
    d_aum = _r(8, 22)
    return {
        "type": "kpi-grid", "columns": 2,
        "items": [
            {"stat": _bn(aum),       "label": "Total AUM",          "delta": f"+{d_aum:.0f}% YoY", "positive": True},
            {"stat": _pct(irr),      "label": "Gross IRR",          "delta": f"+{irr-irr_target:.1f}pp vs. {irr_target}% target", "positive": irr > irr_target},
            {"stat": _x(moic),       "label": "Gross MOIC",         "delta": "Since inception",    "positive": None},
            {"stat": str(cos),       "label": "Portfolio Companies", "delta": f"{new_cos} new in {_rc(YEARS[-2:])}", "positive": True},
        ]
    }

def _kpi_company():
    p = _rc(_COMPANY_PROFILES)
    rev, margin, growth, prior_rev, mkt_growth, emp = p
    margin_delta = _r(0.8, 4.2)
    return {
        "type": "kpi-grid", "columns": 2,
        "items": [
            {"stat": _mn(rev),         "label": "Revenue (LTM)",   "delta": f"+{growth}% YoY vs. ${prior_rev:.0f}M",  "positive": True},
            {"stat": _pct(margin),     "label": "EBITDA Margin",   "delta": f"+{margin_delta:.1f}pp YoY",             "positive": True},
            {"stat": f"{growth}%",     "label": "Revenue Growth",  "delta": f"vs. {mkt_growth}% market CAGR",         "positive": growth > mkt_growth},
            {"stat": f"{emp:,}",       "label": "Employees",       "delta": f"+{_ri(40, max(41, int(emp*0.12)))} YoY", "positive": True},
        ]
    }

def _kpi_saas():
    p = _rc(_SAAS_PROFILES)
    arr, nrr, gr, cac, gm, churn, payback = p
    ltv_cac = round((gm / 100 * arr / (arr * churn / 100 + 0.01)) / (cac * 1000 / arr / 1000), 1)
    ltv_cac = max(2.5, min(ltv_cac, 12.0))  # realistic range
    return {
        "type": "kpi-grid", "columns": 2,
        "items": [
            {"stat": _mn(arr),        "label": "ARR",                    "delta": f"+{gr}% YoY",                  "positive": True},
            {"stat": _pct(nrr),       "label": "Net Revenue Retention",  "delta": f"{'+' if nrr>=110 else ''}{nrr-100:.0f}pp above 100%", "positive": nrr >= 110},
            {"stat": f"${cac}K",      "label": "CAC",                    "delta": f"{payback}-month payback",      "positive": payback <= 18},
            {"stat": f"{ltv_cac:.1f}x", "label": "LTV:CAC",             "delta": f">3x benchmark",                "positive": ltv_cac >= 3},
        ]
    }

def _kpi_market():
    p = _rc(_MARKET_PROFILES)
    size, cagr, pen, players, pen_prior = p
    horizon_start = _rc([2023, 2024, 2025])
    horizon_end   = horizon_start + _ri(5, 8)
    return {
        "type": "kpi-grid", "columns": 2,
        "items": [
            {"stat": _bn(size),    "label": "Total Addressable Market", "delta": f"{horizon_end}E projection", "positive": None},
            {"stat": _pct(cagr),   "label": "Market CAGR",    "delta": f"{horizon_start}–{horizon_end}E",     "positive": True},
            {"stat": _pct(pen),    "label": "Digital Penetration", "delta": f"vs. {pen_prior}% in 2021",      "positive": True},
            {"stat": str(players), "label": "Active Players",  "delta": f"{_ri(1,3)} new entrants in {_rc(YEARS[-2:])}", "positive": False},
        ]
    }

def _kpi_deal():
    p = _rc(_DEAL_PROFILES)
    ev, ev_ebitda, irr, hold, lev = p
    ebitda = round(ev / ev_ebitda)
    comps_mult = round(ev_ebitda - _r(0.8, 2.4), 1)
    exit_yr = 2024 + round(hold)
    return {
        "type": "kpi-grid", "columns": 2,
        "items": [
            {"stat": _mn(ev),         "label": "Enterprise Value",  "delta": f"EV/EBITDA {ev_ebitda:.1f}x", "positive": None},
            {"stat": f"{ev_ebitda:.1f}x","label": "EV / EBITDA",   "delta": f"vs. {comps_mult:.1f}x comps", "positive": None},
            {"stat": _pct(irr),       "label": "Target IRR",        "delta": "Base case",                    "positive": True},
            {"stat": f"{hold:.1f}yr", "label": "Hold Period",       "delta": f"Exit by {exit_yr}E",          "positive": None},
        ]
    }

KPI_GENERATORS = [_kpi_fund, _kpi_company, _kpi_saas, _kpi_market, _kpi_deal]

def _bar_quarterly():
    periods = _rc([QUARTERS[-8:], QUARTERS[-6:], QUARTERS[-4:]])
    metric  = _rc(["Deal Count","Capital Deployed ($M)","New Investments","Revenue ($M)","EBITDA ($M)"])
    lo, hi  = _rc([(3,18),(50,400),(200,1200),(2,15)])
    values  = [{"label": q, "value": _ri(lo, hi)} for q in periods]
    return {"type":"bar-chart","orientation":"vertical","series":values,
            "fmt": "auto","show_values":True,"title":metric}, metric, periods

def _bar_by_sector():
    secs = random.sample(SECTORS, _ri(5, 7))
    lo, hi = _rc([(5,40),(50,500),(10,120),(1,15)])
    values = [{"label": s, "value": _ri(lo, hi)} for s in secs]
    metric = _rc(["Portfolio Allocation (%)","Deal Count","Capital Deployed ($B)","Revenue Mix (%)"])
    return {"type":"bar-chart","orientation":"horizontal","series":values,
            "fmt": "percent" if "%" in metric else "auto","show_values":True,"title":metric}, metric

def _bar_multi_strategy():
    strats  = random.sample(STRATEGIES, _ri(3,5))
    periods = random.sample(YEARS[-4:], _ri(3,4))
    lo, hi  = (1, 15)
    series  = [{"name": p, "values": [_ri(lo,hi) for _ in strats]} for p in periods]
    return {"type":"bar-chart","orientation":"vertical","series":series,
            "labels": strats,"stacked":False,"fmt":"auto","show_values":True,
            "title":"Fundraising by Strategy ($B)"}, strats

def _bar_yoy_comparison():
    cats  = random.sample(["Q1","Q2","Q3","Q4"], 4)
    yr1, yr2 = _rc(YEARS[-4:-1]), _rc(YEARS[-3:])
    lo, hi = (30, 280)
    series = [{"name": yr1, "values": [_ri(lo,hi) for _ in cats]},
              {"name": yr2, "values": [_ri(lo,hi) for _ in cats]}]
    return {"type":"bar-chart","orientation":"vertical","series":series,
            "labels":cats,"stacked":False,"fmt":"auto","show_values":True,
            "title":f"{yr1} vs. {yr2} Performance"}, yr1, yr2

def _line_trend():
    periods = random.sample(QUARTERS, _ri(6, 10))
    n_series = _ri(1, 3)
    names = random.sample(["AUM ($B)","Revenue ($M)","EBITDA ($M)","Net Income ($M)",
                            "ARR ($M)","NRR (%)","Margin (%)","Utilization (%)"], n_series)
    lo_hi = [(1,50),(50,800),(5,40),(15,65)]
    series = []
    for name in names:
        lo, hi = _rc(lo_hi)
        vals = sorted([_r(lo, hi) for _ in periods]) if random.random() > 0.3 else [_r(lo,hi) for _ in periods]
        series.append({"name": name, "values": [round(v,1) for v in vals]})
    return {"type":"line-chart","labels":periods,"series":series,
            "fmt":"auto","show_points":True,"area":False,"title":names[0]+" Trend"}, names

def _waterfall_ebitda():
    base   = _ri(80, 600)
    items  = [
        ("Prior Year EBITDA", base,           "start"),
        ("Volume Growth",     _ri(15, 120),   "positive"),
        ("Pricing",           _ri(5, 60),     "positive"),
        ("New Products",      _ri(5, 40),     "positive"),
        ("Cost Inflation",    -_ri(10, 80),   "negative"),
        ("FX Impact",         -_ri(5, 40),    "negative"),
        ("One-offs",          _rc([-_ri(5,30), _ri(5,20)]), "negative"),
    ]
    total = base + sum(v for _, v, t in items if t != "start")
    items.append(("Current Year EBITDA", round(total), "total"))
    bars  = [{"label": l, "value": abs(v) if t == "negative" else v, "type": t}
             for l, v, t in items]
    # Fix negative bars
    bars2 = []
    for b in bars:
        orig = next(v for l,v,t in items if l==b["label"])
        bars2.append({"label": b["label"], "value": orig, "type": b["type"]})
    return {"type":"waterfall-chart","title":"EBITDA Bridge ($M)","fmt":"auto","bars":bars2}

def _waterfall_aum():
    opening = _ri(3000, 25000)
    contrib  = _ri(500, 4000)
    distrib  = -_ri(300, 2000)
    apprecn  = _ri(100, 3000)
    fees     = -_ri(50, 300)
    fx       = _rc([-_ri(100,500), _ri(100,500)])
    closing  = opening + contrib + distrib + apprecn + fees + fx
    bars = [
        {"label": "Opening AUM",    "value": opening,  "type": "start"},
        {"label": "New Commitments","value": contrib,   "type": "positive"},
        {"label": "Distributions",  "value": distrib,   "type": "negative"},
        {"label": "Appreciation",   "value": apprecn,   "type": "positive"},
        {"label": "Fees & Expenses","value": fees,       "type": "negative"},
        {"label": "FX / Other",     "value": fx,         "type": "positive" if fx >= 0 else "negative"},
        {"label": "Closing AUM",    "value": closing,   "type": "total"},
    ]
    return {"type":"waterfall-chart","title":"AUM Bridge ($M)","fmt":"auto","bars":bars}

def _waterfall_revenue():
    base   = _ri(200, 2000)
    organic = _ri(20, 300)
    acq     = _ri(0, 200)
    price   = _ri(10, 150)
    churn   = -_ri(10, 100)
    fx      = _rc([-_ri(10,80), _ri(10,60)])
    total   = base + organic + acq + price + churn + fx
    bars = [
        {"label": "Prior Year Revenue", "value": base,    "type": "start"},
        {"label": "Organic Growth",     "value": organic, "type": "positive"},
        {"label": "Acquisitions",       "value": acq,     "type": "positive"},
        {"label": "Pricing",            "value": price,   "type": "positive"},
        {"label": "Churn / Attrition",  "value": churn,   "type": "negative"},
        {"label": "FX Impact",          "value": fx,      "type": "positive" if fx >= 0 else "negative"},
        {"label": "Current Revenue",    "value": total,   "type": "total"},
    ]
    return {"type":"waterfall-chart","title":"Revenue Bridge ($M)","fmt":"auto","bars":bars}

def _gantt_ma():
    n_months = _ri(10, 16)
    months   = [f"M{i+1}" for i in range(n_months)]
    rows = [
        {"label": "Preliminary Due Diligence", "start": 0/n_months, "end": 2/n_months, "bar_label": "8 weeks"},
        {"label": "Management Presentations",  "start": 1/n_months, "end": 3/n_months, "bar_label": "4 weeks"},
        {"label": "Confirmatory Due Diligence","start": 2/n_months, "end": 6/n_months, "bar_label": "16 weeks"},
        {"label": "Financing & Structuring",   "start": 4/n_months, "end": 8/n_months, "bar_label": "10 weeks"},
        {"label": "Regulatory Approvals",      "start": 6/n_months, "end": 10/n_months,"bar_label": "8–12 weeks"},
        {"label": "Legal Documentation",       "start": 8/n_months, "end": 11/n_months,"bar_label": "6 weeks"},
        {"label": "Close & Integration",       "start": 10/n_months,"end": 1.0,         "bar_label": "Ongoing"},
    ]
    milestones = [
        {"label": "LOI Signed",        "at": 1/n_months},
        {"label": "SPA Executed",      "at": 9/n_months},
        {"label": "Deal Close",        "at": 11/n_months},
    ]
    return {"type":"gantt-chart","x_labels":months,"title":"M&A Transaction Timeline","rows":rows,"milestones":milestones}

def _gantt_transformation():
    phases_n = _ri(18, 30)
    labels   = [f"Q{i//3+1} {2024 + i//12}" if i % 3 == 0 else "" for i in range(0, phases_n, 3)]
    labels   = [f"Q{i+1} {'2024' if i<4 else '2025' if i<8 else '2026'}" for i in range(phases_n//3)]
    n_labels = len(labels)
    rows = [
        {"label": "Foundation & Assessment",   "start": 0/n_labels, "end": 2/n_labels,  "bar_label": "6 months"},
        {"label": "Technology Architecture",   "start": 1/n_labels, "end": 4/n_labels,  "bar_label": "9 months"},
        {"label": "Process Re-engineering",    "start": 2/n_labels, "end": 6/n_labels,  "bar_label": "12 months"},
        {"label": "Talent & Change Mgmt",      "start": 3/n_labels, "end": 7/n_labels,  "bar_label": "12 months"},
        {"label": "Pilot & Scale",             "start": 5/n_labels, "end": 9/n_labels,  "bar_label": "12 months"},
        {"label": "Full Deployment",           "start": 8/n_labels, "end": 1.0,          "bar_label": "Ongoing"},
    ]
    milestones = [
        {"label": "Kick-off",   "at": 0},
        {"label": "Go-live v1", "at": 5/n_labels},
        {"label": "Full scale", "at": 9/n_labels},
    ]
    return {"type":"gantt-chart","x_labels":labels,"title":"Digital Transformation Roadmap","rows":rows,"milestones":milestones}

def _gantt_fund_launch():
    labels = ["M1","M2","M3","M4","M5","M6","M7","M8","M9","M10","M11","M12"]
    rows = [
        {"label": "Strategy Finalisation",    "start": 0/12, "end": 2/12,  "bar_label": "8 weeks"},
        {"label": "Legal & Structuring",       "start": 1/12, "end": 5/12,  "bar_label": "4 months"},
        {"label": "LP Roadshow",               "start": 3/12, "end": 7/12,  "bar_label": "4 months"},
        {"label": "First Close",               "start": 6/12, "end": 7/12,  "bar_label": "Target"},
        {"label": "Investor Reporting Setup",  "start": 5/12, "end": 8/12,  "bar_label": "3 months"},
        {"label": "Final Close",               "start": 9/12, "end": 10/12, "bar_label": "Target"},
        {"label": "First Deployment",          "start": 7/12, "end": 1.0,   "bar_label": "Ongoing"},
    ]
    milestones = [
        {"label": "First Close", "at": 6.5/12},
        {"label": "Final Close", "at": 9.5/12},
    ]
    return {"type":"gantt-chart","x_labels":labels,"title":"Fund Launch Timeline","rows":rows,"milestones":milestones}

def _scatter_portfolio():
    cos = random.sample(COMPANIES + ["AlphaCore","BetaWorks","GammaTech","DeltaOps",
                                      "EpsilonAI","ZetaSoft","EtaHealth","ThetaRetail"], _ri(8,14))
    lo_x, hi_x = (5, 45)  # revenue growth %
    lo_y, hi_y = (5, 42)  # EBITDA margin %
    pts = [{"label": c, "x": _r(lo_x,hi_x), "y": _r(lo_y,hi_y), "size": _ri(5,12)} for c in cos]
    xm  = math.ceil(max(p["x"] for p in pts) / 10) * 10
    ym  = math.ceil(max(p["y"] for p in pts) / 10) * 10
    return {"type":"scatter-chart","points":pts,
            "x_label":"Revenue Growth (%)","y_label":"EBITDA Margin (%)",
            "x_range":[0,xm],"y_range":[0,ym],
            "quadrant_labels":["Mature\nProfitable","Stars","Underperformers","Growth\nInvest"],
            "title":"Portfolio Company Positioning"}

def _scatter_risk_return():
    assets = ["Global Equities","Private Equity","Real Estate","Infrastructure",
              "Private Credit","High Yield","Investment Grade","Cash"]
    pts = [{"label":a,"x":_r(5,35),"y":_r(3,22),"size":_ri(5,10)} for a in assets]
    return {"type":"scatter-chart","points":pts,
            "x_label":"Risk (Volatility %)","y_label":"Expected Return (%)",
            "x_range":[0,40],"y_range":[0,25],
            "quadrant_labels":["Low Risk\nLow Return","High Risk\nLow Return",
                               "Low Risk\nHigh Return","High Risk\nHigh Return"],
            "title":"Risk-Return by Asset Class"}

def _donut_allocation():
    items = _rc([
        [("Buyout",45),("Growth Equity",25),("Venture",15),("Credit",15)],
        [("North America",48),("Europe",30),("Asia-Pacific",18),("Rest of World",4)],
        [("Technology",35),("Healthcare",22),("Consumer",18),("Industrials",15),("Other",10)],
        [("Equity",55),("Subordinated Debt",25),("Senior Debt",20)],
        [("Contracted",60),("Regulated",25),("Merchant",15)],
    ])
    segs   = [{"label": l, "value": v} for l, v in items]
    total  = sum(v for _, v in items)
    label0 = items[0][0].split()[0]
    return {"type":"donut-chart","segments":segs,
            "center_text":f"{items[0][1]}%","center_label":label0,"show_legend":True}

def _process_investment():
    steps = [
        {"icon":"1","label":"Origination",     "sub":"Proprietary deal sourcing & screening"},
        {"icon":"2","label":"Initial Review",   "sub":"IC memo & preliminary valuation"},
        {"icon":"3","label":"Due Diligence",    "sub":"Commercial, financial & legal review"},
        {"icon":"4","label":"Investment Committee","sub":"Approval & final structuring"},
        {"icon":"5","label":"Execution",        "sub":"Documentation, close & funding"},
        {"icon":"6","label":"Value Creation",   "sub":"100-day plan & portfolio monitoring"},
    ]
    return {"type":"process-flow","direction":"horizontal","steps":steps[:_ri(4,6)]}

def _process_digital():
    steps = [
        {"icon":"1","label":"Assess",    "sub":"Digital maturity & gap analysis"},
        {"icon":"2","label":"Design",    "sub":"Target operating model & architecture"},
        {"icon":"3","label":"Build",     "sub":"Agile development & integrations"},
        {"icon":"4","label":"Deploy",    "sub":"Phased rollout & change management"},
        {"icon":"5","label":"Scale",     "sub":"Continuous improvement & optimisation"},
    ]
    return {"type":"process-flow","direction":"horizontal","steps":steps[:_ri(4,5)]}

def _comparison_matrix():
    scenarios = _rc([
        {
            "cols": ["Status Quo","Organic Growth","M&A"],
            "rows": [
                {"label":"Revenue CAGR",    "values":["3–5%","8–12%","15–20%"],   "highlight":2},
                {"label":"EBITDA Margin",   "values":["22%","24%","21%"],          "highlight":0},
                {"label":"Capex Required",  "values":["Low","Medium","High"],      "highlight":0},
                {"label":"Time to Scale",   "values":["Immediate","2–3 years","1–2 years"],"highlight":0},
                {"label":"Execution Risk",  "values":["Low","Medium","High"],      "highlight":0},
                {"label":"Recommended",     "values":["–","✓","–"],               "highlight":1},
            ]
        },
        {
            "cols": ["In-house","Outsource","JV / Partnership"],
            "rows": [
                {"label":"Cost",            "values":["High","Low","Medium"],      "highlight":1},
                {"label":"Control",         "values":["Full","Limited","Shared"],   "highlight":0},
                {"label":"Speed to Market", "values":["Slow","Fast","Moderate"],   "highlight":1},
                {"label":"Capability Build","values":["Strong","None","Partial"],   "highlight":0},
                {"label":"Recommended",     "values":["–","–","✓"],               "highlight":2},
            ]
        },
        {
            "cols": ["Vendor A","Vendor B","Vendor C"],
            "rows": [
                {"label":"Total Cost (5yr)", "values":["$12M","$8M","$10M"],      "highlight":1},
                {"label":"Implementation",   "values":["9 months","6 months","12 months"],"highlight":1},
                {"label":"Integration Fit",  "values":["High","Medium","High"],    "highlight":0},
                {"label":"Support SLA",      "values":["99.9%","99.5%","99.9%"],  "highlight":0},
                {"label":"Recommended",      "values":["✓","–","–"],              "highlight":0},
            ]
        },
    ])
    rows_out = [{"label": r["label"], "values": r["values"], "highlight": r["highlight"]}
                for r in scenarios["rows"]]
    return {
        "type": "comparison-matrix",
        "title": "Strategic Options Assessment",
        "columns": scenarios["cols"],
        "rows": rows_out,
        "style": _rc(["zebra","bordered","default"])
    }

def _bullet_insights():
    items = random.sample([
        {"text": "Market consolidation accelerating with top 5 players controlling 68% of volume", "sub": "Up from 54% in 2021"},
        {"text": "Digital channels now account for 52% of new customer acquisition", "sub": "vs. 31% pre-pandemic"},
        {"text": "Margin expansion driven by operating leverage and pricing discipline", "sub": "+3.2pp vs. prior year"},
        {"text": "Entry-level segment under pressure from low-cost disruptors", "sub": "Price erosion of 8–12%"},
        {"text": "Regulatory tailwinds support premium product adoption in key markets", "sub": "EU, US, Japan"},
        {"text": "Supply chain restructuring delivers $45M in annualised savings", "sub": "Full benefit from Q3 2025"},
        {"text": "Geographic mix shifting toward higher-margin Asia-Pacific markets", "sub": "APAC now 28% of revenue"},
        {"text": "Talent density in engineering remains a competitive differentiator", "sub": "Top-quartile attrition at 6%"},
    ], _ri(3, 5))
    title = _rc(["Key Insights","Strategic Implications","Key Takeaways","Management Commentary"])
    return {"type":"bullet-list","title":title,"items":items}

def _header(kicker, headline, sub="", page=None):
    h = {"kicker": kicker, "headline": headline, "sub": sub}
    f = {"source": _rc(["Internal analysis","Company financials","Management accounts",
                         "Bloomberg, company filings","PitchBook data, team analysis"]),
         "page": page or _ri(1, 18)}
    return h, f

# ── Pair assemblers ────────────────────────────────────────────────────────────

def _pair(description, spec):
    return {"messages": [
        {"role": "system",    "content": SYSTEM_PROMPT},
        {"role": "user",      "content": description},
        {"role": "assistant", "content": json.dumps(spec, ensure_ascii=False)},
    ]}

def _desc_kpi_bar():
    fund  = _rc(FUND_NAMES)
    period = _rc(["2024 annual investor update","Q4 2024 LP report","H1 2024 mid-year review","FY2024 results"])
    metric = _rc(["deal activity","fundraising by quarter","capital deployment","new investments by sector"])
    return _rc([
        f"Two-column slide for {fund}'s {period}: fund performance KPIs on the left, {metric} bar chart on the right",
        f"Show {fund}'s headline metrics alongside quarterly {metric} for the {period}",
        f"LP update slide — 4 KPI callouts plus a vertical bar chart showing {metric}",
        f"Side-by-side: portfolio performance summary and {metric} breakdown by quarter",
        f"Create a two-column consulting slide with key fund stats on the left and {metric} chart on the right",
    ])

def gen_kpi_bar(n=90):
    pairs = []
    for _ in range(n):
        kpi   = _rc(KPI_GENERATORS)()
        bar, metric, *_ = _rc([_bar_quarterly, _bar_by_sector, _bar_yoy_comparison])()
        fund  = _rc(FUND_NAMES)
        h, f  = _header(
            _rc(["Fund Performance","Portfolio Snapshot","Investor Update","Key Metrics"]),
            _rc([f"{fund}: {_rc(YEARS[-3:])} Performance Overview",
                 f"Portfolio Highlights — {_rc(QUARTERS[-4:])}",
                 f"Quarterly Update: Metrics & Activity",
                 f"{fund} Fund IV — Investor Summary"]),
            sub = _rc(["As of December 2024","LTM basis; management accounts","Unaudited; subject to revision"]),
        )
        layout = _rc(["two-column","sidebar-right"])
        if layout == "two-column":
            content = {"left": kpi, "right": bar}
        else:
            content = {"main": bar, "sidebar": kpi}
        spec = {"slide_type":"content","header":h,"layout":layout,"content":content,"footer":f}
        pairs.append(_pair(_desc_kpi_bar(), spec))
    return pairs

def gen_kpi_line(n=70):
    pairs = []
    for _ in range(n):
        kpi   = _rc(KPI_GENERATORS)()
        line, names = _line_trend()
        fund  = _rc(FUND_NAMES + COMPANIES)
        h, f  = _header(
            _rc(["Performance Trend","Growth Trajectory","Historical Analysis","KPIs & Trends"]),
            _rc([f"{fund}: Metrics & Trend Analysis",
                 f"Performance Summary — {_rc(YEARS[-2:])} to {_rc(YEARS[-1:])}",
                 f"Key Indicators and {names[0]} Trajectory"]),
        )
        layout = _rc(["two-column","sidebar-left"])
        if layout == "two-column":
            content = {"left": kpi, "right": line}
        else:
            content = {"sidebar": kpi, "main": line}
        spec = {"slide_type":"content","header":h,"layout":layout,"content":content,"footer":f}
        desc = _rc([
            f"Side-by-side KPI callouts and {names[0].lower()} trend chart for {fund}",
            f"Show headline metrics alongside the {names[0].lower()} line chart over the past {_ri(6,10)} quarters",
            f"Two-column slide: performance snapshot KPIs left, trend analysis right",
            f"LP presentation: fund KPIs with supporting {names[0].lower()} trend",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_kpi_donut(n=60):
    pairs = []
    for _ in range(n):
        kpi   = _rc(KPI_GENERATORS)()
        donut = _donut_allocation()
        fund  = _rc(FUND_NAMES)
        dim   = _rc(["strategy","geography","sector","asset class"])
        h, f  = _header(
            _rc(["Portfolio Composition","Allocation Overview","Fund Snapshot"]),
            _rc([f"{fund}: Portfolio Allocation & Performance",
                 f"Fund Overview — Composition by {dim.title()} and Key Metrics"]),
        )
        layout = _rc(["two-column","sidebar-right"])
        content = {"left": kpi, "right": donut} if layout == "two-column" else {"main": donut, "sidebar": kpi}
        spec = {"slide_type":"content","header":h,"layout":layout,"content":content,"footer":f}
        desc = _rc([
            f"Show {fund}'s portfolio allocation by {dim} as a donut chart alongside headline fund KPIs",
            f"Two-column slide: key fund metrics on one side, portfolio composition donut on the other",
            f"Fund snapshot: performance callouts plus allocation breakdown by {dim}",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_waterfall(n=90):
    pairs = []
    gens  = [_waterfall_ebitda, _waterfall_aum, _waterfall_revenue]
    for i in range(n):
        wf    = gens[i % len(gens)]()
        title = wf["title"]
        co    = _rc(FUND_NAMES + COMPANIES)
        yr1, yr2 = _rc(YEARS[-4:-1]), _rc(YEARS[-2:])
        h, f  = _header(
            _rc(["Bridge Analysis","Year-on-Year Bridge","Performance Bridge","Value Bridge"]),
            _rc([f"{co}: {title} — {yr1} to {yr2}",
                 f"{title}: Key Drivers of Change",
                 f"{co} — Variance Analysis {yr2}"]),
        )
        spec  = {"slide_type":"content","header":h,"layout":"full","content":{"main":wf},"footer":f}
        btype = "EBITDA" if "EBITDA" in title else "AUM" if "AUM" in title else "Revenue"
        desc  = _rc([
            f"Full-width waterfall chart showing the {btype.lower()} bridge from {yr1} to {yr2} for {co}",
            f"Create a {btype} bridge waterfall chart breaking down the key drivers between {yr1} and {yr2}",
            f"Waterfall analysis: what drove the change in {btype.lower()} year-on-year at {co}",
            f"Show {btype} variance analysis with a waterfall chart — positive and negative contributors",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_gantt(n=90):
    pairs = []
    gens  = [_gantt_ma, _gantt_transformation, _gantt_fund_launch]
    for i in range(n):
        gantt = gens[i % len(gens)]()
        title = gantt["title"]
        co    = _rc(FUND_NAMES + COMPANIES)
        h, f  = _header(
            _rc(["Project Timeline","Transaction Timeline","Roadmap","Execution Plan"]),
            _rc([f"{co}: {title}",
                 f"Indicative Timeline — {title}",
                 f"Workstream Overview: {title}"]),
        )
        spec  = {"slide_type":"content","header":h,"layout":"full","content":{"main":gantt},"footer":f}
        ttype = "M&A transaction" if "M&A" in title else "digital transformation" if "Digital" in title else "fund launch"
        desc  = _rc([
            f"Gantt chart showing the {ttype} timeline for {co}",
            f"Create a project timeline slide with a Gantt chart for our {ttype} at {co}",
            f"Timeline slide: key workstreams and milestones for the {ttype}",
            f"Show the end-to-end {ttype} process with a Gantt chart and milestone markers",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_scatter(n=90):
    pairs = []
    gens  = [_scatter_portfolio, _scatter_risk_return]
    for i in range(n):
        sc    = gens[i % len(gens)]()
        co    = _rc(FUND_NAMES)
        h, f  = _header(
            _rc(["Portfolio Positioning","Risk-Return Analysis","Competitive Landscape","Portfolio Matrix"]),
            _rc([f"{co}: Portfolio Company Matrix",
                 f"Risk-Return by Asset Class",
                 f"Competitive Positioning — Revenue Growth vs. Margin"]),
        )
        spec  = {"slide_type":"content","header":h,"layout":"full","content":{"main":sc},"footer":f}
        xlabel = sc["x_label"]; ylabel = sc["y_label"]
        desc   = _rc([
            f"Scatter plot positioning portfolio companies by {xlabel.lower()} and {ylabel.lower()}",
            f"Create a two-by-two matrix plotting {xlabel.lower()} against {ylabel.lower()} for each portfolio company",
            f"Bubble chart: {xlabel.lower()} on x-axis, {ylabel.lower()} on y-axis, with quadrant labels",
            f"Portfolio positioning matrix showing {xlabel.lower()} vs. {ylabel.lower()}",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_comparison(n=80):
    pairs = []
    for _ in range(n):
        cm   = _comparison_matrix()
        cols = cm["columns"]
        co   = _rc(FUND_NAMES + COMPANIES)
        h, f = _header(
            _rc(["Strategic Options","Options Assessment","Decision Framework","Scenario Comparison"]),
            _rc([f"Strategic Options: {' vs. '.join(cols[:2])} vs. {cols[-1]}",
                 f"{co}: Evaluating {len(cols)} Pathways",
                 f"Options Analysis — Recommendation"]),
        )
        spec = {"slide_type":"content","header":h,"layout":"full","content":{"main":cm},"footer":f}
        desc = _rc([
            f"Comparison matrix evaluating {', '.join(cols)} across key strategic criteria",
            f"Options assessment table comparing {' vs. '.join(cols)} — highlight recommended option",
            f"Strategic decision matrix: assess {len(cols)} options across {len(cm['rows'])-1} dimensions",
            f"Side-by-side evaluation of {', '.join(cols)} with a clear recommendation row",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_process_kpi(n=60):
    pairs = []
    for _ in range(n):
        proc = _rc([_process_investment, _process_digital])()
        kpi  = _rc(KPI_GENERATORS)()
        co   = _rc(FUND_NAMES + COMPANIES)
        h, f = _header(
            _rc(["Investment Process","Operating Model","Methodology","Approach"]),
            _rc([f"{co}: Process & Performance Metrics",
                 f"How We Create Value — Process & Outcomes",
                 f"Approach to Value Creation: Steps & KPIs"]),
        )
        layout  = _rc(["sidebar-right","two-column"])
        content = {"main": proc, "sidebar": kpi} if layout == "sidebar-right" else {"left": proc, "right": kpi}
        spec    = {"slide_type":"content","header":h,"layout":layout,"content":content,"footer":f}
        ptype   = "investment" if "Origination" in str(proc) else "digital transformation"
        desc    = _rc([
            f"Show the {ptype} process as a horizontal flow chart alongside key performance metrics",
            f"Process overview on the left with KPI callouts on the right for {co}",
            f"Two-column slide: step-by-step {ptype} approach and supporting metrics",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_donut_bullets(n=60):
    pairs = []
    for _ in range(n):
        donut  = _donut_allocation()
        bullet = _bullet_insights()
        co     = _rc(FUND_NAMES)
        dim    = _rc(["strategy","geography","sector","asset class"])
        h, f   = _header(
            _rc(["Portfolio Insights","Allocation & Insights","Portfolio Overview"]),
            _rc([f"{co}: Portfolio Mix & Key Takeaways",
                 f"Allocation by {dim.title()} and Strategic Implications"]),
        )
        layout  = _rc(["two-column","sidebar-left"])
        content = {"left": donut, "right": bullet} if layout == "two-column" else {"sidebar": donut, "main": bullet}
        spec    = {"slide_type":"content","header":h,"layout":layout,"content":content,"footer":f}
        desc    = _rc([
            f"Donut chart showing portfolio allocation by {dim} with key insights on the right",
            f"Portfolio composition breakdown and strategic commentary for {co}",
            f"Show fund allocation by {dim} alongside bullet-point takeaways",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_line_full(n=70):
    pairs = []
    for _ in range(n):
        line, names = _line_trend()
        co    = _rc(FUND_NAMES + COMPANIES + BANKS)
        period = _rc(YEARS[-3:])
        h, f  = _header(
            _rc(["Performance Trend","Historical Analysis","Market Trajectory","Trend Analysis"]),
            _rc([f"{co}: {names[0]} Over Time",
                 f"Multi-Year Trend: {' & '.join(names[:2])}",
                 f"{period} Performance — {names[0]} Trajectory"]),
        )
        spec  = {"slide_type":"content","header":h,"layout":"full","content":{"main":line},"footer":f}
        desc  = _rc([
            f"Full-width line chart showing {names[0].lower()} trend over the past {_ri(6,10)} quarters for {co}",
            f"Multi-series line chart: {' vs. '.join(n.split(' ')[0] for n in names)} over time",
            f"Show {co}'s {names[0].lower()} trajectory with a trend line chart",
            f"Time series analysis: {names[0].lower()} from {_rc(YEARS[-5:-3])} to {period}",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_three_column(n=60):
    pairs = []
    for _ in range(n):
        co      = _rc(FUND_NAMES)
        cols    = random.sample(STRATEGIES[:4] + SECTORS[:4], 3)
        kpis    = [_rc(KPI_GENERATORS)() for _ in range(3)]
        h, f    = _header(
            _rc(["Strategy Snapshot","Portfolio Breakdown","Three-Way Comparison"]),
            _rc([f"{co}: Three-Strategy Performance Snapshot",
                 f"Segment Overview — {', '.join(cols)}",
                 f"Comparative Snapshot: {cols[0]}, {cols[1]} & {cols[2]}"]),
        )
        content = {"left": kpis[0], "center": kpis[1], "right": kpis[2]}
        spec    = {"slide_type":"content","header":h,"layout":"three-column","content":content,"footer":f}
        desc    = _rc([
            f"Three-column slide comparing KPI scorecards for {', '.join(cols)} at {co}",
            f"Side-by-side performance metrics for three business segments: {', '.join(cols)}",
            f"Three-way KPI comparison slide for {co}'s {cols[0]}, {cols[1]}, and {cols[2]} portfolios",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_gantt_kpi(n=50):
    pairs = []
    gens  = [_gantt_ma, _gantt_transformation]
    for i in range(n):
        gantt = gens[i % len(gens)]()
        kpi   = _kpi_deal() if "M&A" in gantt["title"] else _kpi_company()
        co    = _rc(FUND_NAMES + COMPANIES)
        h, f  = _header(
            _rc(["Transaction Overview","Project Overview","Deal Summary","Roadmap & Metrics"]),
            _rc([f"{co}: Timeline & Key Parameters",
                 f"Execution Roadmap and Transaction Highlights"]),
        )
        content = {"main": gantt, "sidebar": kpi}
        spec    = {"slide_type":"content","header":h,"layout":"sidebar-right","content":content,"footer":f}
        desc    = _rc([
            f"Transaction timeline Gantt chart with deal metrics sidebar for {co}",
            f"Sidebar layout: project roadmap on the left, key metrics panel on the right",
            f"Show the execution timeline and headline parameters for {co}'s deal",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_scatter_bullets(n=50):
    pairs = []
    for _ in range(n):
        sc     = _scatter_portfolio()
        bullet = _bullet_insights()
        co     = _rc(FUND_NAMES)
        h, f   = _header(
            _rc(["Portfolio Analysis","Competitive Positioning","Portfolio Review"]),
            _rc([f"{co}: Portfolio Positioning & Implications",
                 f"Revenue Growth vs. Margin — Portfolio Analysis"]),
        )
        content = {"main": sc, "sidebar": bullet}
        spec    = {"slide_type":"content","header":h,"layout":"sidebar-right","content":content,"footer":f}
        desc    = _rc([
            f"Portfolio matrix scatter plot with key takeaways sidebar for {co}",
            f"Show portfolio company positioning on a growth-vs-margin matrix with commentary",
            f"Bubble chart of portfolio companies with strategic insights panel on the right",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

def gen_waterfall_bullets(n=40):
    pairs = []
    gens  = [_waterfall_ebitda, _waterfall_revenue]
    for i in range(n):
        wf     = gens[i % len(gens)]()
        bullet = _bullet_insights()
        co     = _rc(COMPANIES + FUND_NAMES)
        h, f   = _header(
            _rc(["Bridge Analysis","Financial Bridge","Variance Commentary"]),
            _rc([f"{co}: Bridge Analysis with Management Commentary",
                 f"Revenue/EBITDA Bridge and Key Drivers"]),
        )
        content = {"main": wf, "sidebar": bullet}
        spec    = {"slide_type":"content","header":h,"layout":"sidebar-right","content":content,"footer":f}
        desc    = _rc([
            f"Waterfall bridge chart with management commentary sidebar for {co}",
            f"EBITDA bridge showing key contributors alongside bullet-point commentary",
            f"Sidebar layout: waterfall chart on the main panel, key insights on the right",
        ])
        pairs.append(_pair(desc, spec))
    return pairs

# ── Build & export ─────────────────────────────────────────────────────────────

GENERATORS = [
    (gen_kpi_bar,         90,  "kpi-grid + bar-chart (two-column)"),
    (gen_kpi_line,        70,  "kpi-grid + line-chart"),
    (gen_kpi_donut,       60,  "kpi-grid + donut-chart"),
    (gen_waterfall,       90,  "waterfall-chart (full)"),
    (gen_gantt,           90,  "gantt-chart (full)"),
    (gen_scatter,         90,  "scatter-chart (full)"),
    (gen_comparison,      80,  "comparison-matrix"),
    (gen_process_kpi,     60,  "process-flow + kpi-grid"),
    (gen_donut_bullets,   60,  "donut + bullets"),
    (gen_line_full,       70,  "line-chart (full)"),
    (gen_three_column,    60,  "three-column kpi"),
    (gen_gantt_kpi,       50,  "gantt + kpi sidebar"),
    (gen_scatter_bullets, 50,  "scatter + bullets sidebar"),
    (gen_waterfall_bullets,40, "waterfall + bullets sidebar"),
]

def build(validate=False):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_pairs = []
    print("Generating synthetic pairs...")
    for fn, n, label in GENERATORS:
        pairs = fn(n)
        all_pairs.extend(pairs)
        print(f"  {len(pairs):4d}  {label}")

    random.shuffle(all_pairs)

    if validate:
        print("\nValidating specs through renderer...")
        sys.path.insert(0, str(Path(__file__).parent))
        from renderer import render_slide
        errors = 0
        for i, p in enumerate(all_pairs):
            try:
                spec = json.loads(p["messages"][2]["content"])
                render_slide(spec)
            except Exception as e:
                print(f"  FAIL [{i}]: {e}")
                errors += 1
        print(f"  {len(all_pairs)-errors}/{len(all_pairs)} passed")

    # 90/10 train-val split
    cut = int(len(all_pairs) * 0.9)
    train_pairs = all_pairs[:cut]
    val_pairs   = all_pairs[cut:]

    train_path = OUT_DIR / "synth_train.jsonl"
    val_path   = OUT_DIR / "synth_val.jsonl"

    train_path.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in train_pairs), encoding="utf-8")
    val_path.write_text(  "\n".join(json.dumps(p, ensure_ascii=False) for p in val_pairs),   encoding="utf-8")

    print(f"\nTotal: {len(all_pairs)} pairs  ->  {len(train_pairs)} train | {len(val_pairs)} val")
    print(f"  {train_path}")
    print(f"  {val_path}")
    return train_path, val_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="Render-test every spec")
    ap.add_argument("--preview",  type=int, default=0, help="Print N sample pairs")
    args = ap.parse_args()

    tp, vp = build(validate=args.validate)

    if args.preview:
        pairs = [json.loads(l) for l in tp.read_text(encoding="utf-8").splitlines()[:args.preview]]
        for p in pairs:
            print("\n-- DESCRIPTION --")
            print(p["messages"][1]["content"])
            print("-- SPEC --")
            spec = json.loads(p["messages"][2]["content"])
            print(json.dumps(spec, indent=2, ensure_ascii=True)[:600] + "...")
