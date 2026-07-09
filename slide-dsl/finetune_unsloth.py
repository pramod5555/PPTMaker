"""
finetune_unsloth.py — Fine-tune Qwen2.5-7B-Instruct on the PPTMaker DSL task.

Run on Google Colab (free T4, 16 GB VRAM) or Kaggle Notebooks (T4, 30 hr/wk free).

Steps:
  1. Upload this file + slide-dsl/mlx_data/ to Colab or Google Drive
  2. Run cells top to bottom
  3. Download pptmaker_dsl.Q4_K_M.gguf at the end (~4.5 GB)
  4. Load into company Ollama server: ollama create pptmaker-dsl -f Modelfile

Estimated time on free T4:
  ~60-80 min for 3 epochs over ~2,000 pairs

Each cell is delimited by  # %%  (works in Colab, Jupyter, and VSCode notebooks)
"""

# %% [markdown]
# ## Cell 0 — Install dependencies
# Run once per session. Takes ~3 minutes on Colab.

# %%
# !pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" -q
# !pip install --no-deps "xformers<0.0.27" trl peft accelerate bitsandbytes -q
# Uncomment the two lines above when running in Colab/Jupyter.
# In a local terminal: pip install unsloth trl peft accelerate bitsandbytes

# %% [markdown]
# ## Cell 1 — Imports and config

# %%
import json
import random
from pathlib import Path

import torch
from datasets import Dataset
from trl import SFTTrainer, SFTConfig
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template

# ── Config — edit these if needed ─────────────────────────────────────────────
BASE_MODEL    = "Qwen/Qwen2.5-7B-Instruct"   # or "Qwen/Qwen2.5-3B-Instruct" for small servers
MAX_SEQ_LEN   = 1024       # covers max token length in our data (~895 tokens)
LORA_RANK     = 64         # higher rank = more capacity for schema learning
LORA_ALPHA    = 128        # 2× rank — standard for structured tasks
LORA_DROPOUT  = 0.05
TARGET_MODS   = [          # fine-tune all linear projections
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]
EPOCHS        = 3
BATCH_SIZE    = 2          # per-GPU; effective batch = BATCH_SIZE × GRAD_ACCUM
GRAD_ACCUM    = 8          # effective batch = 16
LR            = 2e-4
WARMUP_RATIO  = 0.05
WEIGHT_DECAY  = 0.01
OUTPUT_DIR    = "pptmaker_dsl_checkpoints"
GGUF_NAME     = "pptmaker_dsl"        # will create pptmaker_dsl.Q4_K_M.gguf
GGUF_QUANT    = "q4_k_m"             # ~4.5 GB, good quality/size trade-off

# Path to your JSONL training files (adjust if running in Colab with uploaded files)
TRAIN_FILE = Path("mlx_data/train.jsonl")
VAL_FILE   = Path("mlx_data/valid.jsonl")

print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# %% [markdown]
# ## Cell 2 — Load data and inspect

# %%
def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

train_raw = load_jsonl(TRAIN_FILE)
val_raw   = load_jsonl(VAL_FILE)

# Report distribution
from collections import Counter
def dist(data):
    types = Counter()
    for d in data:
        spec = json.loads(d["messages"][2]["content"])
        types[spec.get("slide_type", "?")] += 1
    return dict(types)

print(f"Train: {len(train_raw)} pairs  {dist(train_raw)}")
print(f"Val:   {len(val_raw)}  pairs  {dist(val_raw)}")

# Validate all completions parse as JSON and render
import sys
sys.path.insert(0, ".")  # so we can import renderer.py
try:
    from renderer import render_slide
    ok = fail = 0
    for d in train_raw:
        try:
            render_slide(json.loads(d["messages"][2]["content"]))
            ok += 1
        except Exception:
            fail += 1
    print(f"Renderer check: {ok} OK, {fail} failed (failed pairs will be dropped)")
    # Drop unparseable / unrenderable pairs
    def is_valid(d):
        try:
            render_slide(json.loads(d["messages"][2]["content"]))
            return True
        except Exception:
            return False
    train_raw = [d for d in train_raw if is_valid(d)]
    print(f"Clean train pairs: {len(train_raw)}")
except ImportError:
    print("renderer.py not found — skipping render validation (OK for Colab without full repo)")

# %% [markdown]
# ## Cell 3 — Load model with Unsloth (4-bit QLoRA)

# %%
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name      = BASE_MODEL,
    max_seq_length  = MAX_SEQ_LEN,
    dtype           = None,      # auto-detect: BF16 on Ampere+, FP16 on T4
    load_in_4bit    = True,      # QLoRA — fits in 16 GB VRAM
)

# Apply LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r                   = LORA_RANK,
    target_modules      = TARGET_MODS,
    lora_alpha          = LORA_ALPHA,
    lora_dropout        = LORA_DROPOUT,
    bias                = "none",
    use_gradient_checkpointing = "unsloth",   # saves ~30% VRAM
    random_state        = 42,
    use_rslora          = False,
    loftq_config        = None,
)

print(model.print_trainable_parameters())

# Use Qwen2.5 chat template
tokenizer = get_chat_template(tokenizer, chat_template="qwen-2.5")

# %% [markdown]
# ## Cell 4 — Format data for training

# %%
EOS = tokenizer.eos_token

def format_example(example: dict) -> dict:
    """Convert chat-format dict to a single 'text' string using the model's template."""
    messages = example["messages"]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize    = False,
        add_generation_prompt = False,
    )
    return {"text": text + EOS}

