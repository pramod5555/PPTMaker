"""converter.py — Extract DSL JSON + natural-language description from HTML slides.

For each html_slides/*.html file, calls Azure GPT-4 to produce:
  {
    "description": "natural-language prompt a user might type",
    "spec":        { ...DSL JSON... }
  }

Saved as dsl_slides/<slide_id>.json

Run:
    python slide-dsl/converter.py                  # all slides (resumable)
    python slide-dsl/converter.py --limit 10       # first 10 (smoke test)
    python slide-dsl/converter.py --source bain    # one source only
    python slide-dsl/converter.py --workers 8      # concurrency (default 6)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()
# Also try ppt-dataset/.env (where the key lives in this project)
load_dotenv(Path(__file__).parent.parent / "ppt-dataset" / ".env")

ROOT      = Path(__file__).parent.parent
HTML_DIR  = ROOT / "html_slides"
DSL_DIR   = ROOT / "dsl_slides"
FAIL_LOG  = Path(__file__).parent / "converter_failures.json"

MODEL     = "gpt-5.4"
API_VER   = "2024-12-01-preview"
ENDPOINT  = "https://custom-data-maya-resource.cognitiveservices.azure.com/"

# ── DSL schema embedded in system prompt ──────────────────────────────────────
SYSTEM = """\
You extract consulting slide content from HTML and return a structured JSON object.

OUTPUT FORMAT — return exactly this JSON shape, nothing else:
{
  "description": "<one or two sentences a user might type to request this slide>",
  "spec": { <DSL spec below> }
}

DSL SCHEMA:
{
  "slide_type": "cover | chapter | content | cta",
  "header": { "kicker": "", "headline": "", "sub": "" },
  "layout": "full | two-column | three-column | sidebar-right | sidebar-left",
  "content": {
    "main" | "left" | "right" | "center" | "sidebar": <BLOCK>
  },
  "footer": { "source": "", "page": 0 }
}

BLOCK TYPES:
  bar-chart:
    { "type":"bar-chart", "orientation":"vertical|horizontal",
      "series":[{"label":"","value":0}],           // single-series
      "series":[{"name":"","values":[0,0]}],        // multi-series
      "labels":[], "stacked":false, "fmt":"auto|percent|currency",
      "show_values":true, "title":"" }

  line-chart:
    { "type":"line-chart", "labels":[], "series":[{"name":"","values":[]}],
      "fmt":"auto|percent|decimal", "show_points":true, "area":false, "title":"" }

  scatter-chart:
    { "type":"scatter-chart",
      "points":[{"label":"","x":0,"y":0,"size":6}],
      "x_label":"", "y_label":"", "x_range":[0,100], "y_range":[0,100],
      "quadrant_labels":["TL","TR","BL","BR"], "title":"" }

  donut-chart:
    { "type":"donut-chart", "segments":[{"label":"","value":0}],
      "center_text":"", "center_label":"", "show_legend":true }

  kpi-grid:
    { "type":"kpi-grid", "columns":2,
      "items":[{"stat":"","label":"","delta":"","positive":true|false|null}] }

  bullet-list:
    { "type":"bullet-list", "title":"",
      "items":[{"text":"","sub":""}] }

  table:
    { "type":"table", "headers":["",""], "rows":[["",""]], "highlight_col":0 }

  text-block:
    { "type":"text-block", "title":"", "body":"" }

  gantt-chart:
    { "type":"gantt-chart", "x_labels":[], "title":"",
      "rows":[{"label":"","start":0.0,"end":1.0,"bar_label":""}],
      "milestones":[{"label":"","at":0.0}] }

  waterfall-chart:
    { "type":"waterfall-chart", "title":"", "fmt":"auto",
      "bars":[{"label":"","value":0,"type":"start|positive|negative|total"}] }

  process-flow:
    { "type":"process-flow", "direction":"horizontal|vertical",
      "steps":[{"icon":"1","label":"","sub":""}] }

RULES:
- Extract ONLY semantic content: text, data values, slide structure.
- Do NOT reproduce CSS, pixel values, or colors.
- Map chart types accurately: bar / line / scatter / donut / gantt / waterfall / process.
- For cover slides: set slide_type="cover", no layout/content needed.
- For chapter dividers: set slide_type="chapter", no layout/content needed.
- For the description: write what a consultant would type to request this slide
  (mention the headline topic, chart type, and layout in plain English).
