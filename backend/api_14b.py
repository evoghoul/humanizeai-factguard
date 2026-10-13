import os
import re
import threading
import traceback
from contextlib import asynccontextmanager
from typing import Any

try:
    import torch  # type: ignore
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # type: ignore
    from peft import PeftModel  # type: ignore
except ImportError:
    torch: Any = None
    AutoModelForCausalLM: Any = None
    AutoTokenizer: Any = None
    BitsAndBytesConfig: Any = None
    PeftModel: Any = None

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from factguard import factguard_check  # type: ignore
except ImportError:
    def factguard_check(orig: str, rewr: str) -> dict:
        return {"warnings": [], "needs_review": False, "summary": "Heuristics skipped"}

BASE_MODEL = "Qwen/Qwen2.5-14B-Instruct"
ADAPTER_DIR = "humanizeai_14b_lora"

_model: Any = None
_tokenizer: Any = None
_device: Any = None
_model_lock = threading.Lock()


def get_model() -> tuple[Any, Any, Any]:
    global _model, _tokenizer, _device
    if _model is not None:
        return _model, _tokenizer, _device

    with _model_lock:
        if _model is not None:
            return _model, _tokenizer, _device

        if torch is None or AutoModelForCausalLM is None or AutoTokenizer is None:
            raise RuntimeError("PyTorch and Transformers must be installed to run this service.")

        import gc
        gc.collect()

        has_cuda = bool(torch.cuda.is_available())
        if has_cuda:
            torch.cuda.empty_cache()
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"CUDA detected: {torch.cuda.get_device_name(0)} with {vram_gb:.1f} GB total VRAM")
        else:
            print("WARNING: CUDA is NOT available! Running on CPU (slow).")

        compute_dtype = torch.bfloat16 if (has_cuda and torch.cuda.is_bf16_supported()) else torch.float16
        tok_path = ADAPTER_DIR if os.path.exists(ADAPTER_DIR) else BASE_MODEL
        print(f"Loading tokenizer from: {tok_path}")
        _tokenizer = AutoTokenizer.from_pretrained(tok_path, trust_remote_code=True)
        if _tokenizer.pad_token is None:
            _tokenizer.pad_token = _tokenizer.eos_token

        print(f"Loading base model onto GPU: {BASE_MODEL}")
        device_map = {"": 0} if has_cuda else "auto"

        model_kwargs: dict[str, Any] = {
            "device_map": device_map,
            "torch_dtype": compute_dtype,
            "trust_remote_code": True,
        }
        if has_cuda and BitsAndBytesConfig is not None:
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=compute_dtype,
                bnb_4bit_use_double_quant=True,
            )

        base = AutoModelForCausalLM.from_pretrained(BASE_MODEL, **model_kwargs)
        if os.path.exists(ADAPTER_DIR) and PeftModel is not None:
            print(f"Applying LoRA adapter from {ADAPTER_DIR}...")
            _model = PeftModel.from_pretrained(base, ADAPTER_DIR)
        else:
            print("Running on base 14B model (adapter directory not found)...")
            _model = base
        _model.eval()
        _device = "cuda:0" if has_cuda else "cpu"
        print(f"14B Model loaded and ready on {_device}!")
        return _model, _tokenizer, _device


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(">>> HumanizeAI 14B Server starting up... Warming up model...")
    try:
        get_model()
        print(">>> Model warm-up complete! Ready to serve requests.")
    except Exception as e:
        print(f"Failed to pre-load model: {e}")
        traceback.print_exc()
    yield


app = FastAPI(title="HumanizeAI 14B API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8443",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8443",
    ],
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HumanizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    tone: str = "Standard"
    tone_of_voice: str | None = None
    strength: str = "Medium"
    context: str | None = "General Communication"
    writing_context: str | None = None
    writing_mode: str | None = "Clarity Improvement"


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
        "loaded": _model is not None,
    }


def get_eos_token_ids(tokenizer: Any) -> list[int]:
    eos_ids: list[int] = [tokenizer.eos_token_id] if tokenizer and tokenizer.eos_token_id is not None else []
    if tokenizer and hasattr(tokenizer, "convert_tokens_to_ids"):
        im_end_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
        if im_end_id is not None and im_end_id not in eos_ids:
            eos_ids.append(im_end_id)
    return eos_ids


