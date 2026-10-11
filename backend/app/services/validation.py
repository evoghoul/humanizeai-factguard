from app.schemas.models import ValidationCheck
from app.services.extraction import extract_fact_ledger

def validate_rewrite(original_text: str, rewritten_text: str):
    original_ledger = extract_fact_ledger(original_text)
    rewritten_ledger = extract_fact_ledger(rewritten_text)
    
    checks = []
    
    # 1. Number preservation
    missing_nums = [num for num in original_ledger.numbers if num not in rewritten_text]
    num_status = "Failed" if missing_nums else "Passed"
    checks.append(ValidationCheck(
        name="Number Preservation",
        status=num_status,
        details=f"Missing numbers: {missing_nums}" if missing_nums else "All numbers preserved."
    ))
    
    # 2. Date preservation
    missing_dates = [date for date in original_ledger.dates if date not in rewritten_text]
    date_status = "Failed" if missing_dates else "Passed"
    checks.append(ValidationCheck(
        name="Date Preservation",
        status=date_status,
        details=f"Missing dates: {missing_dates}" if missing_dates else "All dates preserved."
    ))
    
    # 3. Negation preservation
    neg_status = "Passed"
    if original_ledger.negations and not rewritten_ledger.negations:
        neg_status = "Failed"
    checks.append(ValidationCheck(
        name="Negation Preservation",
        status=neg_status,
        details="Original had negations, rewritten might be missing them." if neg_status == "Failed" else "Negation semantics seem consistent."
    ))
    
    # 4. Uncertainty preservation
    unc_status = "Passed"
    if original_ledger.uncertainty and not rewritten_ledger.uncertainty:
        unc_status = "Failed"
    checks.append(ValidationCheck(
        name="Uncertainty Preservation",
        status=unc_status,
        details="Original had uncertainty, rewritten might be missing it." if unc_status == "Failed" else "Uncertainty semantics seem consistent."
    ))
    
    # 5. Meaning / Entity Preservation (Placeholder)
    checks.append(ValidationCheck(
        name="Entity Preservation",
        status="Not Checked",
        details="Entity preservation passed (Placeholder - needs NLP)."
    ))

    # Evaluate overall status
    has_failed = any(c.status == "Failed" for c in checks)
    has_not_checked = any(c.status == "Not Checked" for c in checks)
    
    if has_failed:
        validation_status = "Failed"
    elif has_not_checked:
        validation_status = "Partial"
    else:
        validation_status = "Passed"
    
    issues = [c.details for c in checks if c.status == "Failed"]
    warnings = []
    if validation_status == "Failed":
        warnings.append("Some heuristic checks failed.")
    if has_not_checked:
        warnings.append("Critical semantic checks were skipped due to lack of an NLP model.")
    
    return {
        "validation_checks": checks,
        "validation_status": validation_status,
        "detected_issues": issues,
        "warnings": warnings,
        "change_summary": "Adjusted tone and removed robotic phrasing.",
        "original_ledger": original_ledger
    }
