"""
Materialize a prompt deck plan into the existing PPTXGenJS deck spec.

  deck_plan_*.json -> [LLM content generation] -> deck_spec_*.json -> editable PPTX

Usage:
    python prototypes/materialize_plan_spec.py prototypes/output/deck_plan_ai_transformation_in_indian_banking.json --render
    python prototypes/materialize_plan_spec.py deck_plan.json --skip-llm --render
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests

from common import BASE_DIR, ensure_output_dir

OUT_DIR = ensure_output_dir()
RENDERER = BASE_DIR / "prototypes" / "generate_sample_deck.js"
OLLAMA_URL = "http://localhost:11434/api/generate"


def _strip_md(v: Any) -> Any:
    import re as _re
    if isinstance(v, str):
        return _re.sub(r'\*+([^*]+)\*+', r'\1', v).strip()
    if isinstance(v, list):
        return [_strip_md(i) for i in v]
    if isinstance(v, dict):
        return {k: _strip_md(val) for k, val in v.items()}
    return v


def call_ollama(model: str, prompt: str, timeout: int = 180) -> dict | None:
    import re as _re
    payload = json.dumps({"model": model, "stream": False, "format": "json", "prompt": prompt})
    try:
        r = requests.post(OLLAMA_URL, data=payload, timeout=timeout)
        r.raise_for_status()
        content = r.json().get("response", "").strip()
        m = _re.search(r'\{.*\}', content, _re.DOTALL)
        if m:
            content = m.group(0)
        return _strip_md(json.loads(content))
    except Exception as exc:
        print(f"  [ollama:{model}] {exc.__class__.__name__}: {exc}")
        return None


def llm_slide_content(model: str, topic: str, slide_job: str, recipe_id: str, chart_keys: str) -> dict | None:
    prompt = f"""You are a senior management consultant writing slide copy for a high-fidelity consulting deck.
Topic: "{topic}"
Slide job: "{slide_job}"
Chart/recipe type: "{recipe_id}"
Key data dimensions: {chart_keys}

