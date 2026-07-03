"""build_dsl_dataset.py — Build fine-tuning JSONL from DSL JSON extractions.

Reads:
  dsl_slides/*.json                    (from converter.py)
  ppt-dataset/quality_exclusions.json  (layout failures — exclude these)
  slide-dsl/dsl_finetune/synth_*.jsonl (from synthesize.py, if present)

Writes:
  slide-dsl/dsl_finetune/
    dsl_train.jsonl   (real + synthetic, shuffled)
    dsl_val.jsonl
    dsl_stats.json

Each JSONL line:
  { "messages": [
      { "role": "system",    "content": "<DSL schema>" },
      { "role": "user",      "content": "<description from converter>" },
      { "role": "assistant", "content": "<spec JSON string>" }
  ]}

Run:
    python slide-dsl/build_dsl_dataset.py
    python slide-dsl/build_dsl_dataset.py --dry-run
    python slide-dsl/build_dsl_dataset.py --no-synthetic   # real data only
    python slide-dsl/build_dsl_dataset.py --split 0.85
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ROOT     = Path(__file__).parent.parent
DSL_DIR  = ROOT / "dsl_slides"
QUALITY  = ROOT / "ppt-dataset" / "quality_exclusions.json"
OUT_DIR  = Path(__file__).parent / "dsl_finetune"

# ── System prompt sent at inference time ───────────────────────────────────────
# Must match generate.py and converter.py so train/inference prompts are identical.
SYSTEM_PROMPT = """\
You are a consulting slide generator. Given a plain-English description, return a JSON spec \
for a 1280×720 slide following the schema below. Return ONLY valid JSON — no markdown, no commentary.

SCHEMA:
{
  "slide_type": "cover | chapter | content | cta",
  "header": { "kicker": "", "headline": "", "sub": "" },
  "layout": "full | two-column | three-column | sidebar-right | sidebar-left",
  "content": { "main|left|right|center|sidebar": <BLOCK> },
  "footer": { "source": "", "page": 0 }
}

BLOCKS:
  bar-chart:          { "type":"bar-chart", "orientation":"vertical|horizontal",
                        "series":[{"label":"","value":0}],
                        "series":[{"name":"","values":[]}], "labels":[],
                        "stacked":false, "fmt":"auto|percent|currency", "show_values":true, "title":"" }
  line-chart:         { "type":"line-chart", "labels":[], "series":[{"name":"","values":[]}],
                        "fmt":"auto|decimal|percent", "show_points":true, "area":false, "title":"" }
  scatter-chart:      { "type":"scatter-chart", "points":[{"label":"","x":0,"y":0,"size":6}],
                        "x_label":"", "y_label":"", "x_range":[0,100], "y_range":[0,100],
                        "quadrant_labels":["TL","TR","BL","BR"], "title":"" }
  donut-chart:        { "type":"donut-chart", "segments":[{"label":"","value":0}],
                        "center_text":"", "center_label":"", "show_legend":true }
  kpi-grid:           { "type":"kpi-grid", "columns":2, "style":"default|accent|compact|borderless",
                        "items":[{"stat":"","label":"","delta":"","positive":null,"icon":""}] }
  bullet-list:        { "type":"bullet-list", "title":"", "items":[{"text":"","sub":""}] }
  table:              { "type":"table", "headers":[], "rows":[[]], "highlight_col":0 }
  text-block:         { "type":"text-block", "title":"", "body":"", "style":"default|callout|pull-quote" }
  comparison-matrix:  { "type":"comparison-matrix", "title":"",
                        "columns":["Option A","Option B"],
                        "rows":[{"label":"","values":["",""],"highlight":0}],
                        "style":"zebra|bordered|default" }
  gantt-chart:        { "type":"gantt-chart", "x_labels":[], "title":"",
                        "rows":[{"label":"","start":0.0,"end":1.0,"bar_label":""}],
                        "milestones":[{"label":"","at":0.0}] }
  waterfall-chart:    { "type":"waterfall-chart", "title":"", "fmt":"auto",
                        "bars":[{"label":"","value":0,"type":"start|positive|negative|total"}] }
  process-flow:       { "type":"process-flow", "direction":"horizontal|vertical",
                        "steps":[{"icon":"1","label":"","sub":""}] }

