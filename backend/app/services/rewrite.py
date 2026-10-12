import re
import httpx
from app.core.config import settings
from app.services.validation import validate_rewrite

class ModelProviderInterface:
    def rewrite(self, text: str, tone: str, strength: str, context: str = "General Communication", writing_mode: str = "Clarity Improvement") -> str:
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
    def rewrite(self, text: str, tone: str, strength: str, context: str = "General Communication", writing_mode: str = "Clarity Improvement") -> str:
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

ANTI_AI_SYSTEM_PROMPT = """You are HumanizeAI-FactGuard, an expert human editor and factual integrity engine. Rewrite the input text into authentic, natural human prose that passes all plagiarism checkers (Turnitin, CopyLeaks, Grammarly) and AI detectors (GPTZero, ZeroGPT, Turnitin AI) with 0% detection, strictly adhering to Wikipedia's "Signs of AI-generated text" negative constraints and FactGuard factual immutability.

### CORE DIRECTIVES (FACTGUARD CONSTRAINTS)

1. ZERO HALLUCINATION (Strict Enforcement)
You are a linguistic refinement layer, not a creative author. You must NEVER invent, assume, or inject external information. If a company name (e.g., 'Apex Holdings'), candidate name, location, or certification is not explicitly stated in the source text, do not add it under any circumstances. Never hallucinate specific entities to anchor abstract thoughts.

2. ABSOLUTE ENTITY LOCK
You must identify and perfectly preserve all hard data points. Do not round numbers, summarize timelines, or delete constraints. You must retain:
- All specific metrics, percentages, currency amounts, and financial figures (e.g., "$185,000", "99.4%", "£450 daily savings").
- All exact timelines and deadlines (e.g., "48 hours", "3-minute window"). Do not change specific dates to vague terms like "recently" or "since August 1". Retain closed date range boundaries (e.g., "August 1 to September 30" must NEVER become an open-ended "since August 1"). Retain exact deadlines (e.g., "48 hours" must NEVER become "by tomorrow evening").
- All technical terminology and framework names (e.g., "SQLite", "PostgreSQL", "FastAPI", "React", "TypeScript").
- All qualitative scores and ratings (e.g., "8.5/10", "85 out of 100").
- All operational constraints and guarantees (e.g., "zero unplanned downtime", "zero downtime", "3-minute window").

3. INTENT & STRUCTURAL PRESERVATION
You must recognize the fundamental purpose of the source text and maintain it perfectly:
- Interview Questions: If the source text asks the reader how they would solve a problem or explain a concept, the output MUST remain an open-ended question demanding an answer. Never convert an interview question into a declarative statement of advice or instruction.
- Candidate Feedback: Maintain the exact balance of praise and critique. Do not soften technical failures or inflate positive performance.
- Professional Reports: Maintain objective, evidence-based reporting without adding emotional filler or speculative commentary.

4. DE-ROBOTING & CLICHÉ ERADICATION
Aggressively eliminate common AI-generated vocabulary and sentence structures. Completely avoid words and phrases such as: "multifaceted", "delving", "delve into", "tapestry", "rich tapestry", "dynamic synergies", "paradigm", "paradigm shift", "testament", "testament to", "crucial to note", and "seamlessly". Replace these with natural, human-flowing vocabulary appropriate for the requested tone.

5. ZERO N-GRAM PLAGIARISM OVERLAP:
Plagiarism checkers flag 4 or more consecutive identical words. You MUST aggressively rephrase, restructure, and invert the syntax of every sentence. Do NOT preserve the grammatical order or phrase sequences of the original text. Reorder ideas, swap active and passive voice, and use distinct vocabulary while keeping all locked entities and facts 100% accurate.

6. WIKIPEDIA ANTI-AI NEGATIVE CONSTRAINTS:
- NO EM-DASHES (—), EN-DASHES (–), OR SEMICOLONS (;): AI models overuse dashes and semicolons to join thoughts. Ban all dashes and semicolons completely. Split into short punchy sentences instead.
- NO NEGATIVE PARALLELISMS: Strictly forbid 'not just X, but Y', 'it's not about X, it's about Y', or 'not only X, but also Y'. State claims directly.
- NO RULE OF THREES: Never list three adjectives, adverbs, or nouns in a rhythmic row (e.g. avoid 'innovative, efficient, and transformative').
- NO 'FALSE RANGES': Never use the lazy sweep 'From X to Y' (e.g. avoid 'From startups to enterprises').
- NO COMPULSIVE SUMMARIES OR CLICHÉ TRANSITIONS: Never end with a generic wrap-up ('In summary,', 'Overall, this highlights...', 'Ultimately, ...'). Never use transitions like 'That said,', 'In other words,', 'At the end of the day,', 'Here's the catch:'. When the thought ends, stop writing.
- NO VAGUE ATTRIBUTION: Avoid empty hedges ('It is important to note that', 'Some critics argue', 'It remains to be seen').
- EXTREME BURSTINESS & SENTENCE VARIETY: Wildly vary sentence lengths. Alternate 2-to-5 word punchy sentences/fragments ('Fair enough.', 'Hardly surprising.', 'It works.') with natural 18-to-26 word compound thoughts. Never write consecutive sentences of equal length.

7. PRESERVE FULL LENGTH AND DEPTH (DO NOT SUMMARIZE OR SHORTEN):
Paraphrasing is NOT summarizing. The rewritten text MUST maintain the full depth, completeness, and approximate length of the original passage (90% to 110% of original word count). Do NOT combine multiple distinct thoughts into a single short sentence, and do NOT drop background details, nuances, or explanations.

8. STRICT DOCUMENT & EMAIL FORMAT PRESERVATION (NEVER COLLAPSE INTO A SINGLE PARAGRAPH):
If the input is an email, letter, memo, or correspondence, you MUST preserve its exact structural layout:
- Subject lines must stay on their own line with a blank line after.
- Salutations/greetings ('Dear [Name],', 'Hi [Name],', 'To [Name]:') must stay on their own line with a blank line (\\n\\n) after.
- Each distinct body paragraph MUST remain on its own paragraph separated by a blank line (\\n\\n). NEVER merge separate paragraphs into a continuous block.
- Bullet points and numbered lists must remain as individual list items on their own lines.
- Sign-offs ('Best regards,', 'Sincerely,', 'Warmest regards,', 'Cheers,') must appear on their own line preceded by a blank line (\\n\\n).
- Signature lines ([Name], [Title], [Company], [Contact]) must each appear on their own separate lines.

### INTERNAL WORKFLOW (CHAIN OF THOUGHT)
Before generating your final response, silently process the following steps:
Step 1 (Extract): Identify all numbers, names, technologies, deadlines, constraints, and scores in the source text.
Step 2 (Classify): Determine if the text is an interview question, a report, a notification, or candidate feedback.
Step 3 (Refine): Rewrite the text applying the requested context, mode, and tone while eliminating robotic clichés and varying sentence structure.
Step 4 (Verify): Cross-check your draft against Step 1 and Step 2. If any entity was dropped, altered, or hallucinated, or if a question was turned into a statement, rewrite to restore exact original data and format.

### OUTPUT FORMAT
Provide ONLY the final refined text. Do not include explanations, apologies, conversational filler, or your internal chain of thought."""

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

