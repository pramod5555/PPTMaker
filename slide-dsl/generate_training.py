"""generate_training.py — Use Azure GPT-4 to generate high-quality DSL training pairs.

GPT generates the actual slide content (labels, numbers, titles, insights),
which is what makes these pairs far higher quality than programmatic synthesis.
Each prompt is specific enough to force coherent, realistic content.

Run:
    python slide-dsl/generate_training.py              # all ~400 prompts
    python slide-dsl/generate_training.py --n 30       # smoke-test 30 pairs
    python slide-dsl/generate_training.py --workers 8  # higher concurrency
    python slide-dsl/generate_training.py --resume     # skip already-done prompts

Output:
    slide-dsl/dsl_finetune/api_train.jsonl  (auto-merged by build_dsl_dataset.py)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT    = Path(__file__).parent.parent
OUT_DIR = Path(__file__).parent / "dsl_finetune"
OUT_FILE = OUT_DIR / "api_train.jsonl"

random.seed(0)

# ── System prompt (must match build_dsl_dataset.py / generate.py) ─────────────
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
- Footer source: citation in plain text.
- For KPI grids: use "accent" style when stats are the hero; "compact" for 4+ items in a column.
- Always populate stat fields with real numbers or percentages, never leave them empty."""


# ── Prompt pool ────────────────────────────────────────────────────────────────
# Each prompt is a realistic consultant request.
# Prompts are specific enough to force GPT to generate coherent, real content.
# Mix of explicit (specifies layout/chart type) and implicit (leaves it to GPT).

PROMPTS_PE_KPI_BAR = [
    "Summit Capital Fund IV LP update Q4 2024: two-column slide with 4 fund KPIs on the left (AUM $4.2B, Gross IRR 28.4%, Gross MOIC 2.6x, 14 portfolio companies) and a vertical bar chart on the right showing quarterly capital deployment by sector (Technology, Healthcare, Consumer, Industrials) for Q1–Q4 2024.",
    "Meridian Partners Fund III — annual investor presentation: show four headline metrics (fund size $2.8B, net IRR 22.1%, net MOIC 2.1x, DPI 0.8x) alongside a grouped bar chart comparing deal origination vs. deals closed by quarter across 2022–2024.",
    "Apex Private Equity portfolio review: sidebar layout with gross IRR, MOIC, current AUM, and number of realised exits as KPI callouts, plus a horizontal bar chart showing revenue growth by portfolio company (7 companies, showing FY2023 actual revenue vs. FY2024 budget).",
    "Pinnacle Growth Fund half-year update: key fund metrics (AUM $6.8B, Gross IRR 19.3%, 8 investments YTD, average hold period 4.2 years) on the left with a bar chart showing new investment activity by month (Jan–Jun 2024) on the right.",
    "Harbor Hill Capital — Fund II performance summary for annual LP meeting: two-column slide, headline KPIs (gross IRR 31.2%, gross MOIC 3.1x, 18 portfolio companies, 6 full exits) left side; right side vertical bar chart of total value by vintage year (2018, 2019, 2020, 2021, 2022).",
    "Blue Crest Partners Fund V — 2024 annual report: show fund snapshot KPIs (committed capital $8.5B, invested capital $5.1B, remaining dry powder $3.4B, 22 portfolio companies) next to a bar chart of deployment pace by quarter over 2022–2024.",
    "Crestview Advisors: two-column investor update with SaaS portfolio KPIs (blended ARR $1.2B, median NRR 118%, median gross margin 74%, blended growth 42%) and a bar chart of ARR by portfolio company (top 8 names) showing FY2023 vs. FY2024.",
    "Alderton Equity Fund III — Q3 2024 LP letter visual: headline metrics (Net IRR 24.7%, DPI 1.2x, RVPI 1.4x, TVPI 2.6x) in a 2x2 KPI grid alongside quarterly distributions bar chart (Q1 2022 through Q3 2024).",
    "Vertex Capital mid-year review: fund performance callouts (AUM $11.3B, Gross IRR 17.8%, 31 portfolio companies, 9 realisations since inception) plus a stacked bar chart showing portfolio by sector and investment stage (buyout / growth equity / minority) for the current portfolio.",
    "Stonefield Partners European Buyout Fund: key metrics panel (fund size €3.2B, gross IRR 26.1%, gross MOIC 2.4x, 12 investments) with a grouped bar chart comparing EV/EBITDA entry multiples vs. exit multiples for 6 realised investments.",
]

PROMPTS_PE_KPI_LINE = [
    "Meridian Partners Fund IV: two-column slide showing fund KPIs (AUM $5.8B, gross IRR 24.6%, 19 companies, vintage 2019) on the left and a multi-series line chart on the right tracking NAV per unit vs. public equity index (MSCI World) vs. private equity benchmark over Q1 2020 – Q4 2024.",
    "Summit Capital: 4 headline metrics (Fund IV gross IRR 28%, Fund III DPI 1.8x, total AUM $9.2B, team headcount 48) plus a line chart showing AUM growth from 2018 to 2024 with year-end values annotated.",
    "Harbor Hill Capital — investor confidence track: show NPS score trend (quarterly Q1 2022 – Q4 2024) as a line chart alongside LP satisfaction KPIs (% satisfied, % likely to re-invest, NPS score, % LP retention from prior fund).",
    "Pinnacle Growth Fund portfolio health: KPI panel (average revenue growth 38%, average EBITDA margin 21%, weighted average NRR 112%, % companies on plan 78%) with a line chart showing quarterly revenue run-rate aggregate across portfolio from Q1 2022 to Q4 2024.",
    "Apex Private Equity — value creation track: two-column, left shows entry vs. current metrics (avg entry EV/EBITDA 8.2x, current avg 11.4x, avg revenue CAGR since entry 34%, avg EBITDA expansion +7pp), right shows a line chart of portfolio aggregate EBITDA quarterly for 2021–2024.",
    "Blue Crest Technology Fund: four SaaS KPIs (blended ARR $680M, ARR growth 67% YoY, gross margin 79%, churn 3.2%) and line chart showing blended ARR and NRR over 8 quarters.",
    "Crestview Healthcare Fund: performance panel (AUM $3.1B, IRR 21.4%, 14 healthcare portfolio companies, avg EBITDA margin 28%) plus a line chart of portfolio aggregate revenue by quarter (2021–2024), showing COVID recovery and subsequent growth.",
    "Vertex Capital — Fund V: sidebar layout with deal metrics (avg hold 4.8yr, avg entry revenue $180M, avg exit revenue $420M, avg revenue CAGR 29%) and a line chart showing entry vs. exit revenue for each of the 8 realised investments (sorted by vintage).",
]

