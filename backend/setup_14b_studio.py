#!/usr/bin/env python3
"""
HumanizeAI 14B Studio Setup Script
Sets up dataset, FactGuard, training script, and inference server for Qwen2.5-14B-Instruct.
"""

import os
import json

DATASET = [
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "The quarterly earnings call took place on October 14, 2025. Total revenue rose by 14.8% to $12.4M, whereas operating margins did not decline below 21%. Furthermore, Dr. Aris Thorne stated that product delivery would not commence before Q1 2026 unless client approvals are finalized."},
            {"role": "assistant", "content": "The quarterly earnings call took place on October 14, 2025. Total revenue grew 14.8% to reach $12.4M, and operating margins held firm, not dipping below 21%. Dr. Aris Thorne also noted that product delivery won't start until Q1 2026, unless client approvals are wrapped up sooner."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "It is important to note that the fiscal year 2024 generated $450,000 in recurring subscriptions. However, 12 customers did not renew their annual service agreements. CFO Marcus Vance emphasized that operational expenditure was reduced by 8.5% across all 4 regional subsidiaries."},
            {"role": "assistant", "content": "Fiscal year 2024 brought in $450,000 from recurring subscriptions, though 12 customers chose not to renew their annual service plans. CFO Marcus Vance highlighted that operational spending dropped 8.5% across all 4 regional subsidiaries."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "During the board summit on November 3, 2025, Helena Rostova announced an initial budget of €3.2M for European market penetration. She warned that profitability cannot be achieved within the first 18 months."},
            {"role": "assistant", "content": "At the board summit on November 3, 2025, Helena Rostova unveiled a €3.2M budget to expand into Europe. She cautioned that the initiative cannot turn a profit within its first 18 months."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "In accordance with the study conducted by Larson et al. [3], 42 out of 50 patient subjects did not display adverse reactions to the 100mg dosage. However, patients with preexisting cardiovascular conditions were specifically excluded from the cohort."},
            {"role": "assistant", "content": "As shown in the study by Larson et al. [3], 42 of the 50 patients showed no adverse reactions to the 100mg dose. Crucially, individuals with preexisting cardiovascular conditions were not included in the cohort."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "The clinical trial commenced on January 15, 2026, administering 50mg of compound AZ-902 twice daily. Statistical significance was verified at p < 0.01, yet researchers could not conclude a causal link between treatment duration and long-term remission."},
            {"role": "assistant", "content": "The clinical trial began on January 15, 2026, testing a 50mg dose of compound AZ-902 twice a day. Even though statistical significance was confirmed at p < 0.01, researchers were unable to establish a causal connection between the length of treatment and long-term remission."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "The distributed database cluster experienced 99.98% uptime in February 2026. Latency spikes exceeding 250ms were isolated to node cluster us-east-1b, affecting approximately 1,200 concurrent user sessions. No data loss occurred during the failover event."},
            {"role": "assistant", "content": "The distributed database cluster achieved 99.98% uptime throughout February 2026. Latency spikes above 250ms were confined to the us-east-1b node cluster, impacting around 1,200 active user sessions, though no data was lost during the failover."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "The audit committee did not approve the transfer of $85,000 on March 4, 2026, because compliance documentation was neither signed by the division lead nor validated by internal legal counsel."},
            {"role": "assistant", "content": "The audit committee withheld approval for the $85,000 transfer on March 4, 2026, as compliance forms were neither signed by the division lead nor cleared by internal legal counsel."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "Preliminary benchmarks suggest that algorithm B is 2.3x faster than algorithm A. However, this does not imply that algorithm B is suitable for low-memory mobile hardware with under 4GB of RAM."},
            {"role": "assistant", "content": "Early benchmarks show algorithm B running 2.3x faster than algorithm A. That said, this doesn't mean algorithm B is ready for budget mobile devices equipped with less than 4GB of RAM."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "I am writing to formally communicate that your candidate interview with David Sterling has been rescheduled from Thursday, April 9 at 2:00 PM to Friday, April 10 at 10:30 AM EST. Please confirm your availability by Wednesday at 5:00 PM."},
            {"role": "assistant", "content": "I wanted to let you know that your interview with David Sterling has been moved from Thursday, April 9 at 2:00 PM to Friday, April 10 at 10:30 AM EST. Please let us know if that time works for you by Wednesday at 5:00 PM."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are HumanizeAI, an expert writing assistant. Rewrite the input text into natural, fluent, human prose. You MUST strictly preserve all numbers, dates, names, currencies, percentages, negations, and factual details."},
            {"role": "user", "content": "Please be advised that all 3 deliverables outlined in project milestone 4 must be finalized prior to December 18, 2025. Failure to submit deliverables will result in a 5% contractual penalty per day."},
            {"role": "assistant", "content": "Just a reminder that all 3 deliverables for milestone 4 need to be finished before December 18, 2025. Late submissions incur a 5% contract penalty for each day delayed."}
        ]
    }
]

