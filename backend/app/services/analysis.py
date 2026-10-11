import re

ROBOTIC_PHRASES = [
    "in today's fast-paced world",
    "delve into",
    "foster",
    "spearhead",
    "it is important to note that",
    "in summary",
]

def analyze_robotic_language(text: str):
    text_lower = text.lower()
    detected = []
    for phrase in ROBOTIC_PHRASES:
        if phrase in text_lower:
            detected.append(phrase)
    
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    starts = [s.split()[0].lower() for s in sentences if s.split()]
    repetitive_patterns = []
    if len(starts) > 2:
        for i in range(len(starts) - 2):
            if starts[i] == starts[i+1] == starts[i+2]:
                repetitive_patterns.append(f"Three consecutive sentences start with '{starts[i]}'")
                break
                
    score = min(1.0, (len(detected) * 0.2) + (len(repetitive_patterns) * 0.3))
    
    explanation = "This score is a heuristic based on common AI patterns and repetitive sentence structures, not a definitive AI detector."
    
    return {
        "robotic_score": score,
        "detected_phrases": detected,
        "repetitive_patterns": repetitive_patterns,
        "explanation": explanation
    }
