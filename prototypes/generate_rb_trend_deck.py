"""
generate_rb_trend_deck.py  –  Phase 6: 15-slide Roland Berger Trend Compendium deck.

Topic: "Dynamic Technology & Innovation 2030" (Megatrend 5)
Source data: Roland Berger Trend Compendium 2030 – Megatrend 5 (48-page PDF)

Slide plan
  1  Cover / 3-subtrend overview         content        full-width
  2  Technology adoption speed           bar (horiz)    rail + panel
  3  GDP per capita vs PCT patents        bubble         rail + panel
  4  IoT connected devices 2015->2021      stackedbar     full-width  ← NEW type
  5  Mobile device penetration by region  bar (horiz)    rail + panel
  6  Life Sciences – 3 fields overview    content        full-width
  7  Life Sciences innovation areas       content        full-width
  8  PCT Life Sciences by filing office   dualdoughnut   full-width  ← NEW type
  9  PCT patents by applicant origin      dualdoughnut   full-width  ← NEW type
 10  Digital Transformation – 4 levers   content (4p)   full-width
 11  AI hardware market growth            bar (col)      rail + panel
 12  Venture capital by region            bar (horiz)    rail + panel
 13  IoT economic value callout boxes     callout        full-width  ← NEW type
 14  R&D expenditure as % of GDP          bar (horiz)    rail + panel
 15  Corporate action recommendations     content        full-width

Usage:
    python prototypes/generate_rb_trend_deck.py --skip-ollama
    python prototypes/generate_rb_trend_deck.py --model qwen3:8b --model2 qwen3:8b
    python prototypes/generate_rb_trend_deck.py --out rb_trend_custom.pptx
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from recipe_classifier import pipeline as get_slot_spec
from retrieval import load_index

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR  = BASE_DIR / "prototypes" / "output"
SPEC_PATH = OUT_DIR / "rb_deck_spec.json"
PPTX_DEFAULT = "rb_trend_compendium_15slides.pptx"

# Roland Berger brand colours applied to every slide
RB_COLORS = {
    "background":   "#FFFFFF",
    "rail":         "#30343A",
    "accent":       "#0F2942",
    "panel":        "#D9DDE2",
    "divider":      "#2D79A3",
    "text_primary": "#111216",
}

# Standard layout dims for slides that have a left rail + right panel
RAIL_PANEL_DIMS = {
    "rail_w": 0.133, "panel_x": 0.77, "panel_w": 0.23,
    "panel_y": 0.22, "panel_h": 0.68,
    "title_y": 0.05, "title_h": 0.07,
    "subtitle_y": 0.12, "subtitle_h": 0.05,
    "content_x": 0.133, "content_y": 0.17,
    "content_w": 0.64,  "content_h": 0.66,
    "footer_y": 0.88,   "footer_h": 0.09,
}

# ── slide definitions (chart data is factual from the RB PDF) ─────────────────

SLIDE_DEFS = [
    # 1 ── Overview cover: 3 subtrends
    {
        "brief": "strategic overview three pillars consulting framework, Roland Berger style, no chart",
        "chart_type": "content",
        "has_rail": False, "has_panel": False,
        "chart_data": {
            "pillars": [
                {"num": "01", "title": "POWER OF\nINNOVATION", "color": "2D79A3"},
                {"num": "02", "title": "LIFE\nSCIENCES",       "color": "06466D"},
                {"num": "03", "title": "DIGITAL\nTRANSFORMATION", "color": "4A9B84"},
            ],
        },
    },
    # 2 ── Technology adoption speed (horizontal bar)
    {
        "brief": "horizontal bar chart technology adoption speed years to 25 percent adoption, Roland Berger style, insight panel",
        "chart_type": "bar",
        "has_rail": True, "has_panel": True,
        "chart_data": {
            "categories": [
                "Electricity (1873)", "Telephone (1876)", "Radio (1897)", "Television (1926)",
                "Personal computer (1975)", "Mobile phone (1987)",
                "World Wide Web (1991)", "Facebook (2004)",
            ],
            "series": [{"name": "Years to reach 25% adoption rate (US)", "values": [46, 35, 31, 26, 16, 13, 7, 4]}],
            "x_axis": "Years to reach 25% adoption rate",
            "source": "Source: FAZ, Roland Berger",
        },
    },
    # 3 ── GDP per capita vs PCT patent applications (bubble scatter)
    {
        "brief": "scatter bubble chart GDP per capita versus patent applications per million inhabitants 20 countries, Roland Berger style, insight panel",
        "chart_type": "bubble",
        "has_rail": True, "has_panel": True,
        "chart_data": {
            "x":     [450, 400, 250, 200, 200, 150,  50,  50,  50, 200, 250,  30,  50, 150,  30, 10, 10, 10,  5],
            "y":     [85000, 50000, 27000, 43000, 38000, 43000, 42000, 38000, 36000, 33000, 27000, 30000, 52000, 56000, 27000, 9000, 7000, 8000, 2000],
            "sizes": [14, 13, 11, 12, 11, 11, 10, 10, 10, 10, 10,  9, 10, 13,  9,  7,  7,  7,  6],
            "labels": [
                ["Switzerland", 450, 85000], ["Sweden", 400, 50000],
                ["USA", 150, 56000],         ["Singapore", 50, 52000],
                ["Germany", 200, 43000],     ["Japan", 250, 38000],
                ["South Korea", 250, 27000], ["China", 10, 7000],
                ["India", 5, 2000],
            ],
            "x_axis": "Patent applications per 1 million inhabitants",
            "y_axis": "GDP per capita [USD]",
            "x_min": 0, "x_max": 500, "y_min": 0, "y_max": 90000,
            "x_major_unit": 100, "y_major_unit": 20000,
            "source": "Source: IMF, Wipo, WEF",
        },
    },
    # 4 ── IoT connected devices 2015 vs 2021 (stacked column)
    {
        "brief": "stacked bar chart IoT connected devices forecast 2015 2021 professional clean no rail",
        "chart_type": "stackedbar",
        "has_rail": False, "has_panel": False,
        "chart_data": {
            "categories": ["2015", "2021"],
            "series": [
                {"name": "M2M, non-cellular",    "values": [7.1, 8.7]},
                {"name": "Mobile phones",         "values": [2.6, 10.7]},
                {"name": "CE, non-cellular",      "values": [2.4, 1.5]},
                {"name": "M2M & CE, cellular",    "values": [1.3, 3.1]},
                {"name": "PC, laptop & tablet",   "values": [1.6, 2.8]},
                {"name": "Fixed phones",          "values": [0.4, 1.4]},
            ],
            "y_axis": "Connected devices [billion]",
            "axis_max": 32,
            "total_labels": {"2015": "15.4", "2021": "28.2"},
            "growth_label": "↑ +83.1%",
            "source": "Source: Ericsson, Cisco, Gartner",
        },
    },
    # 5 ── Mobile smart device penetration by region (horizontal bar, 2 series)
    {
        "brief": "grouped bar chart mobile smart device penetration by region 2013 2021, Roland Berger style, insight panel",
        "chart_type": "bar",
        "has_rail": True, "has_panel": True,
        "chart_data": {
            "categories": [
                "North America", "W. Europe",
                "C. & E. Europe", "Africa & Middle East",
                "Latin America", "Asia & Pacific",
            ],
            "series": [
                {"name": "2013 (%)", "values": [65, 45, 15, 10, 14, 17]},
                {"name": "2021 (%)", "values": [99, 92, 92, 71, 80, 81]},
            ],
            "x_axis": "Mobile smart devices as % of total mobile connections",
            "source": "Source: Cisco, Roland Berger",
        },
    },
    # 6 ── Life Sciences: 3 fields overview (content)
    {
        "brief": "three pillar framework life sciences overview consulting Roland Berger style, no chart",
        "chart_type": "content",
        "has_rail": False, "has_panel": False,
        "chart_data": {
            "pillars": [
                {"num": "01", "title": "HEALTHCARE\n& DISEASE",   "color": "2D79A3"},
                {"num": "02", "title": "FOOD &\nENVIRONMENT",     "color": "06466D"},
                {"num": "03", "title": "BIOTECH &\nPHARMA",        "color": "4A9B84"},
            ],
        },
    },
    # 7 ── Life Sciences innovation areas (content)
    {
        "brief": "three pillar framework life sciences innovation personalized medicine synthetic biology diagnostics consulting, no chart",
        "chart_type": "content",
        "has_rail": False, "has_panel": False,
        "chart_data": {
            "pillars": [
                {"num": "01", "title": "PERSONALIZED\nMEDICINE",  "color": "2D79A3"},
                {"num": "02", "title": "SYNTHETIC\nBIOLOGY",       "color": "06466D"},
                {"num": "03", "title": "DIAGNOSTICS\n& GENOMICS",  "color": "4A9B84"},
            ],
        },
    },
    # 8 ── PCT Life Sciences by filing office: dual doughnut 2006 vs 2016
    {
        "brief": "dual doughnut chart life sciences patent share by filing office 2006 versus 2016 professional clean",
        "chart_type": "dualdoughnut",
        "has_rail": False, "has_panel": False,
        "chart_data": {
            "left": {
                "year": "2006",
                "labels": ["USA", "EPO", "Japan", "Other", "South Korea", "China"],
                "values": [47.1, 13.9, 12.8, 22.5, 2.2, 1.5],
            },
            "right": {
                "year": "2016",
                "labels": ["USA", "EPO", "Japan", "Other", "South Korea", "China"],
                "values": [39.5, 16.7, 15.0, 15.2, 6.0, 7.6],
            },
            "source": "Source: Wipo (IPC classification A61/C12), Roland Berger",
        },
    },
    # 9 ── PCT by applicant origin: dual doughnut 2006 vs 2016
    {
        "brief": "dual doughnut chart patent applications by country of applicant origin 2006 versus 2016 professional clean",
        "chart_type": "dualdoughnut",
        "has_rail": False, "has_panel": False,
        "chart_data": {
            "left": {
                "year": "2006",
                "labels": ["USA", "Europe", "Japan", "Other", "South Korea", "China"],
                "values": [43.2, 31.9, 12.5, 8.9, 2.1, 1.5],
            },
            "right": {
                "year": "2016",
                "labels": ["USA", "Europe", "Japan", "Other", "South Korea", "China"],
                "values": [36.6, 28.1, 14.2, 8.6, 5.6, 6.9],
            },
            "source": "Source: Wipo, Roland Berger",
        },
    },
    # 10 ── Digital Transformation: 4 levers (content, 4 pillars)
    {
        "brief": "four pillar framework digital transformation data automation connectivity access consulting Roland Berger, no chart",
        "chart_type": "content",
        "has_rail": False, "has_panel": False,
        "chart_data": {
            "pillars": [
                {"num": "1", "title": "DIGITAL\nDATA",    "color": "2D79A3"},
                {"num": "2", "title": "AUTOMATION",        "color": "06466D"},
                {"num": "3", "title": "CONNECTIVITY",      "color": "4A9B84"},
                {"num": "4", "title": "DIGITAL\nACCESS",  "color": "A99BD1"},
            ],
        },
    },
    # 11 ── AI hardware market growth (vertical column, 2 bars)
    {
        "brief": "column bar chart AI hardware market growth 2016 to 2022 forecast CAGR, Roland Berger style, insight panel",
        "chart_type": "bar",
        "has_rail": True, "has_panel": True,
        "chart_data": {
            "categories": ["2016\n(Actual)", "2022\n(Forecast)"],
            "series": [{"name": "AI hardware market (USD billion)", "values": [0.9, 16.1]}],
            "x_axis": "USD billion",
            "bar_direction": "col",
            "gap_pct": 200,
            "growth_cagr": "+62.9% p.a.",
            "source": "Source: MarketsandMarkets, Stanford University, Gartner",
        },
    },
    # 12 ── Venture capital investment by region (horizontal bar)
    {
        "brief": "horizontal bar chart venture capital investment by region USA Asia Europe comparison, Roland Berger style, insight panel",
        "chart_type": "bar",
        "has_rail": True, "has_panel": True,
        "chart_data": {
            "categories": ["USA", "Asia", "Europe"],
            "series": [{"name": "Venture capital invested, USD bn (2016)", "values": [70, 40, 18]}],
            "x_axis": "USD billion invested",
            "source": "Source: Wipo, IMF, World Bank, EVCA, KPMG",
        },
    },
    # 13 ── IoT economic value callout boxes
    {
        "brief": "large number callout boxes IoT economic value multiple organisations professional clean consulting",
        "chart_type": "callout",
        "has_rail": False, "has_panel": False,
        "chart_data": {
            "boxes": [
                {
                    "org": "Roland Berger",
                    "value": "EUR 1.25 tn",
                    "description": "Increase in value added through Digital Transformation for European industry by 2025 — a 20-30% uplift in productivity",
                },
                {
                    "org": "European Commission",
                    "value": "EUR >1.0 tn",
                    "description": "EU market value of Internet of Things expected to exceed EUR 1 trillion by 2020",
                },
                {
                    "org": "Cisco",
                    "value": "USD 8.0 tn",
                    "description": "IoT Value at Stake worldwide over the next decade, 2015–2024 (private sector and public sector combined)",
                },
                {
                    "org": "Machina Research",
                    "value": "USD 3.0 tn",
                    "description": "Total IoT revenue opportunity by 2025, growing from USD 750 billion in 2015 at a CAGR of ~26%",
                },
            ],
            "source": "Source: Roland Berger, European Commission, Cisco, Machina Research",
        },
    },
    # 14 ── R&D expenditure as % of GDP (horizontal bar)
    {
        "brief": "horizontal bar chart R&D expenditure as percentage of GDP by country 2015, Roland Berger style, insight panel",
        "chart_type": "bar",
        "has_rail": True, "has_panel": True,
        "chart_data": {
            "categories": [
                "South Korea", "Israel", "Japan", "Sweden",
                "Austria", "Germany", "USA", "China",
            ],
            "series": [{"name": "R&D expenditure as % of GDP (2015)", "values": [4.3, 4.1, 3.6, 3.2, 3.0, 2.9, 2.7, 2.1]}],
            "x_axis": "R&D spend as % of GDP",
            "source": "Source: Wipo, IMF, World Bank, OECD",
        },
    },
    # 15 ── Corporate action recommendations (content)
    {
        "brief": "three pillar corporate action framework innovation roadmap research networks agile culture consulting Roland Berger, no chart",
        "chart_type": "content",
        "has_rail": False, "has_panel": False,
        "chart_data": {
            "pillars": [
                {"num": "1", "title": "INNOVATION\nROADMAP",  "color": "2D79A3"},
                {"num": "2", "title": "RESEARCH\nNETWORKS",   "color": "06466D"},
                {"num": "3", "title": "AGILE\nCULTURE",       "color": "D4895A"},
            ],
        },
    },
]

# ── fallback text (accurate consulting-quality copy from RB Trend Compendium) ──

FALLBACK_TEXT: dict[int, dict] = {
    1: {
        "title": "Dynamic Technology & Innovation Will Fundamentally Reshape the Economy by 2030",
        "subtitle": "Three converging megatrend dimensions – Power of Innovation, Life Sciences, and Digital Transformation – define the technology frontier",
        "pillars": [
            {"num": "01", "title": "POWER OF\nINNOVATION", "body": "Accelerating R&D cycles and global venture capital flows are compressing technology adoption from decades to years, rewarding first movers and punishing laggards"},
            {"num": "02", "title": "LIFE\nSCIENCES",       "body": "Convergence of genomics, AI-driven diagnostics and synthetic biology is transforming how disease, food security and environmental challenges are fundamentally addressed"},
            {"num": "03", "title": "DIGITAL\nTRANSFORMATION", "body": "Four digital levers – data, automation, connectivity and access – are simultaneously disrupting all industry verticals at unprecedented and compounding speed"},
        ],
    },
    2: {
        "title": "Technology Adoption Has Compressed 10× Over 130 Years – Digital Platforms Lead",
        "subtitle": "Electricity took 46 years to reach 25% US penetration; Facebook achieved the same milestone in just 4 years",
        "rail_label": "Power of\nInnovation",
        "panel_bullets": [
            {"lead": "Compression accelerating",    "body": "Each digital technology wave reaches 25% penetration in roughly half the time of the previous generation"},
            {"lead": "Network effects dominate",    "body": "Zero marginal cost of digital replication and network effects eliminate physical rollout barriers entirely"},
            {"lead": "First-mover window shrinks",  "body": "Competitive positioning windows have narrowed from 15-20 years (industrial era) to 3-7 years (digital era)"},
            {"lead": "Incumbents face clock risk",  "body": "Legacy firms must assume disruption will arrive 5-10 years earlier than historical technology cycles suggest"},
        ],
    },
    3: {
        "title": "Nations That Invest in R&D Command Disproportionately Higher Economic Prosperity",
        "subtitle": "Strong positive correlation between PCT patent intensity and GDP per capita — Switzerland, Sweden and USA lead; BRIC nations cluster at lower left",
        "rail_label": "Innovation\nOutputs",
        "panel_bullets": [
            {"lead": "Switzerland leads all metrics",  "body": "450 PCT patents per million inhabitants and USD 85,000 GDP per capita — the global benchmark for innovation-led growth"},
            {"lead": "Asia rising rapidly",            "body": "South Korea and Japan are competing with top European nations on patent intensity despite lower GDP bases"},
            {"lead": "BRIC gap remains wide",          "body": "China, India, Brazil and Russia cluster far below the trend line — structural investment constraints persist"},
            {"lead": "Europe's innovation mosaic",     "body": "Germany, Austria and Netherlands outperform France and UK on patent intensity relative to GDP per capita"},
        ],
    },
    4: {
        "title": "IoT Connected Devices Will Surge 83% to 28 Billion by 2021 – Driven by M2M and Mobile",
        "subtitle": "M2M non-cellular networks remain the largest segment while mobile phones show the steepest growth trajectory across the 2015–2021 forecast window",
    },
    5: {
        "title": "Smart Device Penetration Is Converging Globally – Developing Regions Catch Up Rapidly",
        "subtitle": "Central & Eastern Europe and Africa & Middle East show the steepest adoption curves from 2013 to 2021, dramatically narrowing the global digital divide",
        "rail_label": "Digital\nAccess",
        "panel_bullets": [
            {"lead": "CEE acceleration standout",    "body": "C. & E. Europe jumps from 15% to 92% penetration — a 6× increase driven by affordable 4G and localised content"},
            {"lead": "Africa narrows the gap",       "body": "Africa & Middle East climbs from 10% to 71%, the largest absolute improvement in the developing world"},
            {"lead": "Saturation nears in West",     "body": "North America and Western Europe approach 99% and 92% respectively, with growth shifting to device upgrades"},
            {"lead": "Asia Pacific diversity",       "body": "Asia & Pacific regional average masks wide variance — Japan/South Korea at near saturation, South/SE Asia still scaling"},
        ],
    },
    6: {
        "title": "Life Sciences Innovation Spans Three Converging Fields With Trillion-Dollar Impact",
        "subtitle": "Healthcare & Disease, Food & Environment, and Biotech & Pharma are being redefined simultaneously by genetic, digital and biological breakthroughs",
        "pillars": [
            {"num": "01", "title": "HEALTHCARE\n& DISEASE",  "body": "AI-assisted diagnostics, precision oncology and genomic medicine are transforming therapeutic outcomes — global healthcare AI market to reach USD 45 billion by 2026"},
            {"num": "02", "title": "FOOD &\nENVIRONMENT",    "body": "CRISPR crop engineering, vertical farming and biodegradable biopolymers address food security and sustainability challenges for a population of 9 billion"},
            {"num": "03", "title": "BIOTECH &\nPHARMA",      "body": "Personalized biologics, mRNA platforms and AI-accelerated drug discovery are compressing pharma development timelines from 12 years toward 3-5 years"},
        ],
    },
    7: {
        "title": "Three Life Sciences Innovations Will Redefine Human Health and Agricultural Productivity",
        "subtitle": "Personalized medicine, synthetic biology and advanced diagnostics represent the highest-potential frontiers, each converging with digital technology",
        "pillars": [
            {"num": "01", "title": "PERSONALIZED\nMEDICINE",  "body": "Genomic profiling, biomarker-guided therapy and real-world evidence platforms are enabling treatments tailored to individual patient biology — moving beyond population-average medicine"},
            {"num": "02", "title": "SYNTHETIC\nBIOLOGY",      "body": "Engineering biological systems as programmable platforms — from designer microbes producing biofuels to synthetic yeast producing insulin analogs at 40% lower cost"},
            {"num": "03", "title": "DIAGNOSTICS\n& GENOMICS", "body": "Next-generation sequencing costs have fallen 99.9% in 10 years — enabling population-scale genomic programs that will reveal disease risk decades before symptoms emerge"},
        ],
    },
    8: {
        "title": "Life Sciences Patent Share Is Shifting Eastward – China and South Korea Gain Rapidly",
        "subtitle": "China and South Korea grew combined PCT Life Sciences filing share from under 4% in 2006 to over 13% in 2016, reshaping the global innovation geography",
    },
    9: {
        "title": "US Applicant Dominance in Life Sciences Is Eroding as Asian Innovators Scale Up",
        "subtitle": "US and European applicants declined from 75% combined in 2006 to 65% in 2016 while China nearly quintupled its origination share",
    },
    10: {
        "title": "Digital Transformation Is Driven by Four Reinforcing Technology Levers",
        "subtitle": "Digital data, automation, connectivity and digital access form a self-reinforcing cycle that simultaneously disrupts all industries at compound speed",
        "pillars": [
            {"num": "1", "title": "DIGITAL\nDATA",   "body": "Exponential data generation from IoT, social media and enterprise systems creates the fuel for AI, analytics and personalisation — global data volume doubling every two years"},
            {"num": "2", "title": "AUTOMATION",       "body": "Robotic process automation, cognitive AI and physical robotics are eliminating routine tasks across manufacturing, logistics, financial services and professional roles"},
            {"num": "3", "title": "CONNECTIVITY",     "body": "5G, low-Earth-orbit satellite networks and next-generation Wi-Fi are enabling real-time data exchange between 28+ billion devices — the foundation of the industrial internet"},
            {"num": "4", "title": "DIGITAL\nACCESS",  "body": "Mobile-first internet access is reaching 3.5 billion underserved users across developing markets, unlocking new consumer segments and digital service delivery models"},
        ],
    },
    11: {
        "title": "AI Hardware Is the Fastest-Growing Tech Segment – 62.9% Annual CAGR to 2022",
        "subtitle": "The global AI hardware market is forecast to expand 18× from USD 0.9 billion in 2016 to USD 16.1 billion by 2022 as GPU and TPU demand accelerates",
        "rail_label": "Digital\nTransform.",
        "panel_bullets": [
            {"lead": "GPU scarcity is structural",   "body": "GPU and custom AI chip demand exceeds fab capacity — supply constraints will persist through 2025 minimum"},
            {"lead": "Hyperscalers dominate spend",  "body": "Amazon, Microsoft, Google and Meta account for over 60% of AI hardware capex — cloud infrastructure shapes the whole market"},
            {"lead": "Edge AI hardware emerges",     "body": "Inference-optimised chips for edge devices represent the fastest-growing sub-segment, driven by IoT and autonomous systems"},
            {"lead": "China accelerates investment", "body": "Domestic Chinese chip programmes (Huawei HiSilicon, Alibaba Xuantie) aim to reduce Western hardware dependency by 2025"},
        ],
    },
    12: {
        "title": "The USA Commands 70% of Global Venture Capital – Europe Faces a Structural Financing Gap",
        "subtitle": "USD 70 billion in US venture capital investment dwarfs Europe's USD 18 billion, creating a compounding innovation financing disadvantage for European startups",
        "rail_label": "Innovation\nFinancing",
        "panel_bullets": [
            {"lead": "US advantage is structural",   "body": "Deep capital markets, risk-tolerant institutional investors and serial entrepreneur networks create a self-reinforcing US advantage"},
            {"lead": "Asia closes on Europe fast",   "body": "Asia's USD 40bn VC total, led by China and South Korea, is now 2× European investment and growing faster"},
            {"lead": "Europe needs capital reform",  "body": "Fragmented national VC markets, limited pension fund participation and regulatory barriers constrain European innovation scale-up"},
            {"lead": "Unicorn gap is widening",      "body": "US produces 3× more unicorns per USD billion of VC than Europe — reflecting both deal quality and exit market depth"},
        ],
    },
    13: {
        "title": "IoT and Digital Transformation Will Generate Multi-Trillion Dollar Value Globally by 2025",
        "subtitle": "Four major institutions project EUR/USD 1.0–8.0 trillion in value creation from IoT deployment — the largest single economic opportunity of the decade",
    },
    14: {
        "title": "South Korea and Israel Lead Global R&D Investment Intensity at 4%+ of GDP",
        "subtitle": "Nations investing most in R&D as a percentage of GDP consistently produce the strongest innovation outputs, highest patenting rates and fastest productivity growth",
        "rail_label": "R&D\nIntensity",
        "panel_bullets": [
            {"lead": "Asia dominates the top two",  "body": "South Korea (4.3%) and Israel (4.1%) dedicate more than double the OECD average to R&D as share of national output"},
            {"lead": "Germany trails expectations", "body": "At 2.9% of GDP, Germany's R&D intensity falls below Japan and Sweden — below its stated 3% target since 2010"},
            {"lead": "China's rapid ascent",        "body": "China at 2.1% already exceeds several European nations and is growing 15% annually — set to overtake EU average by 2022"},
            {"lead": "Private sector leads spend",  "body": "In all top-5 countries, over 65% of R&D investment comes from private industry rather than government funding"},
        ],
    },
    15: {
        "title": "Three Corporate Imperatives Will Define Innovation Leaders Through 2030",
        "subtitle": "Companies that build structured innovation roadmaps, access external research ecosystems and cultivate agile cultures will outperform peers by 2× on growth metrics",
        "pillars": [
            {"num": "1", "title": "INNOVATION\nROADMAP",  "body": "Define a 5-year technology investment thesis aligned to the three megatrend dimensions — with quarterly review cycles and board-level accountability for innovation KPIs"},
            {"num": "2", "title": "RESEARCH\nNETWORKS",   "body": "Build structured partnerships with universities, start-ups and national research institutes — companies with 5+ external R&D partnerships grow IP portfolios 3× faster"},
            {"num": "3", "title": "AGILE\nCULTURE",       "body": "Implement cross-functional innovation sprints and dedicated technology horizon scouting — organisations with embedded agile practices reduce time-to-market by 40%"},
        ],
    },
}

# ── LLM prompts ───────────────────────────────────────────────────────────────

_PROMPT_NARRATIVE = """You are a senior Roland Berger strategy consultant writing slide headlines for a professional deck.
Deck topic: "Dynamic Technology & Innovation 2030 – Roland Berger Trend Compendium Megatrend 5"
Topics covered: technology adoption speed, GDP vs patents scatter, IoT devices forecast, mobile penetration,
Life Sciences (healthcare/food/biotech), PCT patent share shifts, Digital Transformation levers,
AI hardware market growth, venture capital by region, IoT economic value, R&D investment intensity.

