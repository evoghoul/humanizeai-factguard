from app.services.validation import validate_rewrite
from app.services.extraction import extract_fact_ledger

def test_factguard_a():
    original = "Riya scored 85% in Python and may improve her SQL skills."
    rewritten = "Riya achieved 85% in Python and may enhance her SQL abilities."
    res = validate_rewrite(original, rewritten)
    assert res["validation_status"] == "Partial"

def test_factguard_b():
    original = "The candidate did not demonstrate advanced Java skills."
    rewritten = "The candidate demonstrated advanced Java skills."
    res = validate_rewrite(original, rewritten)
    assert res["validation_status"] == "Failed"
    assert any(c.status == "Failed" for c in res["validation_checks"] if "Negation" in c.name)

def test_factguard_c():
    original = "The candidate has 3 years of experience."
    rewritten = "The candidate has 5 years of experience."
    res = validate_rewrite(original, rewritten)
    assert res["validation_status"] == "Failed"
    assert any(c.status == "Failed" for c in res["validation_checks"] if "Number" in c.name)

def test_factguard_d():
    original = "The interview was on 12 March 2026."
    rewritten = "The interview was on 15 March 2026."
    res = validate_rewrite(original, rewritten)
    assert res["validation_status"] == "Failed"
    assert any(c.status == "Failed" for c in res["validation_checks"] if "Date" in c.name)

def test_factguard_e():
    original = "The candidate has not yet demonstrated leadership skills."
    rewritten = "The candidate has demonstrated leadership skills."
    res = validate_rewrite(original, rewritten)
    assert res["validation_status"] == "Failed"
    assert any(c.status == "Failed" for c in res["validation_checks"] if "Negation" in c.name)

def test_factguard_f():
    original = "The candidate answered two questions correctly."
    rewritten = "The candidate answered all questions correctly."
    res = validate_rewrite(original, rewritten)
    assert res["validation_status"] == "Failed"
    assert any(c.status == "Failed" for c in res["validation_checks"] if "Number" in c.name)

def test_extraction_limitations():
    # Demonstrating the limitation that regex cannot easily extract names or claims
    original = "Riya scored 85% in Python and may improve her SQL skills."
    ledger = extract_fact_ledger(original)
    assert "85%" in ledger.numbers
    assert "may" in ledger.uncertainty
    # Regex fails to extract these, showing the limitation of the heuristic approach
    assert len(ledger.names) == 0
    assert len(ledger.technical_terms) == 0
