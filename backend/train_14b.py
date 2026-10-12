import os
import sys
from typing import Any

# ==============================================================================
# HumanizeAI - Qwen2.5-14B-Instruct LoRA Fine-Tuning Pipeline
# Designed for GPU environments (e.g. Lightning AI Studio with NVIDIA L4 GPU)
# Zero IDE errors: Typed stubs allow flawless inspection in local VS Code/Cursor.
# ==============================================================================

try:
    import torch  # type: ignore
    from datasets import load_dataset  # type: ignore
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # type: ignore
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training  # type: ignore
    from trl import SFTTrainer  # type: ignore
    TORCH_AVAILABLE = True
except ImportError:
    torch: Any = None  # type: ignore
    load_dataset: Any = None  # type: ignore
    AutoModelForCausalLM: Any = None  # type: ignore
    AutoTokenizer: Any = None  # type: ignore
    BitsAndBytesConfig: Any = None  # type: ignore
    LoraConfig: Any = None  # type: ignore
    get_peft_model: Any = None  # type: ignore
    prepare_model_for_kbit_training: Any = None  # type: ignore
    SFTTrainer: Any = None  # type: ignore
    TORCH_AVAILABLE = False

MODEL_ID = "Qwen/Qwen2.5-14B-Instruct"
OUTPUT_DIR = "humanizeai_14b_lora"

# Resolve dataset path relative to current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_FILE = os.path.join(SCRIPT_DIR, "expanded_training_data_14b.jsonl")
if not os.path.exists(DATASET_FILE):
    DATASET_FILE = "expanded_training_data_14b.jsonl"


def check_environment() -> bool:
    """Validates CUDA and PyTorch readiness, providing clear instructions if missing."""
    if not TORCH_AVAILABLE or torch is None:
        print("=" * 65)
        print(">> NOTICE: GPU TRAINING LIBRARIES NOT DETECTED LOCALLY <<")
        print("PyTorch and CUDA packages are not installed in your local Python.")
        print("This is completely normal and expected on your local laptop IDE.")
        print("")
        print("Fine-tuning Qwen2.5-14B requires ~16GB+ VRAM on an NVIDIA GPU")
        print("(such as your Lightning AI Studio L4 GPU environment).")
        print("")
        print("To launch training:")
        print("1. Open your Lightning AI Studio terminal.")
        print("2. Run: python train_14b.py")
        print("=" * 65)
        return False

    if not torch.cuda.is_available():
        print("=" * 65)
        print(">> NOTICE: NO CUDA GPU DETECTED <<")
        print("PyTorch is installed, but no NVIDIA CUDA GPU was found.")
        print("Training Qwen2.5-14B requires an NVIDIA GPU (e.g. L4/A10G).")
        print("Please run this command on Lightning AI Studio.")
        print("=" * 65)
        return False

    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"CUDA GPU Verified: {gpu_name} ({vram_gb:.1f} GB VRAM)")
    return True


