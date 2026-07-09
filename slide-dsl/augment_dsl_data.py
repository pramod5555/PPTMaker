"""
augment_dsl_data.py — Balance the DSL training dataset.

Current distribution (1,660 pairs):
  content : 1,568  (94.5%) — fine
  cover   :    48  ( 2.9%) — needs more
  chapter :    40  ( 2.4%) — needs more
  cta     :     4  ( 0.2%) — critically underrepresented

This script generates ~300 new pairs (chapter, cover, cta) using Azure OpenAI,
validates each through renderer.py, and appends to the training JSONL files.

Target after augmentation:
  content : ~1,560 (75%)
  chapter :   ~220 (11%)
  cover   :   ~155  (7%)
  cta     :   ~115  (6%)

Usage:
    python slide-dsl/augment_dsl_data.py
    python slide-dsl/augment_dsl_data.py --n-chapter 80 --n-cover 50 --n-cta 40  # quick test
    python slide-dsl/augment_dsl_data.py --dry-run   # print prompts only, no API calls
"""
from __future__ import annotations
import argparse, json, os, random, sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from generate import generate_api, SYSTEM_PROMPT
from renderer import render_slide

TRAIN_FILE = Path(__file__).parent / "mlx_data" / "train.jsonl"
VAL_FILE   = Path(__file__).parent / "mlx_data" / "valid.jsonl"

# ── Prompt libraries ───────────────────────────────────────────────────────────

CHAPTER_PROMPTS = [
    # Business strategy
    "[CHAPTER] Section divider: Market Landscape & Competitive Dynamics",
    "[CHAPTER] Section divider: Financial Performance Overview",
    "[CHAPTER] Section divider: Strategic Priorities for 2025",
    "[CHAPTER] Section divider: Revenue Growth Drivers",
    "[CHAPTER] Section divider: Cost Optimisation & Efficiency",
    "[CHAPTER] Section divider: M&A Pipeline & Deal Activity",
    "[CHAPTER] Section divider: Digital Transformation Roadmap",
    "[CHAPTER] Section divider: Operational Excellence",
    "[CHAPTER] Section divider: Risk Assessment & Mitigation",
    "[CHAPTER] Section divider: ESG & Sustainability Strategy",
    "[CHAPTER] Section divider: Talent & Organisation",
    "[CHAPTER] Section divider: Technology & Innovation",
    "[CHAPTER] Section divider: Customer Experience & NPS",
    "[CHAPTER] Section divider: Supply Chain Resilience",
    "[CHAPTER] Section divider: Geographic Expansion",
    "[CHAPTER] Section divider: Portfolio Review",
    "[CHAPTER] Section divider: Capital Allocation Framework",
    "[CHAPTER] Section divider: Investor Relations Update",
    "[CHAPTER] Section divider: Go-to-Market Strategy",
    "[CHAPTER] Section divider: Product Roadmap",
    # Industry specific
    "[CHAPTER] Section 02: Healthcare Market Trends",
    "[CHAPTER] Section 03: Energy Transition Outlook",
    "[CHAPTER] Section 01: Private Equity Deal Flow",
    "[CHAPTER] Section 04: Real Estate Portfolio Analysis",
    "[CHAPTER] Section 02: Automotive Electrification",
    "[CHAPTER] Section 03: Financial Services Regulation",
    "[CHAPTER] Section 02: Logistics & Supply Chain",
    "[CHAPTER] Section 04: Consumer Goods Pricing",
    "[CHAPTER] Section 01: Technology Sector Valuation",
    "[CHAPTER] Section 03: Infrastructure Investment",
    # Operations & execution
    "[CHAPTER] Chapter: Implementation & Execution Plan",
    "[CHAPTER] Chapter: Findings & Diagnostics",
    "[CHAPTER] Chapter: Recommendations",
    "[CHAPTER] Chapter: Next Steps & Governance",
    "[CHAPTER] Chapter: Scenario Analysis",
    "[CHAPTER] Chapter: Benchmarking Results",
    "[CHAPTER] Chapter: Stakeholder Analysis",
    "[CHAPTER] Chapter: Quick Wins vs. Long-term Initiatives",
    "[CHAPTER] Chapter: Investment Case",
    "[CHAPTER] Chapter: Commercial Due Diligence",
    # Numbered sections
    "[CHAPTER] Create a chapter divider for section 01 titled 'Market Context'",
    "[CHAPTER] Create a chapter divider for section 02 titled 'Competitive Position'",
    "[CHAPTER] Create a chapter divider for section 03 titled 'Growth Opportunities'",
    "[CHAPTER] Create a chapter divider for section 04 titled 'Financial Projections'",
    "[CHAPTER] Create a chapter divider for section 05 titled 'Strategic Options'",
    "[CHAPTER] Create a chapter divider for section 06 titled 'Recommendations'",
    "[CHAPTER] Create a chapter divider for section 01 titled 'Executive Briefing'",
    "[CHAPTER] Create a chapter divider for section 02 titled 'Deep Dive Analysis'",
    "[CHAPTER] Create a chapter divider for section 03 titled 'Implications'",
    "[CHAPTER] Create a chapter divider for section 04 titled 'Roadmap'",
    # With kicker context
    "[CHAPTER] Chapter divider with kicker 'Q3 2025 Update' and title 'Revenue Performance'",
    "[CHAPTER] Chapter divider with kicker 'Confidential' and title 'Board Strategy Review'",
    "[CHAPTER] Chapter divider with kicker 'Draft — For Discussion' and title 'Cost Reduction Options'",
    "[CHAPTER] Chapter divider with kicker 'FY2025 Results' and title 'Business Unit Performance'",
    "[CHAPTER] Chapter divider with kicker 'Market Intelligence' and title 'Competitor Activity'",
    "[CHAPTER] Chapter divider with kicker 'Internal' and title 'Organisational Restructuring'",
    "[CHAPTER] Chapter divider with kicker 'Project Alpha' and title 'Integration Workstream'",
    "[CHAPTER] Chapter divider with kicker 'Due Diligence' and title 'Target Company Assessment'",
    # Simple imperative forms
    "Create a chapter divider slide for the section on Digital Innovation",
    "Create a chapter divider slide for the Financials section",
    "Create a chapter divider slide for the Market Overview section",
    "Create a chapter divider slide for the Strategic Outlook section",
    "Create a chapter divider slide titled 'Appendix'",
    "Create a chapter divider slide titled 'Methodology & Data Sources'",
    "Create a chapter divider slide with title 'Growth Strategy' and section number 3",
    "Create a chapter divider slide for Part II: Execution",
    "Section header slide: 'Key Findings'",
    "Section header slide: 'Operational Assessment'",
]

