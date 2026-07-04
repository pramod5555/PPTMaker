"""generate.py — Generate a slide from a natural language prompt.

Modes:
  --mode api    Use Azure GPT-4 (works immediately, costs tokens)
  --mode local  Use local fine-tuned GGUF model via llama.cpp (after Windows training)
  --mode mlx    Use local fine-tuned MLX model (Mac M3, after train_mlx.py)

Examples:
    python slide-dsl/generate.py "Two-column slide showing PE fundraising trends 2019-2024 with a bar chart and 4 KPI callouts"
    python slide-dsl/generate.py "Chapter divider: Market Dynamics"
    python slide-dsl/generate.py "Gantt chart showing 18-month digital transformation roadmap" --out my_slide.html
    python slide-dsl/generate.py "..." --mode local --model slide-dsl/dsl_finetune/gguf/model.gguf
    python slide-dsl/generate.py "..." --mode mlx   --model ppt-dataset/finetune/mlx_fused
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from renderer import render_slide

ROOT = Path(__file__).parent.parent

# ── DSL system prompt (same as training) ──────────────────────────────────────
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
- Footer source: citation in plain text.
- For KPI grids: use "accent" style when stats are the hero; "compact" for 4+ items in a column; "borderless" for minimal look.
- KPI stat strings: use clean units — prefer "$4.7T", "$770M", "1,089", "+18%" over "$0.77B" or "0.77 trillion".
- For two-column comparisons of options/scenarios: prefer comparison-matrix over two text-blocks.
- Always populate stat fields with real numbers or percentages, never leave them empty."""


