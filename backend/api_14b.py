import os
import re
import traceback
try:
    import torch  # type: ignore
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # type: ignore
    from peft import PeftModel  # type: ignore
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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

SYSTEM_INSTRUCTION = (
    "You are HumanizeAI, an expert human editor. Rewrite the input text into authentic, natural human prose "
    "that passes all AI detectors (GPTZero, Turnitin, Originality.ai), strictly adhering to Wikipedia's "
    "'Signs of AI-generated text' negative constraints.\n\n"
    "STRICT WIKIPEDIA ANTI-AI NEGATIVE CONSTRAINTS (NEVER BREAK THESE):\n"
    "1. NO NEGATIVE PARALLELISMS: Strictly forbid 'not just X, but Y', 'it's not about X, it's about Y', or 'not only X, but also Y'. State claims directly without formulaic contrast.\n"
    "2. NO RULE OF THREES: Never list three adjectives, adverbs, or nouns in a rhythmic row (e.g., avoid 'innovative, efficient, and transformative'). Use a single strong word.\n"
    "3. NO 'FALSE RANGES': Never use the lazy sweep 'From X to Y' (e.g., avoid 'From startups to enterprises', 'From marketing to engineering').\n"
    "4. ZERO AI VOCABULARY: Total ban on AI dead-giveaways: delve, intricate, tapestry, pivotal, beacon, crucial, foster, spearhead, furthermore, moreover, in conclusion, realm, landscape, game-changer, seamless, paramount, multifaceted, vibrant, revolutionize, underscore, shed light on, testament, holistic, enhance, cornerstone, in today's fast-paced world.\n"
    "5. NO COMPULSIVE SUMMARIES: Never end with a generic wrap-up or moralizing bow ('In summary,', 'Overall, this highlights...', 'Ultimately, ...'). When the thought ends, stop writing.\n"
    "6. NO VAGUE ATTRIBUTION: Avoid empty hedges ('It is important to note that', 'Some critics argue', 'It remains to be seen').\n"
    "7. EXTREME BURSTINESS: Wildly vary sentence lengths. Alternate 2-to-5 word punchy sentences/fragments ('Fair enough.', 'Hardly surprising.', 'Not quite.') with natural 18-to-26 word compound thoughts. Never write consecutive sentences of equal length.\n"
    "8. FACTGUARD INVARIANTS (100% INVIOLABLE): Strictly preserve every number, date, year, currency ($/€/£), percentage (%), proper name, and negative condition (not, never, cannot). Never drop, round, or alter any fact.\n"
    "9. STRICT FORMAT: Output ONLY the raw rewritten text. Absolutely NO conversational preambles ('Sure!', 'Here is a...'), NO quotation marks, and NO explanations."
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

def clean_wikipedia_ai_tells(text: str) -> str:
    cleaned = strip_preamble(text)
    # Strip compulsive summaries at end
    cleaned = re.sub(r"\n*(?:In conclusion|In summary|Overall|Ultimately),.*$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned

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
                "content": "Tone: Conversational\nStrength: Heavy\n\nOriginal Text:\nArtificial intelligence has transformed the modern business landscape in profound ways. Companies worldwide are leveraging machine learning to enhance operational efficiency and foster innovation. It is important to note that organizations must adopt strategic frameworks to navigate these technological changes seamlessly and remain competitive in today's digital era."
            },
            {
                "role": "assistant",
                "content": "AI has completely upended the modern workplace—and it happened fast. Teams everywhere are leaning on machine learning to speed up clunky workflows and spark fresh ideas. But here's the catch: without a practical game plan, jumping headfirst into these tools usually causes more headaches than breakthroughs. In other words, you need a strategy, not just shiny software."
            },
            {
                "role": "user",
                "content": "Tone: Professional\nStrength: Medium\n\nOriginal Text:\nThe quarterly financial report demonstrates significant revenue growth of 18.5% reaching $4.2 million on September 30, 2025. However, leadership must remain vigilant regarding market volatility."
            },
            {
                "role": "assistant",
                "content": "By September 30, 2025, revenue jumped 18.5% to hit $4.2 million. Solid numbers. Even so, leadership can't afford to get comfortable—market swings are still a very real threat."
            },
            {
                "role": "user",
                "content": f"Tone: {req.tone}\nStrength: {req.strength}\n\nOriginal Text:\n{req.text}"
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
        decoded = clean_wikipedia_ai_tells(raw_decoded)
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