PROMPTS_WATERFALL = [
    "EBITDA bridge for NovaTech Solutions FY2023 to FY2024: opening EBITDA €142M → volume growth +€38M → pricing +€22M → new product lines +€14M → cost inflation −€19M → restructuring savings +€11M → FX impact −€8M → closing EBITDA €200M. Full-width waterfall chart.",
    "Revenue bridge for PulseAI FY2022 to FY2023: show how revenue grew from $186M to $312M, broken down by: existing customer expansion ($72M), new logo acquisition ($48M), price increases ($18M), churn (−$12M). Clean waterfall with total bar.",
    "AUM bridge for Summit Capital Fund III from December 2022 to December 2023: opening AUM $6.8B, new capital calls $420M, distributions to LPs −$580M, net portfolio appreciation $920M, management fees −$68M, FX impact −$145M, closing AUM $7.347B.",
    "Harbour Hill Capital — EBITDA bridge FY2021 to FY2024 for portfolio company ClearPath Systems: entry EBITDA £28M, organic revenue growth +£22M, acquisition contribution +£15M, pricing improvement +£9M, headcount costs −£8M, integration costs −£6M, depreciation increase −£3M, current EBITDA £57M.",
    "Operating cost bridge for Sentinel Health from 2023 to 2024: total cost base increased from $340M to $398M. Break into: headcount growth +$28M, technology & cloud +$18M, real estate +$6M, savings from automation −$12M, one-off restructuring costs +$18M.",
    "Gross profit bridge for RapidScale 2023 to 2024: GP went from $82M (44% margin) to $124M (52% margin). Decompose by: revenue volume effect, pricing improvement, COGS efficiency gains, mix shift toward higher-margin products, one-off cost items.",
    "Deal-level value creation bridge for Orbis Platforms (entry to exit): entry equity value £80M → revenue CAGR contribution +£95M → margin expansion +£48M → multiple re-rating +£62M → net debt reduction +£22M → transaction costs −£8M → exit equity value £299M.",
    "Alderton Equity — portfolio company DataVault: EBITDA bridge from H1 2024 (£31M) to H2 2024 (£44M). Drivers: new enterprise contracts +£9M, reduced customer acquisition cost +£3M, headcount optimisation +£4M, cloud infrastructure savings +£2M, one-off legal costs −£5M.",
    "Revenue bridge for the European business from 2022 to 2024: 2022 revenue €280M → organic growth €62M → acquisition of Nexus Analytics €45M → lost contract (Atlas group) −€18M → FX tailwind €14M → 2024 revenue €383M.",
    "Crestview Advisors — fund AUM bridge for 2024 annual report: opening $14.2B, new commitments $3.6B, capital calls from LPs $1.8B, distributions paid −$2.4B, portfolio fair value appreciation $2.1B, management fees and expenses −$0.34B, FX impact $0.15B, closing AUM $19.11B.",
    "Free cash flow bridge for NovaTech FY2024: operating profit $88M → add depreciation & amortisation $14M → change in working capital −$12M → capex −$18M → interest paid −$6M → tax paid −$16M → free cash flow $50M.",
    "EBITDA bridge for a consumer retail portfolio company (2021 to 2024): from €55M to €112M. Show: like-for-like volume growth, new store openings, digital channel shift contribution, gross margin improvement, SG&A leverage, one-off COVID recovery effects.",
]

