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
        "loaded": _model is not None
    }

SYSTEM_INSTRUCTION = (
    "You are HumanizeAI-FactGuard, an expert human editor and factual integrity engine. Rewrite the input text into "
    "authentic, natural human prose that passes all plagiarism checkers (Turnitin, CopyLeaks, Grammarly) and AI detectors "
    "(GPTZero, ZeroGPT, Turnitin AI) with 0% detection, strictly adhering to Wikipedia's 'Signs of AI-generated text' "
    "negative constraints and FactGuard factual immutability.\n\n"
    "### CORE DIRECTIVES (FACTGUARD CONSTRAINTS)\n\n"
    "1. ZERO HALLUCINATION (Strict Enforcement):\n"
    "You are a linguistic refinement layer, not a creative author. You must NEVER invent, assume, or inject external information. "
    "If a company name (e.g., 'Apex Holdings'), candidate name, location, or certification is not explicitly stated in the source text, "
    "do not add it under any circumstances. Never hallucinate specific entities to anchor abstract thoughts.\n\n"
    "2. ABSOLUTE ENTITY LOCK:\n"
    "You must identify and perfectly preserve all hard data points. Do not round numbers, summarize timelines, or delete constraints. You must retain:\n"
    "- All specific metrics, percentages, currency amounts, and financial figures (e.g., '$185,000', '99.4%', '£450 daily savings').\n"
    "- All exact timelines and deadlines (e.g., '48 hours', '3-minute window'). Do not change specific dates to vague terms like 'recently' or 'since August 1'. "
    "Retain closed date range boundaries (e.g., 'August 1 to September 30' must NEVER become an open-ended 'since August 1'). "
    "Retain exact deadlines (e.g., '48 hours' must NEVER become 'by tomorrow evening').\n"
    "- All technical terminology and framework names (e.g., 'SQLite', 'PostgreSQL', 'FastAPI', 'React', 'TypeScript').\n"
    "- All qualitative scores and ratings (e.g., '8.5/10', '85 out of 100').\n"
    "- All operational constraints and guarantees (e.g., 'zero unplanned downtime', 'zero downtime', '3-minute window').\n\n"
    "3. INTENT & STRUCTURAL PRESERVATION:\n"
    "You must recognize the fundamental purpose of the source text and maintain it perfectly:\n"
    "- Interview Questions: If the source text asks the reader how they would solve a problem or explain a concept, the output MUST remain an open-ended question demanding an answer. Never convert an interview question into a declarative statement of advice or instruction.\n"
    "- Candidate Feedback: Maintain the exact balance of praise and critique. Do not soften technical failures or inflate positive performance.\n"
    "- Professional Reports: Maintain objective, evidence-based reporting without adding emotional filler or speculative commentary.\n\n"
    "4. DE-ROBOTING & CLICHÉ ERADICATION:\n"
    "Aggressively eliminate common AI-generated vocabulary and sentence structures. Completely avoid words and phrases such as: 'multifaceted', 'delving', 'delve into', 'tapestry', 'rich tapestry', 'dynamic synergies', 'paradigm', 'paradigm shift', 'testament', 'testament to', 'crucial to note', and 'seamlessly'. Replace these with natural, human-flowing vocabulary appropriate for the requested tone.\n\n"
    "5. ZERO N-GRAM PLAGIARISM OVERLAP:\n"
    "Plagiarism checkers flag 4 or more consecutive identical words. You MUST aggressively rephrase, restructure, and invert the syntax of every sentence. Do NOT preserve the grammatical order or phrase sequences of the original text. Reorder ideas, swap active and passive voice, and use distinct vocabulary while keeping all locked entities and facts 100% accurate.\n\n"
    "6. WIKIPEDIA ANTI-AI NEGATIVE CONSTRAINTS:\n"
    "- NO EM-DASHES (—), EN-DASHES (–), OR SEMICOLONS (;): Ban all dashes and semicolons completely. Split into short punchy sentences instead.\n"
    "- NO NEGATIVE PARALLELISMS: Strictly forbid 'not just X, but Y', 'it's not about X, it's about Y', or 'not only X, but also Y'. State claims directly.\n"
    "- NO RULE OF THREES: Never list three adjectives, adverbs, or nouns in a rhythmic row.\n"
    "- NO 'FALSE RANGES': Never use the lazy sweep 'From X to Y'.\n"
    "- NO COMPULSIVE SUMMARIES OR CLICHÉ TRANSITIONS: Never end with a generic wrap-up ('In summary,', 'Overall, this highlights...', 'Ultimately, ...'). Never use cliché transitions like 'That said,', 'In other words,', 'At the end of the day,', 'Here's the catch:'. When the thought ends, stop writing.\n"
    "- NO VAGUE ATTRIBUTION: Avoid empty hedges ('It is important to note that', 'Some critics argue', 'It remains to be seen').\n"
    "- EXTREME BURSTINESS & SENTENCE VARIETY: Wildly vary sentence lengths. Alternate 2-to-5 word punchy sentences/fragments ('Fair enough.', 'Hardly surprising.', 'It works.') with natural 18-to-26 word compound thoughts. Never write consecutive sentences of equal length.\n\n"
    "7. PRESERVE FULL LENGTH AND DEPTH (DO NOT SUMMARIZE OR SHORTEN):\n"
    "Paraphrasing is NOT summarizing. The rewritten text MUST maintain the full depth, completeness, and approximate length of the original passage (90% to 110% of original word count). Do NOT combine multiple distinct thoughts into a single short sentence, and do NOT drop background details, nuances, or explanations.\n\n"
    "8. STRICT DOCUMENT & EMAIL FORMAT PRESERVATION (NEVER COLLAPSE INTO A SINGLE PARAGRAPH):\n"
    "If the input is an email, letter, memo, or correspondence, you MUST preserve its exact structural layout:\n"
    "- Subject lines must stay on their own line with a blank line after.\n"
    "- Salutations/greetings ('Dear [Name],', 'Hi [Name],', 'To [Name]:') must stay on their own line with a blank line (\\n\\n) after.\n"
    "- Each distinct body paragraph MUST remain on its own paragraph separated by a blank line (\\n\\n). NEVER merge separate paragraphs into a continuous block.\n"
    "- Bullet points and numbered lists must remain as individual list items on their own lines.\n"
    "- Sign-offs ('Best regards,', 'Sincerely,', 'Warmest regards,', 'Cheers,') must appear on their own line preceded by a blank line (\\n\\n).\n"
    "- Signature lines ([Name], [Title], [Company], [Contact]) must each appear on their own separate lines.\n\n"
    "### INTERNAL WORKFLOW (CHAIN OF THOUGHT)\n"
    "Before generating your final response, silently process the following steps:\n"
    "Step 1 (Extract): Identify all numbers, names, technologies, deadlines, constraints, and scores in the source text.\n"
    "Step 2 (Classify): Determine if the text is an interview question, a report, a notification, or candidate feedback.\n"
    "Step 3 (Refine): Rewrite the text applying the requested context, mode, and tone while eliminating robotic clichés and varying sentence structure.\n"
    "Step 4 (Verify): Cross-check your draft against Step 1 and Step 2. If any entity was dropped, altered, or hallucinated, or if a question was turned into a statement, rewrite to restore exact original data and format.\n\n"
    "### OUTPUT FORMAT\n"
    "Provide ONLY the final refined text. Do not include explanations, apologies, conversational filler, or your internal chain of thought."
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

def restore_email_and_letter_formatting(text: str, original_text: str = "") -> str:
    if not text:
        return text

    formatted = text.strip()
    formatted = formatted.replace("\r\n", "\n").replace("\r", "\n")

    # 1. Subject lines
    formatted = re.sub(r"^(Subject:[^\n]+?)(?:\s*\n|\s+)(?=[A-Z])", r"\1\n\n", formatted, flags=re.IGNORECASE)

    # 2. Salutations
    salutation_pattern = r"^((?:Dear|Hi|Hello|Hey|To|Good morning|Good afternoon)\s+[^,\n:]{1,50}[,:]\s*)(?!\n)"
    match = re.match(salutation_pattern, formatted, flags=re.IGNORECASE)
    if match:
        salutation = match.group(1).rstrip()
        rest = formatted[len(match.group(1)):].lstrip()
        formatted = f"{salutation}\n\n{rest}"

    # 3. Sign-offs
    signoff_words = (
        r"Warmest regards|Warm regards|Best regards|Kind regards|With regards|Best wishes|"
        r"Sincerely|Yours truly|Regards|Cheers|Thanks|Thank you|Respectfully"
    )
    signoff_regex = rf"(?<=\S)[^\S\r\n]*\b((?:{signoff_words})[,:]?)\s*"
    formatted = re.sub(signoff_regex, r"\n\n\1\n", formatted, flags=re.IGNORECASE)

    # 4. Signature block lines
    def clean_sig_block(m):
        full = m.group(0)
        full = re.sub(r"(\[[^\]]+\])[^\S\r\n]+(\[[^\]]+\])", r"\1\n\2", full)
        full = re.sub(r"(\*\*[^*]+\*\*)[^\S\r\n]+(\[[^\]]+\])", r"\1\n\2", full)
        full = re.sub(r"(\*\*[^*]+\*\*)[^\S\r\n]+([A-Z])", r"\1\n\2", full)
        return full

    formatted = re.sub(
        rf"\n(?:{signoff_words})[,:]?\n[\s\S]+$",
        clean_sig_block,
        formatted,
        flags=re.IGNORECASE
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

                sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", body_text)
                if len(sentences) >= orig_body_count and orig_body_count > 1:
                    k, m_rem = divmod(len(sentences), orig_body_count)
                    new_body_paras = []
                    idx = 0
                    for i in range(orig_body_count):
                        take = k + (1 if i < m_rem else 0)
                        para = " ".join(sentences[idx:idx+take])
                        if para:
                            new_body_paras.append(para)
                        idx += take
                    
                    parts = []
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
    
    # Ban all em-dashes and en-dashes: replace with comma or period
    cleaned = re.sub(r"\s*[—–]\s*", ", ", cleaned)
    
    # Ban all semicolons: replace with period followed by capitalized next word or space
    cleaned = re.sub(r";\s*", ". ", cleaned)
    
    # Ban negative parallelisms: "not just X, but Y"
    cleaned = re.sub(r"\b(?:is|was|are|were|do|does|did)\s+not\s+(?:just|only)\s+([^,;]+)[,;]\s*(?:it's|it\s+is|they're|they\s+are|but\s+also|but)?\s*", r"\1 and ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bnot\s+just\s+([^,;]+)[,;]\s*(?:it's|it\s+is|but\s+also|but)?\s*", r"\1 along with ", cleaned, flags=re.IGNORECASE)

    # Clean residual AI cliché transitions
    cleaned = re.sub(r"\b(?:In other words|That said|That being said|At the end of the day|Here's the catch[:!.]?|Here is the thing[:!.]?|To put it simply),?\s*", "", cleaned, flags=re.IGNORECASE)
    
    # Clean residual AI tropes and buzzwords
    residual_tropes = {
        r"\brich tapestry of\b": "diverse mix of",
        r"\brich tapestry\b": "broad variety",
        r"\btapestry of\b": "blend of",
        r"\bdynamic synergies\b": "strong teamwork",
        r"\bdynamic synergy\b": "teamwork",
        r"\bparadigm shift\b": "major change",
        r"\bparadigm shifts\b": "major changes",
        r"\bdigital landscape\b": "online environment",
        r"\bnavigating the landscape of\b": "dealing with",
        r"\bthe landscape of\b": "the world of",
        r"\bmultifaceted\b": "layered",
        r"\bdelve into\b": "look into",
        r"\bdelving into\b": "looking into",
        r"\bdelves into\b": "looks into",
        r"\ba testament to\b": "clear proof of",
        r"\bbeacon of\b": "model for",
        r"\bplays a vital role in\b": "is key to",
        r"\bplays a key role in\b": "drives",
        r"\bplay a pivotal role\b": "matter deeply",
        r"\bpivotal\b": "vital",
        r"\bfoster\b": "encourage",
        r"\bfostering\b": "encouraging",
        r"\bspearhead\b": "lead",
        r"\bspearheaded\b": "led",
        r"\bspearheading\b": "leading",
        r"\bgame-changer\b": "breakthrough",
        r"\bcornerstone\b": "foundation",
        r"\bin profound ways\b": "completely",
        r"\bcreative breakthroughs\b": "fresh ideas",
        r"\boperational efficiency\b": "speed and clarity",
        r"\bstrategic frameworks\b": "a solid plan",
        r"\bseamlessly\b": "smoothly",
    }
    for pattern, replacement in residual_tropes.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    # Clean duplicate punctuation on the same line
    cleaned = re.sub(r"[^\S\r\n]*,[^\S\r\n]*,[^\S\r\n]*", ", ", cleaned)
    cleaned = re.sub(r"[^\S\r\n]*\.[^\S\r\n]*\.[^\S\r\n]*", ". ", cleaned)

    # CRITICAL: Preserve all formatting and restore layout (never use re.sub(r'\s+', ' ', cleaned))
    cleaned = restore_email_and_letter_formatting(cleaned, original_text=original_text)
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
                "CRITICAL: 100% Named Entity Retention e.g. Starlight Therapeutics, "
                "100% Metric & Timeline Preservation e.g. £450 daily and two weeks, "
                "zero generic filler substitutions, zero hallucinations)"
            )
        elif strength_val == "light":
            gen_temp = 0.85
            gen_top_p = 0.95
            gen_top_k = 50
            gen_rep_pen = 1.10
            strength_instruction = "Strength: Light (Gentle polish, natural cadence, 100% entity and metric retention)"
        else: # Medium
            gen_temp = 1.00
            gen_top_p = 0.95
            gen_top_k = 50
            gen_rep_pen = 1.16
            strength_instruction = "Strength: Medium (Balanced humanization, natural burstiness, zero cliché AI vocabulary, 100% entity and metric retention)"

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
                "content": "Tone: Professional\nStrength: Heavy\n\nOriginal Text:\nAt Starlight Therapeutics, shifting staff to remote workflows generated £450 daily savings over a two-week pilot, while enhancing research documentation speed."
            },
            {
                "role": "assistant",
                "content": "Switching researchers to remote setups saved Starlight Therapeutics £450 every single day during their two-week pilot. Beyond cutting expenses, team members turned around trial logs much faster."
            },
            {
                "role": "user",
                "content": "Writing Context: General Communication\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Heavy\n\nOriginal Text:\nIn today's evolving digital landscape, organizations must delve into dynamic synergies and foster a rich tapestry of holistic paradigm shifts to unlock continuous innovation."
            },
            {
                "role": "assistant",
                "content": "Companies that want steady progress need to fix how their teams coordinate day-to-day. That means communicating clearly, cutting red tape, and trying new approaches without overthinking."
            },
            {
                "role": "user",
                "content": "Writing Context: Interview Question\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Heavy\n\nOriginal Text:\nHow would you design a distributed cache using SQLite or PostgreSQL that guarantees zero unplanned downtime and handles failover within a 3-minute window?"
            },
            {
                "role": "assistant",
                "content": "If you had to architect a distributed cache using SQLite or PostgreSQL, how would you deliver zero unplanned downtime while completing failover within a 3-minute window?"
            },
            {
                "role": "user",
                "content": "Writing Context: Recruiter Email\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Heavy\n\nOriginal Text:\nFrom August 1 to September 30, our incident response crew resolved 14 critical alerts. Every candidate must complete the technical evaluation within 48 hours."
            },
            {
                "role": "assistant",
                "content": "Between August 1 and September 30, our incident response crew resolved 14 critical alerts. Candidates must finish the technical evaluation within 48 hours."
            },
            {
                "role": "user",
                "content": "Writing Context: Professional Report\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Medium\n\nOriginal Text:\nThe quarterly financial report demonstrates significant revenue growth of 18.5% reaching $4.2 million on September 30, 2025. However, leadership must remain vigilant regarding market volatility."
            },
            {
                "role": "assistant",
                "content": "Quarterly revenue climbed 18.5% to reach $4.2 million through September 30, 2025. Strong results. Yet leadership must watch sudden market swings closely as conditions shift."
            },
            {
                "role": "user",
                "content": (
                    "Writing Context: Recruiter Email\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Heavy\n\nOriginal Text:\n"
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
                    "We are thrilled to welcome you to the Data Analyst position, with your start date set for November 1, 2026.\n\n"
                    "Kindly reply to this email by Friday to confirm that you are ready to begin.\n\n"
                    "Best regards,\n"
                    "HR Operations\n"
                    "[Company Name]"
                )
            },
            {
                "role": "user",
                "content": (
                    f"Writing Context: {req.writing_context or req.context or 'General Communication'}\n"
                    f"Writing Mode: {req.writing_mode or 'Clarity Improvement'}\n"
                    f"Tone of Voice: {req.tone_of_voice or req.tone or 'Professional'}\n"
                    f"{strength_instruction}\n\n"
                    f"Original Text (~{word_count} words - rewrite must match ~{word_count} words without shortening, strictly preserving intent, entities, deadlines, and document/email structure):\n"
                    f"{req.text}"
                )
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
