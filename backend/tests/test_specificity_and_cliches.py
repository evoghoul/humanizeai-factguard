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

def test_intent_preservation_interview_question():
    """
    Test 3 Failure Fix: An open-ended interview question must NOT be rewritten into declarative advice.
    """
    original_q = "How would you design a distributed cache using SQLite or PostgreSQL that guarantees zero unplanned downtime and handles failover within a 3-minute window?"
    
    # Declarative advice rewrite (Intent Drift Failure)
    bad_declarative_rewrite = "To build a high-performance distributed cache, use SQLite or PostgreSQL with automated replication to ensure zero unplanned downtime and maintain failover in a 3-minute window."
    
    # Open-ended question rewrite (Preserved Intent)
    good_question_rewrite = "If you had to architect a distributed cache using SQLite or PostgreSQL, how would you deliver zero unplanned downtime while completing failover within a 3-minute window?"
    
    fg_bad = factguard_check(original_q, bad_declarative_rewrite)
    assert fg_bad["needs_review"]
    assert any("Intent drift" in w for w in fg_bad["warnings"])
    
    fg_good = factguard_check(original_q, good_question_rewrite)
    assert not fg_good["needs_review"], f"Valid question flagged unexpectedly: {fg_good['warnings']}"

def test_timeline_boundary_and_deadline_preservation():
    """
    Timeline Distortion & Deadline Alteration Fix:
    - 'August 1 to September 30' must not become 'since August 1'.
    - '48 hours' must not become 'by tomorrow evening'.
    """
    original_report = (
        "From August 1 to September 30, the incident response team resolved 14 critical alerts. "
        "Candidates must complete the technical evaluation within 48 hours."
    )
    
    # Distorted rewrite (Timeline summarized & Deadline altered)
    bad_distorted_rewrite = (
        "Since August 1, our incident response crew resolved 14 critical alerts. "
        "Candidates should complete the evaluation by tomorrow evening."
    )
    
    # Accurate rewrite (Exact boundaries and deadlines locked)
    good_accurate_rewrite = (
        "Between August 1 and September 30, our incident response crew resolved 14 critical alerts. "
        "Candidates must finish the technical evaluation within 48 hours."
    )
    
    fg_bad = factguard_check(original_report, bad_distorted_rewrite)
    assert fg_bad["needs_review"]
    assert any("Timeline distortion" in w for w in fg_bad["warnings"])
    assert any("Deadline alteration" in w or "48 hours" in w for w in fg_bad["warnings"])
    
    fg_good = factguard_check(original_report, good_accurate_rewrite)
    assert not fg_good["needs_review"], f"Accurate rewrite flagged unexpectedly: {fg_good['warnings']}"

def test_creative_override_apex_holdings_hallucination():
    """
    Creative Override Fix: The model must NEVER invent company names like 'Apex Holdings'
    to make text sound more natural.
    """
    original_text = "Please submit your verified performance metrics before the final onboarding review."
    
    # Model hallucinated 'Apex Holdings'
    hallucinated_text = "At Apex Holdings, please submit your verified performance metrics before the final onboarding review."
    
    fg = factguard_check(original_text, hallucinated_text)
    assert fg["needs_review"]
    assert any("Apex Holdings" in w or "hallucinated" in w for w in fg["warnings"])

if __name__ == "__main__":
    test_paragraph_b_entity_and_metric_retention()
    test_paragraph_a_hallucination_and_cliche_detection()
    test_intent_preservation_interview_question()
    test_timeline_boundary_and_deadline_preservation()
    test_creative_override_apex_holdings_hallucination()
    print("All prompt architecture tests passed successfully!")
