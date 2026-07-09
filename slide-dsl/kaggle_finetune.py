# =============================================================================
# PPTMaker DSL Fine-tune — Kaggle Notebook
# =============================================================================
# Model  : Qwen2.5-7B-Instruct (pre-quantized 4-bit via Unsloth)
# Method : QLoRA — LoRA adapters trained on top of 4-bit base
# Output : pptmaker_dsl.Q4_K_M.gguf  (~4.5 GB, ready for Ollama / llama.cpp)
#
# DATA SOURCE: slide-dsl/dsl_finetune/kaggle_train.jsonl + kaggle_val.jsonl
#   - kaggle_train.jsonl : 2,079 pairs
#       790 real PPT slides (converter.py → quality screened)
#       960 synthetic pairs (synthesize.py — missing block types)
#       121 API pairs (generate_training.py — high quality)
#       208 augmented chapter/cover/CTA (augment_dsl_data.py — fixes imbalance)
#   - kaggle_val.jsonl   :   231 pairs
#   - Distribution: content 78%  chapter 10%  cover 7%  cta 5%
#   - Full DSL schema in all system prompts (matches generate.py at inference)
#   - mlx_data/ was an MLX-specific derived format (short prompt, char-filtered) — do not use
#
# KAGGLE SETUP (do these before running):
#   1. Create a new Kaggle dataset:
#        Kaggle → Datasets → New Dataset → name it "pptmaker-dsl-data"
#        Upload: slide-dsl/dsl_finetune/kaggle_train.jsonl
#                slide-dsl/dsl_finetune/kaggle_val.jsonl
#   2. New Notebook → Add Data → search "pptmaker-dsl-data" → Add
#   3. Settings → Accelerator → GPU T4 x1
#   4. Settings → Internet → ON  (needed to download base model)
#   5. Paste this file into the notebook (or upload as .py and import)
#   6. Run all cells top to bottom
#   7. When complete: Output tab → download pptmaker_dsl.Q4_K_M.gguf
#
# Expected runtime on T4 (16 GB VRAM): ~60–80 minutes for 3 epochs
# =============================================================================


# ── CELL 1 : Install ──────────────────────────────────────────────────────────
# Run once per session. ~3–4 minutes.

import subprocess, sys

def pip(*args):
    subprocess.check_call([sys.executable, "-m", "pip", *args], stdout=subprocess.DEVNULL)

pip("install", "unsloth[kaggle-new] @ git+https://github.com/unslothai/unsloth.git", "-q")
pip("install", "--no-deps", "trl", "peft", "accelerate", "-q")

print("Install complete.")


# ── CELL 2 : Imports & config ─────────────────────────────────────────────────

import json, os, random
from pathlib import Path
from collections import Counter

import torch
from datasets import Dataset
from trl import SFTTrainer, SFTConfig
from unsloth import FastLanguageModel

# ── Paths ─────────────────────────────────────────────────────────────────────
# Kaggle mounts your dataset under /kaggle/input/<dataset-slug>/
# The slug is the lowercase-hyphenated version of your dataset name.
KAGGLE_INPUT  = Path("/kaggle/input/pptmaker-dsl-data")
KAGGLE_OUTPUT = Path("/kaggle/working")

TRAIN_FILE = KAGGLE_INPUT / "kaggle_train.jsonl"
VAL_FILE   = KAGGLE_INPUT / "kaggle_val.jsonl"

assert TRAIN_FILE.exists(), f"kaggle_train.jsonl not found at {TRAIN_FILE} — check dataset slug"
assert VAL_FILE.exists(),   f"kaggle_val.jsonl not found at {VAL_FILE}   — check dataset slug"

# ── Hyperparameters ───────────────────────────────────────────────────────────
BASE_MODEL   = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
# ^ Unsloth's pre-quantized version: ~4.5 GB download vs ~15 GB for the full model.
# Same weights, just stored in 4-bit. Fits Kaggle's 20 GB disk with GGUF output.

MAX_SEQ_LEN  = 1024     # max token len in dataset is ~1,533 chars ≈ 384 tokens;
                         # 1024 gives plenty of headroom for the full prompt

LORA_RANK    = 64        # higher rank = more schema-learning capacity
LORA_ALPHA   = 128       # 2× rank — standard scaling
LORA_DROPOUT = 0.05
TARGET_MODS  = ["q_proj","k_proj","v_proj","o_proj",
                 "gate_proj","up_proj","down_proj"]

EPOCHS       = 3
BATCH_SIZE   = 2         # per-GPU
GRAD_ACCUM   = 8         # effective batch = 2 × 8 = 16
LR           = 2e-4
WARMUP_RATIO = 0.05
WEIGHT_DECAY = 0.01

