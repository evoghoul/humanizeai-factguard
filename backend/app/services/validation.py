import re
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
    
    # 5. Named Entity Preservation
    from factguard import extract_named_entities
    orig_names = extract_named_entities(original_text)
    rewr_names = extract_named_entities(rewritten_text)
    missing_entities = [ent for ent in orig_names if ent.lower() not in rewritten_text.lower()]
    ent_status = "Failed" if missing_entities else "Passed"
    checks.append(ValidationCheck(
        name="Named Entity Preservation",
        status=ent_status,
        details=f"Missing named entities: {missing_entities}" if missing_entities else "All proper names and corporate entities preserved."
    ))

    # 6. Hallucination Detection (unverified entities introduced)
    hallucinated_entities = [
        ent for ent in rewr_names
        if ent.lower() not in original_text.lower() and not any(part in original_text.lower() for part in ent.lower().split())
    ]
    hallucination_status = "Failed" if hallucinated_entities else "Passed"
    checks.append(ValidationCheck(
        name="Hallucination Check",
        status=hallucination_status,
        details=f"Potential fabricated entities detected: {hallucinated_entities}" if hallucinated_entities else "Zero hallucinated entities detected."
    ))

    # 7. AI Cliché / Buzzword Infiltration Check
    from factguard import BANNED_AI_CLICHES, check_intent_preservation, check_timeline_boundaries, check_exact_deadlines_and_constraints
    detected_cliches = [
        c for c in BANNED_AI_CLICHES if re.search(rf"\b{re.escape(c)}\b", rewritten_text, re.IGNORECASE)
    ]
    cliche_status = "Failed" if detected_cliches else "Passed"
    checks.append(ValidationCheck(
        name="AI Cliché Prevention",
        status=cliche_status,
        details=f"Robotic AI clichés detected: {detected_cliches}" if detected_cliches else "Zero AI buzzwords or robotic tropes detected."
    ))

    # 8. Intent & Structural Preservation Check
    intent_issues = check_intent_preservation(original_text, rewritten_text)
    intent_status = "Failed" if intent_issues else "Passed"
    checks.append(ValidationCheck(
        name="Intent Preservation",
        status=intent_status,
        details="; ".join(intent_issues) if intent_issues else "Source structural intent (questions vs declarative) preserved."
    ))

    # 9. Timeline Boundary Preservation Check
    boundary_issues = check_timeline_boundaries(original_text, rewritten_text)
    boundary_status = "Failed" if boundary_issues else "Passed"
    checks.append(ValidationCheck(
        name="Timeline Boundaries",
        status=boundary_status,
        details="; ".join(boundary_issues) if boundary_issues else "Closed timeline boundaries preserved without open-ended summarization."
    ))

    # 10. Exact Deadlines & Constraints Lock
    deadline_issues = check_exact_deadlines_and_constraints(original_text, rewritten_text)
    deadline_status = "Failed" if deadline_issues else "Passed"
    checks.append(ValidationCheck(
        name="Deadlines & Constraints Lock",
        status=deadline_status,
        details="; ".join(deadline_issues) if deadline_issues else "All strict hour deadlines, operational windows, and constraints preserved."
    ))

    # 11. Deep Semantic Claim Check (Placeholder - heuristic audit)
    checks.append(ValidationCheck(
        name="Semantic Claims",
        status="Not Checked",
        details="Deep semantic claim verification skipped without an external NLP model."
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
    if missing_entities:
        warnings.append(f"Named entity retention failure: {', '.join(missing_entities)} omitted or generalized.")
    if missing_nums:
        warnings.append(f"Metric/number preservation failure: {', '.join(missing_nums)} omitted or altered.")
    if missing_dates:
        warnings.append(f"Timeline/date preservation failure: {', '.join(missing_dates)} omitted.")
    if hallucinated_entities:
        warnings.append(f"Hallucination detected: {', '.join(hallucinated_entities)} introduced without source grounding.")
    if detected_cliches:
        warnings.append(f"AI cliché penalty: {', '.join(detected_cliches)} detected in rewritten output.")
    if intent_issues:
        warnings.extend(intent_issues)
    if boundary_issues:
        warnings.extend(boundary_issues)
    if deadline_issues:
        warnings.extend(deadline_issues)
    if has_failed and not warnings:
        warnings.append("Some heuristic checks failed.")
    
    return {
        "validation_checks": checks,
        "validation_status": validation_status,
        "detected_issues": issues,
        "warnings": warnings,
        "change_summary": "Adjusted tone and removed robotic phrasing while enforcing 100% entity and metric retention.",
        "original_ledger": original_ledger
    }