PROMPTS_GANTT = [
    "M&A transaction timeline for the acquisition of ClearPath Systems by Summit Capital: 14-month Gantt chart covering Preliminary NDA & Teaser (M1), Management Presentations (M2–M3), Financial & Commercial Due Diligence (M2–M5), Legal Due Diligence (M3–M6), Debt Financing (M4–M7), SPA Negotiation (M6–M8), Regulatory Filing (M7–M10), Regulatory Approval (M10–M12), Close & Day-1 Integration (M12–M14). Mark LOI (M2), SPA Signing (M8), and Close (M12) as milestones.",
    "Digital transformation roadmap for a European retail bank (24-month view): 6 workstreams — Core Banking Migration, Digital Channels & UX, Data & Analytics Platform, API Layer, Cybersecurity Uplift, Change Management & Training. Key milestones: core banking go-live (M12), digital channels launch (M16), full cloud migration (M22).",
    "Fund launch timeline for Vertex Capital Fund VI: 12-month Gantt showing Strategy Finalisation (M1–M2), Legal Structuring & Domicile (M2–M5), Placement Agent Mandate (M3–M4), Roadshow — Existing LPs (M4–M7), Roadshow — New Investors (M5–M9), First Close Target (M7), Final Close Target (M10), First Investment (M9–M12). Show First Close and Final Close as milestones.",
    "Post-merger integration roadmap for the Nexus Analytics acquisition (18 months): workstreams — Leadership & Governance, Technology Integration, Customer Migration, Finance & Reporting Consolidation, People & Culture, Brand Transition. Key milestones: Day 1 (M1), interim systems integration (M6), full IT migration (M12), brand transition complete (M15), full integration (M18).",
    "Due diligence process timeline for a UK infrastructure buyout (12-week process): Financial DD (W1–W8), Commercial DD (W1–W7), Legal DD (W2–W10), Technical/Engineering DD (W3–W8), Environmental & ESG (W4–W8), Management References (W6–W9), Debt Term Sheet (W7–W10), IC Presentation (W10), Final Approval (W11), SPA Sign (W12). Mark IC presentation and signing as milestones.",
    "Healthcare sector buy-and-build strategy execution roadmap (36-month view): Platform Acquisition (M1–M4), Integration & Stabilisation (M3–M9), Add-on 1 Origination & Close (M6–M12), Add-on 2 Origination & Close (M10–M18), Combined Entity Integration (M14–M24), Operational Improvement Programme (M12–M30), Exit Preparation & Process (M28–M36). Mark each close as milestone.",
    "Enterprise software implementation timeline for Sentinel Health's new ERP system (18 months): Discovery & Design (M1–M3), System Configuration (M3–M7), Data Migration & Testing (M6–M10), Parallel Run (M9–M12), Phased Rollout — Finance & HR (M12–M14), Rollout — Operations & Supply Chain (M13–M16), Rollout — Customer-Facing (M15–M18). Go-live milestones at each phase.",
    "Regulatory approval process for a cross-border pharmaceutical merger: 20-month Gantt covering Pre-merger Notification (M1), EU Phase I Review (M2–M5), US DOJ Second Request (M3–M7), China SAMR Filing (M4–M9), Remedies Negotiation (M7–M12), Remedies Implementation (M12–M17), Final Clearances (M17–M19), Close (M20). Mark each clearance as a milestone.",
    "Technology carve-out execution timeline (24 months): Separation Planning (M1–M4), IT Infrastructure Separation (M3–M10), Legal Entity Restructuring (M2–M8), TSA Services Wind-down (M6–M18), Brand Separation (M12–M20), Standalone Operations (M18–M24). Mark TSA exit and full independence as milestones.",
    "Go-to-market launch plan for a new B2B SaaS product (12 months): Beta Programme (M1–M3), Product Hunt & PR (M3), Partner Enablement (M2–M5), Sales Playbook Development (M3–M5), Account-Based Marketing Campaigns (M4–M8), First Enterprise Deals Target (M6), Mid-Market Self-Serve Launch (M8), Series B Fundraise (M9–M11), International Expansion (M11–M12).",
]

PROMPTS_SCATTER = [
    "Portfolio company positioning matrix for Apex Private Equity (14 companies): plot revenue growth (x-axis, 0–80%) vs. EBITDA margin (y-axis, 0–45%) with bubble size proportional to revenue. Companies: NovaTech (52%, 31%), PulseAI (78%, 18%), ClearPath (31%, 38%), RapidScale (44%, 24%), Orbis (29%, 42%), DataVault (65%, 22%), Nexus (38%, 35%), CloudBridge (71%, 15%), Sentinel (28%, 40%), Meridian Digital (55%, 19%), Atlas Retail (14%, 28%), Beacon Health (24%, 33%), CityCore (18%, 37%), Horizon (41%, 26%). Quadrant labels: Stars, Harvest, Improve, Invest.",
    "Risk-return scatter for a multi-asset portfolio: plot 10-year expected annual return (y-axis, 0–20%) vs. annualised volatility (x-axis, 0–30%) for: Cash (0.4%, 0.5%), IG Bonds (3.1%, 4.2%), HY Bonds (6.2%, 8.4%), Public Equity (8.8%, 16.2%), Hedge Funds (7.1%, 8.9%), Real Estate (7.8%, 9.8%), Infrastructure (8.2%, 7.4%), Private Credit (8.9%, 6.8%), PE Buyout (14.2%, 18.4%), Venture Capital (17.8%, 28.1%).",
    "European buyout market: plot EV/EBITDA entry multiple (x-axis, 6x–16x) vs. gross IRR achieved (y-axis, 10%–40%) for 15 comparable transactions in Technology and Healthcare sectors from 2018–2022. Larger bubbles = larger transaction size. Show a downward-sloping trend: higher multiples associated with lower returns.",
    "Competitive landscape scatter for enterprise cloud security vendors: plot market share (x-axis, 0–25%) vs. revenue growth rate (y-axis, 0–120%) with bubble size as total revenue. Companies: CrowdStrike (18%, 35%), Palo Alto (22%, 22%), SentinelOne (8%, 66%), Zscaler (7%, 41%), Darktrace (3%, 28%), Lacework (2%, 84%), Orca Security (1%, 97%), Wiz (2%, 112%), Snyk (1%, 93%), Vectra (1%, 31%).",
    "Portfolio strategy quadrant for Stonefield Partners: plot competitive position (x-axis, weak to strong, 1–5) vs. market attractiveness (y-axis, low to high, 1–5) for portfolio companies. BCG matrix style. Companies: DataVault (3.8, 4.6), Orbis Platforms (4.2, 3.9), ClearPath (2.8, 4.4), Nexus Analytics (3.5, 3.2), RapidScale (4.4, 2.8), PulseAI (2.2, 4.7), CloudBridge (3.9, 2.4), Atlas (2.1, 2.1). Quadrant labels: Stars, Question Marks, Cash Cows, Dogs.",
    "NRR vs. ARR growth scatter for SaaS portfolio companies: x-axis ARR growth YoY (20%–150%), y-axis Net Revenue Retention (90%–145%). Plot 12 companies with bubble size proportional to ARR. A well-performing SaaS portfolio shows companies clustered in the high-NRR, high-growth quadrant. Include reference lines at 100% NRR and 50% ARR growth.",
    "Global PE fund performance scatter: plot DPI (distributions to paid-in, x-axis 0–3x) vs. TVPI (total value to paid-in, y-axis 0.8x–4x) for 20 funds vintage 2015–2018. Colour-code by strategy (Buyout, Growth, Venture). Shows buyout funds clustered around DPI 1.0–1.8x / TVPI 1.8–2.4x; venture funds showing higher variance.",
    "Customer cohort analysis scatter for Meridian Digital: plot monthly churn rate (x-axis, 0%–8%) vs. expansion MRR rate (y-axis, 0%–25%) for each customer cohort (2019–2024 vintages). Bubble size = cohort ARR. Recent cohorts should show lower churn and higher expansion.",
]