train_dataset = Dataset.from_list(train_raw).map(format_example, remove_columns=["messages"])
val_dataset   = Dataset.from_list(val_raw).map(format_example,   remove_columns=["messages"])

# Spot-check
sample = train_dataset[0]["text"]
print(f"Sample formatted length: {len(sample)} chars")
print(sample[:400])
print("...")
print(sample[-200:])

# %% [markdown]
# ## Cell 5 — Train

# %%
trainer = SFTTrainer(
    model       = model,
    tokenizer   = tokenizer,
    train_dataset = train_dataset,
    eval_dataset  = val_dataset,
    args = SFTConfig(
        dataset_text_field      = "text",
        max_seq_length          = MAX_SEQ_LEN,
        dataset_num_proc        = 2,
        packing                 = False,      # packing can corrupt structured output tasks
        per_device_train_batch_size = BATCH_SIZE,
        gradient_accumulation_steps = GRAD_ACCUM,
        num_train_epochs        = EPOCHS,
        learning_rate           = LR,
        lr_scheduler_type       = "cosine",
        warmup_ratio            = WARMUP_RATIO,
        weight_decay            = WEIGHT_DECAY,
        optim                   = "adamw_8bit",
        fp16                    = not torch.cuda.is_bf16_supported(),
        bf16                    = torch.cuda.is_bf16_supported(),
        logging_steps           = 10,
        eval_steps              = 100,
        save_steps              = 200,
        save_total_limit        = 3,
        output_dir              = OUTPUT_DIR,
        report_to               = "none",     # change to "wandb" if you have a W&B account
        load_best_model_at_end  = True,
        metric_for_best_model   = "eval_loss",
        greater_is_better       = False,
    ),
)

trainer_stats = trainer.train()
print(f"\nTraining complete.")
print(f"  Runtime:    {trainer_stats.metrics['train_runtime']:.0f}s")
print(f"  Train loss: {trainer_stats.metrics['train_loss']:.4f}")

# %% [markdown]
# ## Cell 6 — Quick quality check before export

# %%
FastLanguageModel.for_inference(model)

TEST_PROMPTS = [
    "Chapter divider for section 02 titled Market Dynamics",
    "Cover slide for a deck titled 'Private Equity Outlook 2025'",
    "CTA closing slide: three next steps — approve budget, launch pilot, hire programme lead",
    "Two-column slide comparing FY2024 vs FY2023 revenue by region using a bar chart",
    "Donut chart showing market share split: Tata 49%, Ashok Leyland 31%, VECV 17%, Others 3%",
]

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

print("=" * 60)
for prompt in TEST_PROMPTS:
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
            input_ids   = inputs,
            max_new_tokens = 800,
            temperature = 0.1,
            do_sample   = True,
            pad_token_id = tokenizer.eos_token_id,
        )

    decoded = tokenizer.decode(out[0][inputs.shape[1]:], skip_special_tokens=True)
    try:
        parsed = json.loads(decoded)
        slide_type = parsed.get("slide_type", "?")
        has_content = bool(parsed.get("content"))
        valid = "✓ valid JSON"
    except Exception as e:
        slide_type = "PARSE ERROR"
        has_content = False
        valid = f"✗ {e}"

    print(f"\nPROMPT: {prompt[:60]}")
    print(f"  slide_type={slide_type}  has_content={has_content}  {valid}")
    if "✗" in valid:
        print(f"  Raw: {decoded[:200]}")

# %% [markdown]
# ## Cell 7 — Save as GGUF (Q4_K_M, ~4.5 GB)
# This is the file you load into Ollama / llama.cpp on the company server.

# %%
print(f"Saving GGUF ({GGUF_QUANT}) — takes 5-10 minutes …")
model.save_pretrained_gguf(
    GGUF_NAME,
    tokenizer,
    quantization_method = GGUF_QUANT,
)
gguf_path = Path(f"{GGUF_NAME}.{GGUF_QUANT.upper().replace('_','-')}.gguf")
if not gguf_path.exists():
    # Unsloth sometimes uses slightly different naming
    candidates = list(Path(".").glob(f"{GGUF_NAME}*.gguf"))
    gguf_path  = candidates[0] if candidates else Path(f"{GGUF_NAME}.gguf")

print(f"\n✓ GGUF saved: {gguf_path}  ({gguf_path.stat().st_size / 1e9:.2f} GB)")
print("\nNext steps:")
print("  1. Download this file from Colab (Files panel → right-click → Download)")
print("  2. Transfer to company server")
print("  3. ollama create pptmaker-dsl -f Modelfile")
print("     (see Modelfile template printed below)")
print()
print("=" * 60)
print("Modelfile template:")
print("=" * 60)
modelfile = f"""FROM ./{gguf_path.name}

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 1024
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"

SYSTEM You are a consulting slide generator. Given a plain-English description, return a JSON spec for a 1280x720 slide. Return ONLY valid JSON — no markdown, no commentary.
"""
print(modelfile)

# Also save the Modelfile next to the gguf
Path("Modelfile").write_text(modelfile)
print("Modelfile written to ./Modelfile")

# %% [markdown]
# ## Cell 8 — (Optional) Also save HuggingFace format
# Keep this if you want to do further fine-tuning or evaluation later.

# %%
HF_SAVE_PATH = "pptmaker_dsl_hf"
model.save_pretrained(HF_SAVE_PATH)
tokenizer.save_pretrained(HF_SAVE_PATH)
print(f"HF model saved to {HF_SAVE_PATH}/")
print("This is also uploadable to HuggingFace Hub: huggingface-cli upload YOUR_USER/pptmaker-dsl ./pptmaker_dsl_hf")