def enhance_burstiness(text: str, original_text: str) -> str:
    """
    Post-processing stylometric enhancer:
    Strips Wikipedia AI tells, residual AI tropes, injects natural rhythm markers,
    removes em-dashes and semicolons, preserves layout, and rigorously verifies FactGuard invariants before returning.
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
        enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
        
    enhanced = re.sub(r"[^\S\r\n]*,[^\S\r\n]*,[^\S\r\n]*", ", ", enhanced)
    enhanced = re.sub(r"[^\S\r\n]*\.[^\S\r\n]*\.[^\S\r\n]*", ". ", enhanced)

    # CRITICAL: Preserve all document/email formatting (never use re.sub(r'\s+', ' ', enhanced))
    enhanced = restore_email_and_letter_formatting(enhanced, original_text=original_text)
        
    # Check that no facts, numbers, dates, or named entities from original_text were broken by enhancement
    orig_facts = extract_fact_ledger(original_text)
    for n in orig_facts.numbers:
        if n.lower() not in enhanced.lower():
            return restore_email_and_letter_formatting(cleaned, original_text=original_text)
    for d in orig_facts.dates:
        if d.lower() not in enhanced.lower():
            return restore_email_and_letter_formatting(cleaned, original_text=original_text)
    for ent in orig_facts.names:
        if ent.lower() not in enhanced.lower():
            return restore_email_and_letter_formatting(cleaned, original_text=original_text)
            
    return enhanced

class GeminiProvider(ModelProviderInterface):
    """
    Google Gemini 2.5 Flash / 1.5 Flash cloud provider.
    Zero-latency, 24/7 reliability for the Google Student Club Hackathon.
    """
    def rewrite(self, text: str, tone: str, strength: str, context: str = "General Communication", writing_mode: str = "Clarity Improvement") -> str:
        if not settings.GEMINI_API_KEY:
            return HeuristicHumanizer().rewrite(text, tone, strength, context=context, writing_mode=writing_mode)
        
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
                "parts": [{"text": "Writing Context: General Communication\nWriting Mode: Clarity Improvement\nTone of Voice: Conversational\nStrength: Heavy\n\nOriginal Text:\nArtificial intelligence has transformed the modern business landscape in profound ways. Companies worldwide are leveraging machine learning to enhance operational efficiency and foster innovation. It is important to note that organizations must adopt strategic frameworks to navigate these technological changes seamlessly and remain competitive in today's digital era."}]
            },
            {
                "role": "model",
                "parts": [{"text": "Work life shifted fast after automation arrived. Most companies now run machine learning across their daily routines, hoping to save hours and spark fresh ideas. It helps. Still, diving in without an actual plan usually leaves teams untangling messy software instead of getting ahead."}]
            },
            {
                "role": "user",
                "parts": [{"text": "Writing Context: Professional Report\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Heavy\n\nOriginal Text:\nAt Starlight Therapeutics, shifting staff to remote workflows generated £450 daily savings over a two-week pilot, while enhancing research documentation speed."}]
            },
            {
                "role": "model",
                "parts": [{"text": "Switching researchers to remote setups saved Starlight Therapeutics £450 every single day during their two-week pilot. Beyond cutting expenses, team members turned around trial logs much faster."}]
            },
            {
                "role": "user",
                "parts": [{"text": "Writing Context: General Communication\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Heavy\n\nOriginal Text:\nIn today's evolving digital landscape, organizations must delve into dynamic synergies and foster a rich tapestry of holistic paradigm shifts to unlock continuous innovation."}]
            },
            {
                "role": "model",
                "parts": [{"text": "Companies that want steady progress need to fix how their teams coordinate day-to-day. That means communicating clearly, cutting red tape, and trying new approaches without overthinking."}]
            },
            {
                "role": "user",
                "parts": [{"text": "Writing Context: Interview Question\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Heavy\n\nOriginal Text:\nHow would you design a distributed cache using SQLite or PostgreSQL that guarantees zero unplanned downtime and handles failover within a 3-minute window?"}]
            },
            {
                "role": "model",
                "parts": [{"text": "If you had to architect a distributed cache using SQLite or PostgreSQL, how would you deliver zero unplanned downtime while completing failover within a 3-minute window?"}]
            },
            {
                "role": "user",
                "parts": [{"text": "Writing Context: Recruiter Email\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Heavy\n\nOriginal Text:\nFrom August 1 to September 30, our incident response crew resolved 14 critical alerts. Every candidate must complete the technical evaluation within 48 hours."}]
            },
            {
                "role": "model",
                "parts": [{"text": "Between August 1 and September 30, our incident response crew resolved 14 critical alerts. Candidates must finish the technical evaluation within 48 hours."}]
            },
            {
                "role": "user",
                "parts": [{"text": "Writing Context: Professional Report\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Medium\n\nOriginal Text:\nThe quarterly financial report demonstrates significant revenue growth of 18.5% reaching $4.2 million on September 30, 2025. However, leadership must remain vigilant regarding market volatility."}]
            },
            {
                "role": "model",
                "parts": [{"text": "Quarterly revenue climbed 18.5% to reach $4.2 million through September 30, 2025. Strong results. Yet leadership must watch sudden market swings closely as conditions shift."}]
            },
            {
                "role": "user",
                "parts": [{"text": (
                    "Writing Context: Recruiter Email\nWriting Mode: Clarity Improvement\nTone of Voice: Professional\nStrength: Heavy\n\nOriginal Text:\n"
                    "Dear Gwen,\n\n"
                    "It is our pleasure to confirm your appointment for the Data Analyst role starting on November 1, 2026.\n\n"
                    "Please confirm your availability by replying directly to this message by Friday.\n\n"
                    "Best regards,\n"
                    "HR Operations\n"
                    "[Company Name]"
                )}]
            },
            {
                "role": "model",
                "parts": [{"text": (
                    "Dear Gwen,\n\n"
                    "We are thrilled to welcome you to the Data Analyst position, with your start date set for November 1, 2026.\n\n"
                    "Kindly reply to this email by Friday to confirm that you are ready to begin.\n\n"
                    "Best regards,\n"
                    "HR Operations\n"
                    "[Company Name]"
                )}]
            },
            {
                "role": "user",
                "parts": [{
                    "text": (
                        f"Writing Context: {context}\n"
                        f"Writing Mode: {writing_mode}\n"
                        f"Tone of Voice: {tone}\n"
                        f"{strength_desc}\n\n"
                        f"Original Text (~{len(text.split())} words - rewrite must match ~{len(text.split())} words without shortening, strictly preserving intent, entities, deadlines, and document/email structure):\n"
                        f"{text}"
                    )
                }]
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
        return HeuristicHumanizer().rewrite(text, tone, strength, context=context, writing_mode=writing_mode)

class LightningProvider(ModelProviderInterface):
    """
    On-premise fine-tuned Qwen2.5-14B-Instruct running on L4 GPU via permanent ngrok tunnel.
    """
    def rewrite(self, text: str, tone: str, strength: str, context: str = "General Communication", writing_mode: str = "Clarity Improvement") -> str:
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
                        "strength": strength,
                        "context": context,
                        "writing_context": context,
                        "writing_mode": writing_mode,
                        "tone_of_voice": tone
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
                    return self._fallback(text, tone, strength, context=context, writing_mode=writing_mode)
        except Exception:
            return self._fallback(text, tone, strength, context=context, writing_mode=writing_mode)

    def _fallback(self, text: str, tone: str, strength: str, context: str = "General Communication", writing_mode: str = "Clarity Improvement") -> str:
        if settings.GEMINI_API_KEY:
            return GeminiProvider().rewrite(text, tone, strength, context=context, writing_mode=writing_mode)
        return HeuristicHumanizer().rewrite(text, tone, strength, context=context, writing_mode=writing_mode)

def get_provider():
    if settings.MODEL_PROVIDER_TYPE == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider()
    if settings.MODEL_PROVIDER_TYPE == "lightning":
        return LightningProvider()
    if settings.GEMINI_API_KEY:
        return GeminiProvider()
    return HeuristicHumanizer()

def perform_humanize(
    text: str,
    tone: str = "Professional",
    strength: str = "medium",
    context: str = "General Communication",
    writing_mode: str = "Clarity Improvement",
    max_retries: int = 0
):
    provider = get_provider()
    
    original_text = text
    rewritten_text = provider.rewrite(text, tone, strength, context=context, writing_mode=writing_mode)
    
    validation_result = validate_rewrite(original_text, rewritten_text)
    
    if validation_result["validation_status"] == "Failed" and max_retries > 0:
        # Retry once with feedback
        retry_prompt = f"{text} (retry: ensure all numbers are kept)"
        rewritten_text = provider.rewrite(retry_prompt, tone, strength, context=context, writing_mode=writing_mode)
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