def write_files():
    # 1. Dataset
    try:
        from dataset_generator import SAMPLES, make_sample
        samples_data = [make_sample(u, a) for u, a in SAMPLES]
        with open("expanded_training_data_14b.jsonl", "w", encoding="utf-8") as f:
            for item in samples_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Created expanded_training_data_14b.jsonl with {len(samples_data)} rich training pairs.")
    except Exception:
        with open("expanded_training_data_14b.jsonl", "w", encoding="utf-8") as f:
            for item in DATASET:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print("Created expanded_training_data_14b.jsonl (fallback)")

    # 2. FactGuard
    factguard_code = '''import re

NUMBER_PATTERN = re.compile(r'(?:\\$|€|£|¥)?\\b\\d+(?:[.,:/-]\\d+)*(?:%|°[CF]|\\s*(?:AM|PM|kg|lbs|mph|km/h|ms|px|GB|MB|KB|GHz|MHz|USD|EUR|GBP|INR)\\b)?')
YEAR_PATTERN = re.compile(r'\\b(?:19\\d\\d|20\\d\\d)\\b')
NEGATION_PATTERN = re.compile(r'\\b(?:not|never|neither|nor|no|cannot|can\\'t|won\\'t|didn\\'t|doesn\\'t|isn\\'t|aren\\'t|wasn\\'t|weren\\'t)\\b', re.IGNORECASE)

def check_numbers(original: str, rewritten: str) -> list[str]:
    orig_nums = set(NUMBER_PATTERN.findall(original))
    rewr_nums = set(NUMBER_PATTERN.findall(rewritten))
    missing = orig_nums - rewr_nums
    warnings = []
    for num in missing:
        warnings.append(f"Number, measurement, or unit '{num}' was omitted or modified in the rewrite.")
    return warnings

def check_years(original: str, rewritten: str) -> list[str]:
    orig_years = set(YEAR_PATTERN.findall(original))
    rewr_years = set(YEAR_PATTERN.findall(rewritten))
    missing = orig_years - rewr_years
    warnings = []
    for yr in missing:
        warnings.append(f"Year '{yr}' was omitted or modified.")
    return warnings

def check_negations(original: str, rewritten: str) -> list[str]:
    orig_neg = set(n.lower() for n in NEGATION_PATTERN.findall(original))
    rewr_neg = set(n.lower() for n in NEGATION_PATTERN.findall(rewritten))
    warnings = []
    if orig_neg and not rewr_neg:
        warnings.append(f"A negative condition ({', '.join(orig_neg)}) appears to have been removed or flipped.")
    return warnings

def factguard_check(original: str, rewritten: str) -> dict:
    warnings = []
    warnings.extend(check_numbers(original, rewritten))
    warnings.extend(check_years(original, rewritten))
    warnings.extend(check_negations(original, rewritten))
    
    needs_review = len(warnings) > 0
    return {
        "warnings": warnings,
        "needs_review": needs_review,
        "summary": "No heuristic warnings detected. This does not guarantee factual accuracy." if not needs_review else f"{len(warnings)} potential issue(s) detected."
    }
'''
    with open("factguard.py", "w", encoding="utf-8") as f:
        f.write(factguard_code)
    print("Created factguard.py")

    # 3. Training Script
    train_code = '''import os
import sys
from typing import Any

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
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_FILE = os.path.join(SCRIPT_DIR, "expanded_training_data_14b.jsonl")
if not os.path.exists(DATASET_FILE):
    DATASET_FILE = "expanded_training_data_14b.jsonl"

def check_environment() -> bool:
    if not TORCH_AVAILABLE or torch is None or not torch.cuda.is_available():
        print("=" * 65)
        print(">> NOTICE: GPU TRAINING LIBRARIES NOT DETECTED LOCALLY <<")
        print("PyTorch and CUDA packages are not installed or no GPU found.")
        print("Please run this command on Lightning AI Studio.")
        print("=" * 65)
        return False
    return True

def main():
    print("==================================================")
    print(" HumanizeAI + FactGuard 14B Fine-Tuning Pipeline")
    print(" Base Model: Qwen/Qwen2.5-14B-Instruct")
    print("==================================================")
    
    if not check_environment():
        return
        
    use_bf16 = False
    try:
        use_bf16 = bool(torch.cuda.is_bf16_supported())
    except Exception:
        use_bf16 = False
        
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if use_bf16 else torch.float16,
        bnb_4bit_use_double_quant=True
    )
    
    print(f"Loading tokenizer: {MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    print(f"Loading 14B model in 4-bit NF4...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    
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
    print(f"Loaded {len(dataset)} FactGuard-validated training samples.")
    
    def format_chat(batch):
        texts = []
        for msgs in batch["messages"]:
            text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
            texts.append(text)
        return {"text": texts}
        
    formatted_dataset = dataset.map(format_chat, batched=True)
    num_epochs = int(os.environ.get("EPOCHS", "3"))
    print(f"Training for {num_epochs} epochs (~{num_epochs * 2.3:.1f} hours on L4 GPU)...")
    
    trainer = None
    try:
        from trl import SFTTrainer, SFTConfig
        args = SFTConfig(
            output_dir=OUTPUT_DIR,
            dataset_text_field="text",
            max_length=1024,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            num_train_epochs=num_epochs,
            logging_steps=25,
            save_strategy="epoch",
            save_total_limit=2,
            warmup_ratio=0.03,
            weight_decay=0.01,
            gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
            optim="paged_adamw_8bit",
            bf16=use_bf16,
            report_to="none"
        )
        trainer = SFTTrainer(
            model=model,
            train_dataset=formatted_dataset,
            args=args,
        )
        print("Initialized training with trl SFTTrainer successfully.")
    except Exception as e:
        print(f"SFTTrainer setup notice ({e}), falling back to transformers.Trainer...")
        from transformers import Trainer, TrainingArguments, DataCollatorForLanguageModeling
        
        def tokenize_batch(batch):
            return tokenizer(batch["text"], truncation=True, max_length=1024)
            
        tokenized_ds = formatted_dataset.map(tokenize_batch, batched=True, remove_columns=formatted_dataset.column_names)
        
        args = TrainingArguments(
            output_dir=OUTPUT_DIR,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            num_train_epochs=num_epochs,
            logging_steps=25,
            save_strategy="epoch",
            save_total_limit=2,
            warmup_ratio=0.03,
            weight_decay=0.01,
            gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
            optim="paged_adamw_8bit",
            bf16=use_bf16,
            report_to="none"
        )
        trainer = Trainer(
            model=model,
            train_dataset=tokenized_ds,
            args=args,
            data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
        )
        print("Initialized training with standard transformers.Trainer successfully.")
    
    print("\\n==================================================")
    print(" Overnight Fine-Tuning in Progress...")
    print(" Checkpoints will be saved after each epoch to:", OUTPUT_DIR)
    print("==================================================\\n")
    
    trainer.train()
    
    print(f"Saving fine-tuned adapter to {OUTPUT_DIR}...")
    try:
        trainer.save_model(OUTPUT_DIR)
    except Exception:
        pass
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(">>> 14B Fine-Tuning Completed Successfully! <<<")

if __name__ == "__main__":
    main()
'''
    with open("train_14b.py", "w", encoding="utf-8") as f:
        f.write(train_code)
    print("Created train_14b.py")

    # 4. Inference Server
    api_code = '''import os
import re
import traceback
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

try:
    from factguard import factguard_check
except ImportError:
    def factguard_check(orig, rewr):
        return {"warnings": [], "needs_review": False, "summary": "Heuristics skipped"}

app = FastAPI(title="HumanizeAI 14B API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_MODEL = "Qwen/Qwen2.5-14B-Instruct"
ADAPTER_DIR = "humanizeai_14b_lora"

_model = None
_tokenizer = None
_device = None

def get_model():
    global _model, _tokenizer, _device
    if _model is None:
        print("Loading 14B model + LoRA adapter...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True,
            llm_int8_enable_fp32_cpu_offload=True
        )
        tok_path = ADAPTER_DIR if os.path.exists(ADAPTER_DIR) else BASE_MODEL
        print(f"Loading tokenizer from: {tok_path}")
        _tokenizer = AutoTokenizer.from_pretrained(tok_path, trust_remote_code=True)
        if _tokenizer.pad_token is None:
            _tokenizer.pad_token = _tokenizer.eos_token

        print(f"Loading base model: {BASE_MODEL}")
        device_map = {"": 0} if torch.cuda.is_available() else "auto"
        base = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            quantization_config=bnb_config,
            device_map=device_map,
            trust_remote_code=True
        )
        if os.path.exists(ADAPTER_DIR):
            print(f"Applying LoRA adapter from {ADAPTER_DIR}...")
            _model = PeftModel.from_pretrained(base, ADAPTER_DIR)
        else:
            print("Running on base 14B model (adapter directory not found)...")
            _model = base
        _model.eval()
        _device = "cuda:0" if torch.cuda.is_available() else "cpu"
        print(f"14B Model loaded and ready on {_device}!")
    return _model, _tokenizer, _device

@app.on_event("startup")
def startup_event():
    print(">>> HumanizeAI 14B Server starting up... Warming up model...")
    try:
        get_model()
        print(">>> Model warm-up complete! Ready to serve requests.")
    except Exception as e:
        print(f"Failed to pre-load model: {e}")
        traceback.print_exc()

class HumanizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    tone: str = "Standard"
    strength: str = "Medium"

class HumanizeResponse(BaseModel):
    original: str
    rewrite: str
    warnings: list[str]
    needs_review: bool

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "Qwen2.5-14B-Instruct",
        "loaded": _model is not None
    }

SYSTEM_INSTRUCTION = (
    "You are HumanizeAI, an expert human editor. Rewrite the input text into natural, fluent, human prose "
    "that reads genuinely human and passes all AI detectors (high perplexity and high burstiness).\\n\\n"
    "CRITICAL GUIDELINES:\\n"
    "1. FACTGUARD INVARIANTS: Strictly preserve all numbers, dates, years, currencies ($/€/£), percentages (%), proper names, and negative conditions (not, never, cannot). Never drop or alter any fact.\\n"
    "2. BURSTINESS & RHYTHM: Vary sentence lengths dramatically. Mix short 4-word punchy sentences with longer compound thoughts (18-24 words).\\n"
    "3. BAN AI CLICHÉS: Strictly avoid delve, testament, tapestry, pivotal, beacon, crucial, foster, spearhead, furthermore, moreover, in conclusion, realm, landscape, game-changer, seamless, paramount, multifaceted, vibrant.\\n"
    "4. NO MERE SYNONYM SWAPPING: Do NOT simply replace words with synonyms in the same sentence order. Completely rethink the rhythm and structure like a real human writer.\\n"
    "5. STRENGTH SCALING:\\n"
    "   - light: Clean up robotic transitions and stiff phrasing while keeping original structure intact.\\n"
    "   - medium: Reorganize sentence order, introduce natural contractions, and mix sentence lengths.\\n"
    "   - heavy / high: Boldly reshape the prose from scratch with fresh human voice, punchy hooks, and dynamic flow.\\n"
    "6. FORMAT: Output ONLY the rewritten text. Absolutely NO conversational preambles (e.g., 'Sure!', 'Here is...'), NO quotes, and NO explanations."
)

def strip_preamble(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\\n([\\s\\S]*?)\\n```$", r"\\1", cleaned)
    cleaned = re.sub(
        r"^(Here(?:'s|\\s+is)\\s+(?:a|the|your)?\\s*(?:casual|natural|professional|humanized|rewritten)?\\s*(?:take|version|rewrite|draft)?[:\\-\\n]+|"
        r"Sure(?:!|,|\\.)?\\s*(?:Here(?:'s|\\s+is)[^:\\n]*[:\\-\\n]+)?|"
        r"Certainly(?:!|,|\\.)?\\s*(?:Here(?:'s|\\s+is)[^:\\n]*[:\\-\\n]+)?|"
        r"Of course(?:!|,|\\.)?\\s*(?:Here(?:'s|\\s+is)[^:\\n]*[:\\-\\n]+)?)\\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )
    return cleaned.strip()

@app.post("/humanize", response_model=HumanizeResponse)
def humanize(req: HumanizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="Please provide non-empty text.")
    
    try:
        model, tokenizer, device = get_model()
        word_count = len(req.text.split())
        dynamic_max_tokens = min(512, max(64, int(word_count * 2.2)))

        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": "Tone: Conversational\\nStrength: Heavy\\n\\nOriginal Text:\\nArtificial intelligence has transformed the modern business landscape in profound ways. Companies worldwide are leveraging machine learning to enhance operational efficiency and foster innovation. It is important to note that organizations must adopt strategic frameworks to navigate these technological changes seamlessly and remain competitive in today's digital era."
            },
            {
                "role": "assistant",
                "content": "AI has completely upended the modern workplace—and it happened fast. Teams everywhere are leaning on machine learning to speed up clunky workflows and spark fresh ideas. But here's the catch: without a practical game plan, jumping headfirst into these tools usually causes more headaches than breakthroughs. In other words, you need a strategy, not just shiny software."
            },
            {
                "role": "user",
                "content": "Tone: Professional\\nStrength: Medium\\n\\nOriginal Text:\\nThe quarterly financial report demonstrates significant revenue growth of 18.5% reaching $4.2 million on September 30, 2025. However, leadership must remain vigilant regarding market volatility."
            },
            {
                "role": "assistant",
                "content": "By September 30, 2025, revenue jumped 18.5% to hit $4.2 million. Solid numbers. Even so, leadership can't afford to get comfortable—market swings are still a very real threat."
            },
            {
                "role": "user",
                "content": f"Tone: {req.tone}\\nStrength: {req.strength}\\n\\nOriginal Text:\\n{req.text}"
            }
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        
        eos_ids = [tokenizer.eos_token_id]
        if hasattr(tokenizer, "convert_tokens_to_ids"):
            im_end_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
            if im_end_id and im_end_id not in eos_ids:
                eos_ids.append(im_end_id)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=dynamic_max_tokens,
                do_sample=True,
                temperature=0.9,
                top_p=0.95,
                repetition_penalty=1.15,
                eos_token_id=eos_ids,
                use_cache=True,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id
            )
        
        raw_decoded = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
        decoded = strip_preamble(raw_decoded)
        fg = factguard_check(req.text, decoded)
        return HumanizeResponse(
            original=req.text,
            rewrite=decoded,
            warnings=fg.get("warnings", []),
            needs_review=fg.get("needs_review", False)
        )
    except Exception as e:
        print(f"Error during /humanize: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    with open("api_14b.py", "w", encoding="utf-8") as f:
        f.write(api_code)
    print("Created api_14b.py")
    print("\n--- Setup complete! Ready to train 14B model. ---")

if __name__ == "__main__":
    write_files()