COVER_PROMPTS = [
    # Management consulting decks
    "Cover slide for a deck titled 'Private Equity Market Outlook 2025'",
    "Cover slide for a deck titled 'Digital Transformation Strategy: A 3-Year Roadmap'",
    "Cover slide for a management consulting deck on 'Healthcare Sector M&A Activity 2025'",
    "Cover slide for 'European Automotive Industry Disruption: EV Transition Analysis'",
    "Cover slide for 'Global Supply Chain Resilience: Post-Pandemic Restructuring'",
    "Cover slide for 'AI Adoption in Financial Services: Benchmarks & Best Practices'",
    "Cover slide for 'Real Estate Investment Outlook: APAC Markets 2025'",
    "Cover slide for 'Retail Sector Consolidation: Strategic Options for Mid-Market Players'",
    "Cover slide for 'Energy Transition Capital: Green Infrastructure Investment Thesis'",
    "Cover slide for 'Consumer Goods Pricing Under Inflation: Strategies That Work'",
    # Board & investor decks
    "Cover slide for a board presentation titled 'Q3 2025 Business Review'",
    "Cover slide for an investor day deck: 'Creating Sustainable Value: 2025–2028 Strategy'",
    "Cover slide for an earnings presentation: 'FY2025 Full Year Results'",
    "Cover slide for a capital markets day: 'Accelerating Growth Through Innovation'",
    "Cover slide for an IPO roadshow deck: 'Building the Future of Industrial Logistics'",
    # Strategy & operations
    "Cover slide for a strategy deck: 'Winning in a Disrupted Market: Three Imperatives'",
    "Cover slide for an operational review: 'Efficiency Programme — Year 2 Progress'",
    "Cover slide for a commercial due diligence report on TechCo Acquisition",
    "Cover slide for a cost transformation programme: 'Project Phoenix'",
    "Cover slide for a market entry analysis: 'Southeast Asia Expansion Feasibility'",
    # Sector-specific
    "Cover slide for an infrastructure deck: 'Ports & Logistics: Investment Case'",
    "Cover slide for a fintech report: 'Embedded Finance: Market Sizing & Player Landscape'",
    "Cover slide for a pharma deck: 'Gene Therapy Pipeline: Valuation & Risk Assessment'",
    "Cover slide for a retail deck: 'Omnichannel Strategy: Closing the Digital Gap'",
    "Cover slide for a mobility deck: 'Future of Urban Logistics: Last-Mile Innovation'",
    # With metadata
    "Cover slide for 'Talent Strategy 2025' prepared for the CHRO",
    "Cover slide for 'Technology Architecture Review' prepared for the CTO",
    "Cover slide for 'Risk Management Framework Update' prepared for Audit Committee",
    "Cover slide titled 'Market Intelligence Briefing' for executive leadership",
    "Cover slide for a client pitch: 'Unlocking €2B in Untapped Revenue'",
]