- Return ONLY valid JSON — no markdown fences, no commentary."""


def make_client() -> AzureOpenAI:
    key = os.getenv("AZURE_OPENAI_API_KEY")
    if not key:
        sys.exit("AZURE_OPENAI_API_KEY not set — add to .env")
    return AzureOpenAI(
        api_key=key,
        api_version=API_VER,
        azure_endpoint=ENDPOINT,
    )


def extract_dsl(client: AzureOpenAI, html: str, slide_id: str,
                retries: int = 2) -> dict | None:
    user_msg = (
        f"Extract the DSL JSON for this consulting slide.\n\n"
        f"```html\n{html[:12000]}\n```"
    )
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=1,   # gpt-5.4 requires temp=1 with json_object
                max_completion_tokens=1200,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content.strip()
            data = json.loads(raw)

            # Validate minimum shape
            if "spec" not in data or "description" not in data:
                raise ValueError("missing spec or description key")
            spec = data["spec"]
            if "slide_type" not in spec:
                raise ValueError("spec missing slide_type")

            return data

        except Exception as e:
            err_str = str(e)
            if attempt < retries:
                wait = 30 if "429" in err_str or "rate" in err_str.lower() else 2 ** attempt
                time.sleep(wait)
            else:
                return {"error": err_str[:200], "slide_id": slide_id}
    return None


def process_slide(args) -> tuple[str, bool, str]:
    """Worker: (slide_id, success, message)"""
    path, client, out_dir = args
    slide_id = path.stem
    out_path = out_dir / f"{slide_id}.json"

    html = path.read_text(encoding="utf-8", errors="ignore")
    result = extract_dsl(client, html, slide_id)

    if result is None or "error" in result:
        err = result.get("error", "unknown") if result else "null response"
        return slide_id, False, err

    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    return slide_id, True, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit",   type=int, default=0,  help="Max slides to process (0=all)")
    ap.add_argument("--source",  default="",           help="Filter by source prefix")
    ap.add_argument("--workers", type=int, default=6,  help="Concurrent API calls")
    ap.add_argument("--redo",    action="store_true",  help="Re-process already converted slides")
    args = ap.parse_args()

    DSL_DIR.mkdir(exist_ok=True)
    client = make_client()

    # Collect target files
    files = sorted(HTML_DIR.glob("*.html"))
    if args.source:
        files = [f for f in files if f.name.lower().startswith(args.source.lower())]

    if not args.redo:
        done = {p.stem for p in DSL_DIR.glob("*.json")
                if "error" not in json.loads(p.read_text(encoding="utf-8"))}
        files = [f for f in files if f.stem not in done]

    if args.limit:
        files = files[:args.limit]

    total = len(files)
    print(f"Slides to convert: {total}  (workers={args.workers})")
    if total == 0:
        print("Nothing to do.")
        return

    successes, failures = [], []
    t0 = time.time()

    work = [(f, client, DSL_DIR) for f in files]

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(process_slide, w): w[0].stem for w in work}
        done_n = 0
        for fut in as_completed(futs):
            slide_id, ok, msg = fut.result()
            done_n += 1
            if ok:
                successes.append(slide_id)
            else:
                failures.append({"slide_id": slide_id, "error": msg})
                # persist partial failures so --resume skips them after inspection
                (DSL_DIR / f"{slide_id}.json").write_text(
                    json.dumps({"error": msg, "slide_id": slide_id}), encoding="utf-8")

            elapsed = time.time() - t0
            rate    = done_n / elapsed if elapsed > 0 else 1
            eta     = (total - done_n) / rate if rate > 0 else 0
            status  = "OK" if ok else "FAIL"
            print(f"  [{done_n:4d}/{total}] {status:<4}  {slide_id[:55]}"
                  f"  eta {eta/60:.1f}m", end="\r")

    print()
    print(f"\nDone in {(time.time()-t0)/60:.1f}min")
    print(f"  Succeeded: {len(successes)}")
    print(f"  Failed:    {len(failures)}")

    if failures:
        FAIL_LOG.write_text(json.dumps(failures, indent=2), encoding="utf-8")
        print(f"  Failure log -> {FAIL_LOG}")


if __name__ == "__main__":
    main()
