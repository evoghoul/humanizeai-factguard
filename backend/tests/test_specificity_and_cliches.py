import pytest
from app.services.validation import validate_rewrite
from app.services.extraction import extract_fact_ledger
from factguard import factguard_check, check_named_entities, check_numbers, check_years_and_timelines, check_ai_cliches, check_hallucinations

def test_paragraph_b_entity_and_metric_retention():
    """
    Paragraph B: concrete entities (Starlight Therapeutics), exact metrics (£450 daily savings),
    and specific timelines (two weeks).
    """
    original_b = (
        "At Starlight Therapeutics, shifting research staff to remote workflows generated £450 daily savings "
        "over a two-week pilot, while enhancing trial documentation output."
    )
    
    # Successful rewrite preserving entities and metrics
    good_rewrite_b = (
        "Switching researchers to remote setups saved Starlight Therapeutics £450 every single day during their "
        "two-week pilot. Beyond cutting expenses, team members turned around trial logs much faster."
    )
    
    # Bad rewrite that erased Starlight Therapeutics and generalized £450 to empty corporate filler
    bad_rewrite_b = (
        "Transitioning to digital landscapes enabled the enterprise to delve into substantial cost reductions "
        "across several weeks, fostering a rich tapestry of dynamic synergies."
    )
    
    # 1. Good rewrite should pass FactGuard
    fg_good = factguard_check(original_b, good_rewrite_b)
    assert not fg_good["needs_review"], f"Good rewrite flagged unexpectedly: {fg_good['warnings']}"
    
    val_good = validate_rewrite(original_b, good_rewrite_b)
    assert val_good["validation_status"] == "Partial", f"Validation status failed: {val_good['detected_issues']}"
    assert len(val_good["detected_issues"]) == 0
    
    # 2. Bad rewrite should be severely flagged for entity omission, metric omission, and AI clichés
    fg_bad = factguard_check(original_b, bad_rewrite_b)
    assert fg_bad["needs_review"]
    assert any("Starlight Therapeutics" in w for w in fg_bad["warnings"])
    assert any("450" in w for w in fg_bad["warnings"])
    assert any("cliché" in w or "buzzword" in w for w in fg_bad["warnings"])

def test_paragraph_a_hallucination_and_cliche_detection():
    """
    Paragraph A: abstract buzzwords. If a rewrite hallucinates fake companies or retains clichés,
    FactGuard must catch it.
    """
    original_a = (
        "In today's evolving digital landscape, organizations must delve into dynamic synergies "
        "and foster a rich tapestry of holistic paradigm shifts to unlock continuous innovation."
    )
    
    # Good rewrite: cleaned of buzzwords, zero fake entities hallucinated
    good_rewrite_a = (
        "Companies that want steady progress need to fix how their teams coordinate day-to-day. "
        "That means communicating clearly, cutting red tape, and trying new approaches without overthinking."
    )
    
    # Bad rewrite 1: retains clichés
    bad_cliche_rewrite = (
        "Teams must embrace a rich tapestry of dynamic synergies to navigate the modern paradigm shift."
    )
    
    # Bad rewrite 2: hallucinates fake specific company where none existed
    bad_hallucinated_rewrite = (
        "At Apex BioLabs, leadership saved $500,000 across twelve months through improved collaboration."
    )
    
    fg_good = factguard_check(original_a, good_rewrite_a)
    assert not fg_good["needs_review"], f"Good rewrite failed: {fg_good['warnings']}"
    
    fg_cliche = factguard_check(original_a, bad_cliche_rewrite)
    assert fg_cliche["needs_review"]
    assert any("cliché" in w for w in fg_cliche["warnings"])
    
    fg_hallucinated = factguard_check(original_a, bad_hallucinated_rewrite)
    assert fg_hallucinated["needs_review"]
    assert any("hallucinated" in w or "Apex BioLabs" in w or "500,000" in w for w in fg_hallucinated["warnings"])

if __name__ == "__main__":
    test_paragraph_b_entity_and_metric_retention()
    test_paragraph_a_hallucination_and_cliche_detection()
    print("All diagnostic tests passed successfully!")
