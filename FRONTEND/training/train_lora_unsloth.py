"""
HumanizeAI QLoRA Fine-Tuning Script using Unsloth
Can be executed in Google Colab (Free T4 or A100) or cloud instance (RunPod/Lambda).
Target Models:
- unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit (Fastest, low VRAM)
- unsloth/Qwen2.5-7B-Instruct-bnb-4bit (Excellent multilingual & reasoning)
- unsloth/Llama-3.3-70B-Instruct-bnb-4bit (State of the art writing quality)
"""

import os
import torch

try:
    from unsloth import FastLanguageModel
    from datasets import load_dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments
except ImportError:
    print("Please install Unsloth: pip install unsloth trl datasets transformers")
    exit(1)

# 1. Model Configuration
max_seq_length = 4096
dtype = None # Auto detection: Float16 for Tesla T4, Bfloat16 for Ampere+
load_in_4bit = True
model_name = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit"

print(f"Loading base model: {model_name}...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=max_seq_length,
    dtype=dtype,
    load_in_4bit=load_in_4bit,
)

# 2. Add LoRA Adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=16, # LoRA Rank
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)

# 3. Load Dataset
dataset_path = "training/dataset_template.jsonl"
dataset = load_dataset("json", data_files={"train": dataset_path}, split="train")

def formatting_prompts_func(examples):
    convos = examples["messages"]
    texts = [tokenizer.apply_chat_template(convo, tokenize=False, add_generation_prompt=False) for convo in convos]
    return {"text": texts}

formatted_dataset = dataset.map(formatting_prompts_func, batched=True)

# 4. Trainer Configuration
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=formatted_dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    dataset_num_proc=2,
    packing=False,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        max_steps=100,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=5,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir="outputs",
    ),
)

# 5. Train and Save
print("Starting fine-tuning...")
trainer_stats = trainer.train()

print("Saving LoRA adapter and merged 16-bit GGUF/Safetensors...")
model.save_pretrained_merged("humanize-ai-model", tokenizer, save_method="merged_16bit")
print("Model fine-tuning script executed successfully.")