# ── Tavily web search ──────────────────────────────────────────────────────────
def search_context(prompt: str) -> str:
    """Fetch real data from Tavily relevant to the slide prompt."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / "ppt-dataset" / ".env")
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return ""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        results = client.search(prompt, max_results=5, search_depth="basic")
        snippets = []
        for r in results.get("results", [])[:5]:
            title   = r.get("title", "")
            content = r.get("content", "")[:400]
            url     = r.get("url", "")
            snippets.append(f"[{title}] {content} (source: {url})")
        if snippets:
            return "\n\n".join(snippets)
    except Exception as e:
        print(f"[search] Tavily error: {e}")
    return ""


# ── Azure API mode ─────────────────────────────────────────────────────────────
def generate_api(prompt: str, use_search: bool = True) -> dict:
    from dotenv import load_dotenv
    from openai import AzureOpenAI

    load_dotenv()
    load_dotenv(ROOT / "ppt-dataset" / ".env")

    # Fetch real data from web before generating the slide
    user_message = prompt
    if use_search:
        print("Searching for real data...")
        context = search_context(prompt)
        if context:
            user_message = (
                f"{prompt}\n\n"
                f"Use the following real data from web search to populate the slide "
                f"(use actual numbers, stats, and facts from these sources — "
                f"do not invent data):\n\n{context}"
            )
            print(f"Search context: {len(context)} chars from {context.count('(source:')} sources")
        else:
            print("No search results — generating without web data.")

    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-12-01-preview",
        azure_endpoint="https://custom-data-maya-resource.cognitiveservices.azure.com/",
    )

    resp = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=1,
        max_completion_tokens=1200,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content.strip()
    return json.loads(raw)


# ── Local GGUF mode (llama.cpp) ────────────────────────────────────────────────
def generate_local(prompt: str, model_path: str) -> dict:
    # Build the chat prompt in Qwen format
    chat_prompt = (
        "<|im_start|>system\n" + SYSTEM_PROMPT + "<|im_end|>\n"
        "<|im_start|>user\n" + prompt + "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                     delete=False, encoding="utf-8") as tmp:
        tmp.write(chat_prompt)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                "llama-cli",
                "-m", model_path,
                "-f", tmp_path,
                "--temp", "0.1",
                "-n", "1200",
                "--no-display-prompt",
                "--json-schema", json.dumps({"type": "object"}),
            ],
            capture_output=True, text=True, timeout=120,
        )
        raw = result.stdout.strip()
        # Strip any trailing tokens
        if "<|im_end|>" in raw:
            raw = raw[:raw.index("<|im_end|>")]
        return json.loads(raw.strip())
    finally:
        os.unlink(tmp_path)


# ── MLX mode (Mac M3) ─────────────────────────────────────────────────────────
def generate_mlx(prompt: str, model_path: str, adapter_path: str = "") -> dict:
    from mlx_lm import load, generate as mlx_generate
    from mlx_lm.sample_utils import make_sampler, make_repetition_penalty

    model, tokenizer = load(model_path, adapter_path=adapter_path or None)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ]
    chat_prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )

    raw = mlx_generate(model, tokenizer, prompt=chat_prompt,
                       max_tokens=1200,
                       sampler=make_sampler(temp=0.1),
                       logits_processors=[make_repetition_penalty(1.15)],
                       verbose=False)

    if "<|im_end|>" in raw:
        raw = raw[:raw.index("<|im_end|>")]
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        # Fix single-quoted keys/values the model occasionally emits
        fixed = re.sub(r"'([^']*)'", r'"\1"', raw)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            print(f"\n[RAW OUTPUT ({len(raw)} chars)]\n{raw}\n[/RAW OUTPUT]")
            raise


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", help="Natural language slide description")
    ap.add_argument("--out",  default="", help="Output HTML path (default: auto-named)")
    ap.add_argument("--mode", choices=["api", "local", "mlx"], default="api",
                    help="api=Azure GPT-4  local=GGUF/llama.cpp  mlx=MLX fused model")
    ap.add_argument("--model", default="",
                    help="Path to GGUF file (--mode local) or fused MLX dir (--mode mlx)")
    ap.add_argument("--adapter", default="",
                    help="Path to LoRA adapter dir (use with --mode mlx before fusing)")
    ap.add_argument("--no-search", action="store_true",
                    help="Skip Tavily web search (API mode only)")
    ap.add_argument("--show-spec", action="store_true",
                    help="Print the DSL JSON spec before rendering")
    args = ap.parse_args()

    print(f"Generating [{args.mode}]: {args.prompt[:80]}")

    if args.mode == "api":
        spec = generate_api(args.prompt, use_search=not args.no_search)
    elif args.mode == "mlx":
        model_path = args.model or str(ROOT / "ppt-dataset" / "finetune" / "mlx_fused")
        adapter_path = args.adapter or ""
        if not Path(model_path).exists():
            if adapter_path:
                model_path = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
            else:
                sys.exit(f"MLX model not found: {model_path}\n"
                         "Train first with: python slide-dsl/train_mlx.py")
        spec = generate_mlx(args.prompt, model_path, adapter_path)
    else:
        model_path = args.model or str(
            ROOT / "ppt-dataset" / "finetune" / "gguf" / "model.gguf")
        if not Path(model_path).exists():
            sys.exit(f"GGUF model not found: {model_path}\n"
                     "Train first with: python ppt-dataset/finetune/train.py")
        spec = generate_local(args.prompt, model_path)

    if args.show_spec:
        print("\n--- DSL SPEC ---")
        print(json.dumps(spec, indent=2, ensure_ascii=False)
              .encode("utf-8", errors="replace").decode("ascii", errors="replace"))
        print("----------------\n")

    # Render to HTML
    html = render_slide(spec)

    # Determine output path
    if args.out:
        out = Path(args.out)
    else:
        slug = args.prompt[:40].lower()
        slug = "".join(c if c.isalnum() else "_" for c in slug).strip("_")
        out  = ROOT / "slide-dsl" / "generated" / f"{slug}.html"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    print(f"Slide -> {out}")
    print(f"Open:    file:///{out.as_posix()}")


if __name__ == "__main__":
    main()
