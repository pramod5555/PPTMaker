"""
Validate generated PPTX decks against the prototype generation quality contract.

This is intentionally package-level QA. It checks the saved PPTX itself rather
than trusting screenshots or generator logs.

Usage:
    python prototypes/deck_quality_gate.py \
      --pptx prototypes/output/hybrid_dense_ai_banking_v2.pptx \
      --spec prototypes/output/materialized_deck_plan_ai_transformation_in_indian_banking.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from common import BASE_DIR, ensure_output_dir

OUT_DIR = ensure_output_dir()
DEFAULT_PPTX = OUT_DIR / "hybrid_dense_ai_banking_v2.pptx"
DEFAULT_SPEC = OUT_DIR / "materialized_deck_plan_ai_transformation_in_indian_banking.json"
REPORT_JSON = OUT_DIR / "deck_quality_gate_report.json"
REPORT_MD = OUT_DIR / "deck_quality_gate_report.md"

CHART_TAGS = (
    "barChart",
    "bubbleChart",
    "areaChart",
    "doughnutChart",
    "lineChart",
    "pieChart",
    "scatterChart",
)

DATA_CHART_TYPES = {
    "bar",
    "bubble",
    "scatter",
    "waterfall",
    "heatmap",
    "matrix",
    "area",
    "slopegraph",
    "dualdoughnut",
    "metric_table",
    "stackedbar",
    "table",
    "callout",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE_DIR.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def read_spec(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def chart_type_from_xml(xml: str) -> str:
    for tag in CHART_TAGS:
        if f"<c:{tag}" in xml:
            return tag
    return "unknownChart"


def inspect_pptx(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing PPTX: {path}")

    xml_parse_errors: list[dict[str, str]] = []
    chart_types: list[str] = []
    chart_groupings: dict[str, list[str]] = {}
    chart_axis_max: dict[str, list[str]] = {}
    negative_extents: dict[str, int] = {}
    flipv_counts: dict[str, int] = {}
    placeholder_hits: list[str] = []

    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        xml_names = [n for n in names if n.endswith(".xml")]
        slide_names = sorted(n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n))
        chart_names = sorted(n for n in names if re.match(r"ppt/charts/chart\d+\.xml$", n))

        for name in xml_names:
            raw = zf.read(name)
            try:
                ET.fromstring(raw)
            except Exception as exc:  # pragma: no cover - exact parser errors vary
                xml_parse_errors.append({"file": name, "error": str(exc)})

        for name in slide_names:
            text = zf.read(name).decode("utf-8", errors="ignore")
            neg = len(re.findall(r"<a:ext[^>]*(?:cx|cy)=\"-\d+\"[^>]*>", text))
            if neg:
                negative_extents[name] = neg
            flips = text.count("flipV=")
            if flips:
                flipv_counts[name] = flips
            if "Slide Number" in text or "sldNum" in text:
                placeholder_hits.append(name)

        for name in chart_names:
            text = zf.read(name).decode("utf-8", errors="ignore")
            chart_types.append(chart_type_from_xml(text))
            chart_groupings[name] = re.findall(r"<c:grouping val=\"([^\"]+)\"", text)
            chart_axis_max[name] = re.findall(r"<c:max val=\"([^\"]+)\"", text)

    return {
        "pptx_path": rel(path),
        "xml_file_count": len(xml_names),
        "xml_parse_errors": xml_parse_errors,
        "slide_count": len(slide_names),
        "native_chart_count": len(chart_names),
        "native_chart_types": chart_types,
        "native_chart_type_counts": dict(Counter(chart_types)),
        "chart_groupings": chart_groupings,
        "chart_axis_max": chart_axis_max,
        "negative_extents": negative_extents,
        "flipv_counts": flipv_counts,
        "placeholder_hits": placeholder_hits,
    }


def inspect_spec(spec: dict[str, Any] | None) -> dict[str, Any]:
    if not spec:
        return {"available": False}

    slides = spec.get("slides", [])
    plan_types = [s.get("chart_type", "unknown") for s in slides]
    recipe_ids = [s.get("recipe", "") for s in slides]
    framework_count = sum("three_pillar" in str(s.get("recipe", "")) for s in slides)
    data_slide_count = sum(t in DATA_CHART_TYPES for t in plan_types)
    consecutive_nondata = 0
    max_consecutive_nondata = 0
    for chart_type in plan_types:
        if chart_type in DATA_CHART_TYPES:
            consecutive_nondata = 0
        else:
            consecutive_nondata += 1
            max_consecutive_nondata = max(max_consecutive_nondata, consecutive_nondata)

    return {
        "available": True,
        "output_path": spec.get("output_path"),
        "data_pack": spec.get("data_pack") or {},
        "slide_count": len(slides),
        "planned_chart_types": plan_types,
        "planned_chart_type_counts": dict(Counter(plan_types)),
        "recipe_ids": recipe_ids,
        "data_slide_count": data_slide_count,
        "framework_slide_count": framework_count,
        "max_consecutive_nondata_slides": max_consecutive_nondata,
    }


def add_check(checks: list[dict[str, Any]], name: str, ok: bool, detail: str, severity: str = "error") -> None:
    checks.append({"name": name, "ok": ok, "detail": detail, "severity": severity})


def run_checks(
    pptx_info: dict[str, Any],
    spec_info: dict[str, Any],
    min_native_charts: int,
    min_data_slides: int,
    max_framework_slides: int,
    require_native_types: list[str],
    require_plan_types: list[str],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    add_check(checks, "xml_parse", not pptx_info["xml_parse_errors"], f"{len(pptx_info['xml_parse_errors'])} XML parse errors")
    neg_count = sum(pptx_info["negative_extents"].values())
    add_check(checks, "no_negative_extents", neg_count == 0, f"{neg_count} negative shape extents")
    add_check(checks, "no_slide_number_placeholders", not pptx_info["placeholder_hits"], f"{len(pptx_info['placeholder_hits'])} placeholder hits")
    add_check(
        checks,
        "native_chart_floor",
        pptx_info["native_chart_count"] >= min_native_charts,
        f"{pptx_info['native_chart_count']} native charts / floor {min_native_charts}",
    )

    native_counts = Counter(pptx_info["native_chart_types"])
    for required in require_native_types:
        add_check(
            checks,
            f"native_{required}",
            native_counts.get(required, 0) > 0,
            f"{native_counts.get(required, 0)} {required} objects",
        )

    area_groupings = [
        grouping
        for chart, groupings in pptx_info["chart_groupings"].items()
        if "areaChart" in pptx_info["native_chart_types"]
        for grouping in groupings
    ]
    if "areaChart" in pptx_info["native_chart_types"]:
        add_check(checks, "area_chart_stacked", "stacked" in area_groupings, f"groupings={area_groupings}")

    if spec_info.get("available"):
        add_check(
            checks,
            "spec_slide_count_matches_pptx",
            spec_info["slide_count"] == pptx_info["slide_count"],
            f"spec {spec_info['slide_count']} / pptx {pptx_info['slide_count']}",
        )
        add_check(
            checks,
            "data_slide_floor",
            spec_info["data_slide_count"] >= min_data_slides,
            f"{spec_info['data_slide_count']} data slides / floor {min_data_slides}",
        )
        add_check(
            checks,
            "framework_slide_ceiling",
            spec_info["framework_slide_count"] <= max_framework_slides,
            f"{spec_info['framework_slide_count']} framework slides / ceiling {max_framework_slides}",
        )
        plan_counts = Counter(spec_info["planned_chart_types"])
        for required in require_plan_types:
            add_check(
                checks,
                f"planned_{required}",
                plan_counts.get(required, 0) > 0,
                f"{plan_counts.get(required, 0)} planned {required} slides",
            )
        data_pack = spec_info.get("data_pack") or {}
        audit = data_pack.get("coverage_audit") or {}
        covered = int(audit.get("covered_metric_count") or 0)
        total = int(audit.get("total_metric_count") or 0)
        add_check(
            checks,
            "research_data_pack_present",
            bool(data_pack.get("mode")),
            data_pack.get("source_note") or "No data pack metadata in spec",
            "warn",
        )
        add_check(
            checks,
            "research_metric_coverage",
            covered >= 3,
            f"{covered}/{total} metric groups covered; fallback synthesis is acceptable for prototypes only",
            "warn",
        )
    else:
        add_check(checks, "spec_available", False, "No materialized deck spec supplied", "warn")

    return checks


def write_reports(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Deck Quality Gate Report",
        "",
        f"Created: {report['created_at']}",
        f"PPTX: `{report['pptx']['pptx_path']}`",
        "",
        "## Summary",
        f"- Slides: {report['pptx']['slide_count']}",
        f"- Native charts: {report['pptx']['native_chart_count']}",
        f"- Native chart types: {report['pptx']['native_chart_type_counts']}",
        f"- Negative extents: {sum(report['pptx']['negative_extents'].values())}",
        f"- Spec available: {report['spec'].get('available')}",
        "",
        "## Checks",
    ]
    for check in report["checks"]:
        mark = "PASS" if check["ok"] else ("WARN" if check["severity"] == "warn" else "FAIL")
        lines.append(f"- {mark}: {check['name']} - {check['detail']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run package-level QA on a generated PPTX deck.")
    parser.add_argument("--pptx", default=str(DEFAULT_PPTX), help="Generated PPTX to inspect")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC), help="Materialized deck spec JSON")
    parser.add_argument("--min-native-charts", type=int, default=4)
    parser.add_argument("--min-data-slides", type=int, default=8)
    parser.add_argument("--max-framework-slides", type=int, default=0)
    parser.add_argument(
        "--require-native-types",
        nargs="*",
        default=["barChart", "bubbleChart", "areaChart", "doughnutChart"],
    )
    parser.add_argument(
        "--require-plan-types",
        nargs="*",
        default=["bar", "waterfall", "bubble", "heatmap", "matrix", "area", "slopegraph", "dualdoughnut", "metric_table"],
    )
    parser.add_argument("--report-json", default=str(REPORT_JSON))
    parser.add_argument("--report-md", default=str(REPORT_MD))
    args = parser.parse_args()

    pptx_path = Path(args.pptx)
    spec_path = Path(args.spec) if args.spec else None
    if not pptx_path.is_absolute():
        pptx_path = BASE_DIR / pptx_path
    if spec_path and not spec_path.is_absolute():
        spec_path = BASE_DIR / spec_path

    pptx_info = inspect_pptx(pptx_path)
    spec_info = inspect_spec(read_spec(spec_path))
    checks = run_checks(
        pptx_info,
        spec_info,
        args.min_native_charts,
        args.min_data_slides,
        args.max_framework_slides,
        args.require_native_types,
        args.require_plan_types,
    )
    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "pptx": pptx_info,
        "spec": spec_info,
        "checks": checks,
    }
    write_reports(report, Path(args.report_json), Path(args.report_md))

    for check in checks:
        mark = "PASS" if check["ok"] else ("WARN" if check["severity"] == "warn" else "FAIL")
        print(f"{mark:<4} {check['name']:<32} {check['detail']}")
    print(f"Wrote {args.report_json}")
    print(f"Wrote {args.report_md}")

    failed = [check for check in checks if not check["ok"] and check["severity"] == "error"]
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
