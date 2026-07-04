"""train_mlx.py — Fine-tune Qwen2.5-Coder-7B on Mac M3 using MLX LoRA.

Requirements:
    pip install mlx-lm

Run:
    python slide-dsl/train_mlx.py
    python slide-dsl/train_mlx.py --fuse-only    # skip training, just fuse adapter
    python slide-dsl/train_mlx.py --epochs 1     # quick smoke-test (178 steps)
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT        = Path(__file__).parent.parent
DSL_DIR     = ROOT / "slide-dsl" / "dsl_finetune"
MLX_DATA    = ROOT / "slide-dsl" / "mlx_data"
ADAPTER_DIR = ROOT / "ppt-dataset" / "finetune" / "mlx_adapter"
FUSED_DIR   = ROOT / "ppt-dataset" / "finetune" / "mlx_fused"

MODEL   = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
RANK    = 8
SCALE   = 2.0
LAYERS  = 8
BATCH   = 1
LR      = 1e-4
MAX_SEQ = 1024


def steps_for_epochs(n_train: int, n_epochs: int) -> tuple[int, int]:
    """Return (total_steps, warmup_steps) for given epoch count."""
    steps_per_epoch = math.ceil(n_train / BATCH)
    total  = steps_per_epoch * n_epochs
    warmup = max(1, round(total * 0.05))
    return total, warmup


TRAIN_SYSTEM_PROMPT = "You are a consulting slide generator. Return ONLY valid JSON — no markdown, no commentary."


def prepare_data() -> tuple[Path, int]:
    """Write mlx_data/ JSONL with a minimal system prompt to save tokens during training.

    The full schema prompt is used at inference; during training the model learns
    the output format from (user, assistant) pairs, not from the schema description.
    """
    import json as _json
    MLX_DATA.mkdir(parents=True, exist_ok=True)

    char_limit = int(MAX_SEQ * 3.5)  # ~3 chars/token

    pairs = [
        (DSL_DIR / "dsl_train.jsonl", MLX_DATA / "train.jsonl"),
        (DSL_DIR / "dsl_val.jsonl",   MLX_DATA / "valid.jsonl"),
    ]
    for src, dst in pairs:
        if not src.exists():
            sys.exit(f"Missing: {src}\nRun build_dsl_dataset.py first.")
        kept, dropped = 0, 0
        with open(dst, "w", encoding="utf-8") as out:
            for line in open(src, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                ex = _json.loads(line)
                # Replace verbose system prompt with minimal one
                msgs = ex["messages"]
                if msgs and msgs[0]["role"] == "system":
                    msgs[0]["content"] = TRAIN_SYSTEM_PROMPT
                # Filter examples still too long after prompt replacement
                total_chars = sum(len(m["content"]) for m in msgs)
                if total_chars <= char_limit:
                    out.write(_json.dumps({"messages": msgs}, ensure_ascii=False) + "\n")
                    kept += 1
                else:
                    dropped += 1
        print(f"  {dst.name}: {kept} kept, {dropped} dropped (>{char_limit} chars)")

    n_train = sum(1 for _ in open(MLX_DATA / "train.jsonl", encoding="utf-8"))
    n_val   = sum(1 for _ in open(MLX_DATA / "valid.jsonl", encoding="utf-8"))
    print(f"Data ready: {n_train} train | {n_val} val")
    return MLX_DATA, n_train


def write_lora_config(data_dir: Path, total_iters: int, warmup_iters: int) -> Path:
    import json
    resume_path = ADAPTER_DIR / "adapters.safetensors"
    config = {
        "model": MODEL,
        "train": True,
        "data": str(data_dir),
        "iters": total_iters,
        "batch_size": BATCH,
        "learning_rate": LR,
        "warmup": warmup_iters,
        "num_layers": LAYERS,
        "val_batches": 8,
        "steps_per_report": 10,
        "steps_per_eval": 50,
        "save_every": 100,
        "adapter_path": str(ADAPTER_DIR),
        "max_seq_length": MAX_SEQ,
        "grad_checkpoint": True,
        "lora_parameters": {
            "rank": RANK,
            "scale": SCALE,
            "dropout": 0.0,
        },
    }
    if resume_path.exists():
        config["resume_adapter_file"] = str(resume_path)
        print(f"Resuming from {resume_path}")
    cfg_path = data_dir / "lora_config.json"
    cfg_path.write_text(json.dumps(config, indent=2))
    return cfg_path


def run_training(data_dir: Path, n_train: int, n_epochs: int) -> None:
    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    total_iters, warmup_iters = steps_for_epochs(n_train, n_epochs)
    cfg_path = write_lora_config(data_dir, total_iters, warmup_iters)

    cmd = [
        sys.executable, "-m", "mlx_lm", "lora",
        "-c", str(cfg_path),
    ]

    print(f"\nModel   : {MODEL}")
    print(f"Pairs   : {n_train} train")
    print(f"Epochs  : {n_epochs}  ({total_iters} steps, batch={BATCH})")
    print(f"Adapter : {ADAPTER_DIR}")
    print(f"Warmup  : {warmup_iters} steps\n")
    subprocess.run(cmd, check=True)


def fuse_model(adapter_path: Path | None = None) -> None:
    FUSED_DIR.mkdir(parents=True, exist_ok=True)
    adapter = adapter_path or ADAPTER_DIR
    print(f"\nFusing adapter into base model -> {FUSED_DIR}")
    print(f"Adapter: {adapter}")
    cmd = [
        sys.executable, "-m", "mlx_lm", "fuse",
        "--model",        MODEL,
        "--adapter-path", str(adapter),
        "--save-path",    str(FUSED_DIR),
    ]
    subprocess.run(cmd, check=True)
    print("Fuse complete.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs",    type=int, default=3)
    ap.add_argument("--fuse-only", action="store_true",
                    help="Skip training, just fuse the saved adapter")
    args = ap.parse_args()

    if not args.fuse_only:
        data_dir, n_train = prepare_data()
        run_training(data_dir, n_train, args.epochs)

    fuse_model()

    print("\n=== Training complete ===")
    print(f"Fused model : {FUSED_DIR}")
    print("\nGenerate a slide (Mac, MLX inference):")
    print(f"  python slide-dsl/generate.py 'your prompt' --mode mlx --model {FUSED_DIR}")
    print("\nGenerate a slide (Windows, llama.cpp) — convert first:")
    print("  python -m mlx_lm.convert --hf-path", FUSED_DIR,
          "--mlx-path /tmp/q4 -q --q-bits 4")
    print("  # Then use llama.cpp convert_hf_to_gguf.py on /tmp/q4")


if __name__ == "__main__":
    main()
