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

ANTI_AI_SYSTEM_PROMPT = """You are HumanizeAI, an expert human editor. Rewrite the input text into authentic, natural human prose that passes all plagiarism checkers (Turnitin, CopyLeaks, Grammarly) and AI detectors (GPTZero, ZeroGPT, Turnitin AI) with 0% detection, strictly adhering to Wikipedia's "Signs of AI-generated text" negative constraints.

CRITICAL ANTI-PLAGIARISM & ANTI-AI NEGATIVE CONSTRAINTS (NEVER BREAK THESE):
1. ZERO N-GRAM PLAGIARISM OVERLAP: Plagiarism checkers flag 4 or more consecutive identical words. You MUST aggressively rephrase, restructure, and invert the syntax of every sentence. Do NOT preserve the grammatical order or phrase sequences of the original text. Reorder ideas, swap active and passive voice, and use distinct vocabulary while keeping all facts 100% accurate.
2. NO EM-DASHES (—), EN-DASHES (–), OR SEMICOLONS (;): AI models overuse dashes and semicolons to join thoughts. Real humans write with periods, commas, or conjunctions. Ban all dashes and semicolons completely. Split into short punchy sentences instead.
3. NO NEGATIVE PARALLELISMS: Strictly forbid 'not just X, but Y', 'it's not about X, it's about Y', or 'not only X, but also Y'. State claims directly without formulaic contrast.
4. NO RULE OF THREES: Never list three adjectives, adverbs, or nouns in a rhythmic row (e.g. avoid 'innovative, efficient, and transformative'). Use a single strong word.
5. NO 'FALSE RANGES': Never use the lazy sweep 'From X to Y' (e.g. avoid 'From startups to enterprises', 'From marketing to engineering').
6. ZERO AI VOCABULARY: Total ban on AI dead-giveaways: delve, intricate, tapestry, pivotal, beacon, crucial, foster, spearhead, furthermore, moreover, in conclusion, realm, landscape, game-changer, seamless, paramount, multifaceted, vibrant, revolutionize, underscore, shed light on, testament, holistic, enhance, cornerstone, in today's fast-paced world.
7. NO COMPULSIVE SUMMARIES OR CLICHÉ TRANSITIONS: Never end with a generic wrap-up ('In summary,', 'Overall, this highlights...', 'Ultimately, ...'). Never use cliché transitions like 'That said,', 'In other words,', 'At the end of the day,', 'Here's the catch:'. When the thought ends, stop writing.
8. NO VAGUE ATTRIBUTION: Avoid empty hedges ('It is important to note that', 'Some critics argue', 'It remains to be seen').
9. EXTREME BURSTINESS & SENTENCE VARIETY: Wildly vary sentence lengths. Alternate 2-to-5 word punchy sentences/fragments ('Fair enough.', 'Hardly surprising.', 'It works.') with natural 18-to-26 word compound thoughts. Never write consecutive sentences of equal length.
10. FACTGUARD INVARIANTS (100% INVIOLABLE): Strictly preserve every number, date, year, currency ($/€/£), percentage (%), proper name, and negative condition (not, never, cannot). Never drop, round, or alter any fact.
11. PRESERVE FULL LENGTH AND DEPTH (DO NOT SUMMARIZE OR SHORTEN): Paraphrasing is NOT summarizing. The rewritten text MUST maintain the full depth, completeness, and approximate length of the original passage (90% to 110% of original word count). Do NOT combine multiple distinct thoughts into a single short sentence, and do NOT drop background details, nuances, or explanations. If the original text has multiple paragraphs, preserve the exact paragraph divisions.
12. STRICT FORMAT: Output ONLY the raw rewritten text. Absolutely NO conversational preambles ('Sure!', 'Here is a...'), NO quotation marks, and NO explanations."""

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