PROMPTS_COMPARISON = [
    "Strategic options assessment for a European industrial conglomerate evaluating three exit routes: Trade Sale vs. IPO vs. PE Secondary. Compare across: valuation certainty, time to execution, management disruption, future upside retention, deal certainty, complexity. Clearly recommend Trade Sale as the preferred route.",
    "Operating model options for a shared services centre: Onshore Centralised vs. Nearshore vs. Offshore. Criteria: total 5-year cost, service quality (SLA attainment), time to implement, talent availability, regulatory risk, change management complexity. Recommend Nearshore as the optimal balance.",
    "Technology vendor comparison for ERP selection: SAP S/4HANA vs. Oracle Fusion vs. Microsoft Dynamics 365. Criteria: total cost of ownership (5yr), implementation complexity, integration with existing systems, mobile/UX capability, vendor stability, support quality. Include a recommended row.",
    "Market entry strategy options for a US healthcare company entering Southeast Asia: wholly-owned subsidiary vs. joint venture with local partner vs. distributor/licensing model. Criteria: speed to revenue, capital required, control over brand & pricing, regulatory pathway, exit optionality, talent access.",
    "Portfolio company DataVault — growth strategy assessment: Organic Growth vs. Adjacent M&A vs. Geographic Expansion. Compare across: revenue CAGR (5yr), investment required, execution risk, time to profitability, management bandwidth, strategic fit. Show Organic Growth + select M&A as recommended.",
    "Digital banking transformation: Build (in-house) vs. Buy (acquisition) vs. Partner (fintech API). Criteria: time to market, upfront investment, talent requirement, IP ownership, regulatory treatment, scalability. Recommend Partner for immediate capability, with Build pathway for core differentiators.",
    "Restructuring options for underperforming retail division: Full Sale vs. Partial Divestiture vs. Turnaround (retain). Criteria: cash proceeds (near-term), earnings impact (yr 1), management focus, brand risk, probability of success, shareholder value creation (3yr). Recommend Full Sale.",
    "Private credit vs. bank debt vs. high yield for a leveraged buyout financing: compare maximum leverage available, pricing (all-in cost), covenant package, execution certainty, call protection, flexibility for add-ons, documentation burden. Show Private Credit as optimal for a mid-market buyout with add-on strategy.",
    "Carbon reduction pathway options for an industrial manufacturer: Internal Abatement vs. Carbon Offsets vs. Carbon Capture Technology. Compare across: cost per tonne CO2, permanence of reduction, reputational benefit, regulatory risk, timeline to impact, scalability. Include net-zero alignment assessment.",
    "Buy-and-build vs. organic growth vs. strategic JV for a healthcare services company seeking scale: compare revenue potential (5yr), EBITDA margin trajectory, execution risk, capital intensity, management capability requirements, valuation multiple impact.",
    "Cloud migration strategy: Lift & Shift vs. Re-platform vs. Re-architect. Criteria: migration timeline, one-time cost, ongoing run-cost saving, business disruption, future flexibility, technical debt reduction. Recommend phased approach: Lift & Shift for legacy systems, Re-architect for customer-facing applications.",
    "Divestiture method assessment for a non-core business unit: Auction Process vs. Bilateral Negotiation vs. Management Buyout (MBO). Compare: expected valuation, deal certainty, timeline, management alignment, confidentiality risk, regulatory complexity.",
]