Return ONLY a valid JSON object with exactly these keys (no markdown, no fences):
{{
  "title": "<insight-led headline, max 14 words, no generic openers>",
  "subtitle": "<one supporting evidence sentence, max 24 words>",
  "rail_label": "<2–3 word left-rail nav label, use \\n for line break>",
  "panel_bullets": [
    {{"lead": "<3–5 bold words>", "body": "<12–18 word evidence or implication>"}},
    {{"lead": "...", "body": "..."}},
    {{"lead": "...", "body": "..."}}
  ]
}}"""
    return call_ollama(model, prompt)


def clean_hex(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    return value if value.startswith("#") else f"#{value}"


def title_for(job: str, prompt: str, recipe_id: str = "") -> str:
    topic = prompt.strip().rstrip(".")
    if recipe_id == "rb_title_cover":
        return topic
    if recipe_id == "rb_section_divider":
        return topic
    mapping = {
        "Frame": f"{topic} is moving from experimentation to scaled value creation",
        "Summarize": f"Three shifts will determine who captures value from {topic}",
        "Establish": f"{topic} requires a step-change in scale, controls and value capture",
        "Quantify": f"Adoption and value capture remain uneven across the operating model",
        "Bridge": f"Service, credit and risk levers can lift the value pool by INR 30 bn",
        "Map": f"Investment intensity increasingly separates leaders from followers",
        "Assess": f"Governance bottlenecks are concentrated in credit, compliance and data readiness",
        "Position": f"Service AI and credit AI sit in the scale-now zone",
        "Show multi-year": f"The AI value pool expands 7x as platforms mature through 2030",
        "Show rank": f"Adoption shifts from isolated functions to broad operating-model coverage",
        "Show how": f"The value mix shifts from efficiency to new growth as capabilities mature",
        "Explain": f"Winning models combine data foundations, workflow redesign and governance",
        "Compare": f"Priority use cases differ sharply by readiness and economic impact",
        "Assess":  f"Governance bottlenecks concentrate in credit, compliance, and data readiness",
        "Show portfolio": f"Resource allocation must rebalance toward scalable AI platforms",
        "Translate": f"The roadmap moves from pilots to industrialized decision systems",
        "Close": f"Leaders should turn AI ambition into a governed transformation agenda",
    }
    for key, value in mapping.items():
        if job.startswith(key):
            return value
    return f"{topic}: strategic implications and next moves"


def subtitle_for(job: str) -> str:
    if "strategic question" in job or "frame" in job.lower():
        return "A structured assessment of transformation priorities, value pools, and execution choices"
    if "executive" in job or "summarize" in job.lower():
        return "Three shifts will determine who captures value — scale, governance, and operating-model redesign"
    if "baseline" in job or "quantified" in job.lower():
        return "Five operating metrics define the gap between today's pilots and scaled institutional capability"
    if "Bridge" in job or "baseline value" in job:
        return "Value bridge from current run-rate to target pool across service, credit, and risk levers"
    if "relationship" in job or "investment" in job.lower():
        return "Investment discipline increasingly separates leaders from followers across the peer set"
    if "risk" in job or "governance" in job:
        return "Governance bottlenecks are concentrated in credit, compliance, and data readiness"
    if "matrix" in job or "position" in job.lower():
        return "Opportunity map combining economic value at stake with implementation readiness"
    if "multi-year" in job or "value pool" in job.lower():
        return "Value pool expands 7x as platforms mature and benefit mix shifts toward revenue and propositions"
    if "rank" in job or "adoption shift" in job or "shift" in job.lower():
        return "Adoption shifts from isolated functions to broad operating-model coverage by 2028"
    if "mix" in job or "portfolio" in job.lower() or "allocation" in job.lower():
        return "Resource allocation must rebalance toward scalable AI platforms and away from isolated proofs"
    if "compare" in job.lower() or "segment" in job.lower() or "initiative" in job.lower():
        return "Priority use cases differ sharply by readiness and economic impact across the operating model"
    if "close" in job.lower() or "decision" in job.lower() or "next step" in job.lower():
        return "Leaders should convert AI ambition into a governed transformation agenda with owned milestones"
    if "assess" in job.lower():
        return "Readiness gaps and governance risks are concentrated in high-value credit and compliance journeys"
    return "Strategic analysis across value, readiness, and execution dimensions"


def panel_bullets() -> list[dict[str, str]]:
    return [
        {"lead": "Value pools are real", "body": "45–60% of impact concentrates in service, credit, and risk journeys."},
        {"lead": "Maturity is uneven", "body": "Biggest gaps: reusable data products and model-ops cadence."},
        {"lead": "Execution decides returns", "body": "Leaders pair funding with process redesign and clear ownership."},
    ]


def content_pillars(recipe_id: str) -> list[dict[str, str]]:
    if recipe_id == "rb_recommendation_close":
        return [
            {"title": "Prioritize", "body": "Select value pools where data access, business ownership, and adoption pressure are already present."},
            {"title": "Industrialize", "body": "Move from isolated proofs of concept to reusable platforms, model operations, and delivery squads."},
            {"title": "Govern", "body": "Build controls for model risk, privacy, explainability, and frontline accountability into the scaling model."},
        ]
    return [
        {"title": "Data foundation", "body": "Target: 80% of priority journeys served by governed data products; current average is 35-45%."},
        {"title": "Workflow redesign", "body": "Redesign 12-15 high-volume decision points rather than adding tools around unchanged processes."},
        {"title": "Scaled governance", "body": "Move from model-by-model sign-off to portfolio controls, monitoring, and reusable policy patterns."},
    ]


def chart_data(recipe_id: str, topic: str = "") -> dict[str, Any]:
    if recipe_id == "rb_title_cover":
        return {"date": "June 2026", "tag": "Confidential — prepared for internal review"}
    if recipe_id == "rb_section_divider":
        return {}
    if recipe_id == "rb_exec_summary_dense":
        return {
            "boxes": [
                {"org": "Value pool", "value": "INR 72 bn", "description": "Target run-rate value after scaling service, credit, risk and operating levers."},
                {"org": "Adoption scale", "value": "75+", "description": "AI use cases in production across priority journeys and control functions."},
                {"org": "Data readiness", "value": "80%", "description": "Priority journeys served by governed data products and reusable features."},
                {"org": "Risk controls", "value": "70%", "description": "Model-risk controls automated through monitoring, drift alerts and evidence logs."},
            ],
            "source": "Source: RBI Annual Report 2024; BCG AI in Banking Survey 2024",
        }
    if recipe_id == "rb_rail_panel_scatter":
        return {
            "x": [0.6, 0.9, 1.2, 1.6, 1.9, 2.2, 2.6, 2.9, 3.2, 3.5, 3.8, 4.1, 4.4],
            "y": [34, 39, 43, 47, 50, 52, 56, 60, 62, 65, 67, 69, 71],
            "sizes": [8, 9, 11, 12, 13, 13, 15, 17, 18, 20, 22, 23, 24],
            "labels": [["Leaders", 3.8, 67], ["Scaled banks", 3.0, 62], ["Pilots", 1.7, 48], ["Laggards", 0.6, 34]],
            "x_axis": "AI investment intensity",
            "y_axis": "Digital maturity index",
            "x_min": 0,
            "x_max": 5,
            "y_min": 30,
            "y_max": 75,
            "y_major_unit": 10,
            "x_major_unit": 1,
            "source": "Source: Roland Berger Digital Banking Benchmarking Study 2024; n=45 institutions",
        }
    if recipe_id == "rb_full_width_stacked_bar":
        return {
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
            "source": "Source: Roland Berger analysis; RBI Digital Banking Report 2024",
        }
    if recipe_id == "bain_value_waterfall":
        return {
            "baseline_label": "Current run-rate value",
            "target_label": "Target value pool",
            "unit": "INR bn",
            "items": [
                {"label": "Current", "value": 42, "kind": "total"},
                {"label": "Service automation", "value": 18, "kind": "increase"},
                {"label": "Credit decisioning", "value": 14, "kind": "increase"},
                {"label": "Fraud/risk controls", "value": 9, "kind": "increase"},
                {"label": "Tech + change cost", "value": -11, "kind": "decrease"},
                {"label": "Target", "value": 72, "kind": "total"},
            ],
            "callouts": [
                {"label": "+43%", "body": "net value uplift after investment and change cost"},
                {"label": "3 levers", "body": "service, credit, and risk account for most impact"},
            ],
            "source": "Source: Roland Berger value analysis; management estimates",
        }
    if recipe_id == "deloitte_risk_heatmap":
        return {
            "columns": ["Value", "Readiness", "Data", "Risk", "Scale"],
            "rows": [
                {"name": "Service operations", "scores": [5, 4, 4, 3, 5], "note": "High-volume journeys with mature playbooks"},
                {"name": "Credit underwriting", "scores": [5, 3, 3, 5, 4], "note": "Requires explainability and policy controls"},
                {"name": "Collections", "scores": [4, 4, 3, 4, 4], "note": "Good economics, sensitive customer treatment"},
                {"name": "Marketing next best action", "scores": [3, 5, 4, 3, 5], "note": "Fast adoption but lower standalone value"},
                {"name": "Compliance monitoring", "scores": [4, 2, 3, 5, 3], "note": "Control-heavy, high governance need"},
            ],
            "legend": ["1 low", "3 medium", "5 high"],
            "source": "Source: Roland Berger AI readiness assessment; Deloitte Banking Risk Survey 2024",
        }
    if recipe_id == "bcg_growth_share_matrix":
        return {
            "x_axis": "Implementation readiness",
            "y_axis": "Economic value at stake",
            "quadrants": ["Selectively invest", "Scale now", "Fix foundations", "Defer / monitor"],
            "items": [
                {"label": "Service AI", "x": 78, "y": 82, "size": 18},
                {"label": "Credit AI", "x": 58, "y": 88, "size": 20},
                {"label": "Fraud AI", "x": 64, "y": 70, "size": 14},
                {"label": "Marketing AI", "x": 84, "y": 52, "size": 12},
                {"label": "Compliance AI", "x": 38, "y": 68, "size": 13},
                {"label": "Treasury AI", "x": 32, "y": 42, "size": 9},
            ],
            "source": "Source: BCG AI in Banking 2024; Roland Berger implementation readiness framework",
        }
    if recipe_id == "hybrid_slopegraph_shift":
        return {
            "left_label": "2024 adoption",
            "right_label": "2028 target",
            "items": [
                {"label": "Service", "left": 34, "right": 78},
                {"label": "Risk", "left": 42, "right": 76},
                {"label": "Credit", "left": 28, "right": 70},
                {"label": "Operations", "left": 31, "right": 68},
                {"label": "Marketing", "left": 44, "right": 63},
                {"label": "Compliance", "left": 18, "right": 52},
            ],
            "source": "Source: RBI Technology Vision 2025; Roland Berger AI adoption tracker",
        }
    if recipe_id == "accenture_area_trend":
        return {
            "categories": ["2024", "2025", "2026", "2027", "2028", "2029", "2030"],
            "series": [
                {"name": "Efficiency", "values": [6, 8, 11, 13, 15, 17, 18]},
                {"name": "Risk + controls", "values": [2, 4, 6, 8, 10, 11, 12]},
                {"name": "Revenue growth", "values": [1, 3, 5, 8, 12, 16, 19]},
                {"name": "New propositions", "values": [0, 1, 3, 5, 8, 11, 15]},
            ],
            "y_axis": "Indexed value pool",
            "y_max": 70,
            "callout": "7x pool expansion",
            "callout_body": "Value mix broadens as efficiency gains are matched by revenue and new propositions.",
            "source": "Source: Accenture Banking Technology Report 2024; illustrative projections",
        }
    if recipe_id == "hybrid_metric_table":
        return {
            "columns": ["Metric", "Today", "Target", "Delta", "Management implication"],
            "rows": [
                ["AI use cases in production", "18", "75+", "+4.2x", "Shift from pilots to product-family scaling"],
                ["Journeys with governed data products", "38%", "80%", "+42 pp", "Fund reusable data assets before model proliferation"],
                ["Decision cycle time reduction", "8-12%", "25-35%", "+17-23 pp", "Prioritize high-volume decisions with measurable baselines"],
                ["Model-risk controls automated", "20%", "70%", "+50 pp", "Automate monitoring, drift alerts, and explainability evidence"],
                ["Run-rate value captured", "INR 42 bn", "INR 72 bn", "+INR 30 bn", "Tie business cases to owner-level accountability"],
            ],
            "source": "Source: RBI Annual Report 2024; Roland Berger operating benchmarks; management estimates",
        }
    if recipe_id == "rb_dual_donut_comparison":
        labels = ["Customer ops", "Risk", "Marketing", "Product", "Technology", "Other"]
        return {
            "left": {"year": "Today", "labels": labels, "values": [34, 22, 15, 10, 9, 10]},
            "right": {"year": "Target", "labels": labels, "values": [24, 18, 17, 16, 18, 7]},
            "source": "Source: Roland Berger AI budget survey; n=32 Indian banks, 2024",
        }
    return {
        "categories": ["Service", "Credit", "Risk", "Sales", "Operations"],
        "series": [
            {"name": "Current", "values": [35, 28, 42, 24, 31]},
            {"name": "Target", "values": [72, 64, 78, 57, 69]},
        ],
        "bar_direction": "bar",
        "x_axis": "Adoption / value index",
        "source": "Source: Roland Berger analysis; RBI Digital Banking Report 2024",
    }


def chart_type(recipe_id: str) -> str:
    return {
        "rb_title_cover": "cover",
        "rb_section_divider": "divider",
        "rb_exec_summary_dense": "callout",
        "rb_rail_panel_scatter": "bubble",
        "rb_rail_panel_bar": "bar",
        "rb_full_width_stacked_bar": "stackedbar",
        "rb_dual_donut_comparison": "dualdoughnut",
        "bain_value_waterfall": "waterfall",
        "deloitte_risk_heatmap": "heatmap",
        "bcg_growth_share_matrix": "matrix",
        "hybrid_slopegraph_shift": "slopegraph",
        "accenture_area_trend": "area",
        "hybrid_metric_table": "metric_table",
    }.get(recipe_id, "content")


def data_pack_source_note(data_pack: dict[str, Any] | None) -> str:
    if not data_pack:
        return "none"
    audit = data_pack.get("coverage_audit") or {}
    return (
        f"{data_pack.get('mode', 'unknown')} "
        f"({audit.get('covered_metric_count', 0)}/{audit.get('total_metric_count', 0)} metric groups)"
    )


def recipe_chart_data(recipe_id: str, data_pack: dict[str, Any] | None) -> dict[str, Any]:
    if data_pack:
        packed = (data_pack.get("chart_data_by_recipe") or {}).get(recipe_id)
        if isinstance(packed, dict):
            return packed
    return chart_data(recipe_id)


def materialize(
    plan: dict[str, Any],
    out_name: str | None,
    data_pack: dict[str, Any] | None = None,
    model: str = "gemma3:27b-cloud",
    skip_llm: bool = False,
) -> dict[str, Any]:
    prompt = plan["input_prompt"]
    pptx_name = out_name or f"planned_deck_{Path(plan.get('input_prompt', 'deck')).stem.replace(' ', '_')}.pptx"
    pptx_path = OUT_DIR / pptx_name

    slides = []
    for slide in plan["slides"]:
        recipe_id = slide["recipe_id"]
        tokens = slide["retrieval_recipe"]
        colors = slide.get("color_tokens") or {}

        llm_out = None
        if not skip_llm:
            cd = recipe_chart_data(recipe_id, data_pack)
            chart_keys = ", ".join(list(cd.keys())[:5])
            print(f"  [llm] slide {slide['slide_num']:02d} {recipe_id} ...")
            llm_out = llm_slide_content(model, prompt, slide["slide_job"], recipe_id, chart_keys)

        def _t(key: str, fallback: str) -> str:
            return (llm_out or {}).get(key) or fallback

        content = {
            "title":        _t("title",   title_for(slide["slide_job"], prompt)),
            "subtitle":     _t("subtitle", subtitle_for(slide["slide_job"])),
            "rail_label":   _t("rail_label", "AI\nTransformation"),
            "panel_bullets": (llm_out or {}).get("panel_bullets") or panel_bullets(),
            "pillars":      content_pillars(recipe_id),
            "footer_note":  "Source: prototype deck plan; illustrative data",
        }
        slides.append(
            {
                "slide_num": slide["slide_num"],
                "recipe": tokens,
                "anchor_slide_id": slide["anchor_slide_id"],
                "has_rail": "left_nav_rail" in tokens,
                "has_panel": "right_insight_panel" in tokens,
                "color_tokens": {
                    "background": clean_hex(
                        colors.get("background"),
                        "#06466D" if recipe_id in ("rb_title_cover", "rb_section_divider") else "#FFFFFF"
                    ),
                    "rail": clean_hex(colors.get("rail"), "#06466D"),
                    "divider": clean_hex(colors.get("divider"), "#1E6B9E"),
                    "accent": clean_hex(colors.get("accent"), "#06466D"),
                    "panel": clean_hex(colors.get("panel"), "#D9DDE2"),
                    "text_primary": clean_hex(colors.get("text_primary"), "#111216"),
                },
                "layout_dims": slide.get("layout_dims") or {},
                "chart_type": chart_type(recipe_id),
                "chart_data": recipe_chart_data(recipe_id, data_pack),
                "content": content,
            }
        )

    return {
        "output_path": str(pptx_path).replace("\\", "/"),
        "density_mode": plan.get("density_mode", "unknown"),
        "quality_contract": plan.get("quality_contract", {}),
        "data_pack": {
            "topic": (data_pack or {}).get("topic"),
            "mode": (data_pack or {}).get("mode"),
            "coverage_audit": (data_pack or {}).get("coverage_audit"),
            "source_note": data_pack_source_note(data_pack),
        },
        "deck": {
            "title": f"{prompt} | {plan.get('style_target', 'Hybrid Consulting')} prototype",
            "footer": "ppt-dataset style prototype",
            "firm": "Roland Berger",
        },
        "slides": slides,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize deck plan into PPTXGenJS spec.")
    parser.add_argument("plan_json")
    parser.add_argument("--out",       default=None,   help="Output PPTX filename")
    parser.add_argument("--data-pack", default=None,   help="Research data pack JSON from research_synthesis.py")
    parser.add_argument("--model",     default="gemma3:27b-cloud",
                        help="Ollama cloud model for LLM content generation")
    parser.add_argument("--skip-llm",  action="store_true",
                        help="Skip LLM calls; use template text (faster, lower quality)")
    parser.add_argument("--render",    action="store_true",
                        help="Run the PPTXGenJS renderer after writing the spec")
    args = parser.parse_args()

    plan_path = Path(args.plan_json)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    data_pack = None
    if args.data_pack:
        data_pack_path = Path(args.data_pack)
        data_pack = json.loads(data_pack_path.read_text(encoding="utf-8"))

    if not args.skip_llm:
        print(f"Generating LLM slide content ({args.model}) ...")
    spec = materialize(plan, args.out, data_pack, model=args.model, skip_llm=args.skip_llm)

    spec_path = OUT_DIR / f"materialized_{plan_path.stem}.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"Wrote {spec_path}")

    if args.render:
        result = subprocess.run(
            ["node", str(RENDERER), str(spec_path)],
            cwd=BASE_DIR,
            text=True,
            capture_output=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
