import os
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

        print(f"Loading base model onto GPU: {BASE_MODEL}")
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

import re

SYSTEM_INSTRUCTION = (
    "You are HumanizeAI, an expert human editor. Rewrite the input text into natural, fluent, human prose "
    "that reads genuinely human and passes all AI detectors (high perplexity and high burstiness).\n\n"
    "CRITICAL GUIDELINES:\n"
    "1. FACTGUARD INVARIANTS: Strictly preserve all numbers, dates, years, currencies ($/€/£), percentages (%), proper names, and negative conditions (not, never, cannot). Never drop or alter any fact.\n"
    "2. BURSTINESS & RHYTHM: Vary sentence lengths dramatically. Mix short 4-word punchy sentences with longer compound thoughts (18-24 words).\n"
    "3. BAN AI CLICHÉS: Strictly avoid delve, testament, tapestry, pivotal, beacon, crucial, foster, spearhead, furthermore, moreover, in conclusion, realm, landscape, game-changer, seamless, paramount, multifaceted, vibrant.\n"
    "4. NO MERE SYNONYM SWAPPING: Do NOT simply replace words with synonyms in the same sentence order. Completely rethink the rhythm and structure like a real human writer.\n"
    "5. STRENGTH SCALING:\n"
    "   - light: Clean up robotic transitions and stiff phrasing while keeping original structure intact.\n"
    "   - medium: Reorganize sentence order, introduce natural contractions, and mix sentence lengths.\n"
    "   - heavy / high: Boldly reshape the prose from scratch with fresh human voice, punchy hooks, and dynamic flow.\n"
    "6. FORMAT: Output ONLY the rewritten text. Absolutely NO conversational preambles (e.g., 'Sure!', 'Here is...'), NO quotes, and NO explanations."
)

def strip_preamble(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\n([\s\S]*?)\n```$", r"\1", cleaned)
    cleaned = re.sub(
        r"^(Here(?:'s|\s+is)\s+(?:a|the|your)?\s*(?:casual|natural|professional|humanized|rewritten)?\s*(?:take|version|rewrite|draft)?[:\-\n]+|"
        r"Sure(?:!|,|\.)?\s*(?:Here(?:'s|\s+is)[^:\n]*[:\-\n]+)?|"
        r"Certainly(?:!|,|\.)?\s*(?:Here(?:'s|\s+is)[^:\n]*[:\-\n]+)?|"
        r"Of course(?:!|,|\.)?\s*(?:Here(?:'s|\s+is)[^:\n]*[:\-\n]+)?)\s*",
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
            {"role": "user", "content": f"Tone: {req.tone}\nStrength: {req.strength}\n\nOriginal Text:\n{req.text}"}
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
                temperature=0.85,
                top_p=0.92,
                repetition_penalty=1.12,
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