CTA_PROMPTS = [
    # Generic consulting close
    "Closing CTA slide for a strategy deck: key next steps are to finalise business case, appoint programme lead, and launch pilot in Q1",
    "Closing slide with three immediate actions: engage board, mobilise task force, set 90-day milestones",
    "Call-to-action slide: recommend three workstreams — data infrastructure, talent hiring, and operating model redesign",
    "CTA slide: next steps are to approve budget allocation, select technology vendor, and begin Phase 1 by March 2025",
    "Closing slide for a market entry deck: recommended actions are conduct pilot in two regions, build local partnerships, appoint country manager",
    "CTA slide for M&A deck: initiate exclusivity, complete legal due diligence, and finalise integration blueprint by end of Q2",
    "Closing slide: three priorities — protect core business margins, invest in digital capabilities, explore bolt-on acquisitions",
    "Call-to-action slide for a cost programme: launch diagnostic workstreams, establish governance, deliver first savings within 6 months",
    "Closing slide with headline 'The Window to Act Is Now' and three strategic imperatives for 2025",
    "CTA slide: 'Start Small, Scale Fast' — pilot in two markets, measure, then expand; assign executive sponsor by month-end",
    # Finance & investment
    "Closing slide for investor presentation: recommending strategic review of portfolio, capital reallocation, and ESG disclosure upgrade",
    "CTA slide for PE deck: key actions are to initiate deal, secure financing, and target close by Q3 2025",
    "Closing slide: contact information and request for term sheet approval to proceed to next stage",
    "CTA for capital markets day: three commitments to shareholders for FY26 — revenue target, margin floor, and dividend policy",
    # Sector specific
    "Closing slide for digital transformation deck: pilot AI use cases in finance and operations, then scale to 5 business units",
    "CTA slide for sustainability strategy: set 2030 net-zero target, link exec pay to ESG, publish first TCFD report by June",
    "Closing slide for talent strategy deck: launch employer brand refresh, open 200 senior roles, and build internal academy",
    "CTA for technology deck: migrate critical workloads to cloud by end of year, decommission legacy systems, hire 50 engineers",
    # Minimal / simple close
    "Simple closing slide with the message 'Thank you — Questions?' and a source attribution line",
    "CTA slide with a bold single headline asking leadership to decide on the recommended growth strategy",
    "Closing CTA with three bullet recommended actions and a deadline of end of Q1 for each",
    "Final slide for a board deck: summarise the ask — board approval to proceed, budget of $50M, monthly progress reporting",
    # With specific formats
    "Create a CTA slide with kicker 'Recommended Next Steps' and three numbered action items for a digital transformation programme",
    "Create a closing slide with kicker 'Our Recommendation' stating the company should pursue Option B: organic growth plus one bolt-on",
    "Create a CTA slide with a strong headline and two columns: 'Quick Wins (0–3 months)' and 'Strategic Initiatives (6–18 months)'",
    "Closing slide for an executive briefing with a call to action and deadline — this is the moment to decide",
]

# ── Core generation logic ──────────────────────────────────────────────────────

def make_pair(prompt: str, expected_type: str, max_retries: int = 2) -> dict | None:
    """Call generate_api and return a valid (prompt, spec) pair or None."""
    for attempt in range(max_retries + 1):
        try:
            spec = generate_api(prompt, use_search=False)

            # Type gate
            if spec.get("slide_type") != expected_type:
                print(f"    ✗ wrong type: got '{spec.get('slide_type')}', wanted '{expected_type}'"
                      f"  (attempt {attempt+1})")
                if attempt < max_retries:
                    continue
                return None

            # Render gate — catches schema errors
            render_slide(spec)

            return {
                "messages": [
                    {"role": "system",    "content": SYSTEM_PROMPT},
                    {"role": "user",      "content": prompt},
                    {"role": "assistant", "content": json.dumps(spec, ensure_ascii=False)},
                ]
            }
        except Exception as exc:
            print(f"    ✗ error: {exc}  (attempt {attempt+1})")
            if attempt < max_retries:
                time.sleep(1)
    return None


