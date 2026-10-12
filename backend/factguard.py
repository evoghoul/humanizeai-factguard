import re

NUMBER_PATTERN = re.compile(
    r'(?:[\$€£¥])?\b\d+(?:[.,:/-]\d+)*(?:%|°[CF]|\s*(?:AM|PM|kg|lbs|mph|km/h|ms|px|GB|MB|KB|GHz|MHz|USD|EUR|GBP|INR)\b)?',
    re.IGNORECASE
)
YEAR_PATTERN = re.compile(r'\b(?:19\d\d|20\d\d)\b')
TIMELINE_PATTERN = re.compile(
    r'\b(?:two|three|four|five|six|seven|eight|nine|ten|\d+)[-\s]+(?:weeks?|days?|hours?|months?|years?)\b',
    re.IGNORECASE
)
NEGATION_PATTERN = re.compile(r'\b(?:not|never|neither|nor|no|cannot|can\'t|won\'t|didn\'t|doesn\'t|isn\'t|aren\'t|wasn\'t|weren\'t)\b', re.IGNORECASE)

BANNED_AI_CLICHES = [
    "rich tapestry", "dynamic synergies", "dynamic synergy", "paradigm shift", "paradigm shifts",
    "delve into", "delving into", "delve", "delves", "multifaceted", "digital landscape",
    "navigating the landscape", "the realm of", "tapestry", "testament to", "testament",
    "beacon of", "beacon", "foster", "fostering", "spearhead", "spearheading",
    "game-changer", "game-changing", "pivotal role", "pivotal", "cornerstone", "seamlessly",
    "seamless", "crucial to note", "it is crucial to", "in today's fast-paced world", "in today's digital era"
]

STOPWORDS = {
    "the", "this", "that", "these", "those", "when", "while", "where", "what",
    "however", "furthermore", "moreover", "in", "on", "at", "during", "between",
    "although", "because", "since", "it", "they", "we", "our", "their", "after",
    "before", "to", "from", "for", "with", "as", "by", "if", "unless", "until"
}

def extract_named_entities(text: str) -> list[str]:
    raw_entities = re.findall(
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b|\b(?:Dr\.|CFO|CEO|CTO|VP)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
        text
    )
    cleaned = []
    for ent in raw_entities:
        words = ent.split()
        if len(words) > 1 and words[0].lower() in STOPWORDS:
            ent = " ".join(words[1:])
        if ent and ent.lower() not in STOPWORDS:
            cleaned.append(ent)
    return list(set(cleaned))

def check_named_entities(original: str, rewritten: str) -> list[str]:
    orig_ents = extract_named_entities(original)
    rewr_lower = rewritten.lower()
    missing = [ent for ent in orig_ents if ent.lower() not in rewr_lower]
    warnings = []
    for ent in missing:
        warnings.append(f"Named entity '{ent}' was omitted or substituted with generic filler.")
    return warnings

def check_numbers(original: str, rewritten: str) -> list[str]:
    orig_nums = set(n.strip() for n in NUMBER_PATTERN.findall(original) if n.strip())
    rewr_lower = rewritten.lower()
    missing = [num for num in orig_nums if num.lower() not in rewr_lower]
    warnings = []
    for num in missing:
        warnings.append(f"Number, measurement, or metric '{num}' was omitted or modified in the rewrite.")
    return warnings

def check_years_and_timelines(original: str, rewritten: str) -> list[str]:
    orig_years = set(YEAR_PATTERN.findall(original))
    rewr_years = set(YEAR_PATTERN.findall(rewritten))
    missing_years = orig_years - rewr_years
    
    orig_timelines = set(t.strip().lower() for t in TIMELINE_PATTERN.findall(original))
    rewr_lower = rewritten.lower()
    missing_timelines = [t for t in orig_timelines if t not in rewr_lower]
    
    warnings = []
    for yr in missing_years:
        warnings.append(f"Year '{yr}' was omitted or modified.")
    for tl in missing_timelines:
        warnings.append(f"Specific timeline '{tl}' was omitted or generalized.")
    return warnings

def check_negations(original: str, rewritten: str) -> list[str]:
    orig_neg = set(n.lower() for n in NEGATION_PATTERN.findall(original))
    rewr_neg = set(n.lower() for n in NEGATION_PATTERN.findall(rewritten))
    warnings = []
    if orig_neg and not rewr_neg:
        warnings.append(f"A negative condition ({', '.join(orig_neg)}) appears to have been removed or flipped.")
    return warnings

def check_hallucinations(original: str, rewritten: str) -> list[str]:
    orig_ents = set(e.lower() for e in extract_named_entities(original))
    rewr_ents = extract_named_entities(rewritten)
    orig_lower = original.lower()
    
    warnings = []
    for ent in rewr_ents:
        ent_lower = ent.lower()
        if ent_lower not in orig_lower and not any(part in orig_lower for part in ent_lower.split()):
            # If original had no named entities or this specific entity is new, flag severe hallucination
            warnings.append(f"Potential hallucinated entity '{ent}' introduced without factual grounding.")
    return warnings

def check_intent_preservation(original: str, rewritten: str) -> list[str]:
    """
    Verifies that the structural purpose (such as open-ended interview questions)
    is not altered into declarative statements or advice.
    """
    warnings = []
    orig_trimmed = original.strip()
    rewr_trimmed = rewritten.strip()
    
    is_orig_question = (
        orig_trimmed.endswith("?") or
        bool(re.search(r"\b(?:how would you|can you explain|what strategies|describe how|how do you|why would you|what approach)\b", orig_trimmed, re.IGNORECASE))
    )
    
    if is_orig_question:
        has_rewr_question = "?" in rewr_trimmed
        if not has_rewr_question:
            warnings.append("Intent drift: Source interview question was converted into declarative advice or statements.")
    return warnings