PROMPTS_PROCESS = [
    "Investment process for Apex Private Equity: 6-step horizontal flow — (1) Origination: proprietary network & intermediary sourcing, 200+ opportunities annually; (2) Screening: IC memo, initial financial model, ~30 pass per year; (3) Preliminary DD: commercial, management meeting, 10–15 per year; (4) Full Due Diligence: financial, legal, technical, ESG, ~6–8 per year; (5) Investment Committee: final approval, structuring, 4–6 investments per year; (6) Value Creation: 100-day plan, operational support, board governance. Show alongside 4 KPI callouts: 200 deals reviewed, 18% conversion to IC, avg 4.5yr hold, 2.8x avg MOIC.",
    "Value creation framework for Summit Capital portfolio companies: 5-step process — (1) Day-1 Readiness: governance, reporting, quick wins; (2) Strategic Clarity: market positioning, growth priorities; (3) Operational Excellence: margin improvement, working capital; (4) Organic Growth: commercial engine, pricing, new markets; (5) M&A & Exits: bolt-on acquisitions, exit preparation. Pair with KPIs showing avg EBITDA margin improvement: +8.2pp, avg revenue CAGR post-entry: 34%, avg hold: 4.1yr.",
    "ESG due diligence process for Meridian Partners: 5-step horizontal flow — (1) ESG Screening at entry (red flags, sector exclusions); (2) Material Risk Assessment (climate, governance, social); (3) ESG Action Plan (100-day priorities, KPIs); (4) Monitoring (quarterly reporting, board oversight); (5) Exit & Disclosure (sustainability report, ESG data room). Alongside KPI panel: 100% portfolio with ESG action plans, 8 portfolio companies with science-based targets, Net Zero commitment 2040.",
    "Customer success process for PulseAI (B2B SaaS): 5-step flow — (1) Onboarding (structured 30-day activation programme); (2) Adoption (in-app guidance, usage analytics); (3) Expansion (QBRs, upsell playbook, champion building); (4) Renewal (90-day out process, risk scoring); (5) Advocacy (case studies, referrals, community). Show with KPI callouts: NRR 118%, onboarding completion 89%, avg time to value 14 days, churn 2.8%.",
    "Deal origination process for a mid-market PE fund: 6-step flow — (1) Sector Mapping: define target sub-verticals and ideal company profiles; (2) Prospecting: proprietary outreach, 500+ companies tracked; (3) Relationship Development: annual touchpoints, management meetings; (4) Mandate Moment: owner-readiness trigger, indication of interest; (5) Exclusivity: term sheet, kick-off DD; (6) Close: financing, legal, day-1. Alongside metrics: 600 companies in pipeline, 12% conversion to LOI, 60% proprietary deal share.",
    "Digital product development process for RapidScale: horizontal flow showing — (1) Discover (user research, data analysis, opportunity sizing); (2) Define (problem statement, OKRs, success metrics); (3) Design (wireframes, prototypes, design system); (4) Build (agile sprints, CI/CD, automated testing); (5) Launch (phased rollout, A/B testing, GTM alignment); (6) Learn (NPS, retention data, iteration cycle). KPI panel: 4-week sprint cycles, 94% uptime SLA, NPS +42, 68% DAU/MAU ratio.",
]

PROMPTS_DONUT_KPI = [
    "Portfolio allocation overview for Alderton Equity: donut chart showing AUM by strategy — Buyout 45% ($6.3B), Growth Equity 28% ($3.9B), Real Assets 18% ($2.5B), Credit 9% ($1.3B) — with $14B total AUM as centre label. Alongside 4 fund KPIs: Total AUM $14B, number of portfolio companies 38, DPI since inception 1.4x, Gross IRR across all strategies 21.8%.",
    "Geographic allocation for Stonefield Partners: donut showing AUM by region — North America 52% ($4.4B), Europe 31% ($2.6B), Asia-Pacific 14% ($1.2B), Rest of World 3% ($0.25B). Centre text: $8.45B total. Two-column with fund metrics KPI grid (vintage 2017, 26 companies, gross IRR 23.4%, gross MOIC 2.2x).",
    "Sector mix for Vertex Capital portfolio: donut chart — Technology 38% (12 cos), Healthcare 24% (8 cos), Consumer 16% (5 cos), Financial Services 12% (4 cos), Industrials 10% (3 cos). Centre: 32 companies. KPI panel: portfolio aggregate revenue $4.8B, revenue growth 31% YoY, % on or ahead of plan 72%, average EBITDA margin 24.1%.",
    "Financing structure for the ClearPath Systems acquisition: donut showing deal structure — Senior Secured Debt 45%, Mezzanine 15%, Rollover Equity (Management) 8%, Sponsor Equity 32%. Centre: $520M EV. Alongside deal metrics KPI grid: EV $520M, EV/EBITDA 8.4x, equity cheque $166M, target IRR 26%.",
    "Atlas Retail revenue by channel: donut — In-store 41%, E-commerce 33%, Marketplace (Amazon/eBay) 14%, Wholesale 12%. Centre: £680M revenue. KPI panel: revenue £680M (+18% YoY), gross margin 48.2%, EBITDA £92M (13.5% margin), e-commerce growing 2.4× faster than in-store.",
    "Sentinel Health revenue by payer type: donut — Commercial Insurance 48%, Medicare 26%, Medicaid 14%, Self-pay 8%, Government Contracts 4%. Total revenue $1.1B. KPI panel: total revenue $1.1B, EBITDA margin 22.4%, patient episodes 180,000/yr, EBITDA per episode $1,370.",
    "DataVault ARR by customer segment: donut — Enterprise (>$1B rev) 54%, Mid-Market ($100M–$1B) 31%, SMB (<$100M) 15%. Centre: $124M ARR. KPI grid: ARR $124M (+58% YoY), NRR 124%, gross margin 82%, average contract value $185K.",
    "Orbis Platforms revenue by geography: donut — United Kingdom 38%, Germany 22%, France 14%, Benelux 11%, Nordics 9%, Other Europe 6%. Total €340M. KPI grid: revenue €340M, EBITDA margin 34.1%, UK market leader with 28% share, 3 acquisitions completed in target markets.",
]

