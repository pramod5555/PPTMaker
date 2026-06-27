"""
Prompt-to-deck planning scaffold for the high-fidelity generator.

This does not render a PPTX. It creates the generation-ready plan:
  prompt -> slide jobs -> recipe IDs -> Roland Berger-heavy gold anchors.

Usage:
    python prototypes/plan_prompt_deck.py "AI transformation in Indian banking" --slides 10
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from common import ensure_output_dir
from recipe_catalog import RECIPES
from style_profiles import get_profile

OUT_DIR = ensure_output_dir()
GOLD_PATH = OUT_DIR / "gold_style_bank.json"

ROLAND_SEQUENCE = [
    "rb_title_cover",
    "rb_exec_summary_dense",
    "rb_rail_panel_bar",
    "rb_rail_panel_scatter",
    "rb_full_width_stacked_bar",
    "rb_three_pillar_framework",
    "rb_rail_panel_bar",
    "rb_dual_donut_comparison",
    "rb_three_pillar_framework",
    "rb_recommendation_close",
]

HYBRID_SEQUENCE = [
    "rb_title_cover",
    "rb_exec_summary_dense",
    "hybrid_metric_table",
    "rb_rail_panel_bar",
    "bain_value_waterfall",
    "rb_rail_panel_scatter",
    "deloitte_risk_heatmap",
    "bcg_growth_share_matrix",
    "accenture_area_trend",
    "hybrid_slopegraph_shift",
    "rb_dual_donut_comparison",
    "rb_recommendation_close",
]

EVIDENCE_DENSE_SEQUENCE = [
    "rb_title_cover",
    "rb_exec_summary_dense",
    "hybrid_metric_table",
    "rb_rail_panel_bar",
    "bain_value_waterfall",
    "rb_rail_panel_scatter",
    "deloitte_risk_heatmap",
    "bcg_growth_share_matrix",
    "accenture_area_trend",
    "hybrid_slopegraph_shift",
    "rb_dual_donut_comparison",
    "rb_full_width_stacked_bar",
    "hybrid_metric_table",
    "rb_rail_panel_bar",
    "rb_recommendation_close",
]

QUALITY_CONTRACTS = {
    "balanced": {
        "min_data_slides_ratio": 0.65,
        "max_framework_slides": 1,
        "required_chart_types": ["bar", "waterfall", "bubble", "heatmap", "matrix", "area", "slopegraph"],
    },
    "evidence_dense": {
        "min_data_slides_ratio": 0.78,
        "max_framework_slides": 0,
        "required_chart_types": ["bar", "waterfall", "bubble", "heatmap", "matrix", "area", "slopegraph", "dualdoughnut", "metric_table"],
    },
}

SLIDE_JOBS = [
    "Frame the strategic question and thesis",
    "Summarize the executive argument",
    "Establish the quantified baseline and target",
    "Compare priority segments or initiatives",
    "Bridge baseline value to target value through drivers",
    "Map the relationship between investment and maturity",
    "Assess risk, readiness, and governance bottlenecks",
    "Position opportunities in a strategic choice matrix",
    "Show multi-year value pool expansion",
    "Show rank or adoption shift between periods",
    "Show portfolio/share shift or resource allocation",
    "Close with decisions, imperatives, and next steps",
]


def slugify(value: str, limit: int = 64) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return value[:limit] or "deck_plan"


def load_gold() -> list[dict[str, Any]]:
    if not GOLD_PATH.exists():
        raise FileNotFoundError(f"Missing {GOLD_PATH}. Run npm run gold:build first.")
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def token_set(recipe: str) -> set[str]:
    return {token.strip() for token in recipe.split("+") if token.strip()}


def anchor_score(record: dict[str, Any], retrieval_recipe: str, source_priority: tuple[str, ...]) -> float:
    fid = record.get("fidelity") or {}
    recipe = fid.get("design_recipe", "")
    wanted = token_set(retrieval_recipe)
    found = token_set(recipe)
    overlap = len(wanted & found) / max(1, len(wanted))
    source = record.get("source_company")
    source_bonus = 0.0
    if source in source_priority:
        source_bonus = max(0.0, 1.0 - source_priority.index(source) * 0.12)
    return float(record.get("gold_score") or 0) + overlap * 8.0 + source_bonus


def recipe_source_priority(recipe_id: str, base_priority: tuple[str, ...]) -> tuple[str, ...]:
    if recipe_id.startswith("bain_"):
        preferred = ("Bain", "BCG", "Roland Berger", "Deloitte", "Accenture")
    elif recipe_id.startswith("bcg_"):
        preferred = ("BCG", "Bain", "Roland Berger", "Accenture", "Deloitte")
    elif recipe_id.startswith("deloitte_"):
        preferred = ("Deloitte", "Accenture", "Bain", "Roland Berger", "BCG")
    elif recipe_id.startswith("accenture_"):
        preferred = ("Accenture", "Deloitte", "BCG", "Bain", "Roland Berger")
    else:
        preferred = base_priority
    return tuple(dict.fromkeys(preferred + base_priority))


def pick_anchor(gold: list[dict[str, Any]], recipe_id: str, used: set[str], source_priority: tuple[str, ...]) -> dict[str, Any]:
    recipe = RECIPES[recipe_id]
    effective_priority = recipe_source_priority(recipe_id, source_priority)
    firm_prefix = {
        "bain_": "Bain",
        "bcg_": "BCG",
        "deloitte_": "Deloitte",
        "accenture_": "Accenture",
    }
    firm_target = next((source for prefix, source in firm_prefix.items() if recipe_id.startswith(prefix)), None)
    candidate_gold = gold
    if firm_target and any(r.get("source_company") == firm_target for r in gold):
        candidate_gold = [r for r in gold if r.get("source_company") == firm_target]
    ranked = sorted(
        candidate_gold,
        key=lambda r: (
            anchor_score(r, recipe.retrieval_recipe, effective_priority),
            -(effective_priority.index(r.get("source_company")) if r.get("source_company") in effective_priority else 999),
            r.get("gold_score") or 0,
        ),
        reverse=True,
    )
    for record in ranked:
        if record["slide_id"] not in used:
            used.add(record["slide_id"])
            return record
    return ranked[0]


def build_plan(prompt: str, slide_count: int, style_profile: str, density_mode: str) -> dict[str, Any]:
    gold = load_gold()
    used: set[str] = set()
    profile = get_profile(style_profile)
    if density_mode == "evidence_dense":
        base_sequence = EVIDENCE_DENSE_SEQUENCE
    else:
        base_sequence = ROLAND_SEQUENCE if profile.id == "roland_berger" else HYBRID_SEQUENCE
    sequence = (base_sequence * ((slide_count // len(base_sequence)) + 1))[:slide_count]
    slides = []

    for idx, recipe_id in enumerate(sequence, 1):
        recipe = RECIPES[recipe_id]
        anchor = pick_anchor(gold, recipe_id, used, profile.source_priority)
        fid = anchor.get("fidelity") or {}
        slides.append(
            {
                "slide_num": idx,
                "slide_job": SLIDE_JOBS[(idx - 1) % len(SLIDE_JOBS)],
                "content_brief": f"{SLIDE_JOBS[(idx - 1) % len(SLIDE_JOBS)]} for: {prompt}",
                "style_profile": profile.id,
                "style_profile_label": profile.label,
                "recipe_id": recipe.id,
                "retrieval_recipe": recipe.retrieval_recipe,
                "chart_type": recipe.chart_type,
                "density": recipe.density,
                "required_inputs": list(recipe.requires),
                "generator_notes": recipe.generator_notes,
                "anchor_slide_id": anchor["slide_id"],
                "anchor_image_path": anchor["image_path"],
                "anchor_source_company": anchor.get("source_company"),
                "gold_score": anchor.get("gold_score"),
                "style_anchor_score": fid.get("style_anchor_score"),
                "color_tokens": fid.get("color_tokens", {}),
                "layout_dims": fid.get("layout_dims", {}),
                "firm_style_notes": profile.generation_notes,
            }
        )

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_prompt": prompt,
        "style_target": profile.label,
        "style_profile": profile.to_dict(),
        "slide_count": slide_count,
        "density_mode": density_mode,
        "quality_contract": QUALITY_CONTRACTS[density_mode],
        "planning_mode": "recipe_sequence_plus_gold_anchor_retrieval",
        "slides": slides,
    }


def write_plan(plan: dict[str, Any]) -> tuple[Path, Path]:
    slug = slugify(plan["input_prompt"])
    json_path = OUT_DIR / f"deck_plan_{slug}.json"
    md_path = OUT_DIR / f"deck_plan_{slug}.md"
    json_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    lines = [
        f"# Deck Plan: {plan['input_prompt']}",
        "",
        f"Style target: {plan['style_target']}",
        f"Slides: {plan['slide_count']}",
        "",
    ]
    for slide in plan["slides"]:
        lines.extend(
            [
                f"## {slide['slide_num']:02d}. {slide['slide_job']}",
                f"- Recipe: {slide['recipe_id']}",
                f"- Anchor: {slide['anchor_slide_id']} ({slide['anchor_source_company']})",
                f"- Chart: {slide['chart_type']} | Density: {slide['density']}",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan a consulting deck from a prompt.")
    parser.add_argument("prompt")
    parser.add_argument("--slides", type=int, default=10)
    parser.add_argument("--style-profile", default="hybrid_consulting",
                        help="One of: hybrid_consulting, roland_berger, bain, bcg, deloitte, accenture")
    parser.add_argument("--density-mode", choices=sorted(QUALITY_CONTRACTS), default="evidence_dense",
                        help="balanced keeps more framework flexibility; evidence_dense prioritizes chart/table slides")
    args = parser.parse_args()

    plan = build_plan(args.prompt, max(3, args.slides), args.style_profile, args.density_mode)
    json_path, md_path = write_plan(plan)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print("\nAnchors:")
    for slide in plan["slides"]:
        print(
            f"  {slide['slide_num']:02d} {slide['recipe_id']:<26} "
            f"{slide['anchor_source_company']:<15} {slide['anchor_slide_id']}"
        )


if __name__ == "__main__":
    main()