OUTPUT_DIR   = str(KAGGLE_OUTPUT / "checkpoints")
GGUF_STEM    = str(KAGGLE_OUTPUT / "pptmaker_dsl")
GGUF_QUANT   = "q4_k_m"

print(f"CUDA : {torch.cuda.is_available()}")
if torch.cuda.is_available():
    props = torch.cuda.get_device_properties(0)
    print(f"GPU  : {props.name}  ({props.total_memory/1e9:.1f} GB VRAM)")


# ── CELL 3 : Load & validate data ─────────────────────────────────────────────

def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

train_raw = load_jsonl(TRAIN_FILE)
val_raw   = load_jsonl(VAL_FILE)

def dist(data: list[dict]) -> dict:
    c = Counter()
    for d in data:
        c[json.loads(d["messages"][2]["content"]).get("slide_type","?")] += 1
    return dict(c)

print(f"Train : {len(train_raw):,} pairs  {dist(train_raw)}")
print(f"Val   : {len(val_raw):,} pairs  {dist(val_raw)}")

# Drop any pair whose completion isn't valid JSON (safety net)
def valid_json(d: dict) -> bool:
    try:
        json.loads(d["messages"][2]["content"])
        return True
    except Exception:
        return False

before = len(train_raw)
train_raw = [d for d in train_raw if valid_json(d)]
print(f"Dropped {before - len(train_raw)} malformed pairs → {len(train_raw):,} clean train pairs")


# ── CELL 4 : Load model ───────────────────────────────────────────────────────

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name     = BASE_MODEL,
    max_seq_length = MAX_SEQ_LEN,
    dtype          = None,       # auto: BF16 on Ampere+, FP16 on T4
    load_in_4bit   = True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r                          = LORA_RANK,
    target_modules             = TARGET_MODS,
    lora_alpha                 = LORA_ALPHA,
    lora_dropout               = LORA_DROPOUT,
    bias                       = "none",
    use_gradient_checkpointing = "unsloth",   # saves ~30% VRAM
    random_state               = 42,
    use_rslora                 = False,
)

print(model.print_trainable_parameters())


# ── CELL 5 : Format data ──────────────────────────────────────────────────────
# Format manually in Qwen ChatML — avoids Unsloth's get_chat_template EOS token issue.

