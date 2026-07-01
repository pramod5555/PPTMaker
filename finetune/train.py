"""train.py — QLoRA fine-tune Qwen2.5-Coder-7B on HTML slide pairs.

Hardware target: RTX 4060 8GB (fits with 4-bit + seq_len=4096)
Expected time:  3-5 hours for 570 pairs x 3 epochs

Run:
    python ppt-dataset/finetune/train.py
    python ppt-dataset/finetune/train.py --epochs 1   # quick test run
"""
import argparse
import json
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_ID      = "Qwen/Qwen2.5-Coder-3B-Instruct"
# 3B fits 8GB laptop GPU comfortably; sufficient for constrained DSL schema task
MAX_SEQ_LEN   = 2048
LORA_R        = 16     # LoRA rank — 16 suits 600-700 pair dataset
LORA_ALPHA    = 32
BATCH_SIZE    = 2      # 3B model frees enough VRAM for batch=2 on 8GB
GRAD_ACCUM    = 4      # effective batch = 8
LR            = 2e-4
WARMUP_RATIO  = 0.05

FINETUNE_DIR  = Path(__file__).parent
# DSL dataset (preferred) — falls back to raw HTML dataset if not yet built
_DSL_TRAIN = Path(__file__).parent.parent.parent / "slide-dsl" / "dsl_finetune" / "dsl_train.jsonl"
_DSL_VAL   = Path(__file__).parent.parent.parent / "slide-dsl" / "dsl_finetune" / "dsl_val.jsonl"
TRAIN_JSONL   = _DSL_TRAIN if _DSL_TRAIN.exists() else FINETUNE_DIR / "finetune_train.jsonl"
VAL_JSONL     = _DSL_VAL   if _DSL_VAL.exists()   else FINETUNE_DIR / "finetune_val.jsonl"
OUTPUT_DIR    = FINETUNE_DIR / "checkpoints"
GGUF_DIR      = FINETUNE_DIR / "gguf"


def load_jsonl(path):
    data = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--export-only", action="store_true",
                        help="Skip training, just export latest checkpoint to GGUF")
    args = parser.parse_args()

    from unsloth import FastLanguageModel
    from unsloth.chat_templates import get_chat_template
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import Dataset

    print(f"Loading {MODEL_ID} in 4-bit...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_ID,
        max_seq_length=MAX_SEQ_LEN,
        dtype=None,           # auto-detect (bf16 on RTX 4060)
        load_in_4bit=True,
    )
    tokenizer = get_chat_template(tokenizer, chat_template="qwen-2.5")

    if not args.export_only:
        # Apply LoRA adapters
        model = FastLanguageModel.get_peft_model(
            model,
            r=LORA_R,
            lora_alpha=LORA_ALPHA,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",  # saves ~30% VRAM
            random_state=42,
        )
        model.print_trainable_parameters()

        # Load data — already in OpenAI chat format {messages: [...]}
        train_raw = load_jsonl(TRAIN_JSONL)
        val_raw   = load_jsonl(VAL_JSONL)

        def format_messages(examples):
            texts = []
            for msgs in examples["messages"]:
                text = tokenizer.apply_chat_template(
                    msgs,
                    tokenize=False,
                    add_generation_prompt=False,
                )
                texts.append(text)
            return {"text": texts}

        train_ds = Dataset.from_list(train_raw).map(format_messages, batched=True,
                                                     remove_columns=["messages"])
        val_ds   = Dataset.from_list(val_raw).map(format_messages,   batched=True,
                                                   remove_columns=["messages"])

        print(f"Train: {len(train_ds)} pairs | Val: {len(val_ds)} pairs")

        # Check token length distribution
        sample_lens = []
        for ex in train_raw[:20]:
            toks = tokenizer.apply_chat_template(ex["messages"], tokenize=True)
            sample_lens.append(len(toks))
        p50 = sorted(sample_lens)[len(sample_lens)//2]
        p95 = sorted(sample_lens)[int(len(sample_lens)*0.95)]
        print(f"Token length sample — median: {p50}  p95: {p95}  (max_seq_len: {MAX_SEQ_LEN})")
        if p95 > MAX_SEQ_LEN:
            print(f"WARNING: some pairs exceed max_seq_len and will be truncated.")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=train_ds,
            eval_dataset=val_ds,
            dataset_text_field="text",
            max_seq_length=MAX_SEQ_LEN,
            dataset_num_proc=2,
            args=TrainingArguments(
                per_device_train_batch_size=BATCH_SIZE,
                gradient_accumulation_steps=GRAD_ACCUM,
                num_train_epochs=args.epochs,
                learning_rate=LR,
                warmup_ratio=WARMUP_RATIO,
                lr_scheduler_type="cosine",
                fp16=False,
                bf16=True,           # RTX 4060 supports bf16
                optim="adamw_8bit",  # 8-bit AdamW saves ~2GB VRAM
                logging_steps=10,
                eval_strategy="epoch",
                save_strategy="epoch",
                save_total_limit=2,
                output_dir=str(OUTPUT_DIR),
                report_to="none",    # disable wandb/tensorboard
                seed=42,
            ),
        )

        print(f"\nStarting training ({args.epochs} epoch(s))...")
        trainer.train()
        print("Training complete.")

        # Save final LoRA adapter
        model.save_pretrained(OUTPUT_DIR / "lora_adapter")
        tokenizer.save_pretrained(OUTPUT_DIR / "lora_adapter")
        print(f"LoRA adapter saved -> {OUTPUT_DIR / 'lora_adapter'}")

    # Export to GGUF (Q4_K_M) for llama.cpp / LM Studio inference
    GGUF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nExporting to GGUF (Q4_K_M) -> {GGUF_DIR}...")
    model.save_pretrained_gguf(
        str(GGUF_DIR),
        tokenizer,
        quantization_method="q4_k_m",   # ~4.1 GB, best quality/size for 7B
    )
    print(f"GGUF export complete. Load in LM Studio or llama.cpp.")
    print(f"\nTo test inference with llama.cpp:")
    print(f"  llama-cli -m {GGUF_DIR}/*.gguf --temp 0.1 -p '<your prompt here>'")


if __name__ == "__main__":
    main()