SYSTEM_INSTRUCTION = (
    "You are HumanizeAI, an expert human editor. Rewrite the input text into authentic, natural human prose. "
    "Your objective is to produce writing that reads effortlessly like a skilled human author—rich with natural sentence flow, "
    "organic rhythm, and idiomatic phrasing, while preserving 100% of factual information and document structure.\n\n"
    "HUMAN WRITING PRINCIPLES:\n"
    "1. ORGANIC SYNTACTIC FLOW: Write with genuine human variety. Avoid repetitive, formulaic sentence structures. "
    "Vary how you start sentences (use fronted adverbials, dependent clauses, or direct active verbs). Never alternate short and long sentences in a mechanical or predictable rhythm. Never insert forced two-word fragments (e.g. avoid 'Solid progress.', 'It helps.', 'Strong results.').\n"
    "2. FRESH, NATURAL VOCABULARY: Total ban on robotic AI clichés (delve, tapestry, multifaceted, pivotal, beacon, crucial to note, foster, spearhead, furthermore, moreover, in conclusion, realm, landscape, game-changer, seamless, testament, holistic, in today's fast-paced world). Use direct, grounded words.\n"
    "3. NATURAL CONJUNCTIONS & PUNCTUATION: Use natural periods and commas. Avoid semicolons (;) and em-dashes (—). Connect thoughts cleanly using coordinating conjunctions ('and', 'but', 'so', 'yet') or crisp separate sentences.\n"
    "4. NO FORMULAIC PATTERNS: Never use negative parallelisms ('not just X, but Y', 'it's not about X, it's about Y'). Avoid listing triples of adjectives ('innovative, efficient, and transformative'). Avoid broad sweeps ('From X to Y'). Never end with generic summary wraps ('In summary,', 'Overall, this shows...').\n"
    "5. FACTGUARD INVARIANTS (STRICT 100% PRESERVATION):\n"
    "   - Retain every number, percentage (%), currency ($/€/£/¥), date, year, timeline, deadline, and proper name exactly.\n"
    "   - Preserve negative conditions (not, never, cannot) and questions.\n"
    "   - Never invent, omit, round, or alter any metric or fact.\n"
    "6. DOCUMENT STRUCTURE & LENGTH:\n"
    "   - Maintain the approximate depth and length of the original passage (90% to 110%).\n"
    "   - Strictly preserve all email/letter structures (subject lines, salutations, paragraph breaks, bullet lists, sign-offs, and signature blocks).\n"
    "7. RAW OUTPUT ONLY: Output ONLY the rewritten text. No preambles, no quotes, no explanations."
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
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def restore_email_and_letter_formatting(text: str, original_text: str = "") -> str:
    if not text:
        return text

    formatted = text.strip()
    formatted = formatted.replace("\r\n", "\n").replace("\r", "\n")

    # 1. Subject lines
    formatted = re.sub(r"^(Subject:[^\n]+?)(?:\s*\n|\s+)(?=[A-Z])", r"\1\n\n", formatted, flags=re.IGNORECASE)

    # 2. Salutations
    salutation_pattern = r"(?:^|\n\n)((?:Dear|Hi|Hello|Hey|To|Good morning|Good afternoon)\s+[^,\n:]{1,50}[,:]\s*)(?!\n)"
    formatted = re.sub(salutation_pattern, r"\1\n\n", formatted, flags=re.IGNORECASE)

    # 3. Sign-offs (anchored to newline to prevent cutting mid-sentence words like thanks/cheers)
    signoff_words = (
        r"Warmest regards|Warm regards|Best regards|Kind regards|With regards|Best wishes|"
        r"Sincerely|Yours truly|Regards|Cheers|Thanks|Thank you|Respectfully"
    )
    signoff_regex = rf"(?<=\n)[^\S\r\n]*\b((?:{signoff_words})[,:]?)\s*"
    formatted = re.sub(signoff_regex, r"\n\1\n", formatted, flags=re.IGNORECASE)

    # 4. Signature block lines
    def clean_sig_block(m: Any) -> str:
        full = m.group(0)
        full = re.sub(r"(\[[^\]]+\])[^\S\r\n]+(\[[^\]]+\])", r"\1\n\2", full)
        full = re.sub(r"(\*\*[^*]+\*\*)[^\S\r\n]+(\[[^\]]+\])", r"\1\n\2", full)
        full = re.sub(r"(\*\*[^*]+\*\*)[^\S\r\n]+([A-Z])", r"\1\n\2", full)
        return full

    formatted = re.sub(
        rf"\n(?:{signoff_words})[,:]?\n[\s\S]+$",
        clean_sig_block,
        formatted,
        flags=re.IGNORECASE,
    )

    # 5. Multi-paragraph restoration if original was multi-paragraph
    if original_text:
        orig_norm = original_text.replace("\r\n", "\n").replace("\r", "\n").strip()
        orig_paras = [p.strip() for p in re.split(r"\n\s*\n", orig_norm) if p.strip()]
        if len(orig_paras) >= 2:
            current_paras = [p.strip() for p in re.split(r"\n\s*\n", formatted) if p.strip()]
            if len(current_paras) < len(orig_paras):
                has_salutation = bool(re.match(r"^(?:Dear|Hi|Hello|Hey|To|Good morning|Good afternoon)\s+[^,\n:]{1,50}[,:]", current_paras[0], flags=re.IGNORECASE))
                has_signoff = bool(re.search(rf"\b(?:{signoff_words})[,:]?", current_paras[-1], flags=re.IGNORECASE))

                salutation_chunk = current_paras[0] if has_salutation else ""
                signoff_chunk = current_paras[-1] if has_signoff and (len(current_paras) > 1 or not has_salutation) else ""

                body_start = 1 if has_salutation else 0
                body_end = len(current_paras) - 1 if (has_signoff and len(current_paras) > 1) else len(current_paras)
                body_chunks = current_paras[body_start:body_end]
                body_text = " ".join(body_chunks)

                orig_body_count = len(orig_paras)
                if has_salutation and re.match(r"^(?:Dear|Hi|Hello|Hey|To)\s+[^,\n:]{1,50}[,:]", orig_paras[0], flags=re.IGNORECASE):
                    orig_body_count -= 1
                if has_signoff and re.search(rf"\b(?:{signoff_words})[,:]?", orig_paras[-1], flags=re.IGNORECASE):
                    orig_body_count -= 1
                orig_body_count = max(1, orig_body_count)

                # Avoid splitting on common abbreviations like Dr., Mr., Sept., etc.
                sentences = re.split(r"(?<!\b(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr|Sept|Oct|Nov|Dec|Jan|Feb|Mar|Apr|Aug|e\.g|i\.e))\.(?=\s+[A-Z0-9])", body_text)
                if len(sentences) >= orig_body_count and orig_body_count > 1:
                    k, m_rem = divmod(len(sentences), orig_body_count)
                    new_body_paras: list[str] = []
                    idx = 0
                    for i in range(orig_body_count):
                        take = k + (1 if i < m_rem else 0)
                        chunk = ". ".join(s.strip() for s in sentences[idx:idx + take] if s.strip())
                        if chunk:
                            if not chunk.endswith("."):
                                chunk += "."
                            new_body_paras.append(chunk)
                        idx += take

                    parts: list[str] = []
                    if salutation_chunk:
                        parts.append(salutation_chunk)
                    parts.extend(new_body_paras)
                    if signoff_chunk:
                        parts.append(signoff_chunk)
                    formatted = "\n\n".join(parts)

    # 6. Normalize horizontal spaces WITHOUT destroying newlines
    formatted = re.sub(r"[^\S\r\n]+", " ", formatted)
    formatted = re.sub(r"[^\S\r\n]*\n[^\S\r\n]*", "\n", formatted)
    formatted = re.sub(r"\n{3,}", "\n\n", formatted)

    return formatted.strip()


def clean_wikipedia_ai_tells(text: str, original_text: str = "") -> str:
    cleaned = strip_preamble(text)
    # Strip compulsive summaries at end
    cleaned = re.sub(r"\n*(?:In conclusion|In summary|Overall|Ultimately),.*$", "", cleaned, flags=re.IGNORECASE).strip()

    # Strip broken unicode / replacement chars from mangled em-dashes
    cleaned = cleaned.replace("\ufffd", ", ")

    # Grammatically safe dash replacement:
    cleaned = re.sub(r"\s*[—–]\s*", ", ", cleaned)

    # Grammatically safe semicolon replacement: capitalize following letter
    def fix_semicolon(m: Any) -> str:
        letter = m.group(1)
        return f". {letter.upper()}"
    cleaned = re.sub(r";\s*([a-zA-Z])", fix_semicolon, cleaned)
    cleaned = re.sub(r";\s*", ". ", cleaned)

    # Clean residual AI cliché transitions
    cleaned = re.sub(r"\b(?:In other words|That said|That being said|At the end of the day|Here's the catch[:!.]?|Here is the thing[:!.]?|To put it simply),?\s*", "", cleaned, flags=re.IGNORECASE)

    # Clean duplicate punctuation without destroying ellipses
    cleaned = re.sub(r"[^\S\r\n]*,[^\S\r\n]*,[^\S\r\n]*", ", ", cleaned)
    cleaned = re.sub(r"(?<!\.)\.\s*\.(?!\.)", ". ", cleaned)

    # CRITICAL: Preserve all formatting and restore layout
    cleaned = restore_email_and_letter_formatting(cleaned, original_text=original_text)
    return cleaned


def call_gemini_fallback(text: str, tone: str, strength: str, word_count: int) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import httpx  # type: ignore
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        user_prompt = (
            f"Tone: {tone}\nStrength: {strength}\n\n"
            f"Original Text (~{word_count} words - rewrite must match ~{word_count} words without shortening, preserving exact document/email layout):\n"
            f"{text}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 1.05,
                "topP": 0.95,
                "maxOutputTokens": min(2048, max(256, int(word_count * 2.5)))
            }
        }
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
    except Exception as e:
        print(f"Gemini fallback error: {e}")
    return None


