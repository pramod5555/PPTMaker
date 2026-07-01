"""
Phase 3 – prompt-to-recipe classifier + full pre-generation pipeline.

Converts a natural language brief into a generation-ready SlotSpec by:
  1. Calling Claude claude-haiku-4-5 (tool use) to classify recipe + constraints
  2. Retrieving the best anchor slide from the Phase 2 index
  3. Returning a SlotSpec that bundles recipe, anchor colours, and layout dims

Usage
-----
CLI:
    python recipe_classifier.py "scatter of AI investment vs maturity, RB style, insight panel"
    python recipe_classifier.py "bar chart comparing adoption by sector, clean professional"
    python recipe_classifier.py "text-heavy framework slide, three columns"

Import:
    from recipe_classifier import pipeline, classify
    spec = pipeline("scatter of AI investment, Roland Berger style")
    print(spec.to_generator_context())
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict
from typing import Any

from retrieval import query as retrieve, RECIPE_TOKENS, SOURCES

# ── vocabulary description for the LLM ───────────────────────────────────────

_TOKEN_DOCS = {
    "left_nav_rail":          "branded left column (Roland Berger / consulting style only)",
    "title_stack":            "ALWAYS include — title + subtitle area at the top",
    "scatter_evidence_field": "scatter or bubble chart as the primary evidence panel",
    "mixed_chart_field":      "complex multi-series, grouped, or combo chart",
    "bar_chart_field":        "clean bar or column chart",
    "line_chart_field":       "line, area, or time-series chart",
    "pie_chart_field":        "pie or donut chart",
    "content_field":          "text-heavy — bullet points, frameworks, icons — no chart",
    "right_insight_panel":    "right sidebar with 3-5 key takeaway bullets",
}

_SYSTEM_PROMPT = f"""
You are a slide layout classifier for a deck-generation system.

Given a natural language brief, use the classify_brief tool to output a
recipe string and retrieval constraints.

RECIPE TOKEN VOCABULARY (join with ' + '):
{chr(10).join(f'  {t:<28} {d}' for t, d in _TOKEN_DOCS.items())}

