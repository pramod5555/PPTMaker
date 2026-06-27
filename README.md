# PPT Slide Dataset Pipeline

A pipeline to collect consulting deck PDFs, convert them to slide images,
and prepare them for manual labeling via claude.ai — no API key required.

**Target:** 100+ labeled slide PNGs with structured JSON labels.

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Poppler (required by pdf2image)

| Platform | Command |
|----------|---------|
| Windows  | Download from [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases), extract, add `bin/` to PATH **or** set `POPPLER_PATH=C:\path\to\poppler\bin` in a `.env` file |
| macOS    | `brew install poppler` |
| Linux    | `sudo apt install poppler-utils` |

Create a `.env` file in this folder if needed:
```
POPPLER_PATH=C:\poppler\bin
```

---

## Running the Pipeline

### Full automated run (scrape → convert → batch prep)

```bash
python run_pipeline.py
```

### If PDFs are already downloaded

```bash
python run_pipeline.py --skip-scrape
```

### If slide PNGs are already generated

```bash
python run_pipeline.py --skip-scrape --skip-convert
```

### JS-heavy sources returned 0 PDFs? Try sitemap fallback

```bash
python run_pipeline.py --sitemap
```

### After all batches are labeled

```bash
python run_pipeline.py --ingest-only
```

---

## Manual Labeling Workflow

After running `python run_pipeline.py`, the slide PNGs are organized into
upload-ready batches. Follow these steps for each batch:

### Step-by-step