PROMPTS_LINE_FULL = [
    "Multi-series line chart showing Summit Capital Fund IV's NAV per unit (left axis) vs. capital called (right axis) vs. cumulative distributions (right axis) over 16 quarters from fund inception (Q1 2020 to Q4 2024). NAV per unit started at 100, peaked at 248 at Q12, currently 231 with distributions. Show J-curve.",
    "European private equity dry powder vs. deal volume trend: dual-axis line chart from 2015 to 2024. Left axis: European PE dry powder ($B) — 2015: $280B, 2016: $310B, 2017: $345B, 2018: $390B, 2019: $420B, 2020: $380B, 2021: $450B, 2022: $510B, 2023: $480B, 2024: $520B. Right axis: deal count — 2015: 1,820, 2016: 1,940, ..., generally trending upward to 2,600 in 2024 with a dip in 2020.",
    "NovaTech revenue vs. EBITDA trend FY2019–FY2024: line chart with two series — Revenue ($M): 82, 94, 110, 148, 196, 268; EBITDA ($M): 12, 15, 19, 32, 51, 78. Add EBITDA margin as area or annotate: 14.6%, 16.0%, 17.3%, 21.6%, 26.0%, 29.1%. Shows operating leverage kicking in from FY2021.",
    "RapidScale ARR trend with NRR overlay: primary y-axis ARR ($M) growing from $18M (Q1 2021) to $312M (Q4 2024); secondary y-axis NRR (%) ranging from 108% to 136% over same period. Show quarterly data points. NRR peaked at 136% in Q2 2023, dipped to 121% in Q2 2024 as market normalised.",
    "Global M&A deal volume by quarter 2019–2024: single-series line chart showing quarterly deal value ($B) — strong 2019 (avg $850B/quarter), COVID dip Q2 2020 ($420B), recovery through 2021 (peak $1,380B in Q4 2021), correction in 2022–2023 (avg $650B/quarter), recovery in 2024. Annotate key market events.",
    "Harbour Hill Capital portfolio company Sentinel Health: quarterly performance metrics — revenue ($M), EBITDA ($M), and patient volumes (thousands) over Q1 2020 to Q4 2024. Revenue: 220, 198, 215, 240, 262, 285, 310, 335, 358, 382, 408, 430, 452, 475, 496, 512, 535, 558, 582, 611. Show COVID trough in Q2 2020 and strong recovery.",
    "PE vs. Public Equity performance comparison: line chart showing cumulative performance of a £1 invested in 2015 — PE Buyout index vs. MSCI World vs. UK FTSE All-Share — through end 2024. PE buyout grows to £3.8, MSCI World to £2.7, FTSE All-Share to £1.9. Show significant PE outperformance especially post-2020.",
    "Macroeconomic backdrop for a European PE LP presentation: three-series line chart showing ECB policy rate (%), Euro area CPI (%), and Euro area GDP growth (%) from Q1 2020 to Q4 2024. Rate: near 0% until Q3 2022, then sharp rise to 4.5% by Q3 2023, cuts begin Q2 2024. CPI: 2%, then surge to 10.6% peak Q4 2022, back to 2.4% by Q4 2024.",
]

PROMPTS_THREE_COL = [
    "Three-column KPI scorecard for Apex Private Equity Fund IV — three segments: Buyout Portfolio (8 companies, avg EV/EBITDA entry 9.2x, avg revenue growth 28% since entry, 0 exits), Growth Portfolio (6 companies, avg entry ARR $85M, avg NRR 118%, 2 IPO candidates), Credit Portfolio (12 positions, avg yield 11.4%, avg LTV 52%, 0 defaults).",
    "Alderton Equity Fund III — performance by geography: three-column slide with North America (6 companies, gross IRR 29.1%, gross MOIC 2.8x, 2 full exits), Europe (5 companies, gross IRR 21.4%, gross MOIC 2.1x, 1 full exit), Asia-Pacific (3 companies, gross IRR 17.8%, gross MOIC 1.6x, 0 exits). Each column as a KPI card.",
    "RapidScale Q4 2024 business review — three divisions: Core Platform (ARR $186M, +44% YoY, NRR 122%, gross margin 82%), Professional Services (revenue $48M, +18% YoY, utilisation 86%, EBITDA margin 22%), Marketplace (GMV $124M, +78% YoY, take rate 14.2%, EBITDA neutral). Three-column KPI grids.",
    "Sentinel Health operating segment performance: three columns for Hospital Division (12 hospitals, $640M revenue, 21% EBITDA margin, 92% bed occupancy, NPS 48), Outpatient Clinics (84 clinics, $280M revenue, 28% EBITDA margin, patient satisfaction 4.4/5), Digital Health (2.1M registered users, $180M ARR, 68% DAU/MAU, NPS 62).",
    "Summit Capital — Fund managers vs. infrastructure vs. advisory: three-column slide comparing the three business lines with key metrics each — Fund Management (AUM $18B, fee revenue $180M, EBITDA margin 48%), Infrastructure (7 assets, EV $4.2B, avg yield 8.4%, occupancy 96%), Advisory (12 mandates YTD, fee revenue $42M, win rate 68%).",
    "PulseAI product suite three-column overview: Analytics Platform (2,400 enterprise customers, ARR $280M, NPS 64, gross margin 84%), Data Integration Layer (890 customers, ARR $148M, NPS 58, gross margin 79%), AI Decision Engine (320 customers in beta, ARR $82M, NPS 71, gross margin 88%).",
    "Portfolio company ClearPath Systems — three-year plan milestones: Year 1 (revenue £48M, EBITDA margin 14%, 3 new enterprise wins, complete ERP migration), Year 2 (revenue £72M, EBITDA margin 20%, UK market leadership, first EU office), Year 3 (revenue £108M, EBITDA margin 26%, Series B / IPO-ready, 8 EU markets). Three KPI columns.",
    "Nexus Analytics go-to-market overview — three channels: Direct Sales (42 reps, $4.8M quota/rep, $186M ARR contribution, avg deal size $420K), Partner/Reseller (28 active partners, $94M ARR, 32% of new ARR, avg deal size $185K), Product-Led Growth (1.2M free users, $62M conversion ARR, avg ACV $52K, 14% conversion trial-to-paid).",
]