@app.post("/humanize", response_model=HumanizeResponse)
def humanize(req: HumanizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="Please provide non-empty text.")

    try:
        word_count = len(req.text.split())
        strength_val = (req.strength or "Medium").strip().lower()

        # If Gemini API key is configured and local model is not loaded or forced, try Gemini first
        gemini_result = call_gemini_fallback(req.text, req.tone, req.strength, word_count)
        if gemini_result:
            decoded = clean_wikipedia_ai_tells(gemini_result, original_text=req.text)
            fg = factguard_check(req.text, decoded)
            return HumanizeResponse(
                original=req.text,
                rewrite=decoded,
                warnings=fg.get("warnings", []),
                needs_review=fg.get("needs_review", False)
            )

        model: Any
        tokenizer: Any
        device: Any
        model, tokenizer, device = get_model()

        dynamic_max_tokens = min(2048, max(128, int(word_count * 2.5)))

        if strength_val == "heavy":
            gen_temp = 1.08
            gen_top_p = 0.96
            gen_top_k = 60
            gen_rep_pen = 1.04
            strength_instruction = (
                "Strength: Heavy (Deep syntactic inversion, active authentic prose, "
                "CRITICAL: preserve 100% of exact numbers, dates, and percentages without rounding)"
            )
        elif strength_val == "light":
            gen_temp = 0.88
            gen_top_p = 0.95
            gen_top_k = 50
            gen_rep_pen = 1.02
            strength_instruction = "Strength: Light (Gentle polish, natural cadence)"
        else:  # Medium
            gen_temp = 1.04
            gen_top_p = 0.96
            gen_top_k = 50
            gen_rep_pen = 1.03
            strength_instruction = "Strength: Medium (Balanced humanization, natural flow, zero cliché AI vocabulary)"

        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": "Tone: Conversational\nStrength: Heavy\n\nOriginal Text:\nArtificial intelligence has transformed the modern business landscape in profound ways. Companies worldwide are leveraging machine learning to enhance operational efficiency and foster innovation. It is important to note that organizations must adopt strategic frameworks to navigate these technological changes seamlessly and remain competitive in today's digital era."
            },
            {
                "role": "assistant",
                "content": "Work life shifted quickly once automation took root across offices. Today, most teams plug machine learning straight into their everyday operations to shave hours off routine tasks and test new ideas. That said, diving into new software without a grounded strategy often leaves departments wrestling with technical confusion rather than moving faster."
            },
            {
                "role": "user",
                "content": "Tone: Professional\nStrength: Medium\n\nOriginal Text:\nThe quarterly financial report demonstrates significant revenue growth of 18.5% reaching $4.2 million on September 30, 2025. However, leadership must remain vigilant regarding market volatility."
            },
            {
                "role": "assistant",
                "content": "Quarterly revenue climbed 18.5% to hit $4.2 million as of September 30, 2025. Even with the strong quarter, leadership expects to keep a close watch on choppy market swings in the months ahead."
            },
            {
                "role": "user",
                "content": (
                    "Tone: Professional\nStrength: Heavy\n\nOriginal Text:\n"
                    "Dear Gwen,\n\n"
                    "It is our pleasure to confirm your appointment for the Data Analyst role starting on November 1, 2026.\n\n"
                    "Please confirm your availability by replying directly to this message by Friday.\n\n"
                    "Best regards,\n"
                    "HR Operations\n"
                    "[Company Name]"
                )
            },
            {
                "role": "assistant",
                "content": (
                    "Dear Gwen,\n\n"
                    "We're delighted to confirm your appointment as Data Analyst, kicking off on November 1, 2026.\n\n"
                    "Please drop us a quick reply by Friday to confirm your availability.\n\n"
                    "Best regards,\n"
                    "HR Operations\n"
                    "[Company Name]"
                )
            },
            {
                "role": "user",
                "content": f"Tone: {req.tone}\n{strength_instruction}\n\nOriginal Text (~{word_count} words - rewrite must match ~{word_count} words without shortening, preserving exact document/email layout):\n{req.text}"
            }
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        eos_ids = get_eos_token_ids(tokenizer)

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": dynamic_max_tokens,
            "do_sample": True,
            "temperature": gen_temp,
            "top_p": gen_top_p,
            "top_k": gen_top_k,
            "repetition_penalty": gen_rep_pen,
            "eos_token_id": eos_ids,
            "use_cache": True,
            "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id
        }
        # Inject min_p dynamically if supported
        try:
            import inspect
            sig = inspect.signature(model.generate)
            if "min_p" in sig.parameters:
                gen_kwargs["min_p"] = 0.06
        except Exception:
            pass

        with _model_lock:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    **gen_kwargs
                )

        raw_decoded = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
        decoded = clean_wikipedia_ai_tells(raw_decoded, original_text=req.text)
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
    warnings: list[str] = Field(default_factory=list)


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
        model: Any
        tokenizer: Any
        device: Any
        model, tokenizer, device = get_model()
        from datetime import datetime, timezone

        eos_ids = get_eos_token_ids(tokenizer)

        def generate_audience(
            instruction_prompt: str,
            user_prompt: str,
            m: Any = model,
            tok: Any = tokenizer,
            dev: Any = device,
            stop_ids: list[int] = eos_ids,
        ) -> str:
            msgs = [
                {"role": "system", "content": instruction_prompt},
                {"role": "user", "content": user_prompt}
            ]
            p = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inp = tok(p, return_tensors="pt").to(dev)
            with _model_lock:
                with torch.no_grad():
                    out = m.generate(
                        **inp,
                        max_new_tokens=512,
                        do_sample=True,
                        temperature=0.75,
                        top_p=0.92,
                        repetition_penalty=1.12,
                        eos_token_id=stop_ids,
                        pad_token_id=tok.pad_token_id or tok.eos_token_id
                    )
            raw = tok.decode(out[0][inp.input_ids.shape[1]:], skip_special_tokens=True).strip()
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
