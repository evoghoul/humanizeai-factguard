import re
from app.schemas.models import FactLedger

def extract_fact_ledger(text: str) -> FactLedger:
    numbers = re.findall(r'\b\d+(?:\.\d+)?(?:%|k|M|B)?(?!\w)|\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\b', text.lower())
    dates = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?:, \d{4})?\b|\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b|\b\d{4}\b', text, re.IGNORECASE)
    
    negations = []
    for word in ["not", "never", "no", "none", "cannot", "don't", "doesn't", "didn't", "won't", "wouldn't", "can't", "couldn't", "isn't", "aren't", "hasn't", "haven't"]:
        if re.search(rf'\b{word}\b', text.lower()):
            negations.append(word)
            
    uncertainty = []
    for word in ["might", "may", "could", "possibly", "perhaps", "probably"]:
        if re.search(rf'\b{word}\b', text.lower()):
            uncertainty.append(word)
            
    return FactLedger(
        names=[],
        organizations=[],
        dates=list(set(dates)),
        numbers=list(set(numbers)),
        technical_terms=[],
        claims=[],
        negations=list(set(negations)),
        uncertainty=list(set(uncertainty)),
        important_evidence=[]
    )
