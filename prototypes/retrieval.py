"""
Phase 2 – structural slide retrieval.

Feature vector:
  [0-8]   recipe tokens   (one-hot, weight 3×) — 9 dims
  [9-16]  layout dims     (normalised floats)   — 8 dims
  [17-19] style dims      (ws, ink, score_norm) — 3 dims
  [20-24] source flags    (one-hot, weight 1×)  — 5 dims
  [25-27] text_density    (one-hot)              — 3 dims

Usage
-----
Build / rebuild the index:
    python retrieval.py --build

Query from the CLI:
    python retrieval.py "left_nav_rail + scatter_evidence_field" --company "Roland Berger" --k 5

Import in other scripts:
    from retrieval import load_index, query
    results = query("left_nav_rail + scatter_evidence_field", k=5)
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from common import BASE_DIR, ensure_output_dir

OUT_DIR = ensure_output_dir()
INDEX_PATH = OUT_DIR / "retrieval_index.json"
SUMMARY_PATH = OUT_DIR / "fidelity_summary.json"

# ── vocabulary ────────────────────────────────────────────────────────────────

RECIPE_TOKENS = [
    "left_nav_rail",
    "title_stack",
    "scatter_evidence_field",
    "mixed_chart_field",
    "bar_chart_field",
    "line_chart_field",
    "pie_chart_field",
    "content_field",
    "right_insight_panel",
]

LAYOUT_KEYS = [
    "rail_w",
    "content_x",
    "title_y",
    "title_h",
    "content_y",
    "content_h",
    "panel_x",
    "panel_w",
]

LAYOUT_DEFAULTS = {
    "rail_w": 0.0,
    "content_x": 0.05,
    "title_y": 0.05,
    "title_h": 0.06,
    "content_y": 0.18,
    "content_h": 0.65,
    "panel_x": 0.75,
    "panel_w": 0.22,
}

SOURCES = [
    "Roland Berger",
    "BCG",
    "Bain",
    "Accenture",
    "Deloitte",
    "World Bank",
    "IMF",
    "McKinsey",
    "WEF",
]

# Dimension weights (applied before cosine similarity).
# Recipe match is the strongest signal; layout dims and style secondary.
WEIGHTS_RECIPE = 3.0
WEIGHTS_LAYOUT = 1.0
WEIGHTS_STYLE  = 0.5
WEIGHTS_SOURCE = 1.0
WEIGHTS_TD     = 0.8


# ── vector encoding ───────────────────────────────────────────────────────────

def _encode(
    recipe: str,
    layout_dims: dict[str, float],
    whitespace: float,
    ink_fraction: float,
    style_anchor_score: float,
    source_company: str | None,
    text_density_category: str,
) -> list[float]:
    tokens = {t.strip() for t in recipe.split("+")}

    # Dims 0-8: recipe token one-hot × weight
    vec: list[float] = [
        WEIGHTS_RECIPE * (1.0 if t in tokens else 0.0)
        for t in RECIPE_TOKENS
    ]

    # Dims 9-16: layout dims, normalised, × weight
    for key in LAYOUT_KEYS:
        val = layout_dims.get(key, LAYOUT_DEFAULTS.get(key, 0.0)) or 0.0
        vec.append(WEIGHTS_LAYOUT * float(val))

    # Dims 17-19: style (ws, ink, score 0-7 → 0-1)
    vec.append(WEIGHTS_STYLE * float(whitespace or 0.0))
    vec.append(WEIGHTS_STYLE * float(ink_fraction or 0.0))
    vec.append(WEIGHTS_STYLE * float((style_anchor_score or 0.0) / 7.0))

    # Dims 20-24: source one-hot × weight
    for src in SOURCES:
        vec.append(WEIGHTS_SOURCE * (1.0 if source_company == src else 0.0))

    # Dims 25-27: text density one-hot × weight
    td_cat = (text_density_category or "low").lower()
    vec.append(WEIGHTS_TD * (1.0 if td_cat == "low" else 0.0))
    vec.append(WEIGHTS_TD * (1.0 if td_cat == "medium" else 0.0))
    vec.append(WEIGHTS_TD * (1.0 if td_cat == "high" else 0.0))

    return vec


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ── index build ───────────────────────────────────────────────────────────────

def build_index(summary_path: Path = SUMMARY_PATH, out_path: Path = INDEX_PATH) -> dict[str, Any]:
    """
    Build the retrieval index from fidelity_summary.json and write it to disk.
    """
    records = json.loads(summary_path.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []

    for r in records:
        fid = r["fidelity"]
        td = fid.get("text_density", {})
        vec = _encode(
            recipe=fid["design_recipe"],
            layout_dims=fid.get("layout_dims", {}),
            whitespace=fid.get("whitespace_share", 0.5),
            ink_fraction=td.get("ink_fraction", 0.0),
            style_anchor_score=fid.get("style_anchor_score", 0.0),
            source_company=r.get("source_company"),
            text_density_category=td.get("category", "medium"),
        )

        entries.append({
            "slide_id": r["slide_id"],
            "image_path": r["image_path"],
            "source_company": r.get("source_company"),
            "estimated_quality_score": r["label"].get("estimated_quality_score"),
            "style_anchor_score": fid["style_anchor_score"],
            "design_recipe": fid["design_recipe"],
            "color_tokens": fid.get("color_tokens", {}),
            "layout_dims": fid.get("layout_dims", {}),
            "text_density": td,
            "has_left_nav_rail": fid.get("has_left_nav_rail", False),
            "has_right_insight_panel": fid.get("has_right_insight_panel", False),
            "whitespace_share": fid.get("whitespace_share", 0.0),
            "vector": vec,
        })

    index = {
        "vocab": {
            "recipe_tokens": RECIPE_TOKENS,
            "layout_keys": LAYOUT_KEYS,
            "sources": SOURCES,
        },
        "dim": len(entries[0]["vector"]) if entries else 28,
        "count": len(entries),
        "slides": entries,
    }

    out_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Built retrieval index: {len(entries)} slides -> {out_path}")
    return index


# ── query ─────────────────────────────────────────────────────────────────────

_cached_index: dict[str, Any] | None = None


def load_index(path: Path = INDEX_PATH) -> dict[str, Any]:
    global _cached_index
    if _cached_index is None:
        _cached_index = json.loads(path.read_text(encoding="utf-8"))
    return _cached_index


def query(
    recipe: str,
    *,
    source_company: str | None = None,
    quality_min: int | None = None,
    text_density: str | None = None,
    k: int = 5,
    index: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve the top-k slides that best match the given recipe and constraints.

    Parameters
    ----------
    recipe         : space-separated token string, e.g.
                     "left_nav_rail + scatter_evidence_field"
    source_company : hard filter — "Roland Berger", "BCG", …  (None = any)
    quality_min    : hard filter — minimum estimated_quality_score (None = any)
    text_density   : soft hint   — "low" / "medium" / "high" (None = any)
    k              : number of results to return

    Returns
    -------
    List of result dicts, sorted by similarity descending:
      { slide_id, image_path, source_company, style_anchor_score,
        design_recipe, color_tokens, layout_dims, similarity }
    """
    idx = index or load_index()

    # Encode the query.  For layout dims, text density, etc. we use mid-range
    # defaults — the recipe token match dominates the score.
    layout_defaults_for_query = {**LAYOUT_DEFAULTS}
    query_td_cat = text_density or "medium"

    # Infer layout hints from the recipe tokens
    tokens = {t.strip() for t in recipe.split("+")}
    if "left_nav_rail" not in tokens:
        layout_defaults_for_query["rail_w"] = 0.0
        layout_defaults_for_query["content_x"] = 0.0
    if "right_insight_panel" not in tokens:
        layout_defaults_for_query["panel_x"] = 0.0
        layout_defaults_for_query["panel_w"] = 0.0

    q_vec = _encode(
        recipe=recipe,
        layout_dims=layout_defaults_for_query,
        whitespace=0.55,
        ink_fraction=0.04,
        style_anchor_score=5.0,
        source_company=source_company,
        text_density_category=query_td_cat,
    )

    results = []
    for entry in idx["slides"]:
        # Hard filters
        if source_company and entry["source_company"] != source_company:
            continue
        if quality_min is not None:
            q = entry.get("estimated_quality_score")
            if q is None or int(q) < quality_min:
                continue

        sim = _cosine(q_vec, entry["vector"])
        results.append({**entry, "similarity": round(sim, 5)})

    results.sort(key=lambda r: (r["similarity"], r["style_anchor_score"]), reverse=True)
    return results[:k]


