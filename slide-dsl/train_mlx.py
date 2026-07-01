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

MODEL   = "Qwen/Qwen2.5-Coder-7B-Instruct"
RANK    = 16
SCALE   = 2.0   # lora_alpha / lora_rank = 32/16
LAYERS  = 16    # apply LoRA to last 16 of 28 transformer layers
BATCH   = 4     # M3 16GB handles batch=4 at 2048 seq_len comfortably
LR      = 2e-4
N_TRAIN = 711   # pairs in dsl_train.jsonl


def steps_for_epochs(n_epochs: int) -> tuple[int, int]:
    """Return (total_steps, warmup_steps) for given epoch count."""
    steps_per_epoch = math.ceil(N_TRAIN / BATCH)
    total  = steps_per_epoch * n_epochs
    warmup = max(1, round(total * 0.05))
    return total, warmup


def prepare_data() -> Path:
    """Copy dsl_train/val JSONL into mlx_data/ with names mlx_lm expects."""
    MLX_DATA.mkdir(parents=True, exist_ok=True)
    pairs = [
        (DSL_DIR / "dsl_train.jsonl", MLX_DATA / "train.jsonl"),
        (DSL_DIR / "dsl_val.jsonl",   MLX_DATA / "valid.jsonl"),
    ]
    for src, dst in pairs:
        if not src.exists():
            sys.exit(f"Missing: {src}\nRun build_dsl_dataset.py first.")
        shutil.copy2(src, dst)

    n_train = sum(1 for _ in open(MLX_DATA / "train.jsonl", encoding="utf-8"))
    n_val   = sum(1 for _ in open(MLX_DATA / "valid.jsonl", encoding="utf-8"))
    print(f"Data ready: {n_train} train | {n_val} val")
    return MLX_DATA


def run_training(data_dir: Path, n_epochs: int) -> None:
    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    total_iters, warmup_iters = steps_for_epochs(n_epochs)

    cmd = [
        sys.executable, "-m", "mlx_lm.lora",
        "--model",            MODEL,
        "--data",             str(data_dir),
        "--train",
        "--iters",            str(total_iters),
        "--batch-size",       str(BATCH),
        "--learning-rate",    str(LR),
        "--warmup",           str(warmup_iters),
        "--lora-layers",      str(LAYERS),
        "--lora-rank",        str(RANK),
        "--lora-scale",       str(SCALE),
        "--val-batches",      "20",
        "--steps-per-report", "10",
        "--steps-per-eval",   "50",
        "--save-every",       "100",
        "--adapter-path",     str(ADAPTER_DIR),
    ]

    print(f"\nModel   : {MODEL}")
    print(f"Epochs  : {n_epochs}  ({total_iters} steps, batch={BATCH})")
    print(f"Adapter : {ADAPTER_DIR}")
    print(f"Warmup  : {warmup_iters} steps\n")
    subprocess.run(cmd, check=True)


def fuse_model() -> None:
    FUSED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nFusing adapter into base model -> {FUSED_DIR}")
    cmd = [
        sys.executable, "-m", "mlx_lm.fuse",
        "--model",        MODEL,
        "--adapter-path", str(ADAPTER_DIR),
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
        data_dir = prepare_data()
        run_training(data_dir, args.epochs)

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
