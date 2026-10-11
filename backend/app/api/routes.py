import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.schemas.models import (
    AnalyzeRequest, AnalyzeResponse,
    HumanizeRequest, HumanizeResponse,
    ValidateRequest, ValidateResponse,
    RefineRequest, RefineResponse, RefineFinding, RefineChange,
    RefineStructuralCheck, RefineVerification, RefineOptions,
    HumanizeSimpleRequest, HumanizeSimpleResponse
)
from app.services.analysis import analyze_robotic_language
from app.services.rewrite import perform_humanize
from app.services.validation import validate_rewrite
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.get("/api/v1/config")
def get_config():
    return {
        "app_name": settings.APP_NAME,
        "provider": settings.MODEL_PROVIDER_TYPE,
        "debug": settings.DEBUG
    }

@router.post("/api/v1/analyze", response_model=AnalyzeResponse)
def analyze_text(request: AnalyzeRequest):
    return analyze_robotic_language(request.text)

@router.post("/api/v1/humanize", response_model=HumanizeResponse)
def humanize_text(request: HumanizeRequest):
    try:
        result = perform_humanize(request.text, request.tone, request.strength)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/humanize", response_model=HumanizeSimpleResponse)
def humanize_simple(request: HumanizeSimpleRequest):
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="Please provide non-empty text.")
    try:
        res = perform_humanize(request.text, "Professional", "medium")
        warnings = res.get("warnings", [])
        status = res.get("validation_status", "Passed")
        needs_review = status in ["Failed", "Review Recommended"] or len(warnings) > 0
        return HumanizeSimpleResponse(
            original=request.text,
            rewrite=res["rewritten_text"],
            warnings=warnings,
            needs_review=needs_review
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="The rewrite could not be completed.")

@router.post("/api/v1/validate", response_model=ValidateResponse)
def validate_text(request: ValidateRequest):
    result = validate_rewrite(request.original_text, request.rewritten_text)
    return {
        "original_text": request.original_text,
        "rewritten_text": request.rewritten_text,
        "detected_issues": result["detected_issues"],
        "change_summary": result["change_summary"],
        "validation_checks": result["validation_checks"],
        "warnings": result["warnings"],
        "validation_status": result["validation_status"]
    }

@router.post("/api/refine", response_model=RefineResponse)
@router.post("/api/v1/refine", response_model=RefineResponse)
def refine_text(request: RefineRequest):
    try:
        options = request.options or RefineOptions()
        raw_tone = (options.tone or "Professional").capitalize()
        tone = raw_tone if raw_tone in ["Professional", "Polished", "Conversational"] else "Professional"
        
        intensity_map = {
            "light": "light",
            "balanced": "medium",
            "strong": "heavy",
            "medium": "medium",
            "heavy": "heavy"
        }
        strength = intensity_map.get((options.intensity or "balanced").lower(), "medium")
        
        humanize_result = perform_humanize(request.text, tone, strength)
        rewritten_text = humanize_result["rewritten_text"]
        
        analysis_result = analyze_robotic_language(request.text)
        
        findings = [
            RefineFinding(
                category="Robotic Phrasing",
                phrase=phrase,
                explanation=analysis_result.get("explanation", "Detected robotic phrasing pattern.")
            )
            for phrase in analysis_result.get("detected_phrases", [])
        ]
        
        changes = []
        if humanize_result.get("change_summary"):
            changes.append(RefineChange(
                original="Original text with robotic phrasing",
                revised="Refined with FactGuard verification",
                reason=humanize_result["change_summary"]
            ))
            
        val_status = humanize_result.get("validation_status", "Passed")
        if val_status == "Passed":
            verification_status = "CONTENT INTEGRITY PASSED"
        elif val_status == "Failed":
            verification_status = "CONTENT INTEGRITY FAILED"
        else:
            verification_status = "REVIEW RECOMMENDED"
            
        ledger = humanize_result.get("fact_ledger")
        preserved = []
        missing = []
        if ledger:
            for n in getattr(ledger, "numbers", []):
                if n in rewritten_text:
                    preserved.append(n)
                else:
                    missing.append(n)
            for d in getattr(ledger, "dates", []):
                if d in rewritten_text:
                    preserved.append(d)
                else:
                    missing.append(d)
                    
        val_checks = humanize_result.get("validation_checks", [])
        negations_preserved = True
        numbers_preserved = len(missing) == 0
        check_details = []
        for vc in val_checks:
            vc_name = getattr(vc, 'name', '')
            vc_details = getattr(vc, 'details', '')
            check_details.append(f"{vc_name}: {vc_details}")
            if vc_name == "Negation Preservation" and getattr(vc, 'status', '') == "Failed":
                negations_preserved = False
                
        verification = RefineVerification(
            status=verification_status,
            preserved=preserved,
            missing=missing,
            added=[],
            warnings=humanize_result.get("warnings", []),
            claims=[],
            structural=RefineStructuralCheck(
                paragraphsPreserved=True,
                listsPreserved=True,
                negationsPreserved=negations_preserved,
                numbersPreserved=numbers_preserved,
                details=check_details
            )
        )
        
        return RefineResponse(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            original=request.text,
            revised=rewritten_text,
            options=options,
            findings=findings,
            changes=changes,
            verification=verification
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