Rules:
- titles: max 14 words, action-oriented, data-anchored
- subtitles: max 20 words, state the "so what"
- pillar body text: max 20 words, specific and insight-rich
- Return ONLY valid JSON — no markdown, no code fences, no explanation.

{
  "slides": [
    {
      "num": 1,
      "title": "...",
      "subtitle": "...",
      "pillars": [
        {"num": "01", "title": "POWER OF INNOVATION", "body": "..."},
        {"num": "02", "title": "LIFE SCIENCES",        "body": "..."},
        {"num": "03", "title": "DIGITAL TRANSFORMATION","body": "..."}
      ]
    },
    {"num": 2,  "title": "...", "subtitle": "..."},
    {"num": 3,  "title": "...", "subtitle": "..."},
    {"num": 4,  "title": "...", "subtitle": "..."},
    {"num": 5,  "title": "...", "subtitle": "..."},
    {
      "num": 6,
      "title": "...", "subtitle": "...",
      "pillars": [
        {"num": "01", "title": "HEALTHCARE & DISEASE",  "body": "..."},
        {"num": "02", "title": "FOOD & ENVIRONMENT",    "body": "..."},
        {"num": "03", "title": "BIOTECH & PHARMA",      "body": "..."}
      ]
    },
    {
      "num": 7,
      "title": "...", "subtitle": "...",
      "pillars": [
        {"num": "01", "title": "PERSONALIZED MEDICINE", "body": "..."},
        {"num": "02", "title": "SYNTHETIC BIOLOGY",      "body": "..."},
        {"num": "03", "title": "DIAGNOSTICS & GENOMICS", "body": "..."}
      ]
    },
    {"num": 8,  "title": "...", "subtitle": "..."},
    {"num": 9,  "title": "...", "subtitle": "..."},
    {
      "num": 10,
      "title": "...", "subtitle": "...",
      "pillars": [
        {"num": "1", "title": "DIGITAL DATA",    "body": "..."},
        {"num": "2", "title": "AUTOMATION",       "body": "..."},
        {"num": "3", "title": "CONNECTIVITY",     "body": "..."},
        {"num": "4", "title": "DIGITAL ACCESS",   "body": "..."}
      ]
    },
    {"num": 11, "title": "...", "subtitle": "..."},
    {"num": 12, "title": "...", "subtitle": "..."},
    {"num": 13, "title": "...", "subtitle": "..."},
    {"num": 14, "title": "...", "subtitle": "..."},
    {
      "num": 15,
      "title": "...", "subtitle": "...",
      "pillars": [
        {"num": "1", "title": "INNOVATION ROADMAP",  "body": "..."},
        {"num": "2", "title": "RESEARCH NETWORKS",   "body": "..."},
        {"num": "3", "title": "AGILE CULTURE",        "body": "..."}
      ]
    }
  ]
}"""

_PROMPT_BULLETS = """You are a management consultant writing sharp insight bullets for a Roland Berger presentation.
Deck topic: "Dynamic Technology & Innovation 2030"