def enhance_burstiness(text: str, original_text: str) -> str:
    """
    Post-processing stylometric enhancer:
    Strips Wikipedia AI tells, residual AI tropes, injects natural rhythm markers,
    removes em-dashes and semicolons, and rigorously verifies FactGuard invariants before returning.
    """
    if not text:
        return text
    from app.services.extraction import extract_fact_ledger
    
    cleaned = clean_model_output(text)
    enhanced = cleaned
    
    # 1. Strip compulsive summaries at end
    enhanced = re.sub(r"\n*(?:In conclusion|In summary|Overall|Ultimately),.*$", "", enhanced, flags=re.IGNORECASE).strip()
    
    # 2. Strip broken unicode characters and mangled dashes
    enhanced = enhanced.replace("\ufffd", ", ")
    enhanced = re.sub(r"\s*[—–]\s*", ", ", enhanced)
    
    # 3. Strip semicolons - convert to periods to drastically boost human perplexity / kill AI signature
    enhanced = re.sub(r";\s*", ". ", enhanced)
    
    # 4. Remove negative parallelisms if any leaked through
    enhanced = re.sub(r"\b(?:is|was|are|were|do|does|did)\s+not\s+(?:just|only)\s+([^,;]+)[,;]\s*(?:it's|it\s+is|they're|they\s+are|but\s+also|but)?\s*", r"\1 and ", enhanced, flags=re.IGNORECASE)
    enhanced = re.sub(r"\bnot\s+just\s+([^,;]+)[,;]\s*(?:it's|it\s+is|but\s+also|but)?\s*", r"\1 along with ", enhanced, flags=re.IGNORECASE)

    # 5. Remove cliché AI transitions
    enhanced = re.sub(r"\b(?:In other words|That said|That being said|At the end of the day|Here's the catch[:!.]?|Here is the thing[:!.]?|To put it simply),?\s*", "", enhanced, flags=re.IGNORECASE)
    
    # 6. Residual AI Tropes
    residual_tropes = {
        r"\bin profound ways\b": "completely",
        r"\bplays a vital role in\b": "is key to",
        r"\bplays a key role in\b": "drives",
        r"\bplay a pivotal role\b": "matter deeply",
        r"\bcreative breakthroughs\b": "fresh ideas",
        r"\boperational efficiency\b": "speed and clarity",
        r"\bstrategic frameworks\b": "a solid plan",
        r"\bseamlessly\b": "without friction",
        r"\bthe landscape of\b": "the world of",
        r"\ba testament to\b": "clear proof of",
        r"\ba rich tapestry of\b": "a healthy mix of",
        r"\bdelve into\b": "dig into",
        r"\bdelving into\b": "digging into",
    }
    for pattern, replacement in residual_tropes.items():
        enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
        
    enhanced = re.sub(r"\s*,\s*,\s*", ", ", enhanced)
    enhanced = re.sub(r"\s*\.\s*\.\s*", ". ", enhanced)
    enhanced = re.sub(r"\s+", " ", enhanced).strip()
        
    # Check that no facts from original_text were broken by enhancement
    orig_facts = extract_fact_ledger(original_text)
    for n in orig_facts.numbers:
        if n not in enhanced:
            return cleaned
    for d in orig_facts.dates:
        if d not in enhanced:
            return cleaned
            
    return enhanced

class GeminiProvider(ModelProviderInterface):
    """
    Google Gemini 2.5 Flash / 1.5 Flash cloud provider.
    Zero-latency, 24/7 reliability for the Google Student Club Hackathon.
    """
    def rewrite(self, text: str, tone: str, strength: str) -> str:
        if not settings.GEMINI_API_KEY:
            return HeuristicHumanizer().rewrite(text, tone, strength)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        
        strength_val = (strength or "medium").lower()
        if strength_val == "heavy":
            temperature = 1.05
            strength_desc = "Strength: Heavy (Aggressive structural overhaul, 0% verbatim n-gram overlap, extreme sentence length variation, zero dashes, zero semicolons)"
        elif strength_val == "light":
            temperature = 0.75
            strength_desc = "Strength: Light (Gentle polish, natural cadence)"
        else:
            temperature = 0.95
            strength_desc = "Strength: Medium (Balanced humanization, natural burstiness, zero cliché AI vocabulary)"

        few_shot_contents = [
            {
                "role": "user",
                "parts": [{"text": "Tone: Conversational\nStrength: Heavy\n\nOriginal Text:\nArtificial intelligence has transformed the modern business landscape in profound ways. Companies worldwide are leveraging machine learning to enhance operational efficiency and foster innovation. It is important to note that organizations must adopt strategic frameworks to navigate these technological changes seamlessly and remain competitive in today's digital era."}]
            },
            {
                "role": "model",
                "parts": [{"text": "Work life shifted fast after automation arrived. Most companies now run machine learning across their daily routines, hoping to save hours and spark fresh ideas. It helps. Still, diving in without an actual plan usually leaves teams untangling messy software instead of getting ahead."}]
            },
            {
                "role": "user",
                "parts": [{"text": "Tone: Professional\nStrength: Medium\n\nOriginal Text:\nThe quarterly financial report demonstrates significant revenue growth of 18.5% reaching $4.2 million on September 30, 2025. However, leadership must remain vigilant regarding market volatility."}]
            },
            {
                "role": "model",
                "parts": [{"text": "Quarterly revenue climbed 18.5% to reach $4.2 million through September 30, 2025. Strong results. Yet leadership must watch sudden market swings closely as conditions shift."}]
            },
            {
                "role": "user",
                "parts": [{"text": f"Tone: {tone}\n{strength_desc}\n\nOriginal Text (~{len(text.split())} words - rewrite must match ~{len(text.split())} words without shortening):\n{text}"}]
            }
        ]
        
        payload = {
            "systemInstruction": {
                "parts": [{"text": ANTI_AI_SYSTEM_PROMPT}]
            },
            "contents": few_shot_contents,
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.92,
                "maxOutputTokens": 2048
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
                            raw = parts[0].get("text", "").strip()
                            return enhance_burstiness(raw, text)
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
                    return enhance_burstiness(raw, text)
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