PROMPTS_KPIS_ONLY = [
    "Four-metric KPI hero slide for DataVault's Series C investor pitch: ARR $124M (bold, large), NRR 124% (strong expansion), Gross Margin 82% (SaaS-grade), Payback Period 14 months (best-in-class). Each with a meaningful delta vs. prior year and vs. benchmarks. Use accent KPI style.",
    "Single-page fund snapshot for Crestview Advisors Fund IV: AUM $3.8B (Fund IV vintage 2021), Gross IRR 28.4% (vs. 20% target), Gross MOIC 2.2x (vs. 2.0x target), 14 Portfolio Companies (2 in active exit process), DPI 0.3x (early), TVPI 2.2x. Six-item KPI grid, 2 columns.",
    "Macro dashboard for an LP investment committee: US GDP Growth +2.8% (Q3 2024, vs. +1.4% Q2), Core CPI 3.2% (still above 2% target), Fed Funds Rate 5.25% (peak, cuts expected 2025), S&P 500 +18.4% YTD, USD Index 104.2 (−2.1% QoQ), Credit Spreads 180bps IG / 420bps HY. Six-metric grid.",
    "RapidScale operational scorecard Q4 2024: ARR $312M (+68% YoY), NRR 126% (3rd consecutive quarter >120%), Gross Margin 81% (+2pp YoY), Rule of 40 score: 109 (ARR growth 68% + FCF margin 41%), Months CAC Payback: 11 months (down from 18 months Q4 2022), Churn: 2.1% gross annual. Show each metric with context.",
    "Healthcare private equity market overview dashboard: Total PE healthcare deal volume $142B (2024 YTD), Avg EV/EBITDA healthcare buyouts 12.4x (vs. 10.8x all-sector), % deals with ESG DD 78% (up from 44% in 2021), Digital health funding $18.2B (−32% from 2021 peak), Healthcare AI investment $9.4B (+87% YoY), Regulatory scrutiny index High (FTC active).",
    "M&A advisory market KPIs for a boutique firm's capability slide: Global M&A volume $2.8T (2024 YTD), Cross-border share 38%, Average deal premium 31%, Technology sector share of global M&A 24%, Hostile/contested deals 8% (elevated), Time from announcement to close average 7.2 months.",
]

PROMPTS_TABLE = [
    "Peer group benchmarking table for NovaTech: 8 comparable SaaS companies, 6 metrics — ARR, ARR growth %, NRR %, Gross Margin %, EV/ARR multiple, EV/NRR multiple. Companies: Salesforce, ServiceNow, HubSpot, Veeva, Workday, Zendesk, NovaTech (highlighted row), Freshworks. NovaTech should appear best-in-class on growth and NRR.",
    "Portfolio company quarterly operating table for Apex Private Equity: 8 portfolio companies (rows), 5 columns — Revenue LTM ($M), Revenue Growth YoY, EBITDA margin, vs. budget (RAG), Management team rating. Sort by revenue. Use red/amber/green for vs. budget column.",
    "Transaction comparables table for a healthcare services M&A advisory: 10 transactions (rows), columns — Target, Acquirer, Date, EV ($M), Revenue ($M), EV/Revenue, EBITDA ($M), EV/EBITDA, Premium to unaffected. Sort by date descending. Last 3 years, European healthcare services sector.",
    "LP commitment summary for Alderton Equity Fund IV first close: 12 LP investors (rows), columns — LP Name, Type (pension/SWF/endowment/FO), Commitment ($M), % of Fund, Prior Fund Relationship (Y/N), Geography. Total first close $680M. Blend of new and returning LPs.",
    "Debt financing comparison for a leveraged buyout: 5 financing options (rows) — Unitranche, Term Loan B, Senior + Mezzanine, High Yield Bonds, Senior + PIK. Columns: max leverage (EBITDA), all-in cost, call protection period, covenants, min EBITDA size, typical timeline. Show unitranche as sweet spot for mid-market.",
]

PROMPTS_MIXED = [
    "Scatter chart showing Summit Capital's full portfolio (28 companies) plotted by revenue growth (x-axis) vs. EBITDA margin (y-axis) with bubble size representing EV. Colour-code by sector (Technology, Healthcare, Consumer, Industrials). Add quadrant labels: Scale-Up, Stars, Mature, Repositioning. Show the bulk of portfolio in Stars and Scale-Up quadrants.",
    "Donut chart of Stonefield Partners' portfolio by EV range: <£100M (6 companies, 8%), £100–250M (9 companies, 22%), £250–500M (7 companies, 31%), £500M–1B (4 companies, 24%), >£1B (2 companies, 15%). Centre shows 28 portfolio companies. Full-width layout with analysis bullet-list on the right sidebar: portfolio is mid-market focused, average EV £320M, largest 3 companies represent 39% of portfolio value.",
    "Process flow for value creation at a PE-backed consumer brand: (1) Brand Audit & Repositioning — heritage reanalysis, consumer research, competitive positioning; (2) Commercial Engine — pricing architecture, channel optimisation, DTC acceleration; (3) Supply Chain — COGS reduction, supplier consolidation, nearshoring; (4) Digital & Data — CRM, loyalty programme, analytics; (5) M&A & International — bolt-on brands, European roll-out. Below the process, a sidebar with KPI outcomes: gross margin +6pp, DTC revenue +180%, NPS +22 points, 3 bolt-ons completed.",
    "Full-width waterfall showing the reconciliation between reported EBITDA and adjusted / normalised EBITDA for due diligence on a portfolio company: Reported EBITDA £48M → add back one-off restructuring costs +£4.2M → add back founder salary above market +£1.8M → add back non-recurring legal fees +£0.9M → reverse IFRS 16 lease adjustment −£2.4M → normalise for full-year M&A contribution +£3.1M → adjust for run-rate savings not yet in P&L +£2.8M → Adjusted EBITDA £58.4M.",
    "Three-column comparison of private equity, private credit, and infrastructure as asset classes for an institutional LP presentation: Private Equity (target return 15–20% net, typical fund life 10yr, liquidity low, avg hold 5yr, correlation to public equity 0.62), Private Credit (target return 9–12% net, typical fund life 7yr, liquidity low, current yields elevated, downside protection via covenants), Infrastructure (target return 8–12% net, typical fund life 12–15yr, inflation linkage 80%+ of cash flows, correlation to public equity 0.18).",
    "Two-column slide for a logistics company: left side shows operational KPIs (daily parcel volume 1.2M, on-time delivery 94.8%, damage rate 0.12%, cost per parcel £2.84, fleet utilisation 87%, NPS 52); right side shows a horizontal bar chart of cost breakdown by driver (Labour 42%, Transport 28%, Fuel 14%, Technology & Infrastructure 9%, Overheads 7%). Headline: cost efficiency improving as volume scales.",
    "Gantt chart showing the 12-month integration plan post-acquisition of Nexus Analytics by CloudBridge: workstreams — Technology (API integration M1–M6, data migration M3–M9, legacy sunset M9–M12), Commercial (joint GTM M1–M3, cross-sell launch M3–M6, combined sales team M6–M12), People (org design M1–M2, role alignment M2–M4, culture programme M1–M12), Finance (ERP consolidation M3–M8, combined reporting M8–M12). Milestones: Day 1 complete, integration complete, full synergy run-rate.",
    "Comparison matrix evaluating three geographic markets for expansion: UK (already present) vs. Germany vs. France vs. Netherlands. Criteria: market size (TAM), regulatory environment, competitive intensity, talent availability, speed to profitability, strategic fit with brand. Recommend Germany as priority market based on TAM and lower competitive intensity.",
    "Line chart showing 5-year revenue, gross profit, and EBITDA trajectory for a SaaS company from Series A through pre-IPO: FY2020 revenue $8M / GP $5.8M / EBITDA −$12M; FY2021 $22M / $16.8M / −$18M; FY2022 $54M / $43.2M / −$8M; FY2023 $124M / $103.2M / +$18M; FY2024E $268M / $231M / +$68M. Show transition from investment mode to profitability. Annotate funding rounds.",
]

