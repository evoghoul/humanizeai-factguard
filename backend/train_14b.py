import os, torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

MODEL_ID = "Qwen/Qwen2.5-14B-Instruct"
DATASET_FILE = "expanded_training_data_14b.jsonl"
OUTPUT_DIR = "humanizeai_14b_lora"

def main():
    print("==================================================")
    print("Starting Qwen2.5-14B-Instruct Fine-Tuning on GPU")
    print("==================================================")
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
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
    
    model = prepare_model_for_kbit_training(model)
    model.gradient_checkpointing_enable()
    
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
    
    def format_chat(batch):
        texts = []
        for msgs in batch["messages"]:
            text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
            texts.append(text)
        return {"text": texts}
        
    formatted_dataset = dataset.map(format_chat, batched=True)
    
    trainer = None
    # 1. Try modern trl with SFTConfig
    try:
        from trl import SFTTrainer, SFTConfig
        try:
            # Modern trl (>=0.14) uses max_length
            args = SFTConfig(
                output_dir=OUTPUT_DIR,
                dataset_text_field="text",
                max_length=1024,
                per_device_train_batch_size=1,
                gradient_accumulation_steps=4,
                learning_rate=2e-4,
                num_train_epochs=3,
                logging_steps=2,
                optim="paged_adamw_8bit",
                bf16=torch.cuda.is_bf16_supported(),
                report_to="none"
            )
        except TypeError:
            # trl 0.12-0.13 used max_seq_length
            args = SFTConfig(
                output_dir=OUTPUT_DIR,
                dataset_text_field="text",
                max_seq_length=1024,
                per_device_train_batch_size=1,
                gradient_accumulation_steps=4,
                learning_rate=2e-4,
                num_train_epochs=3,
                logging_steps=2,
                optim="paged_adamw_8bit",
                bf16=torch.cuda.is_bf16_supported(),
                report_to="none"
            )
        trainer = SFTTrainer(
            model=model,
            train_dataset=formatted_dataset,
            args=args,
        )
        print("Initialized training with trl SFTTrainer successfully.")
    except Exception as e:
        print(f"SFTTrainer setup failed ({e}), falling back to standard transformers.Trainer...")
        from transformers import Trainer, TrainingArguments, DataCollatorForLanguageModeling
        
        def tokenize_batch(batch):
            return tokenizer(batch["text"], truncation=True, max_length=1024)
            
        tokenized_ds = formatted_dataset.map(tokenize_batch, batched=True, remove_columns=formatted_dataset.column_names)
        
        args = TrainingArguments(
            output_dir=OUTPUT_DIR,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            num_train_epochs=3,
            logging_steps=2,
            optim="paged_adamw_8bit",
            bf16=torch.cuda.is_bf16_supported(),
            report_to="none"
        )
        trainer = Trainer(
            model=model,
            train_dataset=tokenized_ds,
            args=args,
            data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
        )
        print("Initialized training with standard transformers.Trainer successfully.")
    
    print("Fine-tuning in progress...")
    trainer.train()
    
    print(f"Saving fine-tuned adapter to {OUTPUT_DIR}...")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(">>> 14B Fine-Tuning Completed Successfully! <<<")

if __name__ == "__main__":
    main()
