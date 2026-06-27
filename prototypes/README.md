# Prototype Workspace

This folder contains lightweight scripts for experimenting with the current
audited slide dataset.

Run from the project root:

```bash
python prototypes/build_manifest.py
python prototypes/make_splits.py
python prototypes/retrieval_baseline.py --query roland_berger_trend_compendium_2050_technology_and_innovation_slide_008 --top-k 8
npm run style:refresh
python prototypes/plan_prompt_deck.py "AI transformation in Indian banking" --slides 10 --density-mode evidence_dense
npm run plan:hybrid-sample
npm run research:hybrid-sample
npm run deck:hybrid-sample
npm run deck:qc
npm run deck:hybrid-sample:qced
npm run deck:pptxgen
python prototypes/render_pptxgenjs_preview.py
```

Outputs are written to `prototypes/output/`.

## What These Scripts Give You

- `manifest.csv`: flat table of every labeled slide and its label fields.
- `dataset_summary.md`: quick label/source/deck distribution.
- `train.json`, `eval.json`, `test.json`: deterministic split by deck.
- `feature_index.json`: compact image+label features for retrieval.
- `retrieval_results_*.html`: visual nearest-neighbor report you can open in a browser.
- `gold_style_bank.json/csv`: Roland Berger-weighted anchors for high-fidelity generation.
- `deck_plan_*.json/md`: prompt-to-recipe deck plans with selected style anchors.
- `research_data_pack_*.json/md`: research plan, source candidates, evidence snippets, coverage audit, and chart-ready recipe data.
- `hybrid_dense_ai_banking_v3.pptx`: denser hybrid consulting sample with native charts plus editable infographics.
- `deck_quality_gate_report.json/md`: package-level PPTX QC report for chart variety, XML validity, and geometry safety.
- `builder_tool_decision.md`: current builder decision and extension strategy.
- `sample_deck_pptxgenjs_v03.pptx`: editable pptxgenJS sample deck with native charts.
- `pptxgenjs_deck_v03_previews/`: preview PNGs for quick visual inspection.

This is intentionally a baseline, not the final model. It gives you a working
loop for checking whether labels, slide images, and generation ideas line up.

## Current Development Loop

Use the QC-wrapped command when iterating on the high-fidelity generator:

```bash
npm run deck:hybrid-sample:qced
```

The default planner now uses `--density-mode evidence_dense`, which biases
prompt decks toward tables, native charts, and editable data infographics. The
QC gate fails on package-level defects such as invalid XML, negative shape
extents, missing native chart types, too few data slides, or accidental generic
framework slide creep.

The research layer is API-free and writes a data pack before rendering. It uses
`ddgs` search when available, scores source quality, extracts metric-like
evidence snippets, audits metric coverage, and emits `chart_data_by_recipe` so
the PPTX materializer can replace illustrative fixtures with sourced or
source-adjacent synthesized values.