STYLE RULES:
- Consulting tone: precise, data-driven, no filler text.
- Kicker: short uppercase label (e.g. "Section 02", "Key Insight").
- Headline: declarative statement of the main finding.
- Sub: one-line context or methodology note.
- Footer source: citation in plain text."""


def load_exclusions() -> set[str]:
    excluded = set()
    if QUALITY.exists():
        q = json.loads(QUALITY.read_text(encoding="utf-8"))
        excluded = set(q.get("excluded_slide_ids", []))
    return excluded


def validate_pair(data: dict) -> bool:
    """Return True if the extracted DSL is usable as a training pair."""
    if "error" in data:
        return False
    desc = data.get("description", "").strip()
    spec = data.get("spec", {})
    if not desc or len(desc) < 10:
        return False
    if not spec.get("slide_type"):
        return False
    # Content slides must have at least one block
    if spec.get("slide_type") == "content":
        content = spec.get("content", {})
        if not content:
            return False
        for v in content.values():
            if isinstance(v, dict) and v.get("type"):
                return True
        return False
    return True


def build_pair(data: dict) -> dict:
    """Build a single chat-format training pair."""
    desc = data["description"].strip()
    spec = data["spec"]
    # Compact spec JSON (no indent) for smaller token count
    spec_str = json.dumps(spec, ensure_ascii=False, separators=(",", ":"))
    return {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": desc},
            {"role": "assistant", "content": spec_str},
        ]
    }


def load_synthetic() -> tuple[list[dict], list[dict]]:
    """Load pre-split synthetic pairs from synthesize.py output if present."""
    s_train = OUT_DIR / "synth_train.jsonl"
    s_val   = OUT_DIR / "synth_val.jsonl"
    train, val = [], []
    for path, bucket in [(s_train, train), (s_val, val)]:
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    bucket.append(json.loads(line))
    return train, val


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split",        type=float, default=0.9)
    ap.add_argument("--seed",         type=int,   default=42)
    ap.add_argument("--dry-run",      action="store_true")
    ap.add_argument("--no-synthetic", action="store_true",
                    help="Exclude synthetic pairs even if synth_train.jsonl exists")
    args = ap.parse_args()

    excluded = load_exclusions()
    print(f"Quality exclusions loaded: {len(excluded)} slide IDs")

    dsl_files = sorted(DSL_DIR.glob("*.json"))
    print(f"DSL files found: {len(dsl_files)}")

    pairs        = []
    skipped_excl = []
    skipped_fail = []
    skipped_bad  = []

    for path in dsl_files:
        sid = path.stem
        if sid in excluded:
            skipped_excl.append(sid)
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            skipped_bad.append(sid)
            continue

        if not validate_pair(data):
            if "error" in data:
                skipped_fail.append(sid)
            else:
                skipped_bad.append(sid)
            continue

        pairs.append(build_pair(data))

    print(f"\nReal pairs:         {len(pairs)}")
    print(f"  Skipped (quality exclusion): {len(skipped_excl)}")
    print(f"  Skipped (converter failure): {len(skipped_fail)}")
    print(f"  Skipped (bad schema):        {len(skipped_bad)}")

    if not pairs:
        print("\nNo pairs to write — run converter.py first.")
        return

    random.seed(args.seed)
    random.shuffle(pairs)

    split_n = int(len(pairs) * args.split)
    train   = pairs[:split_n]
    val     = pairs[split_n:]

    # Merge synthetic pairs if available
    synth_train_count = synth_val_count = 0
    if not args.no_synthetic:
        s_train, s_val = load_synthetic()
        if s_train or s_val:
            train.extend(s_train)
            val.extend(s_val)
            synth_train_count = len(s_train)
            synth_val_count   = len(s_val)
            random.shuffle(train)
            random.shuffle(val)
            print(f"\nSynthetic pairs:    {len(s_train)+len(s_val)}"
                  f"  ({len(s_train)} train | {len(s_val)} val)")
        else:
            print("\nNo synthetic pairs found — run synthesize.py to generate them.")

    print(f"\n  Train: {len(train)}  |  Val: {len(val)}")

    # Token estimate (rough: 1 token ≈ 4 chars)
    all_pairs = train + val
    total_chars = sum(len(m["content"]) for p in all_pairs for m in p["messages"])
    print(f"  Estimated tokens: ~{total_chars // 4:,}")

    if args.dry_run:
        print("\nDRY RUN — no files written.")
        return

    OUT_DIR.mkdir(exist_ok=True)

    def write_jsonl(path: Path, data: list[dict]):
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        mb = path.stat().st_size / 1_048_576
        print(f"  {path.name}  ({len(data)} pairs, {mb:.1f} MB)")

    write_jsonl(OUT_DIR / "dsl_train.jsonl", train)
    write_jsonl(OUT_DIR / "dsl_val.jsonl",   val)

    stats = {
        "total_pairs": len(train) + len(val),
        "train": len(train),
        "val":   len(val),
        "real_pairs": len(pairs),
        "synthetic_train": synth_train_count,
        "synthetic_val":   synth_val_count,
        "split": args.split,
        "skipped_quality_exclusion": len(skipped_excl),
        "skipped_converter_failure": len(skipped_fail),
        "skipped_bad_schema":        len(skipped_bad),
        "estimated_tokens": total_chars // 4,
    }
    (OUT_DIR / "dsl_stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8")
    print(f"  dsl_stats.json")
    print(f"\nDataset ready -> {OUT_DIR}")


if __name__ == "__main__":
    main()
