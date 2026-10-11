import re

NUMBER_PATTERN = re.compile(r'(?:\$|€|£|¥)?\b\d+(?:[.,:/-]\d+)*(?:%|°[CF]|\s*(?:AM|PM|kg|lbs|mph|km/h|ms|px|GB|MB|KB|GHz|MHz|USD|EUR|GBP|INR)\b)?')
YEAR_PATTERN = re.compile(r'\b(?:19\d\d|20\d\d)\b')
NEGATION_PATTERN = re.compile(r'\b(?:not|never|neither|nor|no|cannot|can\'t|won\'t|didn\'t|doesn\'t|isn\'t|aren\'t|wasn\'t|weren\'t)\b', re.IGNORECASE)

def check_numbers(original: str, rewritten: str) -> list[str]:
    orig_nums = set(NUMBER_PATTERN.findall(original))
    rewr_nums = set(NUMBER_PATTERN.findall(rewritten))
    missing = orig_nums - rewr_nums
    warnings = []
    for num in missing:
        warnings.append(f"Number, measurement, or unit '{num}' was omitted or modified in the rewrite.")
    return warnings

def check_years(original: str, rewritten: str) -> list[str]:
    orig_years = set(YEAR_PATTERN.findall(original))
    rewr_years = set(YEAR_PATTERN.findall(rewritten))
    missing = orig_years - rewr_years
    warnings = []
    for yr in missing:
        warnings.append(f"Year '{yr}' was omitted or modified.")
    return warnings

def check_negations(original: str, rewritten: str) -> list[str]:
    orig_neg = set(n.lower() for n in NEGATION_PATTERN.findall(original))
    rewr_neg = set(n.lower() for n in NEGATION_PATTERN.findall(rewritten))
    warnings = []
    if orig_neg and not rewr_neg:
        warnings.append(f"A negative condition ({', '.join(orig_neg)}) appears to have been removed or flipped.")
    return warnings

def factguard_check(original: str, rewritten: str) -> dict:
    warnings = []
    warnings.extend(check_numbers(original, rewritten))
    warnings.extend(check_years(original, rewritten))
    warnings.extend(check_negations(original, rewritten))
    
    needs_review = len(warnings) > 0
    return {
        "warnings": warnings,
        "needs_review": needs_review,
        "summary": "No heuristic warnings detected. This does not guarantee factual accuracy." if not needs_review else f"{len(warnings)} potential issue(s) detected."
    }
