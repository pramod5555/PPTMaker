"""
Consulting-firm style profiles for hybrid deck generation.

These are design biases, not brand-copy templates. The generator uses them to
choose anchor sources, chart density, palette behavior, and layout vocabulary.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class StyleProfile:
    id: str
    label: str
    source_priority: tuple[str, ...]
    strengths: tuple[str, ...]
    chart_bias: tuple[str, ...]
    layout_bias: tuple[str, ...]
    color_notes: str
    generation_notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


STYLE_PROFILES: dict[str, StyleProfile] = {
    "roland_berger": StyleProfile(
        id="roland_berger",
        label="Roland Berger",
        source_priority=("Roland Berger", "Bain", "BCG", "Accenture", "Deloitte"),
        strengths=("left navigation rail", "right insight panel", "dense evidence charts", "subdued technical palette"),
        chart_bias=("scatter", "bar", "stacked bar", "dual donut", "framework"),
        layout_bias=("rail_panel", "full_width_chart", "dense_framework"),
        color_notes="charcoal rail, violet divider/accent, pale gray insight panels, dark blue chart marks",
        generation_notes="Best for technical strategy and trend compendium slides with evidence plus narrative panel.",
    ),
    "bain": StyleProfile(
        id="bain",
        label="Bain",
        source_priority=("Bain", "BCG", "Roland Berger", "Deloitte", "Accenture"),
        strengths=("commercial storylines", "value bridge logic", "operating implications", "strong executive synthesis"),
        chart_bias=("waterfall", "bar", "matrix", "table"),
        layout_bias=("open_chart", "executive_evidence", "value_bridge"),
        color_notes="clean white pages, disciplined red/blue accents, strong headline logic",
        generation_notes="Best for value creation, private equity, performance improvement, and commercial due diligence pages.",
    ),
    "bcg": StyleProfile(
        id="bcg",
        label="BCG",
        source_priority=("BCG", "Bain", "Accenture", "Roland Berger", "Deloitte"),
        strengths=("2x2 matrices", "portfolio views", "strategic choices", "growth-share framing"),
        chart_bias=("matrix", "bubble", "scatter", "bar"),
        layout_bias=("matrix", "portfolio_map", "strategic_options"),
        color_notes="crisp high-contrast fields, green/teal accents, economical labels",
        generation_notes="Best for market maps, portfolio positioning, competitive strategy, and choice architecture.",
    ),
    "deloitte": StyleProfile(
        id="deloitte",
        label="Deloitte",
        source_priority=("Deloitte", "Accenture", "Bain", "BCG", "Roland Berger"),
        strengths=("risk/control heatmaps", "dense tables", "operating model detail", "implementation governance"),
        chart_bias=("heatmap", "table", "stacked bar", "line"),
        layout_bias=("dense_table", "risk_heatmap", "governance_grid"),
        color_notes="black/green accents, compact tables, clear status encodings",
        generation_notes="Best for implementation, risk, operating models, governance, and functional transformation.",
    ),
    "accenture": StyleProfile(
        id="accenture",
        label="Accenture",
        source_priority=("Accenture", "Deloitte", "BCG", "Bain", "Roland Berger"),
        strengths=("technology stacks", "capability roadmaps", "digital operating architecture", "future-facing framing"),
        chart_bias=("timeline", "area", "stacked bar", "architecture"),
        layout_bias=("roadmap", "technology_stack", "capability_map"),
        color_notes="dark neutral base with vivid purple/cyan accents when appropriate",
        generation_notes="Best for technology transformation, capability build, and digital architecture stories.",
    ),
    "hybrid_consulting": StyleProfile(
        id="hybrid_consulting",
        label="Hybrid Consulting",
        source_priority=("Roland Berger", "Bain", "BCG", "Deloitte", "Accenture"),
        strengths=("RB evidence panels", "Bain value logic", "BCG matrices", "Deloitte heatmaps", "Accenture technology roadmaps"),
        chart_bias=("bar", "scatter", "waterfall", "heatmap", "matrix", "slopegraph", "area", "dual donut"),
        layout_bias=("mixed_density", "native_charts", "structured_tables", "strategic_maps"),
        color_notes="use RB as the spine, then borrow accent behaviors per slide archetype",
        generation_notes="Default for variation: retain consulting discipline while broadening evidence forms.",
    ),
}


def get_profile(profile_id: str) -> StyleProfile:
    return STYLE_PROFILES.get(profile_id, STYLE_PROFILES["hybrid_consulting"])


def list_profiles() -> list[dict[str, Any]]:
    return [profile.to_dict() for profile in STYLE_PROFILES.values()]
