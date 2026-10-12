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
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"CUDA detected: {torch.cuda.get_device_name(0)} with {vram_gb:.1f} GB total VRAM")
        else:
            print("WARNING: CUDA is NOT available! Running on CPU (slow).")

        print("Loading 14B model + LoRA adapter...")
        compute_dtype = torch.bfloat16 if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else torch.float16
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True
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
            torch_dtype=compute_dtype,
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
    "that passes all plagiarism checkers (Turnitin, CopyLeaks, Grammarly) and AI detectors (GPTZero, ZeroGPT, Turnitin AI) "
    "with 0% detection, strictly adhering to Wikipedia's 'Signs of AI-generated text' negative constraints.\n\n"
    "CRITICAL ANTI-PLAGIARISM & ANTI-AI NEGATIVE CONSTRAINTS (NEVER BREAK THESE):\n"
    "1. ZERO N-GRAM PLAGIARISM OVERLAP: Plagiarism checkers flag 4 or more consecutive identical words. "
    "You MUST aggressively rephrase, restructure, and invert the syntax of every sentence. Do NOT preserve the grammatical "
    "order or phrase sequences of the original text. Reorder ideas, swap active and passive voice, and use distinct vocabulary while keeping all facts 100% accurate.\n"
    "2. NO EM-DASHES (—), EN-DASHES (–), OR SEMICOLONS (;): AI models overuse dashes and semicolons to join thoughts. "
    "Real humans write with periods, commas, or conjunctions. Ban all dashes and semicolons completely. Split into short punchy sentences instead.\n"
    "3. NO NEGATIVE PARALLELISMS: Strictly forbid 'not just X, but Y', 'it's not about X, it's about Y', or 'not only X, but also Y'. State claims directly without formulaic contrast.\n"
    "4. NO RULE OF THREES: Never list three adjectives, adverbs, or nouns in a rhythmic row (e.g., avoid 'innovative, efficient, and transformative'). Use a single strong word.\n"
    "5. NO 'FALSE RANGES': Never use the lazy sweep 'From X to Y' (e.g., avoid 'From startups to enterprises', 'From marketing to engineering').\n"
    "6. ZERO AI VOCABULARY: Total ban on AI dead-giveaways: delve, intricate, tapestry, pivotal, beacon, crucial, foster, spearhead, furthermore, moreover, in conclusion, realm, landscape, game-changer, seamless, paramount, multifaceted, vibrant, revolutionize, underscore, shed light on, testament, holistic, enhance, cornerstone, in today's fast-paced world.\n"
    "7. NO COMPULSIVE SUMMARIES OR CLICHÉ TRANSITIONS: Never end with a generic wrap-up ('In summary,', 'Overall, this highlights...', 'Ultimately, ...'). Never use cliché transitions like 'That said,', 'In other words,', 'At the end of the day,', 'Here's the catch:'. When the thought ends, stop writing.\n"
    "8. NO VAGUE ATTRIBUTION: Avoid empty hedges ('It is important to note that', 'Some critics argue', 'It remains to be seen').\n"
    "9. EXTREME BURSTINESS & SENTENCE VARIETY: Wildly vary sentence lengths. Alternate 2-to-5 word punchy sentences/fragments ('Fair enough.', 'Hardly surprising.', 'It works.') with natural 18-to-26 word compound thoughts. Never write consecutive sentences of equal length.\n"
    "10. FACTGUARD INVARIANTS (100% INVIOLABLE): Strictly preserve every number, date, year, currency ($/€/£), percentage (%), proper name, and negative condition (not, never, cannot). Never drop, round, or alter any fact.\n"
    "11. PRESERVE FULL LENGTH AND DEPTH (DO NOT SUMMARIZE OR SHORTEN): Paraphrasing is NOT summarizing. The rewritten text MUST maintain the full depth, completeness, and approximate length of the original passage (90% to 110% of original word count). Do NOT combine multiple distinct thoughts into a single short sentence, and do NOT drop background details, nuances, or explanations. If the original text has multiple paragraphs, preserve the exact paragraph divisions.\n"
    "12. STRICT FORMAT: Output ONLY the raw rewritten text. Absolutely NO conversational preambles ('Sure!', 'Here is a...'), NO quotation marks, and NO explanations."
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
    
    # Strip broken unicode / replacement chars from mangled em-dashes
    cleaned = cleaned.replace("\ufffd", ", ")
    
    # Ban all em-dashes and en-dashes: replace with comma or period
    cleaned = re.sub(r"\s*[—–]\s*", ", ", cleaned)
    
    # Ban all semicolons: replace with period followed by capitalized next word or space
    cleaned = re.sub(r";\s*", ". ", cleaned)
    
    # Ban negative parallelisms: "not just X, but Y"
    cleaned = re.sub(r"\b(?:is|was|are|were|do|does|did)\s+not\s+(?:just|only)\s+([^,;]+)[,;]\s*(?:it's|it\s+is|they're|they\s+are|but\s+also|but)?\s*", r"\1 and ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bnot\s+just\s+([^,;]+)[,;]\s*(?:it's|it\s+is|but\s+also|but)?\s*", r"\1 along with ", cleaned, flags=re.IGNORECASE)

    # Clean residual AI cliché transitions
    cleaned = re.sub(r"\b(?:In other words|That said|That being said|At the end of the day|Here's the catch[:!.]?|Here is the thing[:!.]?|To put it simply),?\s*", "", cleaned, flags=re.IGNORECASE)
    
    # Clean double spaces or duplicate punctuation
    cleaned = re.sub(r"\s*,\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s*\.\s*\.\s*", ". ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

@app.post("/humanize", response_model=HumanizeResponse)
def humanize(req: HumanizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="Please provide non-empty text.")
    
    try:
        model, tokenizer, device = get_model()
        word_count = len(req.text.split())
        dynamic_max_tokens = min(2048, max(128, int(word_count * 2.5)))

        strength_val = (req.strength or "Medium").strip().lower()
        if strength_val == "heavy":
            gen_temp = 1.04
            gen_top_p = 0.92
            gen_top_k = 50
            gen_rep_pen = 1.15
            strength_instruction = (
                "Strength: Heavy (Aggressive structural overhaul, 0% verbatim n-gram overlap, "
                "extreme sentence length variation, zero dashes, zero semicolons, "
                "CRITICAL: preserve 100% of exact numbers, dates, and percentages without rounding)"
            )
        elif strength_val == "light":
            gen_temp = 0.85
            gen_top_p = 0.95
            gen_top_k = 50
            gen_rep_pen = 1.10
            strength_instruction = "Strength: Light (Gentle polish, natural cadence)"
        else: # Medium
            gen_temp = 1.00
            gen_top_p = 0.95
            gen_top_k = 50
            gen_rep_pen = 1.16
            strength_instruction = "Strength: Medium (Balanced humanization, natural burstiness, zero cliché AI vocabulary)"

        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": "Tone: Conversational\nStrength: Heavy\n\nOriginal Text:\nArtificial intelligence has transformed the modern business landscape in profound ways. Companies worldwide are leveraging machine learning to enhance operational efficiency and foster innovation. It is important to note that organizations must adopt strategic frameworks to navigate these technological changes seamlessly and remain competitive in today's digital era."
            },
            {
                "role": "assistant",
                "content": "Work life shifted fast after automation arrived. Most companies now run machine learning across their daily routines, hoping to save hours and spark fresh ideas. It helps. Still, diving in without an actual plan usually leaves teams untangling messy software instead of getting ahead."
            },
            {
                "role": "user",
                "content": "Tone: Professional\nStrength: Medium\n\nOriginal Text:\nThe quarterly financial report demonstrates significant revenue growth of 18.5% reaching $4.2 million on September 30, 2025. However, leadership must remain vigilant regarding market volatility."
            },
            {
                "role": "assistant",
                "content": "Quarterly revenue climbed 18.5% to reach $4.2 million through September 30, 2025. Strong results. Yet leadership must watch sudden market swings closely as conditions shift."
            },
            {
                "role": "user",
                "content": f"Tone: {req.tone}\n{strength_instruction}\n\nOriginal Text (~{word_count} words - rewrite must match ~{word_count} words without shortening):\n{req.text}"
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
                temperature=gen_temp,
                top_p=gen_top_p,
                top_k=gen_top_k,
                repetition_penalty=gen_rep_pen,
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

class AudienceSplitReq(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    context: str = "Candidate Interview"

class AudienceOut(BaseModel):
    title: str
    audience: str
    tone: str
    text: str
    warnings: list[str] = []

class AudienceSplitResp(BaseModel):
    original_text: str
    candidate: AudienceOut
    hiring_manager: AudienceOut
    compliance: AudienceOut
    verification_status: str = "CONTENT INTEGRITY PASSED"
    timestamp: str = ""

@app.post("/split", response_model=AudienceSplitResp)
def split_endpoint(req: AudienceSplitReq):
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="Please provide non-empty interview notes.")
    try:
        model, tokenizer, device = get_model()
        from datetime import datetime, timezone

        def generate_audience(instruction_prompt: str, user_prompt: str) -> str:
            msgs = [
                {"role": "system", "content": instruction_prompt},
                {"role": "user", "content": user_prompt}
            ]
            p = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inp = tokenizer(p, return_tensors="pt").to(device)
            with torch.no_grad():
                out = model.generate(
                    **inp,
                    max_new_tokens=512,
                    do_sample=True,
                    temperature=0.75,
                    top_p=0.92,
                    repetition_penalty=1.12,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id
                )
            raw = tokenizer.decode(out[0][inp.input_ids.shape[1]:], skip_special_tokens=True).strip()
            return clean_wikipedia_ai_tells(raw)

        # 1. Candidate email
        cand_text = generate_audience(
            "You are an empathetic HR Talent Partner. Transform raw interview notes into an encouraging, professional, and warm follow-up email directly to the candidate. Thank them, highlight strengths, outline next steps without revealing internal evaluation rubrics. Preserve exact dates and facts. Output ONLY the email.",
            f"Raw Notes:\n{req.text}"
        )
        # 2. Hiring manager memo
        mgr_text = generate_audience(
            "You are an Executive Recruiting Lead. Transform raw interview notes into a direct, bulleted decision memo for the Hiring Manager. Sections: Recommendation Status, Key Strengths (pros), Watchouts / Discussion Areas (cons), and Candidate Comp / Experience. Zero fluff. Preserve 100% of numbers, dates, and metrics. Output ONLY the memo.",
            f"Raw Notes:\n{req.text}"
        )
        # 3. Compliance record
        comp_text = generate_audience(
            "You are an HR Compliance and ATS Audit Officer. Transform raw interview notes into a formal, objective audit summary for the ATS record. Record evaluation dates, verified credentials, evaluation scores, and compensation expectation with neutral objectivity. 100% preservation of all numbers and dates. Output ONLY the record.",
            f"Raw Notes:\n{req.text}"
        )

        fg_cand = factguard_check(req.text, cand_text)
        fg_mgr = factguard_check(req.text, mgr_text)
        fg_comp = factguard_check(req.text, comp_text)

        status = "CONTENT INTEGRITY PASSED"
        if any(fg.get("needs_review") for fg in [fg_cand, fg_mgr, fg_comp]):
            status = "REVIEW RECOMMENDED"

        return AudienceSplitResp(
            original_text=req.text,
            candidate=AudienceOut(
                title="Candidate-Facing Follow-Up",
                audience="Candidate",
                tone="Encouraging & Constructive",
                text=cand_text,
                warnings=fg_cand.get("warnings", [])
            ),
            hiring_manager=AudienceOut(
                title="Hiring Manager Decision Memo",
                audience="Hiring Manager",
                tone="Direct & Actionable (Pros/Cons)",
                text=mgr_text,
                warnings=fg_mgr.get("warnings", [])
            ),
            compliance=AudienceOut(
                title="ATS & Compliance Record",
                audience="ATS / Compliance Archive",
                tone="Formal & Objective Audit Log",
                text=comp_text,
                warnings=fg_comp.get("warnings", [])
            ),
            verification_status=status,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        print(f"Error during /split: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