Each slide has a right-side insight panel. Write 3-4 bullets per slide.
Rules: 'lead' max 4 words (bold), 'body' max 12 words (specific, data-grounded).
Return ONLY valid JSON — no markdown, no code fences, no explanation.

{
  "slides": [
    {
      "num": 2,
      "rail_label": "Power of\\nInnovation",
      "panel_bullets": [
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}
      ]
    },
    {
      "num": 3,
      "rail_label": "Innovation\\nOutputs",
      "panel_bullets": [
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}
      ]
    },
    {
      "num": 5,
      "rail_label": "Digital\\nAccess",
      "panel_bullets": [
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}
      ]
    },
    {
      "num": 11,
      "rail_label": "Digital\\nTransform.",
      "panel_bullets": [
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}
      ]
    },
    {
      "num": 12,
      "rail_label": "Innovation\\nFinancing",
      "panel_bullets": [
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}
      ]
    },
    {
      "num": 14,
      "rail_label": "R&D\\nIntensity",
      "panel_bullets": [
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."},
        {"lead": "...", "body": "..."}
      ]
    }
  ]
}"""


# ── Ollama helper ──────────────────────────────────────────────────────────────

import re as _re_md

def _strip_md_values(v):
    if isinstance(v, str):
        return _re_md.sub(r'\*+([^*]+)\*+', r'\1', v).strip()
    if isinstance(v, list):
        return [_strip_md_values(i) for i in v]
    if isinstance(v, dict):
        return {k: _strip_md_values(val) for k, val in v.items()}
    return v


def call_ollama(model: str, prompt: str, timeout: int = 300) -> dict | None:
    payload = json.dumps({
        "model": model, "stream": False, "format": "json",
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        raw  = json.loads(resp.read())
        content = raw["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.rstrip("`").strip()
        result = json.loads(content)
        return _strip_md_values(result)
    except Exception as exc:
        print(f"  [ollama:{model}] {exc.__class__.__name__}: {exc}")
        return None


def _parse_slides(result: dict | None) -> dict[int, dict]:
    if result is None or "slides" not in result:
        return {}
    return {int(s["num"]): s for s in result.get("slides", [])}


def _is_weak(text: str) -> bool:
    t = (text or "").strip()
    return not t or t == "..." or len(t) < 6


# ── text generation ────────────────────────────────────────────────────────────

# Slides that have right insight panels (need rail_label + panel_bullets)
_PANEL_SLIDES = {2, 3, 5, 11, 12, 14}
# Content slides that need pillars body text
_PILLAR_SLIDES = {1, 6, 7, 10, 15}


def get_text_content(model1: str, model2: str, skip: bool) -> dict[int, dict]:
    if skip:
        print("  [text] --skip-ollama: using built-in fallback text")
        return FALLBACK_TEXT

    print(f"  [text:narrative] {model1} -> titles, subtitles, pillar bodies ...")
    narrative = _parse_slides(call_ollama(model1, _PROMPT_NARRATIVE))
    if not narrative:
        print(f"  [text:narrative] {model1} failed -> fallback")
        narrative = {}

    print(f"  [text:bullets]   {model2} -> insight panel bullets ...")
    bullets = _parse_slides(call_ollama(model2, _PROMPT_BULLETS))
    if not bullets:
        print(f"  [text:bullets]   {model2} failed -> fallback")
        bullets = {}

    out: dict[int, dict] = {}
    for i in range(1, 16):
        fb = FALLBACK_TEXT.get(i, {})
        n  = narrative.get(i, {})
        b  = bullets.get(i, {})

        title    = n.get("title")    or fb.get("title",    f"Slide {i}")
        subtitle = n.get("subtitle") or fb.get("subtitle", "")
        if _is_weak(title):    title    = fb.get("title",    f"Slide {i}")
        if _is_weak(subtitle): subtitle = fb.get("subtitle", "")
        merged: dict = {"title": title, "subtitle": subtitle}

        # Pillar body text for content slides
        if i in _PILLAR_SLIDES:
            llm_pillars = n.get("pillars") or []
            fb_pillars  = fb.get("pillars", [])
            for j, p in enumerate(llm_pillars):
                if _is_weak(p.get("body", "")) and j < len(fb_pillars):
                    llm_pillars[j]["body"] = fb_pillars[j]["body"]
            merged["pillars"] = llm_pillars if llm_pillars else fb_pillars

        # Panel bullets for rail+panel slides
        if i in _PANEL_SLIDES:
            rl   = (b.get("rail_label") or n.get("rail_label") or fb.get("rail_label", "Insights"))
            pb   = b.get("panel_bullets") or n.get("panel_bullets") or fb.get("panel_bullets", [])
            fb_pb = fb.get("panel_bullets", [])
            for j, bul in enumerate(pb):
                if _is_weak(bul.get("lead", "")) or _is_weak(bul.get("body", "")):
                    pb[j] = fb_pb[j] if j < len(fb_pb) else bul
            merged["rail_label"]    = rl
            merged["panel_bullets"] = pb if pb else fb_pb

        out[i] = merged
    return out


# ── build slide specs via retrieval ──────────────────────────────────────────

def build_slide_specs(idx) -> list[dict]:
    specs = []
    for i, sdef in enumerate(SLIDE_DEFS, 1):
        os.environ["CLASSIFIER_VERBOSE"] = "0"
        spec = get_slot_spec(sdef["brief"], k=1, index=idx)
        os.environ["CLASSIFIER_VERBOSE"] = "1"

        # Use retrieved layout_dims; override colors with RB brand palette
        color_tokens = {**spec.color_tokens, **RB_COLORS}

        # For full-width slides (no rail/panel), layout_dims from retrieval may
        # not apply — but pass them through anyway (renderers ignore them)
        layout_dims = spec.layout_dims if (sdef["has_rail"] or sdef["has_panel"]) else {}

        specs.append({
            "slide_num":      i,
            "recipe":         spec.recipe,
            "anchor_slide_id": spec.anchor_slide_id,
            "has_rail":       sdef["has_rail"],
            "has_panel":      sdef["has_panel"],
            "color_tokens":   color_tokens,
            "layout_dims":    layout_dims,
            "chart_type":     sdef["chart_type"],
            "chart_data":     sdef["chart_data"],
        })
        print(f"  slide {i:2d}: {spec.recipe[:56]}  sim={spec.similarity:.3f}")
    return specs


def assemble_spec(slide_specs: list[dict], text: dict[int, dict], pptx_path: Path) -> dict:
    for s in slide_specs:
        n  = s["slide_num"]
        t  = text.get(n, FALLBACK_TEXT.get(n, {}))
        ct = s["chart_type"]

        s["content"] = {"title": t.get("title", f"Slide {n}"), "subtitle": t.get("subtitle", "")}

        if ct == "content":
            fb_pillars  = FALLBACK_TEXT.get(n, {}).get("pillars", [])
            llm_pillars = t.get("pillars", fb_pillars)
            cd_pillars  = s["chart_data"]["pillars"]
            for j, p in enumerate(llm_pillars):
                if j < len(cd_pillars):
                    p["color"] = cd_pillars[j]["color"]
                    p["num"]   = cd_pillars[j]["num"]
            s["content"]["pillars"] = llm_pillars

        elif ct in ("bar", "bubble") and (s["has_rail"] and s["has_panel"]):
            fb = FALLBACK_TEXT.get(n, {})
            s["content"]["rail_label"]    = t.get("rail_label",    fb.get("rail_label",    "Insights"))
            s["content"]["panel_bullets"] = t.get("panel_bullets", fb.get("panel_bullets", []))

    return {
        "output_path": str(pptx_path).replace("\\", "/"),
        "deck": {
            "title":  "Roland Berger Trend Compendium 2030 | Dynamic Technology & Innovation",
            "footer": "Roland Berger Trend Compendium 2030",
        },
        "slides": slide_specs,
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 15-slide RB Trend Compendium deck")
    parser.add_argument("--model",       default="gemma3:27b-cloud",
                        help="Primary model (narrative: titles/subtitles/pillar bodies)")
    parser.add_argument("--model2",      default="gemma3:27b-cloud",
                        help="Secondary model (analytical: panel bullets)")
    parser.add_argument("--skip-ollama", action="store_true",
                        help="Skip LLM calls; use handcrafted fallback text (recommended for accuracy)")
    parser.add_argument("--out",         default=None,
                        help=f"Output PPTX filename (default: {PPTX_DEFAULT})")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    pptx_path = OUT_DIR / (args.out or PPTX_DEFAULT)

    print("Phase 3: retrieving slide anchors from 641-slide index ...")
    idx = load_index()
    slide_specs = build_slide_specs(idx)

    print("\nGenerating text content ...")
    text = get_text_content(args.model, args.model2, args.skip_ollama)

    print("\nAssembling deck spec ...")
    spec = assemble_spec(slide_specs, text, pptx_path)
    SPEC_PATH.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"  Written: {SPEC_PATH}")

    print("\nRendering PPTX (node) ...")
    js_script = Path(__file__).parent / "generate_sample_deck.js"
    r = subprocess.run(["node", str(js_script), str(SPEC_PATH)], capture_output=True, text=True)
    if r.stdout:
        print(r.stdout.rstrip())
    if r.returncode != 0:
        print(f"  ERROR: node exited {r.returncode}\n{r.stderr[:1000]}")
        sys.exit(1)

    print("\nPatching bubble chart XML ...")
    fix = Path(__file__).parent / "fix_pptx_bubble_charts.py"
    if fix.exists():
        r2 = subprocess.run([sys.executable, str(fix), str(pptx_path)], capture_output=True, text=True)
        if r2.stdout:
            print(r2.stdout.rstrip())

    print(f"\nDone -> {pptx_path}")


if __name__ == "__main__":
    main()
