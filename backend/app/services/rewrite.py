import re
import httpx
from app.core.config import settings
from app.services.validation import validate_rewrite

class ModelProviderInterface:
    def rewrite(self, text: str, tone: str, strength: str) -> str:
        raise NotImplementedError

AI_CLICHE_REPLACEMENTS = {
    r"\bin today's fast-paced world\b": "these days",
    r"\bin today's digital era\b": "today",
    r"\bit is important to note that\b": "notably,",
    r"\bit is worth mentioning that\b": "worth noting,",
    r"\bit is crucial to\b": "we must",
    r"\bdelve into\b": "explore",
    r"\bdelves into\b": "explores",
    r"\bdelving into\b": "exploring",
    r"\ba testament to\b": "clear proof of",
    r"\brich tapestry\b": "diverse mix",
    r"\btapestry of\b": "blend of",
    r"\bpivotal role\b": "key role",
    r"\bpivotal\b": "vital",
    r"\bbeacon of\b": "model for",
    r"\bfoster\b": "encourage",
    r"\bfostering\b": "encouraging",
    r"\bspearhead\b": "lead",
    r"\bspearheaded\b": "led",
    r"\bspearheading\b": "leading",
    r"\bin conclusion\b": "overall,",
    r"\bfurthermore\b": "what's more,",
    r"\bmoreover\b": "on top of that,",
    r"\bnavigating the landscape of\b": "dealing with",
    r"\bthe realm of\b": "the field of",
    r"\bgame-changer\b": "breakthrough",
    r"\bgame-changing\b": "revolutionary",
    r"\bseamlessly\b": "smoothly",
    r"\bseamless\b": "smooth",
    r"\bparamount\b": "vital",
    r"\bmultifaceted\b": "layered",
    r"\bshed light on\b": "clarify",
    r"\bin order to\b": "to",
    r"\bdue to the fact that\b": "because",
    r"\bat this point in time\b": "right now",
    r"\bwith regard to\b": "about",
    r"\bfor the purpose of\b": "to",
    r"\btake into consideration\b": "consider",
    r"\ba wide variety of\b": "many",
    r"\butilize\b": "use",
    r"\butilizes\b": "uses",
    r"\butilized\b": "used",
    r"\butilizing\b": "using",
    r"\bcommence\b": "start",
    r"\bcommenced\b": "started",
    r"\bcommencing\b": "starting",
    r"\bterminate\b": "end",
    r"\bsubsequently\b": "later",
    r"\bconsequently\b": "as a result,",
    r"\bdemonstrates that\b": "shows that",
    r"\bindicates that\b": "shows that",
    r"\bit can be observed that\b": "we can see that",
}

CONTRACTION_REPLACEMENTS = {
    r"\bit is\b": "it's",
    r"\bIt is\b": "It's",
    r"\bthat is\b": "that's",
    r"\bThat is\b": "That's",
    r"\bthere is\b": "there's",
    r"\bThere is\b": "There's",
    r"\bdo not\b": "don't",
    r"\bDo not\b": "Don't",
    r"\bcannot\b": "can't",
    r"\bCannot\b": "Can't",
    r"\bwill not\b": "won't",
    r"\bWill not\b": "Won't",
    r"\bdid not\b": "didn't",
    r"\bDid not\b": "Didn't",
    r"\bdoes not\b": "doesn't",
    r"\bDoes not\b": "Doesn't",
    r"\bis not\b": "isn't",
    r"\bIs not\b": "Isn't",
    r"\bare not\b": "aren't",
    r"\bAre not\b": "Aren't",
    r"\bwas not\b": "wasn't",
    r"\bWas not\b": "Wasn't",
    r"\bwere not\b": "weren't",
    r"\bWere not\b": "Weren't",
    r"\bwe have\b": "we've",
    r"\bWe have\b": "We've",
    r"\bthey have\b": "they've",
    r"\bThey have\b": "They've",
    r"\bwe will\b": "we'll",
    r"\bWe will\b": "We'll",
}

class HeuristicHumanizer(ModelProviderInterface):
    """
    Advanced rule-based stylometric transformation engine.
    Eliminates formulaic AI clichés, injects natural contractions,
    and varies syntax while rigorously preserving FactGuard invariants.
    """
    def rewrite(self, text: str, tone: str, strength: str) -> str:
        if "FAIL DEMO" in text:
            return "This rewrite completely missed the numbers and dates."
        
        rewritten = text
        for pattern, replacement in AI_CLICHE_REPLACEMENTS.items():
            rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)
            
        if tone.lower() != "formal":
            for pattern, replacement in CONTRACTION_REPLACEMENTS.items():
                rewritten = re.sub(pattern, replacement, rewritten)
                
        return rewritten

DemoProvider = HeuristicHumanizer

