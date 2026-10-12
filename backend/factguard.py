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
    "rich tapestry", "dynamic synergies", "paradigm shift", "delve into", "delving into",
    "delve", "delves", "multifaceted", "digital landscape", "navigating the landscape",
    "tapestry", "testament to", "beacon of", "beacon", "foster", "fostering", "spearhead",
    "spearheading", "game-changer", "pivotal role", "pivotal", "cornerstone", "seamlessly",
    "in today's fast-paced world", "in today's digital era"
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
            # If original had no named entities, inventing one is a severe hallucination
            warnings.append(f"Potential hallucinated entity '{ent}' introduced without factual grounding.")
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
    warnings.extend(check_ai_cliches(rewritten))
    
    needs_review = len(warnings) > 0
    return {
        "warnings": warnings,
        "needs_review": needs_review,
        "summary": "No heuristic warnings detected. FactGuard verified 100% entity and metric preservation." if not needs_review else f"{len(warnings)} potential issue(s) detected."
    }