def generate_batch(
    prompts: list[str],
    expected_type: str,
    target: int,
    val_frac: float = 0.1,
) -> tuple[list[dict], list[dict]]:
    """Generate `target` valid pairs from the prompt pool. Returns (train, val) lists."""
    pool = prompts.copy()
    random.shuffle(pool)
    # Cycle the pool if target > pool size
    while len(pool) < target:
        pool += prompts
    random.shuffle(pool)

    train_pairs, val_pairs = [], []
    needed = target
    i = 0
    while needed > 0 and i < len(pool):
        p = pool[i]; i += 1
        print(f"  [{expected_type}] {len(train_pairs)+len(val_pairs)+1}/{target}  »  {p[:70]}")
        pair = make_pair(p, expected_type)
        if pair is None:
            continue
        # Route to val based on fraction
        total_so_far = len(train_pairs) + len(val_pairs)
        in_val = len(val_pairs) / max(1, total_so_far + 1) < val_frac
        if in_val:
            val_pairs.append(pair)
        else:
            train_pairs.append(pair)
        needed -= 1
        time.sleep(0.3)  # gentle rate limiting

    return train_pairs, val_pairs


def append_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  → wrote {len(records)} pairs to {path.name}")


def count_types(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        st = json.loads(d["messages"][2]["content"]).get("slide_type", "?")
        counts[st] = counts.get(st, 0) + 1
    return counts


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-chapter", type=int, default=180, help="chapter pairs to generate")
    ap.add_argument("--n-cover",   type=int, default=110, help="cover pairs to generate")
    ap.add_argument("--n-cta",     type=int, default=110, help="cta pairs to generate")
    ap.add_argument("--val-frac",  type=float, default=0.1, help="fraction sent to val set")
    ap.add_argument("--dry-run",   action="store_true", help="print prompts only")
    ap.add_argument("--seed",      type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)

    print("Current dataset distribution:")
    for path, label in [(TRAIN_FILE, "train"), (VAL_FILE, "val")]:
        print(f"  {label}: {count_types(path)}")

    if args.dry_run:
        print("\nDRY RUN — sample prompts (no API calls):")
        for p in random.sample(CHAPTER_PROMPTS, 3): print(f"  [chapter] {p}")
        for p in random.sample(COVER_PROMPTS,   3): print(f"  [cover]   {p}")
        for p in random.sample(CTA_PROMPTS,     3): print(f"  [cta]     {p}")
        return

    total_new = args.n_chapter + args.n_cover + args.n_cta
    print(f"\nGenerating {total_new} new pairs "
          f"(chapter:{args.n_chapter}, cover:{args.n_cover}, cta:{args.n_cta})")
    print("This will make API calls — Ctrl-C to stop safely at any point.\n")

    # ── Chapter ───────────────────────────────────────────────────────────────
    print(f"\n── CHAPTER ({args.n_chapter} pairs) ──")
    ch_train, ch_val = generate_batch(CHAPTER_PROMPTS, "chapter", args.n_chapter, args.val_frac)
    append_jsonl(TRAIN_FILE, ch_train)
    append_jsonl(VAL_FILE,   ch_val)

    # ── Cover ─────────────────────────────────────────────────────────────────
    print(f"\n── COVER ({args.n_cover} pairs) ──")
    cv_train, cv_val = generate_batch(COVER_PROMPTS, "cover", args.n_cover, args.val_frac)
    append_jsonl(TRAIN_FILE, cv_train)
    append_jsonl(VAL_FILE,   cv_val)

    # ── CTA ───────────────────────────────────────────────────────────────────
    print(f"\n── CTA ({args.n_cta} pairs) ──")
    ct_train, ct_val = generate_batch(CTA_PROMPTS, "cta", args.n_cta, args.val_frac)
    append_jsonl(TRAIN_FILE, ct_train)
    append_jsonl(VAL_FILE,   ct_val)

    print("\n\nFinal dataset distribution:")
    for path, label in [(TRAIN_FILE, "train"), (VAL_FILE, "val")]:
        print(f"  {label}: {count_types(path)}")
    print("\nDone. Run finetune_unsloth.py next.")


if __name__ == "__main__":
    main()
