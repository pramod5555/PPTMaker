"""
batch_prep.py — Group slide PNGs into batches of 5 for manual claude.ai labeling.

Creates:
  batches/batch_001/ ... batch_NNN/  — each with 5 PNGs + prompt.txt
  batches/INSTRUCTIONS.txt           — step-by-step labeling workflow
"""

import shutil
import sys
import re
from pathlib import Path

from tqdm import tqdm

BASE_DIR = Path(__file__).parent
SLIDES_DIR = BASE_DIR / "slides"
BATCHES_DIR = BASE_DIR / "batches"
BATCHES_DIR.mkdir(exist_ok=True)

BATCH_SIZE = 5
BATCH_DIR_RE = re.compile(r"batch_\d{3}$")

# The prompt template sent to claude.ai alongside the uploaded images.
# Curly braces inside the JSON schema are doubled to escape Python's str.format().
PROMPT_TEMPLATE = """\
I am uploading {count} consulting presentation slides. For each slide, analyze it and \
return a JSON object. Return a JSON array containing one object per slide in the order \
they were uploaded. Return only the raw JSON array, no explanation, no markdown fences.

Each object must follow this exact schema:

{{
  "slide_filename": "<filename of the slide image>",
  "layout_type": "<one of: title_slide | section_divider | three_col_text | two_col_chart | full_width_chart | scatter_bubble_chart | process_flow_timeline | comparison_table | icon_grid | exec_summary | quote_pullout | appendix | mixed_layout>",
  "chart_type": "<one of: bar | line | scatter | pie | waterfall | mixed | none>",
  "text_density": "<one of: low | medium | high>",
  "has_icons_illustrations": <true or false>,
  "has_data_callouts": <true or false>,
  "column_count": <integer 1-4, or 0 if not applicable>,
  "color_palette": {{
    "primary_accent": "<hex color of dominant accent e.g. #00A0C6>",
    "background": "<hex color of slide background>"
  }},
  "headline_present": <true or false>,
  "source_company": "<one of: Roland Berger | BCG | McKinsey | Bain | WEF | Deloitte | World Bank | ADB | IMF | PwC | OECD | Accenture | Unknown>",
  "slide_purpose": "<one of: data_evidence | framing_context | recommendation | process_explanation | executive_summary | transition | reference>",
  "estimated_quality_score": <integer 1-5 where 5 is polished consulting quality>
}}

The slide filenames in order are:
{filenames}
"""

INSTRUCTIONS_TEMPLATE = """\
PPT DATASET — MANUAL LABELING INSTRUCTIONS
===========================================

Total batches created : {total_batches}
Total slides covered  : {total_slides}
Batch size            : {batch_size} slides per batch


WORKFLOW
--------
Repeat the following for every batch folder (batch_001, batch_002, ...):

  1. Open https://claude.ai in your browser and start a NEW conversation.

  2. Upload all {batch_size} PNG images from the batch folder.
     (The last batch may have fewer than {batch_size} images — that is fine.)

  3. Open prompt.txt from the same batch folder.
     Copy its entire contents.

  4. Paste the prompt text as your message to Claude and send it.
     Claude will return a JSON array — one object per slide.

  5. Copy the entire JSON array from Claude's response.
     It should look like:
       [
         {{ "slide_filename": "...", ... }},
         ...
       ]

  6. Save it as a file named response.json inside the batch folder:
       batches/batch_001/response.json
       batches/batch_002/response.json
       ...

  7. Repeat for the next batch.


TIPS
----
- If Claude wraps the JSON in markdown fences (```json ... ```), remove the
  fence lines before saving as response.json.
- If Claude returns fewer objects than expected (network cut-off, etc.),
  ask it to continue and merge the arrays before saving.
- You can process batches in any order — label_ingest.py is order-independent.
- Re-running label_ingest.py is safe; it is fully idempotent.


AFTER ALL BATCHES ARE LABELED
------------------------------
Run:

  python run_pipeline.py --ingest-only

Or directly:

  python label_ingest.py

This will:
  - Parse every batches/batch_*/response.json
  - Write individual label files to /labels/
  - Build / refresh dataset.json
  - Print a breakdown summary (layout types, companies, chart types, quality scores)
"""


def main():
    slide_files = sorted(SLIDES_DIR.glob("*.png"))
    if not slide_files:
        print(f"No slides found in {SLIDES_DIR}. Run converter.py first.")
        sys.exit(0)

    # Warn if response.json files already exist — re-running will shift batch assignments
    existing_responses = list(BATCHES_DIR.glob("batch_*/response.json"))
    if existing_responses:
        print(
            f"WARNING: {len(existing_responses)} batch(es) already have response.json files.\n"
            "Re-running batch_prep adds new batches for new slides but may shift batch\n"
            "numbering if new slides sort BEFORE existing ones alphabetically.\n"
            "label_ingest.py reads by slide_filename (not batch number) so labels are safe,\n"
            "but check that existing response.json files still match their batch slides.\n"
        )

    batches = [
        slide_files[i : i + BATCH_SIZE]
        for i in range(0, len(slide_files), BATCH_SIZE)
    ]

    print(f"Found {len(slide_files)} slides -> {len(batches)} batches of up to {BATCH_SIZE}.\n")

    # Remove stale PNGs from old batch folders before rebuilding. This keeps
    # prompts and uploaded images aligned when the slide list changes.
    for old_batch_dir in BATCHES_DIR.glob("batch_*"):
        if not old_batch_dir.is_dir() or not BATCH_DIR_RE.fullmatch(old_batch_dir.name):
            continue
        if (old_batch_dir / "response.json").exists():
            continue
        old_index = int(old_batch_dir.name.split("_")[1])
        if old_index > len(batches):
            shutil.rmtree(old_batch_dir)
            continue
        for old_png in old_batch_dir.glob("*.png"):
            old_png.unlink()

    for batch_idx, batch in enumerate(tqdm(batches, desc="Preparing batches"), start=1):
        batch_dir = BATCHES_DIR / f"batch_{batch_idx:03d}"
        batch_dir.mkdir(exist_ok=True)

        # Copy PNGs into batch folder
        for slide in batch:
            dest = batch_dir / slide.name
            if not dest.exists():
                shutil.copy2(slide, dest)

        # Build and write prompt.txt
        filenames_list = "\n".join(s.name for s in batch)
        prompt = PROMPT_TEMPLATE.format(count=len(batch), filenames=filenames_list)
        (batch_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    # Write top-level INSTRUCTIONS.txt
    instructions = INSTRUCTIONS_TEMPLATE.format(
        total_batches=len(batches),
        total_slides=len(slide_files),
        batch_size=BATCH_SIZE,
    )
    (BATCHES_DIR / "INSTRUCTIONS.txt").write_text(instructions, encoding="utf-8")

    print(f"\nBatches created  : {len(batches)}")
    print(f"Slides covered   : {len(slide_files)}")
    print(f"Batches folder   : {BATCHES_DIR}")
    print(f"\nNext step: read batches/INSTRUCTIONS.txt and start labeling on claude.ai")


if __name__ == "__main__":
    main()