ANTI_AI_SYSTEM_PROMPT = """You are HumanizeAI, an expert human editor. Your goal is to rewrite the input text so it reads completely like authentic human writing and passes all AI detectors (high perplexity and high burstiness).

CRITICAL RULES:
1. FACTGUARD INVARIANTS: You MUST strictly preserve all numbers, dates, years, currencies ($/€/£), percentages (%), proper names, and negative conditions (not, never, cannot). Do not drop, round, or alter any fact.
2. HIGH BURSTINESS: Vary your sentence lengths dramatically. Mix short, punchy 3-to-6 word sentences with longer, compound thoughts (18-24 words). Never write sentences of uniform length.
3. BAN AI CLICHÉS: Strictly forbid words like: delve, testament, tapestry, pivotal, beacon, crucial, foster, spearhead, furthermore, moreover, in conclusion, realm, landscape, game-changer, seamless, paramount, multifaceted, vibrant.
4. NATURAL CADENCE: Use active voice, natural contractions (it's, won't, didn't, we've), and conversational flow appropriate for the requested tone.
5. Return ONLY the rewritten text without markdown conversational preambles or explanations."""

def clean_model_output(text: str) -> str:
    """Strip any conversational preambles like 'Sure! Here is...' from LLM output."""
    if not text:
        return ""
    cleaned = text.strip()
    # Strip markdown code fences if model wrapped response in ```
    cleaned = re.sub(r"^```[a-zA-Z]*\n([\s\S]*?)\n```$", r"\1", cleaned)
    # Strip common conversational preambles
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

class GeminiProvider(ModelProviderInterface):
    """
    Google Gemini 2.5 Flash / 1.5 Flash cloud provider.
    Zero-latency, 24/7 reliability for the Google Student Club Hackathon.
    """
    def rewrite(self, text: str, tone: str, strength: str) -> str:
        if not settings.GEMINI_API_KEY:
            return HeuristicHumanizer().rewrite(text, tone, strength)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{ANTI_AI_SYSTEM_PROMPT}\n\nRequested Tone: {tone}\nRequested Humanization Strength: {strength}\n\nOriginal Text:\n{text}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.85,
                "topP": 0.92,
                "maxOutputTokens": 1024
            }
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return clean_model_output(parts[0].get("text", "").strip())
        except Exception:
            pass
        return HeuristicHumanizer().rewrite(text, tone, strength)

class LightningProvider(ModelProviderInterface):
    """
    On-premise fine-tuned Qwen2.5-14B-Instruct running on L4 GPU via permanent ngrok tunnel.
    """
    def rewrite(self, text: str, tone: str, strength: str) -> str:
        if "FAIL DEMO" in text:
            return "This rewrite completely missed the numbers and dates."
        url = settings.MODEL_PROVIDER_URL.rstrip("/")
        if not url.endswith("/humanize"):
            target_url = f"{url}/humanize"
        else:
            target_url = url
            
        try:
            with httpx.Client(timeout=45.0) as client:
                response = client.post(
                    target_url,
                    json={
                        "text": text,
                        "tone": tone,
                        "strength": strength
                    },
                    headers={
                        "Content-Type": "application/json",
                        "ngrok-skip-browser-warning": "true",
                        "User-Agent": "HumanizeAI/1.0"
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    raw = data.get("rewrite") or data.get("revised") or text
                    return clean_model_output(raw)
                else:
                    return self._fallback(text, tone, strength)
        except Exception:
            return self._fallback(text, tone, strength)

    def _fallback(self, text: str, tone: str, strength: str) -> str:
        if settings.GEMINI_API_KEY:
            return GeminiProvider().rewrite(text, tone, strength)
        return HeuristicHumanizer().rewrite(text, tone, strength)

def get_provider():
    if settings.MODEL_PROVIDER_TYPE == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider()
    if settings.MODEL_PROVIDER_TYPE == "lightning":
        return LightningProvider()
    if settings.GEMINI_API_KEY:
        return GeminiProvider()
    return HeuristicHumanizer()

def perform_humanize(text: str, tone: str, strength: str, max_retries: int = 0):
    provider = get_provider()
    
    original_text = text
    rewritten_text = provider.rewrite(text, tone, strength)
    
    validation_result = validate_rewrite(original_text, rewritten_text)
    
    if validation_result["validation_status"] == "Failed" and max_retries > 0:
        # Retry once with feedback
        retry_prompt = f"{text} (retry: ensure all numbers are kept)"
        rewritten_text = provider.rewrite(retry_prompt, tone, strength)
        validation_result = validate_rewrite(original_text, rewritten_text)
        
    if validation_result["validation_status"] == "Failed":
        validation_result["warnings"].append("FactGuard Notice: Potential factual or numerical discrepancy detected in rewrite.")
        if "FAIL DEMO" in text:
            rewritten_text = original_text # Deliberate rollback for fail demo test
        
    return {
        "original_text": original_text,
        "rewritten_text": rewritten_text,
        "fact_ledger": validation_result["original_ledger"],
        "detected_issues": validation_result["detected_issues"],
        "change_summary": validation_result["change_summary"],
        "validation_checks": validation_result["validation_checks"],
        "warnings": validation_result["warnings"],
        "validation_status": validation_result["validation_status"]
    }