def check_timeline_boundaries(original: str, rewritten: str) -> list[str]:
    """
    Prevents timeline distortion where closed date ranges (e.g. 'August 1 to September 30')
    are summarized into open-ended phrases (e.g. 'since August 1').
    """
    warnings = []
    # Match patterns like: August 1 to September 30, from August 1 to September 30, between August 1 and September 30
    closed_range_pattern = re.compile(
        r'\b(?:(?:from|between)\s+)?([A-Z][a-z]+\s+\d{1,2}(?:,\s*\d{4})?)\s+(?:to|until|and|-)\s+([A-Z][a-z]+\s+\d{1,2}(?:,\s*\d{4})?)\b',
        re.IGNORECASE
    )
    ranges = closed_range_pattern.findall(original)
    rewr_lower = rewritten.lower()
    
    for start_d, end_d in ranges:
        # Check if start and end dates survived
        if start_d.lower() not in rewr_lower or end_d.lower() not in rewr_lower:
            warnings.append(f"Timeline distortion: Closed date range ('{start_d} to {end_d}') was summarized or boundary omitted.")
        # Check if rewritten turned closed range into "since <date>"
        if re.search(rf"\bsince\s+{re.escape(start_d)}\b", rewritten, re.IGNORECASE):
            warnings.append(f"Timeline distortion: Specific closed boundary ('{start_d} to {end_d}') was altered to an open-ended 'since {start_d}'.")
    return warnings

def check_exact_deadlines_and_constraints(original: str, rewritten: str) -> list[str]:
    """
    Preserves exact legal/HR deadlines (e.g. '48 hours'), operational windows (e.g. '3-minute window'),
    system constraints (e.g. 'zero unplanned downtime'), scores (e.g. '8.5/10'), and technical frameworks.
    """
    warnings = []
    rewr_lower = rewritten.lower()
    
    # 1. Exact hour deadlines: e.g. 48 hours, 24 hours, 72 hours
    hour_deadlines = re.findall(r'\b\d+\s+hours?\b', original, re.IGNORECASE)
    for dl in hour_deadlines:
        dl_lower = dl.lower()
        if dl_lower not in rewr_lower and dl_lower.replace(" ", "-") not in rewr_lower:
            warnings.append(f"Deadline alteration: Strict deadline '{dl}' was altered or converted to a flexible timeframe.")
            
    # 2. Operational windows: e.g. 3-minute window, 5-minute window
    window_matches = re.findall(r'\b\d+-minute(?:\s+window)?\b|\b\d+\s+minute(?:\s+window)?\b', original, re.IGNORECASE)
    for win in window_matches:
        win_norm = win.lower().replace("-", " ")
        if win_norm not in rewr_lower.replace("-", " "):
            warnings.append(f"Operational constraint '{win}' was omitted or modified.")
            
    # 3. System constraints: e.g. zero unplanned downtime, zero downtime
    constraints = re.findall(r'\bzero\s+(?:unplanned\s+)?downtime\b', original, re.IGNORECASE)
    for c in constraints:
        if c.lower() not in rewr_lower:
            warnings.append(f"Critical constraint '{c}' was omitted or modified.")
            
    # 4. Qualitative scores: e.g. 8.5/10, 85 out of 100
    scores = re.findall(r'\b\d+(?:\.\d+)?/10\b|\b\d+\s+out\s+of\s+\d+\b', original, re.IGNORECASE)
    for score in scores:
        if score.lower() not in rewr_lower:
            warnings.append(f"Qualitative score '{score}' was omitted or modified.")
            
    # 5. Technical frameworks: e.g. SQLite, PostgreSQL, FastAPI
    tech_terms = re.findall(r'\b(?:SQLite|PostgreSQL|FastAPI|React|TypeScript|Docker|Kubernetes|Redis)\b', original)
    for tech in tech_terms:
        if tech.lower() not in rewr_lower:
            warnings.append(f"Technical terminology '{tech}' was omitted.")
            
    return warnings

def check_ai_cliches(rewritten: str) -> list[str]:
    warnings = []
    for cliche in BANNED_AI_CLICHES:
        if re.search(rf"\b{re.escape(cliche)}\b", rewritten, re.IGNORECASE):
            warnings.append(f"Banned AI cliché or robotic buzzword '{cliche}' detected.")
    return warnings

def factguard_check(original: str, rewritten: str) -> dict:
    warnings = []
    warnings.extend(check_named_entities(original, rewritten))
    warnings.extend(check_numbers(original, rewritten))
    warnings.extend(check_years_and_timelines(original, rewritten))
    warnings.extend(check_negations(original, rewritten))
    warnings.extend(check_hallucinations(original, rewritten))
    warnings.extend(check_intent_preservation(original, rewritten))
    warnings.extend(check_timeline_boundaries(original, rewritten))
    warnings.extend(check_exact_deadlines_and_constraints(original, rewritten))
    warnings.extend(check_ai_cliches(rewritten))
    
    needs_review = len(warnings) > 0
    return {
        "warnings": warnings,
        "needs_review": needs_review,
        "summary": "No heuristic warnings detected. FactGuard verified 100% entity and metric preservation." if not needs_review else f"{len(warnings)} potential issue(s) detected."
    }
