"""
Build a sourced research/data pack for prompt-driven deck generation.

The output sits between deck planning and PPTX materialization:

  prompt + deck_plan.json
      -> research_data_pack_*.json
      -> materialize_plan_spec.py --data-pack ...

This layer is intentionally deterministic and API-free. It uses web search when
available, extracts metric-like evidence snippets, scores source quality, audits
coverage against recipe needs, then emits chart-ready data keyed by recipe ID.

Usage:
    python prototypes/research_synthesis.py "AI transformation in Indian banking" \
      --plan prototypes/output/deck_plan_ai_transformation_in_indian_banking.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from common import ensure_output_dir

OUT_DIR = ensure_output_dir()
USER_AGENT = "PPTDatasetResearchBot/1.0 (local consulting deck research prototype)"

try:  # Optional at runtime, present on this machine.
    from ddgs import DDGS  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    DDGS = None


@dataclass(frozen=True)
class MetricNeed:
    id: str
    label: str
    keywords: tuple[str, ...]
    preferred_units: tuple[str, ...]
    chart_roles: tuple[str, ...]


METRIC_NEEDS: tuple[MetricNeed, ...] = (
    MetricNeed(
        "market_size",
        "Market/value pool size",
        ("market size", "value pool", "opportunity", "revenue", "profit pool", "assets", "inr", "billion"),
        ("INR bn", "USD bn", "bn", "%"),
        ("exec_summary", "waterfall", "area"),
    ),
    MetricNeed(
        "adoption",
        "Adoption scale and use-case penetration",
        ("adoption", "use cases", "production", "deployment", "digital", "ai adoption", "gen ai"),
        ("%", "count", "index"),
        ("bar", "slopegraph", "metric_table"),
    ),
    MetricNeed(
        "investment",
        "Investment intensity and capability maturity",
        ("investment", "spending", "technology spend", "capex", "opex", "maturity", "readiness"),
        ("%", "INR bn", "USD bn", "index"),
        ("bubble", "matrix"),
    ),
    MetricNeed(
        "risk_controls",
        "Risk, compliance, controls and governance",
        ("risk", "compliance", "governance", "fraud", "control", "model risk", "cyber"),
        ("%", "score", "index"),
        ("heatmap", "metric_table"),
    ),
    MetricNeed(
        "operations",
        "Operating model and productivity improvement",
        ("productivity", "automation", "cycle time", "cost", "efficiency", "operations", "service"),
        ("%", "INR bn", "index"),
        ("waterfall", "bar", "area"),
    ),
    MetricNeed(
        "portfolio_mix",
        "Portfolio/resource allocation mix",
        ("allocation", "portfolio", "mix", "share", "segment", "customer", "product"),
        ("%", "share"),
        ("dualdoughnut", "stackedbar"),
    ),
)

QUERY_INTENTS = (
    "{topic} market size banking AI India report",
    "{topic} AI adoption banking India survey",
    "{topic} banking technology investment India",
    "{topic} fraud risk compliance AI banking India",
    "{topic} generative AI banking productivity value pool",
    "{topic} Indian banking digital transformation statistics",
)

HIGH_TRUST_DOMAINS = (
    "rbi.org.in",
    "npci.org.in",
    "iba.org.in",
    "niti.gov.in",
    "meity.gov.in",
    "bis.org",
    "worldbank.org",
    "imf.org",
    "mckinsey.com",
    "bcg.com",
    "bain.com",
    "deloitte.com",
    "accenture.com",
    "rolandberger.com",
    "pwc.in",
    "ey.com",
    "kpmg.com",
)

LOW_TRUST_HINTS = (
    "blogspot.",
    "medium.com",
    "reddit.com",
    "quora.com",
    "wikipedia.org",
    "linkedin.com",
    "slideshare.net",
    "scribd.com",
)

NUMBER_RE = re.compile(
    r"(?P<prefix>INR|Rs\.?|₹|USD|US\$)?\s*"
    r"(?P<value>\d+(?:,\d{2,3})*(?:\.\d+)?)\s*"
    r"(?P<unit>%|percent|percentage|bn|billion|mn|million|trillion|crore|lakh|x|pp)?",
    re.IGNORECASE,
)


def slugify(value: str, limit: int = 72) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug[:limit] or "research_pack"


def domain_for(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def source_quality(url: str, title: str = "") -> float:
    domain = domain_for(url)
    score = 0.35
    if any(domain.endswith(d) for d in HIGH_TRUST_DOMAINS):
        score += 0.45
    if url.lower().endswith(".pdf"):
        score += 0.12
    if any(hint in domain for hint in LOW_TRUST_HINTS):
        score -= 0.45
    if re.search(r"report|survey|insight|annual|statistics|index|pdf", f"{title} {url}", re.I):
        score += 0.08
    return max(0.05, min(1.0, score))


def build_research_plan(topic: str, plan: dict[str, Any] | None) -> dict[str, Any]:
    recipe_ids = [s.get("recipe_id") for s in (plan or {}).get("slides", []) if isinstance(s, dict)]
    required_roles = sorted({role for need in METRIC_NEEDS for role in need.chart_roles})
    return {
        "topic": topic,
        "recipe_ids": recipe_ids,
        "metric_needs": [asdict(need) for need in METRIC_NEEDS],
        "required_chart_roles": required_roles,
        "query_intents": [template.format(topic=topic) for template in QUERY_INTENTS],
        "source_policy": {
            "prefer": list(HIGH_TRUST_DOMAINS),
            "avoid": list(LOW_TRUST_HINTS),
            "minimum_source_quality_for_evidence": 0.35,
        },
    }


def search_sources(topic: str, max_results: int, delay: float) -> list[dict[str, Any]]:
    queries = [template.format(topic=topic) for template in QUERY_INTENTS]
    if DDGS is None:
        return []

    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    with DDGS() as ddgs:
        for query in queries:
            try:
                results = ddgs.text(query, max_results=max_results)
            except Exception:
                results = []
            for result in results or []:
                url = result.get("href") or result.get("url") or ""
                if not url or url in seen:
                    continue
                seen.add(url)
                title = result.get("title") or ""
                body = result.get("body") or result.get("snippet") or ""
                candidates.append(
                    {
                        "query": query,
                        "title": title,
                        "url": url,
                        "snippet": body,
                        "domain": domain_for(url),
                        "source_quality": source_quality(url, title),
                    }
                )
            time.sleep(delay)
    return sorted(candidates, key=lambda item: item["source_quality"], reverse=True)


def fetch_text(url: str, timeout: int = 10) -> str:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        return ""
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    return text[:120_000]


def classify_metric(context: str) -> tuple[str, float]:
    lowered = context.lower()
    best_id = "general"
    best_score = 0.0
    for need in METRIC_NEEDS:
        hits = sum(1 for keyword in need.keywords if keyword in lowered)
        score = hits / max(1, len(need.keywords))
        if score > best_score:
            best_id = need.id
            best_score = score
    return best_id, best_score


def parse_number(match: re.Match[str]) -> tuple[float | None, str]:
    raw_value = match.group("value").replace(",", "")
    try:
        value = float(raw_value)
    except ValueError:
        return None, ""
    prefix = (match.group("prefix") or "").strip()
    unit = (match.group("unit") or "").strip()
    if prefix in {"₹", "Rs.", "Rs", "INR"} and not unit:
        unit = "INR"
    elif prefix in {"USD", "US$"} and not unit:
        unit = "USD"
    if unit.lower() == "percent":
        unit = "%"
    return value, unit


def preferred_unit_score(metric_id: str, unit: str) -> float:
    need = next((item for item in METRIC_NEEDS if item.id == metric_id), None)
    if not need:
        return 0.0
    unit_l = unit.lower()
    preferred = {u.lower() for u in need.preferred_units}
    if unit_l in preferred:
        return 0.18
    if unit_l == "%" and "%" in preferred:
        return 0.18
    if unit_l in {"bn", "billion", "crore"} and any(u.lower().endswith("bn") or u.lower() == "bn" for u in preferred):
        return 0.12
    return 0.0


def reject_numeric_artifact(value: float, unit: str, context: str) -> bool:
    lowered = context.lower()
    if "doi" in lowered or "10." in str(value):
        return True
    if not unit and 1900 <= value <= 2100:
        return True
    if not unit and ("index" not in lowered or value < 20 or value > 100):
        return True
    if not unit and any(token in lowered for token in ("chapter", "figure", "page", "section", "top ", "no.")):
        return True
    if unit.lower() in {"x", "pp"}:
        return False
    return False


def extract_evidence_from_text(source: dict[str, Any], text: str, max_per_source: int) -> list[dict[str, Any]]:
    combined = f"{source.get('title', '')}. {source.get('snippet', '')}. {text}"
    evidence: list[dict[str, Any]] = []
    for match in NUMBER_RE.finditer(combined):
        value, unit = parse_number(match)
        if value is None:
            continue
        if not unit and value > 3000:
            continue
        start = max(0, match.start() - 150)
        end = min(len(combined), match.end() + 170)
        context = combined[start:end].strip()
        metric_id, metric_score = classify_metric(context)
        if metric_id == "general" or metric_score <= 0:
            continue
        if reject_numeric_artifact(value, unit, context):
            continue
        unit_boost = preferred_unit_score(metric_id, unit or "number")
        confidence = round(min(0.95, source["source_quality"] * 0.68 + metric_score * 0.42 + unit_boost), 2)
        evidence.append(
            {
                "metric_id": metric_id,
                "metric_label": next((n.label for n in METRIC_NEEDS if n.id == metric_id), metric_id),
                "figure": match.group(0).strip(),
                "value": value,
                "unit": unit or "number",
                "context": context,
                "source_title": source.get("title", ""),
                "source_url": source.get("url", ""),
                "source_domain": source.get("domain", ""),
                "source_quality": source.get("source_quality", 0),
                "confidence": confidence,
            }
        )
    evidence.sort(key=lambda item: (item["confidence"], item["source_quality"]), reverse=True)
    return evidence[:max_per_source]


def collect_evidence(candidates: list[dict[str, Any]], fetch_limit: int, max_per_source: int, delay: float) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for source in candidates[:fetch_limit]:
        text = ""
        try:
            text = fetch_text(source["url"])
        except Exception as exc:
            source["fetch_error"] = str(exc)
        combined_text = text or source.get("snippet", "")
        evidence.extend(extract_evidence_from_text(source, combined_text, max_per_source))
        time.sleep(delay)
    deduped = []
    seen: set[tuple[str, str, str]] = set()
    for item in sorted(evidence, key=lambda x: x["confidence"], reverse=True):
        key = (item["metric_id"], item["figure"], item["source_domain"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def metric_best(evidence: list[dict[str, Any]], metric_id: str, default: float) -> dict[str, Any]:
    matches = [e for e in evidence if e["metric_id"] == metric_id]
    if not matches:
        return {"value": default, "confidence": 0.25, "source": "Prototype synthesis fallback"}
    best = matches[0]
    return {"value": best["value"], "confidence": best["confidence"], "source": best["source_domain"]}


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def rounded(value: float) -> int:
    return int(round(value))


def source_note(evidence: list[dict[str, Any]], fallback: str) -> str:
    domains = []
    for item in evidence:
        domain = item.get("source_domain")
        if domain and domain not in domains:
            domains.append(domain)
        if len(domains) >= 3:
            break
    if not domains:
        return f"Source: {fallback}"
    return f"Source: synthesized from {', '.join(domains)}"


def synthesize_chart_data(topic: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    market = metric_best(evidence, "market_size", 72)
    adoption = metric_best(evidence, "adoption", 38)
    investment = metric_best(evidence, "investment", 2.7)
    risk = metric_best(evidence, "risk_controls", 55)
    operations = metric_best(evidence, "operations", 18)
    portfolio = metric_best(evidence, "portfolio_mix", 34)

    base_value = rounded(clamp(market["value"], 35, 120))
    target_value = rounded(base_value * 1.55)
    adoption_base = rounded(clamp(adoption["value"], 18, 55))
    adoption_target = rounded(clamp(adoption_base + 36, 58, 86))
    risk_score = rounded(clamp(risk["value"], 25, 80))
    invest_intensity = clamp(investment["value"], 0.8, 5.0)
    ops_gain = rounded(clamp(operations["value"], 8, 24))
    portfolio_share = rounded(clamp(portfolio["value"], 18, 42))
    note = source_note(evidence, "prototype synthesis; replace with verified figures before external use")

    waterfall_gain_1 = ops_gain
    waterfall_gain_2 = rounded(clamp(ops_gain * 0.78, 8, 20))
    waterfall_gain_3 = rounded(clamp(risk_score / 7, 6, 14))
    waterfall_cost = -rounded(clamp((waterfall_gain_1 + waterfall_gain_2 + waterfall_gain_3) * 0.24, 8, 16))
    target_bridge = base_value + waterfall_gain_1 + waterfall_gain_2 + waterfall_gain_3 + waterfall_cost

    current_mix = [portfolio_share, 22, 15, 10, 9, max(4, 44 - portfolio_share)]
    target_mix = [max(18, portfolio_share - 10), 18, 17, 16, 18, 7]
    target_mix[-1] += 100 - sum(target_mix)

    return {
        "rb_exec_summary_dense": {
            "boxes": [
                {"org": "Value pool", "value": f"INR {target_bridge} bn", "description": "Target run-rate value after scaling priority journeys and governance controls."},
                {"org": "Adoption scale", "value": f"{adoption_target}%", "description": "Target operating-model coverage across priority AI-enabled journeys."},
                {"org": "Investment intensity", "value": f"{invest_intensity:.1f}x", "description": "Relative maturity/investment index used for benchmark positioning."},
                {"org": "Risk controls", "value": f"{risk_score}%", "description": "Model-risk and governance control readiness proxy for scaling."},
            ],
            "source": note,
        },
        "hybrid_metric_table": {
            "columns": ["Metric", "Today", "Target", "Delta", "Management implication"],
            "rows": [
                ["AI operating-model coverage", f"{adoption_base}%", f"{adoption_target}%", f"+{adoption_target - adoption_base} pp", "Move from pilots to governed journey-level scaling"],
                ["Run-rate value captured", f"INR {base_value} bn", f"INR {target_bridge} bn", f"+INR {target_bridge - base_value} bn", "Fund the use cases with measurable P&L ownership"],
                ["Investment / maturity index", f"{invest_intensity:.1f}", f"{min(5.0, invest_intensity + 1.4):.1f}", "+1.4 pts", "Sequence spend behind reusable data and model operations"],
                ["Control readiness", f"{risk_score}%", f"{min(90, risk_score + 22)}%", f"+{min(90, risk_score + 22) - risk_score} pp", "Scale explainability, monitoring, and audit evidence"],
                ["Operational uplift", f"{ops_gain}%", f"{min(40, ops_gain + 12)}%", "+12 pp", "Prioritize high-volume service, credit and risk decisions"],
            ],
            "source": note,
        },
        "bain_value_waterfall": {
            "baseline_label": "Current run-rate value",
            "target_label": "Target value pool",
            "unit": "INR bn",
            "items": [
                {"label": "Current", "value": base_value, "kind": "total"},
                {"label": "Service automation", "value": waterfall_gain_1, "kind": "increase"},
                {"label": "Credit decisioning", "value": waterfall_gain_2, "kind": "increase"},
                {"label": "Fraud/risk controls", "value": waterfall_gain_3, "kind": "increase"},
                {"label": "Tech + change cost", "value": waterfall_cost, "kind": "decrease"},
                {"label": "Target", "value": target_bridge, "kind": "total"},
            ],
            "callouts": [
                {"label": f"+{rounded(((target_bridge / base_value) - 1) * 100)}%", "body": "net value uplift after investment and change cost"},
                {"label": "3 levers", "body": "service, credit, and risk account for most modeled impact"},
            ],
            "source": note,
        },
        "rb_rail_panel_bar": {
            "categories": ["Service", "Credit", "Risk", "Sales", "Operations"],
            "series": [
                {"name": "Current", "values": [adoption_base, max(20, adoption_base - 6), risk_score - 12, max(18, adoption_base - 10), max(22, adoption_base - 4)]},
                {"name": "Target", "values": [adoption_target, adoption_target - 8, min(86, risk_score + 20), adoption_target - 15, adoption_target - 6]},
            ],
            "bar_direction": "bar",
            "x_axis": "Adoption / readiness index",
            "source": note,
        },
        "rb_rail_panel_scatter": {
            "x": [0.6, 0.9, 1.2, 1.6, 1.9, 2.2, 2.6, invest_intensity, 3.2, 3.5, 3.8, 4.1, 4.4],
            "y": [34, 39, 43, 47, 50, 52, 56, min(74, risk_score + 4), 62, 65, 67, 69, 71],
            "sizes": [8, 9, 11, 12, 13, 13, 15, 17, 18, 20, 22, 23, 24],
            "labels": [["Leaders", 3.8, 67], ["Scaled banks", invest_intensity, min(74, risk_score + 4)], ["Pilots", 1.7, 48], ["Laggards", 0.6, 34]],
            "x_axis": "AI investment intensity",
            "y_axis": "Digital maturity index",
            "x_min": 0,
            "x_max": 5,
            "y_min": 30,
            "y_max": 75,
            "y_major_unit": 10,
            "x_major_unit": 1,
            "source": note,
        },
        "deloitte_risk_heatmap": {
            "columns": ["Value", "Readiness", "Data", "Risk", "Scale"],
            "rows": [
                {"name": "Service operations", "scores": [5, 4, 4, 3, 5], "note": "High-volume journeys with mature automation playbooks"},
                {"name": "Credit underwriting", "scores": [5, 3, 3, 5, 4], "note": "Requires explainability, policy controls and audit trails"},
                {"name": "Collections", "scores": [4, 4, 3, 4, 4], "note": "Good economics, sensitive customer treatment"},
                {"name": "Marketing next best action", "scores": [3, 5, 4, 3, 5], "note": "Fast adoption but lower standalone value"},
                {"name": "Compliance monitoring", "scores": [4, 2, 3, 5, 3], "note": "Control-heavy, high governance need"},
            ],
            "legend": ["1 low", "3 medium", "5 high"],
            "source": note,
        },
        "bcg_growth_share_matrix": {
            "x_axis": "Implementation readiness",
            "y_axis": "Economic value at stake",
            "quadrants": ["Selectively invest", "Scale now", "Fix foundations", "Defer / monitor"],
            "items": [
                {"label": "Service AI", "x": 78, "y": min(90, 65 + ops_gain), "size": 18},
                {"label": "Credit AI", "x": 58, "y": 88, "size": 20},
                {"label": "Fraud AI", "x": 64, "y": min(86, risk_score + 10), "size": 14},
                {"label": "Marketing AI", "x": 84, "y": 52, "size": 12},
                {"label": "Compliance AI", "x": 38, "y": min(82, risk_score), "size": 13},
                {"label": "Treasury AI", "x": 32, "y": 42, "size": 9},
            ],
            "source": note,
        },
        "hybrid_slopegraph_shift": {
            "left_label": "Current adoption",
            "right_label": "Target coverage",
            "items": [
                {"label": "Service", "left": adoption_base, "right": adoption_target},
                {"label": "Risk", "left": max(20, risk_score - 18), "right": min(86, risk_score + 16)},
                {"label": "Credit", "left": max(18, adoption_base - 8), "right": adoption_target - 8},
                {"label": "Operations", "left": max(20, adoption_base - 4), "right": adoption_target - 10},
                {"label": "Marketing", "left": min(55, adoption_base + 6), "right": adoption_target - 16},
                {"label": "Compliance", "left": max(14, risk_score - 35), "right": min(78, risk_score + 8)},
            ],
            "source": note,
        },
        "accenture_area_trend": {
            "categories": ["2024", "2025", "2026", "2027", "2028", "2029", "2030"],
            "series": [
                {"name": "Efficiency", "values": [6, 8, 11, 13, 15, 17, 18]},
                {"name": "Risk + controls", "values": [2, 4, 6, 8, 10, 11, 12]},
                {"name": "Revenue growth", "values": [1, 3, 5, 8, 12, 16, 19]},
                {"name": "New propositions", "values": [0, 1, 3, 5, 8, 11, 15]},
            ],
            "y_axis": "Indexed value pool",
            "y_max": 70,
            "callout": "Total value pool expands from 9 to 64 index points",
            "source": note,
        },
        "rb_dual_donut_comparison": {
            "left": {"year": "Today", "labels": ["Customer ops", "Risk", "Marketing", "Product", "Technology", "Other"], "values": current_mix},
            "right": {"year": "Target", "labels": ["Customer ops", "Risk", "Marketing", "Product", "Technology", "Other"], "values": target_mix},
            "source": note,
        },
        "rb_full_width_stacked_bar": {
            "categories": ["2024", "2026", "2028", "2030"],
            "series": [
                {"name": "Efficiency", "values": [7, 10, 13, 16]},
                {"name": "Risk control", "values": [3, 5, 7, 9]},
                {"name": "Revenue growth", "values": [2, 5, 9, 14]},
                {"name": "New propositions", "values": [1, 3, 6, 10]},
            ],
            "axis_max": 55,
            "total_labels": {"2024": "13", "2026": "23", "2028": "35", "2030": "49"},
            "growth_label": "3.8x value pool growth",
            "y_axis": "Indexed value pool",
            "source": note,
        },
    }


def coverage_audit(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    by_metric: dict[str, list[dict[str, Any]]] = {need.id: [] for need in METRIC_NEEDS}
    for item in evidence:
        if item["metric_id"] in by_metric:
            by_metric[item["metric_id"]].append(item)
    covered = {
        need.id: {
            "label": need.label,
            "evidence_count": len(by_metric[need.id]),
            "best_confidence": max((e["confidence"] for e in by_metric[need.id]), default=0),
            "covered": any(e["confidence"] >= 0.45 for e in by_metric[need.id]),
        }
        for need in METRIC_NEEDS
    }
    covered_count = sum(1 for item in covered.values() if item["covered"])
    return {
        "covered_metric_count": covered_count,
        "total_metric_count": len(METRIC_NEEDS),
        "coverage_ratio": round(covered_count / len(METRIC_NEEDS), 2),
        "metrics": covered,
        "status": "sourced" if covered_count >= 3 else "prototype_synthesis_with_source_snippets",
    }


def write_markdown(pack: dict[str, Any], path: Path) -> None:
    audit = pack["coverage_audit"]
    lines = [
        f"# Research Data Pack: {pack['topic']}",
        "",
        f"Created: {pack['created_at']}",
        f"Mode: {pack['mode']}",
        f"Coverage: {audit['covered_metric_count']}/{audit['total_metric_count']} metric groups",
        "",
        "## Metric Coverage",
    ]
    for metric_id, item in audit["metrics"].items():
        mark = "covered" if item["covered"] else "fallback"
        lines.append(f"- {metric_id}: {mark}, evidence={item['evidence_count']}, confidence={item['best_confidence']}")
    lines.extend(["", "## Top Evidence"])
    for item in pack["evidence"][:12]:
        lines.append(f"- {item['metric_id']} | {item['figure']} | {item['source_domain']} | conf={item['confidence']}")
    lines.extend(["", "## Chart Data Keys"])
    lines.extend(f"- {key}" for key in pack["chart_data_by_recipe"].keys())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_pack(args: argparse.Namespace) -> dict[str, Any]:
    plan = None
    if args.plan:
        plan_path = Path(args.plan)
        if not plan_path.is_absolute():
            plan_path = Path.cwd() / plan_path
        if plan_path.exists():
            plan = json.loads(plan_path.read_text(encoding="utf-8"))

    topic = args.topic or (plan or {}).get("input_prompt")
    if not topic:
        raise SystemExit("Provide a topic or a plan JSON with input_prompt.")

    research_plan = build_research_plan(topic, plan)
    candidates = [] if args.no_search else search_sources(topic, args.max_results, args.delay)
    candidates = [c for c in candidates if c["source_quality"] >= args.min_source_quality]
    evidence = collect_evidence(candidates, args.fetch_limit, args.max_evidence_per_source, args.delay) if candidates else []
    audit = coverage_audit(evidence)
    mode = audit["status"] if evidence else "prototype_synthesis_no_search_results"
    chart_data = synthesize_chart_data(topic, evidence)

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "topic": topic,
        "mode": mode,
        "plan_path": args.plan,
        "research_plan": research_plan,
        "source_candidates": candidates,
        "evidence": evidence,
        "coverage_audit": audit,
        "chart_data_by_recipe": chart_data,
        "notes": [
            "Use chart_data_by_recipe directly in materialize_plan_spec.py.",
            "Evidence extraction is heuristic and should be reviewed before external use.",
            "Fallback synthesis keeps the deck pipeline alive but is marked in coverage_audit.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a sourced research/data pack for deck generation.")
    parser.add_argument("topic", nargs="?", help="Deck topic; optional if --plan contains input_prompt")
    parser.add_argument("--plan", default=None, help="Deck plan JSON to align metric needs with recipe IDs")
    parser.add_argument("--out", default=None, help="Output JSON path")
    parser.add_argument("--max-results", type=int, default=4, help="Search results per query")
    parser.add_argument("--fetch-limit", type=int, default=12, help="Number of candidate pages to fetch")
    parser.add_argument("--max-evidence-per-source", type=int, default=5)
    parser.add_argument("--min-source-quality", type=float, default=0.35)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--no-search", action="store_true", help="Skip web search and emit fallback synthesis")
    args = parser.parse_args()

    pack = build_pack(args)
    out_path = Path(args.out) if args.out else OUT_DIR / f"research_data_pack_{slugify(pack['topic'])}.json"
    if not out_path.is_absolute():
        out_path = Path.cwd() / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    md_path = out_path.with_suffix(".md")
    write_markdown(pack, md_path)

    audit = pack["coverage_audit"]
    print(f"Wrote {out_path}")
    print(f"Wrote {md_path}")
    print(f"Mode: {pack['mode']}")
    print(f"Coverage: {audit['covered_metric_count']}/{audit['total_metric_count']} metric groups")
    print(f"Sources: {len(pack['source_candidates'])}; evidence objects: {len(pack['evidence'])}")


if __name__ == "__main__":
    main()