# ── evaluation ────────────────────────────────────────────────────────────────

def evaluate_retrieval(index: dict[str, Any] | None = None, k: int = 5) -> None:
    """
    Leave-one-out evaluation: for each slide, retrieve its nearest neighbours
    (excluding itself) and measure recipe match rate in top-k.
    """
    idx = index or load_index()
    slides = idx["slides"]

    correct_top1 = 0
    correct_topk = 0
    n = len(slides)

    for i, slide in enumerate(slides):
        q_vec = slide["vector"]
        scores = []
        for j, other in enumerate(slides):
            if i == j:
                continue
            sim = _cosine(q_vec, other["vector"])
            scores.append((sim, other["design_recipe"]))
        scores.sort(reverse=True)

        target_recipe = slide["design_recipe"]
        if scores and scores[0][1] == target_recipe:
            correct_top1 += 1
        if any(r == target_recipe for _, r in scores[:k]):
            correct_topk += 1

    print(f"Leave-one-out retrieval evaluation  (n={n}, k={k})")
    print(f"  Recipe match @ top-1 : {correct_top1}/{n} = {correct_top1/n:.1%}")
    print(f"  Recipe match @ top-{k}: {correct_topk}/{n} = {correct_topk/n:.1%}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Slide retrieval — Phase 2")
    parser.add_argument("recipe", nargs="?", default=None,
                        help='Recipe string, e.g. "left_nav_rail + scatter_evidence_field"')
    parser.add_argument("--build", action="store_true", help="Rebuild the retrieval index and exit")
    parser.add_argument("--eval", action="store_true", help="Run leave-one-out evaluation")
    parser.add_argument("--company", default=None,
                        help="Filter by source company: 'Roland Berger', 'BCG', …")
    parser.add_argument("--quality", type=int, default=None,
                        help="Minimum estimated_quality_score (e.g. 4)")
    parser.add_argument("--density", default=None,
                        choices=["low", "medium", "high"],
                        help="Preferred text density")
    parser.add_argument("--k", type=int, default=5, help="Number of results (default 5)")
    args = parser.parse_args()

    if args.build:
        build_index()
        return

    if args.eval:
        idx = load_index()
        evaluate_retrieval(idx, k=args.k)
        return

    if not args.recipe:
        parser.print_help()
        return

    results = query(
        args.recipe,
        source_company=args.company,
        quality_min=args.quality,
        text_density=args.density,
        k=args.k,
    )

    print(f"\nTop {len(results)} results for: \"{args.recipe}\"")
    if args.company:
        print(f"  Filtered to: {args.company}")
    print()
    for i, r in enumerate(results, 1):
        print(f"  #{i}  sim={r['similarity']:.4f}  score={r['style_anchor_score']}  {r['source_company']}")
        print(f"       {r['slide_id']}")
        print(f"       recipe: {r['design_recipe']}")
        ct = r["color_tokens"]
        ld = r["layout_dims"]
        print(f"       colors: bg={ct.get('background')}  rail={ct.get('rail')}  accent={ct.get('accent')}  panel={ct.get('panel')}")
        print(f"       layout: rail_w={ld.get('rail_w')}  panel_x={ld.get('panel_x')}  panel_w={ld.get('panel_w')}  content_y={ld.get('content_y')}")
        print()


if __name__ == "__main__":
    main()