def format_example(example: dict) -> dict:
    parts = []
    for msg in example["messages"]:
        parts.append(f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n")
    return {"text": "".join(parts)}

train_ds = Dataset.from_list(train_raw).map(format_example, remove_columns=["messages"])
val_ds   = Dataset.from_list(val_raw).map(format_example,   remove_columns=["messages"])

# Spot-check lengths
lengths = [len(tokenizer.encode(ex["text"])) for ex in train_ds.select(range(200))]
print(f"Token lengths (sample 200) — min:{min(lengths)}  avg:{sum(lengths)//len(lengths)}  max:{max(lengths)}")
if max(lengths) > MAX_SEQ_LEN:
    print(f"WARNING: {sum(l > MAX_SEQ_LEN for l in lengths)} examples exceed MAX_SEQ_LEN={MAX_SEQ_LEN} and will be truncated")


# ── CELL 6 : Train ────────────────────────────────────────────────────────────

trainer = SFTTrainer(
    model              = model,
    processing_class   = tokenizer,
    train_dataset      = train_ds,
    eval_dataset       = val_ds,
    args = SFTConfig(
        dataset_text_field          = "text",
        max_length                  = MAX_SEQ_LEN,
        eos_token                   = "<|im_end|>",
        dataset_num_proc            = 2,
        packing                     = False,
        per_device_train_batch_size = BATCH_SIZE,
        gradient_accumulation_steps = GRAD_ACCUM,
        num_train_epochs            = EPOCHS,
        learning_rate               = LR,
        lr_scheduler_type           = "cosine",
        warmup_steps                = 100,
        weight_decay                = WEIGHT_DECAY,
        optim                       = "adamw_8bit",
        fp16                        = not torch.cuda.is_bf16_supported(),
        bf16                        = torch.cuda.is_bf16_supported(),
        logging_steps               = 10,
        eval_strategy               = "steps",
        eval_steps                  = 200,
        save_strategy               = "best",
        save_total_limit            = 2,
        output_dir                  = OUTPUT_DIR,
        report_to                   = "none",
        load_best_model_at_end      = True,
        metric_for_best_model       = "eval_loss",
        greater_is_better           = False,
    ),
)

print("Starting training …")
stats = trainer.train()
print(f"\nDone.  train_loss={stats.metrics['train_loss']:.4f}  "
      f"runtime={stats.metrics['train_runtime']:.0f}s")


# ── CELL 7 : Quality check ────────────────────────────────────────────────────

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
- For KPI grids: use "accent" style when stats are the hero; "compact" for 4+ items in a column.
- Always populate stat fields with real numbers or percentages, never leave them empty."""

TEST_PROMPTS = [
    ("chapter", "Chapter divider for section 02 titled Market Dynamics"),
    ("cover",   "Cover slide for a deck titled 'Private Equity Outlook 2025'"),
    ("cta",     "Closing CTA: three next steps — approve budget, launch pilot, hire programme lead"),
    ("content", "Two-column slide: bar chart of FY2024 revenue by region vs FY2023"),
    ("content", "Donut chart of MHCV market share: Tata 47%, Ashok Leyland 30%, VECV 17%, Others 6%"),
    ("content", "KPI grid showing Q3 results: revenue $4.2B +8%, EBIT margin 11.2% -0.3pp, units 48k +2%"),
]

FastLanguageModel.for_inference(model)

print("\n" + "="*65)
print("QUALITY CHECK")
print("="*65)

passed = 0
for expected_type, prompt in TEST_PROMPTS:
    messages = [
        {"role": "system",    "content": SYSTEM_PROMPT},
        {"role": "user",      "content": prompt},
    ]
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize              = True,
        add_generation_prompt = True,
        return_tensors        = "pt",
    ).to("cuda")

    with torch.no_grad():
        out = model.generate(
            input_ids      = inputs,
            max_new_tokens = 600,
            temperature    = 0.1,
            do_sample      = True,
            pad_token_id   = tokenizer.eos_token_id,
        )

    raw = tokenizer.decode(out[0][inputs.shape[1]:], skip_special_tokens=True)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()

    try:
        spec       = json.loads(raw)
        got_type   = spec.get("slide_type", "?")
        has_header = bool(spec.get("header", {}).get("headline"))
        type_ok    = got_type == expected_type
        status     = "✓" if type_ok else "✗ type mismatch"
        if type_ok:
            passed += 1
    except json.JSONDecodeError as e:
        got_type   = "PARSE ERROR"
        has_header = False
        status     = f"✗ JSON error: {e}"

    print(f"\n[{expected_type:7s}] {prompt[:55]}")
    print(f"         → slide_type={got_type}  header={'ok' if has_header else 'missing'}  {status}")

print(f"\n{passed}/{len(TEST_PROMPTS)} test prompts passed type check")
print("="*65)


# ── CELL 8 : Export GGUF ─────────────────────────────────────────────────────
# Merges LoRA into base weights and quantizes to Q4_K_M in one step.
# The output file is what you load into Ollama on the company server.

print(f"\nExporting GGUF ({GGUF_QUANT}) — takes ~5-10 minutes …")
model.save_pretrained_gguf(GGUF_STEM, tokenizer, quantization_method=GGUF_QUANT)

# Find the output file (Unsloth naming varies slightly)
gguf_candidates = list(KAGGLE_OUTPUT.glob("*.gguf"))
gguf_path = gguf_candidates[0] if gguf_candidates else Path(f"{GGUF_STEM}.gguf")

print(f"\n✓ GGUF saved: {gguf_path}")
print(f"  Size: {gguf_path.stat().st_size / 1e9:.2f} GB")


# ── CELL 9 : Write Modelfile for Ollama ──────────────────────────────────────

modelfile_content = f"""FROM ./{gguf_path.name}

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 1024
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"

SYSTEM {SYSTEM_PROMPT}
"""

modelfile_path = KAGGLE_OUTPUT / "Modelfile"
modelfile_path.write_text(modelfile_content)
print(f"✓ Modelfile written: {modelfile_path}")

print("""
========================================================
DEPLOYMENT — load on company Ollama server:

  # Copy both files to server, then:
  ollama create pptmaker-dsl -f Modelfile

  # Test:
  ollama run pptmaker-dsl "Chapter divider for Section 02: Market Dynamics"

  # In PPTMaker .env:
  LLM_BACKEND=local
  LOCAL_LLM_URL=http://<server-ip>:11434/v1
  LOCAL_LLM_MODEL=pptmaker-dsl
========================================================
""")


# ── CELL 10 : List output files ───────────────────────────────────────────────

print("Files in /kaggle/working/:")
for f in sorted(KAGGLE_OUTPUT.rglob("*")):
    if f.is_file() and "checkpoint" not in str(f):
        print(f"  {f.relative_to(KAGGLE_OUTPUT)}  ({f.stat().st_size/1e6:.1f} MB)")
