from app.core.config import settings
from app.services.validation import validate_rewrite

class ModelProviderInterface:
    def rewrite(self, text: str, tone: str, strength: str) -> str:
        raise NotImplementedError

class DemoProvider(ModelProviderInterface):
    def rewrite(self, text: str, tone: str, strength: str) -> str:
        if "FAIL DEMO" in text:
            return "This rewrite completely missed the numbers and dates."
        
        import re
        replacements = {
            "in today's fast-paced world": "currently",
            "delve into": "explore",
            "foster": "encourage",
            "spearhead": "lead",
            "it is important to note that": "notably,",
            "in summary": "overall",
        }
        
        rewritten = text
        for old, new in replacements.items():
            rewritten = re.sub(re.escape(old), new, rewritten, flags=re.IGNORECASE)
            
        return rewritten

import httpx

class LightningProvider(ModelProviderInterface):
    def rewrite(self, text: str, tone: str, strength: str) -> str:
        if "FAIL DEMO" in text:
            return "This rewrite completely missed the numbers and dates."
        url = settings.MODEL_PROVIDER_URL.rstrip("/")
        if not url.endswith("/humanize"):
            target_url = f"{url}/humanize"
        else:
            target_url = url
            
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    target_url,
                    json={"text": text},
                    headers={
                        "Content-Type": "application/json",
                        "ngrok-skip-browser-warning": "true",
                        "User-Agent": "HumanizeAI/1.0"
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("rewrite") or data.get("revised") or text
                else:
                    return DemoProvider().rewrite(text, tone, strength)
        except Exception:
            return DemoProvider().rewrite(text, tone, strength)

def get_provider():
    if settings.MODEL_PROVIDER_TYPE == "lightning":
        return LightningProvider()
    return DemoProvider()

def perform_humanize(text: str, tone: str, strength: str, max_retries: int = 1):
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
        validation_result["warnings"].append("Validation still failed after retry. Returning original text.")
        rewritten_text = original_text # Fallback
        
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
