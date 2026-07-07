"""
Reusable recipe catalog for high-fidelity consulting deck generation.

The generator should pick one of these archetypes, retrieve one or more gold
anchors, and then fill a structured deck spec. This is deliberately explicit:
it turns "make it Roland Berger-like" into repeatable layout decisions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Recipe:
    id: str
    retrieval_recipe: str
    purpose: str
    chart_type: str
    density: str
    requires: tuple[str, ...]
    generator_notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


RECIPES: dict[str, Recipe] = {
    "rb_title_cover": Recipe(
        id="rb_title_cover",
        retrieval_recipe="title_stack + content_field",
        purpose="Open the deck with a premium consulting cover and thesis.",
        chart_type="none",
        density="low",
        requires=("deck_title", "subtitle", "date_or_context"),
        generator_notes="Distinct cover composition; do not reuse normal rail/panel content slide chrome.",
    ),
    "rb_rail_panel_scatter": Recipe(
        id="rb_rail_panel_scatter",
        retrieval_recipe="left_nav_rail + title_stack + scatter_evidence_field + right_insight_panel",
        purpose="Show a correlation, benchmark map, or strategic positioning field.",
        chart_type="scatter",
        density="medium",
        requires=("x_axis", "y_axis", "series_points", "right_panel_bullets", "rail_label"),
        generator_notes="Native scatter/bubble chart, right insight panel with bold lead phrases, dark rail and violet divider.",
    ),
    "rb_rail_panel_bar": Recipe(
        id="rb_rail_panel_bar",
        retrieval_recipe="left_nav_rail + title_stack + bar_chart_field + right_insight_panel",
        purpose="Compare ranked categories while preserving consulting-style takeaways.",
        chart_type="bar",
        density="medium",
        requires=("categories", "series", "right_panel_bullets", "rail_label"),
        generator_notes="Horizontal bars preferred for long labels; direct labels beat legends when possible.",
    ),
    "rb_full_width_stacked_bar": Recipe(
        id="rb_full_width_stacked_bar",
        retrieval_recipe="title_stack + mixed_chart_field",
        purpose="Show composition changing over time without rail/panel chrome.",
        chart_type="mixed",
        density="medium",
        requires=("periods", "stack_series", "total_labels", "source_note"),
        generator_notes="Large central chart, restrained legend, title/subtitle carry the insight.",
    ),
    "rb_dual_donut_comparison": Recipe(
        id="rb_dual_donut_comparison",
        retrieval_recipe="title_stack + pie_chart_field",
        purpose="Compare two market-share or portfolio compositions.",
        chart_type="pie",
        density="low",
        requires=("left_composition", "right_composition", "delta_callouts"),
        generator_notes="Use two native doughnuts with direct labels and a small central conclusion.",
    ),
    "rb_three_pillar_framework": Recipe(
        id="rb_three_pillar_framework",
        retrieval_recipe="title_stack + content_field",
        purpose="Explain a strategic framework, operating model, or capability system.",
        chart_type="none",
        density="high",
        requires=("pillars", "short_body", "icons_or_markers"),
        generator_notes="Avoid three generic cards; use open typography, lines, numbered systems, and consistent visual weight.",
    ),
    "rb_exec_summary_dense": Recipe(
        id="rb_exec_summary_dense",
        retrieval_recipe="title_stack + content_field",
        purpose="Summarize the argument as a dense consulting leave-behind slide.",
        chart_type="none",
        density="high",
        requires=("headline_claim", "evidence_points", "implications"),
        generator_notes="High information density is allowed, but preserve strict alignment and a single first read.",
    ),
    "bain_value_waterfall": Recipe(
        id="bain_value_waterfall",
        retrieval_recipe="title_stack + bar_chart_field",
        purpose="Show how multiple drivers build from baseline to target value.",
        chart_type="waterfall",
        density="high",
        requires=("baseline", "drivers", "target", "variance_notes"),
        generator_notes="PPTXGenJS lacks native waterfall; use an editable shape-built bridge with explicit connector rules.",
    ),
    "deloitte_risk_heatmap": Recipe(
        id="deloitte_risk_heatmap",
        retrieval_recipe="title_stack + mixed_chart_field",
        purpose="Compare functions or initiatives across maturity, risk, value, and readiness dimensions.",
        chart_type="heatmap",
        density="high",
        requires=("rows", "columns", "scores", "legend"),
        generator_notes="Use an authored table/heatmap with semantic cell fills; avoid stock Office table styling.",
    ),
    "bcg_growth_share_matrix": Recipe(
        id="bcg_growth_share_matrix",
        retrieval_recipe="title_stack + scatter_evidence_field",
        purpose="Position opportunities in a 2x2 strategic choice matrix.",
        chart_type="matrix",
        density="medium",
        requires=("x_axis", "y_axis", "items", "quadrant_labels"),
        generator_notes="Use a clean 2x2 map with direct labels and one highlighted strategic zone.",
    ),
    "hybrid_slopegraph_shift": Recipe(
        id="hybrid_slopegraph_shift",
        retrieval_recipe="title_stack + line_chart_field",
        purpose="Show rank or value shifts between two periods without clutter.",
        chart_type="slopegraph",
        density="medium",
        requires=("left_period", "right_period", "entities", "values"),
        generator_notes="Shape-built direct-label slopegraph because native line charts are too generic for rank shift stories.",
    ),
    "accenture_area_trend": Recipe(
        id="accenture_area_trend",
        retrieval_recipe="title_stack + line_chart_field",
        purpose="Show multi-year technology/value pool growth and mix expansion.",
        chart_type="area",
        density="medium",
        requires=("periods", "series", "callouts"),
        generator_notes="Use native area chart with direct callouts and stronger technology-forward accents.",
    ),
    "hybrid_metric_table": Recipe(
        id="hybrid_metric_table",
        retrieval_recipe="title_stack + content_field",
        purpose="Present dense KPI, evidence, and implication rows in a polished consulting table.",
        chart_type="table",
        density="high",
        requires=("metrics", "baseline", "target", "delta", "implication"),
        generator_notes="Authored table from shapes/text for better typography than default Office grids.",
    ),
    "rb_recommendation_close": Recipe(
        id="rb_recommendation_close",
        retrieval_recipe="title_stack + content_field",
        purpose="Close with a concise implication stack or action agenda.",
        chart_type="none",
        density="medium",
        requires=("recommendations", "next_steps", "owner_or_time_horizon"),
        generator_notes="Use a strong hierarchy and open text, not a generic three-card ending.",
    ),
}


def get_recipe(recipe_id: str) -> Recipe:
    return RECIPES[recipe_id]


def list_recipes() -> list[dict[str, Any]]:
    return [recipe.to_dict() for recipe in RECIPES.values()]