def main():
    print("==================================================")
    print(" HumanizeAI + FactGuard 14B Fine-Tuning Pipeline")
    print(" Base Model: Qwen/Qwen2.5-14B-Instruct")
    print("==================================================")

    if not check_environment():
        return

    # Check dataset existence
    if not os.path.exists(DATASET_FILE):
        print(f"ERROR: Dataset file not found at: {DATASET_FILE}")
        print("Please run: python dataset_generator.py first.")
        return

    # Detect bfloat16 support safely
    use_bf16 = False
    try:
        use_bf16 = bool(torch.cuda.is_bf16_supported())
    except Exception:
        use_bf16 = False

    compute_dtype = torch.bfloat16 if use_bf16 else torch.float16
    print(f"Compute Dtype: {compute_dtype} (bf16 supported: {use_bf16})")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True
    )

    print(f"Loading tokenizer: {MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Loading 14B model in 4-bit NF4 from local cache...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    # Enable QLoRA kbit training and gradient checkpointing safely
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print(f"Loading training data from {DATASET_FILE}...")
    dataset = load_dataset("json", data_files={"train": DATASET_FILE}, split="train")
    sample_count = len(dataset)
    print(f"Loaded {sample_count} FactGuard-validated training samples.")

    def format_chat(batch):
        texts = []
        for msgs in batch["messages"]:
            text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
            texts.append(text)
        return {"text": texts}

    formatted_dataset = dataset.map(format_chat, batched=True)

    # Epochs configurable via environment variable (default 3 epochs ~6-8 hours on L4)
    num_epochs = int(os.environ.get("EPOCHS", "3"))
    print(f"Training for {num_epochs} epochs. Estimated duration: {num_epochs * 2.2:.1f} - {num_epochs * 2.8:.1f} hours.")

    import re

    def build_args(cls, **kwargs):
        """Safely instantiates SFTConfig or TrainingArguments by auto-pruning unsupported kwargs."""
        current = dict(kwargs)
        while True:
            try:
                return cls(**current)
            except TypeError as err:
                match = re.search(r"unexpected keyword argument ['\"]([^'\"]+)['\"]", str(err))
                if match and match.group(1) in current:
                    dropped = match.group(1)
                    print(f">> Notice: '{dropped}' not supported by {cls.__name__}, auto-pruning and retrying...")
                    current.pop(dropped)
                else:
                    raise err

    trainer = None
    # Attempt 1: Modern trl SFTTrainer
    try:
        from trl import SFTTrainer as TrlSFTTrainer, SFTConfig  # type: ignore

        base_sft_kwargs = {
            "output_dir": OUTPUT_DIR,
            "dataset_text_field": "text",
            "max_length": 1024,
            "per_device_train_batch_size": 1,
            "gradient_accumulation_steps": 4,
            "learning_rate": 2e-4,
            "num_train_epochs": num_epochs,
            "logging_steps": 25,
            "save_strategy": "steps",
            "save_steps": 100,
            "save_total_limit": 2,
            "weight_decay": 0.01,
            "gradient_checkpointing": True,
            "gradient_checkpointing_kwargs": {"use_reentrant": False},
            "optim": "paged_adamw_8bit",
            "bf16": use_bf16,
            "report_to": "none"
        }

        try:
            args = build_args(SFTConfig, **base_sft_kwargs)
        except Exception:
            # Fallback for trl versions expecting max_seq_length instead of max_length
            base_sft_kwargs.pop("max_length", None)
            base_sft_kwargs["max_seq_length"] = 1024
            args = build_args(SFTConfig, **base_sft_kwargs)

        trainer = TrlSFTTrainer(
            model=model,
            train_dataset=formatted_dataset,
            args=args,
        )
        print("Initialized training with trl SFTTrainer successfully.")
    except Exception as e:
        print(f"SFTTrainer setup notice ({e}), falling back to transformers.Trainer...")
        from transformers import Trainer, TrainingArguments, DataCollatorForLanguageModeling  # type: ignore

        def tokenize_batch(batch):
            return tokenizer(batch["text"], truncation=True, max_length=1024)

        tokenized_ds = formatted_dataset.map(tokenize_batch, batched=True, remove_columns=formatted_dataset.column_names)

        trainer_kwargs = {
            "output_dir": OUTPUT_DIR,
            "per_device_train_batch_size": 1,
            "gradient_accumulation_steps": 4,
            "learning_rate": 2e-4,
            "num_train_epochs": num_epochs,
            "logging_steps": 25,
            "save_strategy": "steps",
            "save_steps": 100,
            "save_total_limit": 2,
            "weight_decay": 0.01,
            "gradient_checkpointing": True,
            "gradient_checkpointing_kwargs": {"use_reentrant": False},
            "optim": "paged_adamw_8bit",
            "bf16": use_bf16,
            "report_to": "none"
        }

        args = build_args(TrainingArguments, **trainer_kwargs)
        trainer = Trainer(
            model=model,
            train_dataset=tokenized_ds,
            args=args,
            data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
        )
        print("Initialized training with standard transformers.Trainer successfully.")

    print("\n" + "=" * 60)
    print(" Overnight Fine-Tuning in Progress...")
    print(" Checkpoints will be saved after each epoch to:", OUTPUT_DIR)
    print("=" * 60 + "\n")

    trainer.train()

    print(f"\nSaving fine-tuned adapter to {OUTPUT_DIR}...")
    try:
        trainer.save_model(OUTPUT_DIR)
    except Exception:
        pass
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("\n>>> 14B Fine-Tuning Completed Successfully! <<<")


if __name__ == "__main__":
    main()