RULES:
- Always start with "title_stack" or "left_nav_rail + title_stack".
- Use left_nav_rail ONLY when the user explicitly requests RB, consulting, or branded style.
- Include right_insight_panel when user mentions insight panel, key takeaways, or consulting style.
- Pick exactly ONE chart field (scatter / mixed / bar / line / pie / content).
- source_company: one of {SOURCES} or null.
- quality_min: 5 for "high quality / consulting grade", 4 for "professional / clean", null otherwise.
- text_density: "low" for chart-dominant, "high" for text-heavy bullets, "medium" otherwise.
""".strip()

_CLASSIFY_TOOL: dict[str, Any] = {
    "name": "classify_brief",
    "description": "Classify a slide brief into a recipe string and retrieval constraints.",
    "input_schema": {
        "type": "object",
        "properties": {
            "recipe": {
                "type": "string",
                "description": "Token string joined with ' + '. Must start with title_stack or left_nav_rail + title_stack.",
            },
            "source_company": {
                "type": "string",
                "description": "One of the known source companies, or null / 'none' for no preference.",
            },
            "text_density": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
            "quality_min": {
                "type": "integer",
                "description": "Minimum quality score: 4 or 5. Omit (null) for no constraint.",
            },
            "rationale": {
                "type": "string",
                "description": "One sentence explaining the classification decision.",
            },
        },
        "required": ["recipe", "source_company", "text_density", "rationale"],
    },
}


# ── output data structures ────────────────────────────────────────────────────

@dataclass
class ClassifiedRecipe:
    recipe: str
    source_company: str | None
    text_density: str
    quality_min: int | None
    rationale: str


@dataclass
class SlotSpec:
    """
    Full generation-ready specification — output of Phase 3, input to Phase 4.

    Contains everything the code generator needs to produce a PPTX:
      - which layout to build (recipe)
      - exact fractional slot dimensions (layout_dims)
      - brand colours (color_tokens)
      - which anchor slide to reference (anchor_slide_id)
    """
    brief: str
    recipe: str
    anchor_slide_id: str
    anchor_image_path: str
    source_company: str
    estimated_quality_score: int | None
    style_anchor_score: float
    color_tokens: dict[str, str | None]
    layout_dims: dict[str, float]
    text_density: str
    similarity: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_generator_context(self) -> str:
        """
        Compact text block that Phase 4 can paste into a generation prompt.
        Describes the layout and brand colours in plain terms.
        """
        ct = self.color_tokens
        ld = self.layout_dims
        lines = [
            f"Brief        : {self.brief}",
            f"Recipe       : {self.recipe}",
            f"Anchor       : {self.anchor_slide_id}",
            f"Company      : {self.source_company}  (quality {self.estimated_quality_score}, score {self.style_anchor_score})",
            f"Retrieval sim: {self.similarity}",
            "",
            "Color tokens:",
            f"  background : {ct.get('background')}",
            f"  rail       : {ct.get('rail')}",
            f"  divider    : {ct.get('divider')}",
            f"  accent     : {ct.get('accent')}",
            f"  panel      : {ct.get('panel')}",
            f"  text       : {ct.get('text_primary')}",
            "",
            "Layout dims (fractions of slide W / H):",
        ]
        for k, v in sorted(ld.items()):
            lines.append(f"  {k:<18}: {v}")
        return "\n".join(lines)


# ── LLM classifier ────────────────────────────────────────────────────────────

def _call_anthropic(brief: str, model: str) -> dict[str, Any]:
    """Classify via Anthropic tool use. Returns the raw tool input dict."""
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": brief}],
        tools=[_CLASSIFY_TOOL],
        tool_choice={"type": "tool", "name": "classify_brief"},
    )
    tool_block = next(b for b in response.content if b.type == "tool_use")
    return tool_block.input


def _call_openai(brief: str, model: str) -> dict[str, Any]:
    """Classify via OpenAI function calling. Returns the raw function argument dict."""
    import openai as _openai
    client = _openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    fn = {
        "type": "function",
        "function": {
            "name": _CLASSIFY_TOOL["name"],
            "description": _CLASSIFY_TOOL["description"],
            "parameters": _CLASSIFY_TOOL["input_schema"],
        },
    }
    response = client.chat.completions.create(
        model=model,
        max_tokens=512,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": brief},
        ],
        tools=[fn],
        tool_choice={"type": "function", "function": {"name": "classify_brief"}},
    )
    raw_args = response.choices[0].message.tool_calls[0].function.arguments
    return json.loads(raw_args)


def _rule_based_classify(brief: str) -> dict[str, Any]:
    """
    Keyword-heuristic fallback when no LLM API key is available.
    Covers ~85% of common briefs correctly.
    """
    b = brief.lower()

    # Explicit no-chart / text-heavy signals come first to avoid false bar/column matches
    _text_signals = ("no chart", "text only", "text-only", "bullet", "framework",
                     "icon", "three column", "two column", "three-column", "two-column",
                     "pillars", "principles", "agenda", "checklist", "steps", "phases")
    if any(w in b for w in _text_signals):
        chart_token = "content_field"
    elif any(w in b for w in ("scatter", "bubble", "correlation", "vs ", "versus")):
        chart_token = "scatter_evidence_field"
    elif any(w in b for w in ("bar chart", "bar graph", "column chart", "compar",
                               "ranking", "breakdown", "grouped bar", "stacked")):
        chart_token = "bar_chart_field"
    elif any(w in b for w in ("line", "trend", "time series", "over time", "area chart")):
        chart_token = "line_chart_field"
    elif any(w in b for w in ("pie", "donut", "share", "proportion", "composition")):
        chart_token = "pie_chart_field"
    elif "bar" in b or "column" in b:
        chart_token = "bar_chart_field"
    else:
        chart_token = "mixed_chart_field"

    # Structural tokens
    rb_style = any(w in b for w in ("roland", "rb ", "rb-", "consulting style",
                                    "branded", "nav rail"))
    insight_panel = any(w in b for w in ("insight", "panel", "right panel",
                                          "key takeaway", "takeaway", "callout"))

    tokens = []
    if rb_style:
        tokens.append("left_nav_rail")
    tokens.append("title_stack")
    tokens.append(chart_token)
    if insight_panel or rb_style:
        tokens.append("right_insight_panel")

    # Source company
    company: str | None = None
    if any(w in b for w in ("roland berger", "rb style", "roland")):
        company = "Roland Berger"
    elif "bcg" in b:
        company = "BCG"
    elif "accenture" in b:
        company = "Accenture"
    elif any(w in b for w in ("world bank", "worldbank")):
        company = "World Bank"
    elif "imf" in b:
        company = "IMF"

    # Quality
    quality_min: int | None = None
    if any(w in b for w in ("high quality", "consulting grade", "premium", "best")):
        quality_min = 5
    elif any(w in b for w in ("professional", "clean", "polished")):
        quality_min = 4

    # Text density
    if chart_token == "content_field":
        td = "high"
    elif chart_token in ("scatter_evidence_field", "pie_chart_field"):
        td = "low"
    else:
        td = "medium"

    return {
        "recipe": " + ".join(tokens),
        "source_company": company or "none",
        "text_density": td,
        "quality_min": quality_min,
        "rationale": f"Rule-based: chart={chart_token}, rb_style={rb_style}, panel={insight_panel}",
    }


def classify(
    brief: str,
    *,
    model: str | None = None,
) -> ClassifiedRecipe:
    """
    Classify a brief into a recipe + constraints.

    Provider priority:
      1. OpenAI gpt-4o-mini         (OPENAI_API_KEY set)
      2. Rule-based keyword heuristic (no API key needed)

    Validates all recipe tokens against the known vocabulary.
    """
    if os.environ.get("OPENAI_API_KEY"):
        try:
            effective_model = model or "gpt-4o-mini"
            raw = _call_openai(brief, effective_model)
            provider = "openai"
        except Exception:
            raw = _rule_based_classify(brief)
            provider = "rules"
    else:
        raw = _rule_based_classify(brief)
        provider = "rules"
    _verbose = os.environ.get("CLASSIFIER_VERBOSE", "1") != "0"
    if _verbose:
        print(f"  [classifier] provider={provider}")

    # Normalise source_company
    company_raw = raw.get("source_company", "")
    source_company: str | None = None
    if isinstance(company_raw, str) and company_raw.lower() not in ("none", "null", ""):
        match = next((s for s in SOURCES if s.lower() == company_raw.lower()), None)
        if match:
            source_company = match

    # Validate and clean recipe tokens
    raw_recipe = raw.get("recipe", "title_stack + content_field")
    validated_tokens = []
    for tok in raw_recipe.split("+"):
        tok = tok.strip()
        if tok in RECIPE_TOKENS:
            validated_tokens.append(tok)
        else:
            print(f"  [classifier] unknown token '{tok}' — dropped")
    if not validated_tokens:
        validated_tokens = ["title_stack", "content_field"]
    recipe = " + ".join(validated_tokens)

    quality_raw = raw.get("quality_min")
    quality_min: int | None = int(quality_raw) if quality_raw in (4, 5) else None

    return ClassifiedRecipe(
        recipe=recipe,
        source_company=source_company,
        text_density=raw.get("text_density", "medium"),
        quality_min=quality_min,
        rationale=raw.get("rationale", ""),
    )


# ── full pipeline ─────────────────────────────────────────────────────────────

def pipeline(
    brief: str,
    *,
    k: int = 3,
    model: str | None = None,
    index: dict[str, Any] | None = None,
) -> SlotSpec:
    """
    Phase 3 entry point: brief -> ClassifiedRecipe -> retrieve -> SlotSpec.

    Parameters
    ----------
    brief : natural language slide description
    k     : number of candidate anchors to retrieve (returns the best one)
    model : Claude model ID to use for classification
    index : pre-loaded retrieval index (optional, avoids re-loading)

    Returns
    -------
    SlotSpec with the best-matching anchor's layout and colours.
    """
    cr = classify(brief, model=model)

    anchors = retrieve(
        cr.recipe,
        source_company=cr.source_company,
        quality_min=cr.quality_min,
        text_density=cr.text_density,
        k=k,
        index=index,
    )

    if not anchors:
        # Relax constraints and retry
        anchors = retrieve(cr.recipe, k=k, index=index)

    if not anchors:
        raise RuntimeError(f"No anchors found for recipe: {cr.recipe}")

    top = anchors[0]

    return SlotSpec(
        brief=brief,
        recipe=cr.recipe,
        anchor_slide_id=top["slide_id"],
        anchor_image_path=top["image_path"],
        source_company=top["source_company"],
        estimated_quality_score=top.get("estimated_quality_score"),
        style_anchor_score=top["style_anchor_score"],
        color_tokens=top.get("color_tokens", {}),
        layout_dims=top.get("layout_dims", {}),
        text_density=cr.text_density,
        similarity=top["similarity"],
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3: prompt -> recipe -> SlotSpec")
    parser.add_argument("brief", help="Natural language slide description")
    parser.add_argument("--k", type=int, default=3, help="Number of anchors to retrieve")
    parser.add_argument("--classify-only", action="store_true",
                        help="Only classify (skip retrieval)")
    parser.add_argument("--json", action="store_true",
                        help="Output SlotSpec as JSON")
    parser.add_argument("--model", default=None,
                        help="Model ID override (auto-selects based on available API key)")
    args = parser.parse_args()

    print(f"\nClassifying: \"{args.brief}\"")
    print("-" * 60)

    cr = classify(args.brief, model=args.model)
    print(f"Recipe       : {cr.recipe}")
    print(f"Company      : {cr.source_company}")
    print(f"Text density : {cr.text_density}")
    print(f"Quality min  : {cr.quality_min}")
    print(f"Rationale    : {cr.rationale}")

    if args.classify_only:
        return

    print()
    print("Retrieving anchors ...")

    from retrieval import query as retrieve_fn, load_index
    idx = load_index()
    anchors = retrieve_fn(
        cr.recipe,
        source_company=cr.source_company,
        quality_min=cr.quality_min,
        text_density=cr.text_density,
        k=args.k,
        index=idx,
    )
    if not anchors:
        anchors = retrieve_fn(cr.recipe, k=args.k, index=idx)

    print(f"Top {len(anchors)} anchors:")
    for i, a in enumerate(anchors, 1):
        print(f"  #{i}  sim={a['similarity']:.4f}  score={a['style_anchor_score']}  {a['source_company']}")
        print(f"       {a['slide_id']}")

    if anchors:
        top = anchors[0]
        spec = SlotSpec(
            brief=args.brief,
            recipe=cr.recipe,
            anchor_slide_id=top["slide_id"],
            anchor_image_path=top["image_path"],
            source_company=top["source_company"],
            estimated_quality_score=top.get("estimated_quality_score"),
            style_anchor_score=top["style_anchor_score"],
            color_tokens=top.get("color_tokens", {}),
            layout_dims=top.get("layout_dims", {}),
            text_density=cr.text_density,
            similarity=top["similarity"],
        )

        print()
        print("=" * 60)
        print("SLOT SPEC (top anchor)")
        print("=" * 60)
        if args.json:
            print(json.dumps(spec.to_dict(), indent=2))
        else:
            print(spec.to_generator_context())


if __name__ == "__main__":
    main()