1. Open [claude.ai](https://claude.ai) in your browser.
2. Start a **new conversation**.
3. Navigate to `ppt-dataset/batches/batch_001/`.
4. **Upload all 5 PNG files** into the Claude conversation.
5. Open `batches/batch_001/prompt.txt`.
6. **Copy the entire contents** of `prompt.txt`.
7. **Paste it** as your message to Claude and send.
8. Claude returns a JSON array — **copy the entire array**.
9. Save it as `batches/batch_001/response.json`.
10. Repeat for `batch_002`, `batch_003`, etc.

> See `batches/INSTRUCTIONS.txt` for the full instructions after running the pipeline.

### Troubleshooting Claude responses

- If Claude wraps the JSON in markdown fences (` ```json ... ``` `), remove
  the fence lines before saving as `response.json`.
- If Claude truncates the response mid-array, ask it to continue from where
  it stopped, then merge the two arrays before saving.
- The `label_ingest.py` script automatically strips fences, but raw JSON
  is cleanest.

### After labeling all batches

```bash
python run_pipeline.py --ingest-only
```

This builds `dataset.json` and prints a full breakdown.

---

## Style Generation Development Workflow

After the corpus is labeled or auto-labeled, use the prototype tooling to
prepare a high-fidelity consulting-style generation layer.

```bash
python normalize_dataset.py
npm run index:build
npm run gold:build
python prototypes/plan_prompt_deck.py "AI transformation in Indian banking" --slides 10
```

Or run the common refresh path:

```bash
npm run style:refresh
```

Current style-generation artifacts:

- `prototypes/output/fidelity_summary.json` - object/region/color features for each slide.
- `prototypes/output/retrieval_index.json` - structural retrieval index.
- `prototypes/output/gold_style_bank.json` - Roland Berger-weighted style anchors.
- `prototypes/output/gold_style_bank.csv` - sortable review table for the gold bank.
- `prototypes/output/deck_plan_*.json` - prompt-to-recipe deck plan with selected anchors.

The intended generation sequence is:

1. Normalize `dataset.json` into the canonical metadata + slides schema.
2. Rebuild or refresh fidelity features when slides or labels change.
3. Rebuild the retrieval index.
4. Build the Roland Berger-weighted gold style bank.
5. Plan a prompted deck into recipes and anchors.
6. Build a research data pack with source candidates, evidence snippets, coverage audit, and chart-ready recipe data.
7. Render the PPTX from the plan using editable native PPTX objects.
8. Run QC for chart presence, text overflow, collision risk, research coverage, and source/style fit.

Current high-fidelity prototype loop:

```bash
npm run deck:hybrid-sample:qced
```

This runs the evidence-dense planner, renders the editable PPTX, and writes
`prototypes/output/deck_quality_gate_report.json` plus a Markdown report. The
gate now runs after `prototypes/research_synthesis.py`, which creates
`research_data_pack_*.json` from web/source candidates and fallback synthesis.
The QC gate inspects the saved PPTX package for XML validity, negative shape
extents, native chart coverage, planned chart diversity, research metric
coverage, and framework-slide creep.

For Roland Berger-style output, prefer the gold bank over the full corpus. The
full corpus is useful for variety, but the gold bank keeps Deloitte, World Bank,
and IMF slides from diluting the consulting design target.

### While waiting to label

Use these helpers to keep the queue clean:

```bash
python status.py
python validate_batches.py
python labeling_queue.py
```

- `status.py` prints the current pipeline counts.
- `validate_batches.py` checks batch folders, prompts, slide assignment, and any
  saved `response.json` files.
- `labeling_queue.py` writes `labeling_queue.csv`, sorted with Roland Berger
  batches first.

---

## JavaScript-Heavy Sources — Fallback Strategies

Several sources (McKinsey, BCG, Roland Berger, Bain) render content via JavaScript
and may return 0 PDFs with the default `requests` scraper.

**Option A — Sitemap fallback (easiest)**
```bash
python run_pipeline.py --sitemap
```
This reads each site's `sitemap.xml` which often lists PDF URLs statically.

**Option B — Manual seeding**
Download PDFs manually from the sources below and drop them into `ppt-dataset/pdfs/`
with the naming convention `{company}_{slug}.pdf`, then run:
```bash
python run_pipeline.py --skip-scrape
```

Good public sources for manual seeding:
- WEF Reports: https://www.weforum.org/reports/
- Roland Berger: https://www.rolandberger.com/en/Insights/Publications/
- BCG Henderson Institute: https://www.bcg.com/publications
- McKinsey: https://www.mckinsey.com/featured-insights
- Bain: https://www.bain.com/insights/
- Deloitte: https://www2.deloitte.com/us/en/insights.html

**Option C — Playwright (advanced)**
```bash
pip install playwright
playwright install chromium
```
Then write a custom scraper using `playwright.sync_api` to navigate JS-rendered pages.
The existing scraper functions in `scraper.py` can serve as templates for the URL
extraction logic.

---

## Project Structure

```
ppt-dataset/
├── pdfs/              # downloaded PDF decks (git-ignored)
├── slides/            # individual slide PNGs (git-ignored)
├── labels/            # one JSON label file per slide
├── batches/           # upload batches for claude.ai (git-ignored)
│   ├── INSTRUCTIONS.txt
│   ├── batch_001/
│   │   ├── slide_001.png ... slide_005.png
│   │   ├── prompt.txt
│   │   └── response.json  ← you fill this in
│   └── ...
├── dataset.json       # final merged dataset (git-ignored)
├── scraper.py         # PDF collection
├── converter.py       # PDF → PNG slides
├── batch_prep.py      # group slides into upload batches
├── label_ingest.py    # parse responses → labels/ → dataset.json
├── merger.py          # rebuild dataset.json from existing labels/
├── run_pipeline.py    # orchestrator with CLI flags
└── requirements.txt
```

---

## dataset.json Schema

```json
{
  "metadata": {
    "total_slides": 150,
    "labeled_slides": 120,
    "unlabeled_slides": 30,
    "created_at": "2026-06-24T10:00:00+00:00",
    "label_schema_version": "1.0",
    "sources": ["BCG", "Bain", "Deloitte", "McKinsey", "Roland Berger", "WEF"]
  },
  "slides": [
    {
      "slide_id": "bcg_digital_2024_slide_003",
      "image_path": "slides/bcg_digital_2024_slide_003.png",
      "label": {
        "slide_filename": "bcg_digital_2024_slide_003.png",
        "layout_type": "two_col_chart",
        "chart_type": "bar",
        "text_density": "medium",
        "has_icons_illustrations": false,
        "has_data_callouts": true,
        "column_count": 2,
        "color_palette": {
          "primary_accent": "#00A0C6",
          "background": "#FFFFFF"
        },
        "headline_present": true,
        "source_company": "BCG",
        "slide_purpose": "data_evidence",
        "estimated_quality_score": 4
      }
    }
  ]
}
```

---

## Requirements

- Python 3.10+
- Poppler (for pdf2image)
- Claude Pro subscription at claude.ai (for manual labeling — no API key needed)