# Combine all prompts
ALL_PROMPTS = (
    PROMPTS_PE_KPI_BAR +
    PROMPTS_PE_KPI_LINE +
    PROMPTS_WATERFALL +
    PROMPTS_GANTT +
    PROMPTS_SCATTER +
    PROMPTS_COMPARISON +
    PROMPTS_PROCESS +
    PROMPTS_DONUT_KPI +
    PROMPTS_LINE_FULL +
    PROMPTS_THREE_COL +
    PROMPTS_KPIS_ONLY +
    PROMPTS_TABLE +
    PROMPTS_MIXED
)


# ── API call ───────────────────────────────────────────────────────────────────
def call_api(prompt: str) -> dict:
    from dotenv import load_dotenv
    from openai import AzureOpenAI

    load_dotenv()
    load_dotenv(ROOT / "ppt-dataset" / ".env")

    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-12-01-preview",
        azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
    )
    resp = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=1,
        max_completion_tokens=1800,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content.strip()
    return json.loads(raw)


def _make_pair(prompt: str, spec: dict) -> dict:
    return {"messages": [
        {"role": "system",    "content": SYSTEM_PROMPT},
        {"role": "user",      "content": prompt},
        {"role": "assistant", "content": json.dumps(spec, ensure_ascii=False)},
    ]}


# ── Worker ─────────────────────────────────────────────────────────────────────
def process_prompt(args: tuple[int, str, bool]) -> tuple[str, dict | str]:
    idx, prompt, validate = args
    try:
        spec = call_api(prompt)
        if validate:
            sys.path.insert(0, str(Path(__file__).parent))
            from renderer import render_slide
            render_slide(spec)
        return ("ok", _make_pair(prompt, spec))
    except Exception as e:
        return ("err", f"[{idx}] {type(e).__name__}: {str(e)[:120]}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n",        type=int, default=0,
                    help="Max prompts to run (default: all)")
    ap.add_argument("--workers",  type=int, default=5,
                    help="Concurrent API calls")
    ap.add_argument("--validate", action="store_true",
                    help="Render each spec through renderer before saving")
    ap.add_argument("--resume",   action="store_true",
                    help="Skip prompts whose description already exists in output file")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    prompts = ALL_PROMPTS[:]
    random.shuffle(prompts)
    if args.n:
        prompts = prompts[:args.n]

    # Resume: skip already-done descriptions
    if args.resume and OUT_FILE.exists():
        done = set()
        for line in OUT_FILE.read_text(encoding="utf-8").splitlines():
            try:
                p = json.loads(line)
                done.add(p["messages"][1]["content"])
            except Exception:
                pass
        before = len(prompts)
        prompts = [p for p in prompts if p not in done]
        print(f"Resume: skipping {before - len(prompts)} already-done prompts")

    print(f"Generating {len(prompts)} pairs with {args.workers} workers...")
    print(f"Output: {OUT_FILE}\n")

    ok_count = err_count = 0
    tasks = [(i, p, args.validate) for i, p in enumerate(prompts)]

    with open(OUT_FILE, "a", encoding="utf-8") as f:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(process_prompt, t): t for t in tasks}
            for i, fut in enumerate(as_completed(futures)):
                status, result = fut.result()
                if status == "ok":
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                    f.flush()
                    ok_count += 1
                    if ok_count % 10 == 0:
                        print(f"  [{ok_count+err_count}/{len(prompts)}] {ok_count} ok, {err_count} err")
                else:
                    err_count += 1
                    print(f"  FAIL: {result}")

    print(f"\nDone: {ok_count} saved, {err_count} failed -> {OUT_FILE}")
    total_lines = sum(1 for _ in OUT_FILE.open(encoding="utf-8")) if OUT_FILE.exists() else 0
    print(f"Total in file: {total_lines} pairs")


if __name__ == "__main__":
    main()
