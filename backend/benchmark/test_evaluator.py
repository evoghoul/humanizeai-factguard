"""Mutation tests and verification suite for the factual benchmark evaluator.

Tests the 10 required evaluator behaviors:
1. Unchanged source text passes.
2. A changed monetary value fails.
3. A missing negation fails.
4. Swapped financial-period attribution fails.
5. A missing date or altered range fails.
6. An unexpected protected value is reported.
7. A valid paraphrase passes when specified facts and relationships remain intact.
8. Formatting collapse is detected for a structured email.
9. An unverifiable relationship is reported as UNCERTAIN / NOT_CHECKED rather than passed.
10. Critical failures cannot be masked by a high overall score.
"""

import json
from pathlib import Path
import pytest

import sys
try:
    from benchmark.evaluator import (
        EvaluationReport,
        EvaluationStatus,
        FactualBenchmarkEvaluator,
        Severity,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from benchmark.evaluator import (
        EvaluationReport,
        EvaluationStatus,
        FactualBenchmarkEvaluator,
        Severity,
    )


@pytest.fixture
def cases():
    cases_file = Path(__file__).parent / "cases.json"
    with open(cases_file, "r", encoding="utf-8") as f:
        case_list = json.load(f)
    return {c["id"]: c for c in case_list}


@pytest.fixture
def evaluator():
    return FactualBenchmarkEvaluator()


def test_unchanged_source_text_passes(cases, evaluator):
    """1. Unchanged source text must pass with 100% score and 0 critical failures."""
    case = cases["fin_01_swapped_quarterly_revenue"]
    source = case["fixtures"]["unchanged"]
    
    report: EvaluationReport = evaluator.evaluate(case, source)
    
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert report.critical_failure_count == 0
    assert report.warning_count == 0
    assert report.score == 100.0
    assert len(report.missing_values) == 0


def test_changed_monetary_value_fails(cases, evaluator):
    """2. A changed monetary value ($4.5M instead of $4.2M) must trigger a hard FAIL."""
    case = cases["fin_01_swapped_quarterly_revenue"]
    mutated = case["fixtures"]["mutations"]["changed_monetary_value"]
    
    report: EvaluationReport = evaluator.evaluate(case, mutated)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert "$4.2M" in report.missing_values
    assert report.critical_failure_count >= 1


def test_missing_negation_fails(cases, evaluator):
    """3. A dropped or affirmative negation ('exceeded' instead of 'did not exceed') must trigger a hard FAIL."""
    case = cases["fin_01_swapped_quarterly_revenue"]
    mutated = case["fixtures"]["mutations"]["missing_negation"]
    
    report: EvaluationReport = evaluator.evaluate(case, mutated)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert "exceed" in report.failed_negations
    assert report.critical_failure_count >= 1
    # Confirm a check result exists specifically for the negation failure
    neg_checks = [c for c in report.checks if c.category == "negations"]
    assert any(c.status == EvaluationStatus.FAIL for c in neg_checks)


def test_swapped_financial_period_attribution_fails(cases, evaluator):
    """4. Swapped attribution ($5.1M in Q2 and $4.2M in Q3) must fail even though all numbers exist."""
    case = cases["fin_01_swapped_quarterly_revenue"]
    mutated = case["fixtures"]["mutations"]["swapped_attribution"]
    
    # Crucial test: both $4.2M and $5.1M exist in the mutated text!
    # A naive co-occurrence check would falsely pass this.
    report: EvaluationReport = evaluator.evaluate(case, mutated)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert len(report.failed_relations) >= 1
    assert any(fr["issue"] == "swapped_attribution" for fr in report.failed_relations)
    assert report.critical_failure_count >= 1


def test_missing_date_or_altered_range_fails(cases, evaluator):
    """5. Altering a closed range to open-ended ('since Aug 1') or missing a date boundary must fail."""
    case = cases["timeline_01_closed_range_audit"]
    
    # 5a. Closed range altered to open-ended 'since August 1'
    altered = case["fixtures"]["mutations"]["altered_range_open_ended"]
    report_altered: EvaluationReport = evaluator.evaluate(case, altered)
    assert report_altered.overall_status == EvaluationStatus.FAIL
    assert report_altered.passed is False
    assert "August 1 to September 30" in report_altered.altered_values
    assert report_altered.critical_failure_count >= 1

    # 5b. Missing date boundary (missing start date)
    missing = case["fixtures"]["mutations"]["missing_date_boundary"]
    report_missing: EvaluationReport = evaluator.evaluate(case, missing)
    assert report_missing.overall_status == EvaluationStatus.FAIL
    assert report_missing.passed is False
    assert "August 1 to September 30" in report_missing.missing_values
    assert report_missing.critical_failure_count >= 1


def test_unexpected_protected_value_reported(cases, evaluator):
    """6. An unexpected ungrounded financial value ($9.9M) must be reported under unexpected_values."""
    case = cases["fin_01_swapped_quarterly_revenue"]
    mutated = case["fixtures"]["mutations"]["unexpected_value"]
    
    report: EvaluationReport = evaluator.evaluate(case, mutated)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert "$9.9M" in report.unexpected_values
    assert any(c.category == "unexpected_values" and c.status == EvaluationStatus.FAIL for c in report.checks)


def test_valid_paraphrase_passes(cases, evaluator):
    """7. A legitimate paraphrase retaining all metrics, periods, relations, and negations must PASS."""
    case = cases["fin_01_swapped_quarterly_revenue"]
    paraphrase = case["fixtures"]["valid_paraphrase"]
    
    report: EvaluationReport = evaluator.evaluate(case, paraphrase)
    
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert report.critical_failure_count == 0
    assert len(report.missing_values) == 0
    assert len(report.failed_relations) == 0
    assert len(report.failed_negations) == 0


def test_formatting_collapse_detected_for_structured_email(cases, evaluator):
    """8. Collapsing email paragraph breaks or stripping greeting/signoff must trigger formatting failures."""
    case = cases["email_01_executive_escalation"]
    
    # 8a. Collapsed paragraphs (all line breaks removed into a single block)
    collapsed = case["fixtures"]["mutations"]["collapsed_formatting"]
    report_col: EvaluationReport = evaluator.evaluate(case, collapsed)
    assert report_col.overall_status == EvaluationStatus.FAIL
    assert "collapsed_paragraphs" in report_col.formatting_issues

    # 8b. Stripped salutation and sign-off
    stripped = case["fixtures"]["mutations"]["stripped_salutation_and_signoff"]
    report_str: EvaluationReport = evaluator.evaluate(case, stripped)
    assert report_str.overall_status == EvaluationStatus.FAIL
    assert "missing_greeting" in report_str.formatting_issues
    assert "missing_signoff" in report_str.formatting_issues


def test_unverifiable_relationship_reported_as_uncertain(cases, evaluator):
    """9. Relationships that cannot be deterministically verified offline must report UNCERTAIN, never PASS."""
    case = cases["spec_01_unverifiable_complex_clause"]
    unverifiable = case["fixtures"]["unverifiable_syntax"]
    
    report: EvaluationReport = evaluator.evaluate(case, unverifiable)
    
    # CRITICAL: An unverifiable relationship must NOT be reported as PASS!
    assert report.overall_status == EvaluationStatus.UNCERTAIN
    assert report.passed is False
    assert len(report.uncertain_relations) >= 1
    assert any(c.status == EvaluationStatus.UNCERTAIN for c in report.checks)


def test_critical_failure_cannot_be_masked_by_high_overall_score(cases, evaluator):
    """10. A single fatal error (50mg altered to 500mg) must override a high overall score (83%+)."""
    case = cases["clinical_01_dosage_score_masking"]
    corrupted = case["fixtures"]["mutations"]["fatal_dosage_corruption"]
    
    report: EvaluationReport = evaluator.evaluate(case, corrupted)
    
    # 5 out of 6 items passed (83.3% retention score), but 50mg is corrupted to 500mg
    assert report.score >= 80.0
    assert "50mg" in report.missing_values
    assert report.critical_failure_count == 1
    # HARD FAILURE GATE:
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert "HARD FAILURE" in report.summary


# ---------------------------------------------------------------------------
# Directional Claims & Modality Regression / Adversarial Tests
# ---------------------------------------------------------------------------

def test_directional_grew_to_dropped_fails(cases, evaluator):
    """Directional reversal 'grew' -> 'dropped' must trigger hard FAIL."""
    case = cases["fin_02_directional_revenue_growth"]
    corrupted = case["fixtures"]["mutations"]["grew_to_dropped"]
    
    report: EvaluationReport = evaluator.evaluate(case, corrupted)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert len(report.failed_directional) >= 1
    assert any(fd["issue"] == "reversed_direction" for fd in report.failed_directional)
    assert report.critical_failure_count >= 1


def test_directional_increased_to_decreased_fails(cases, evaluator):
    """Directional reversal 'increased' -> 'decreased' must trigger hard FAIL."""
    case = cases["fin_02_directional_revenue_growth"]
    corrupted = case["fixtures"]["mutations"]["increased_to_decreased"]
    
    report: EvaluationReport = evaluator.evaluate(case, corrupted)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert len(report.failed_directional) >= 1
    assert any(fd["issue"] == "reversed_direction" for fd in report.failed_directional)
    assert report.critical_failure_count >= 1


def test_directional_unchanged_passes(cases, evaluator):
    """Unchanged directional claim ('grew' by 15%, 'increased' by 4%) must PASS."""
    case = cases["fin_02_directional_revenue_growth"]
    source = case["fixtures"]["unchanged"]
    
    report: EvaluationReport = evaluator.evaluate(case, source)
    
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_directional) == 0
    assert report.critical_failure_count == 0


def test_directional_unrelated_opposite_clause_passes(cases, evaluator):
    """Opposite directional word ('dropped') in an unrelated clause must NOT trigger false positive."""
    case = cases["fin_02_directional_revenue_growth"]
    unrelated_opposite = case["fixtures"]["adversarial_passes"]["unrelated_opposite_clause"]
    
    report: EvaluationReport = evaluator.evaluate(case, unrelated_opposite)
    
    # Revenue grew and expenses increased in their clauses, so the claim passes
    # despite 'dropped' appearing in the unrelated marketing clause
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_directional) == 0


def test_directional_valid_paraphrase_passes(cases, evaluator):
    """Valid paraphrase ('expanded 15%', 'climbed 4%') must PASS."""
    case = cases["fin_02_directional_revenue_growth"]
    paraphrase = case["fixtures"]["valid_paraphrase"]
    
    report: EvaluationReport = evaluator.evaluate(case, paraphrase)
    
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_directional) == 0



def test_directional_unverifiable_returns_uncertain(cases, evaluator):
    """Directional claim with omitted directional predicate must return UNCERTAIN, never PASS."""
    case = cases["fin_02_directional_revenue_growth"]
    unverifiable = case["fixtures"]["unverifiable_syntax"]
    
    report: EvaluationReport = evaluator.evaluate(case, unverifiable)
    
    assert report.overall_status == EvaluationStatus.UNCERTAIN
    assert report.passed is False
    assert len(report.uncertain_directional) >= 1


def test_modality_may_to_must_fails(cases, evaluator):
    """Modality shift from possibility ('may') to obligation ('must') must trigger hard FAIL."""
    case = cases["policy_02_approval_and_compliance_modality"]
    corrupted = case["fixtures"]["mutations"]["may_to_must"]
    
    report: EvaluationReport = evaluator.evaluate(case, corrupted)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert len(report.failed_modality) >= 1
    assert any(fm["issue"] == "modality_shift" for fm in report.failed_modality)
    assert report.critical_failure_count >= 1


def test_modality_must_to_may_fails(cases, evaluator):
    """Modality shift from obligation ('must') to possibility ('may') must trigger hard FAIL."""
    case = cases["policy_02_approval_and_compliance_modality"]
    corrupted = case["fixtures"]["mutations"]["must_to_may"]
    
    report: EvaluationReport = evaluator.evaluate(case, corrupted)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert len(report.failed_modality) >= 1
    assert any(fm["issue"] == "modality_shift" for fm in report.failed_modality)
    assert report.critical_failure_count >= 1


def test_modality_unchanged_passes(cases, evaluator):
    """Unchanged modality conditions ('may approve', 'must complete') must PASS."""
    case = cases["policy_02_approval_and_compliance_modality"]
    source = case["fixtures"]["unchanged"]
    
    report: EvaluationReport = evaluator.evaluate(case, source)
    
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_modality) == 0
    assert report.critical_failure_count == 0


def test_modality_unrelated_opposite_clause_passes(cases, evaluator):
    """Opposite modal ('must') in an unrelated clause must NOT trigger false positive on 'may approve'."""
    case = cases["policy_02_approval_and_compliance_modality"]
    unrelated_opposite = case["fixtures"]["adversarial_passes"]["unrelated_opposite_clause"]
    
    report: EvaluationReport = evaluator.evaluate(case, unrelated_opposite)
    
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_modality) == 0


def test_modality_valid_paraphrase_passes(cases, evaluator):
    """Valid paraphrase ('permitted to approve', 'required to complete') must PASS."""
    case = cases["policy_02_approval_and_compliance_modality"]
    paraphrase = case["fixtures"]["valid_paraphrase"]
    
    report: EvaluationReport = evaluator.evaluate(case, paraphrase)
    
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_modality) == 0



def test_modality_unverifiable_returns_uncertain(cases, evaluator):
    """Unmodalized indicative statement omitting auxiliary modals must report UNCERTAIN, never PASS."""
    case = cases["policy_02_approval_and_compliance_modality"]
    unverifiable = case["fixtures"]["unverifiable_syntax"]
    
    report: EvaluationReport = evaluator.evaluate(case, unverifiable)
    
    assert report.overall_status == EvaluationStatus.UNCERTAIN
    assert report.passed is False
    assert len(report.uncertain_modality) >= 1


def test_semantic_reversal_cannot_be_offset_by_aggregate_score(cases, evaluator):
    """A critical directional reversal must force overall FAIL even when 85%+ of checks pass."""
    case = cases["fin_02_directional_revenue_growth"]
    corrupted = case["fixtures"]["mutations"]["grew_to_dropped"]
    
    report: EvaluationReport = evaluator.evaluate(case, corrupted)
    
    # Values ($5.1M, 15%, 4%, Q3 2025) and relations still pass, giving a high retention percentage
    assert report.score >= 80.0
    # HARD FAILURE GATE:
    assert report.critical_failure_count >= 1
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert "HARD FAILURE" in report.summary


def test_directional_opposite_in_prior_sentence_passes(cases, evaluator):
    """An opposite word in a prior sentence must NOT trigger a false positive on Q3 revenue."""
    case = cases["fin_02_directional_revenue_growth"]
    multi_sentence = (
        "In Q1, sales dropped sharply across all regions. However, in Q3 2025, "
        "CloudOps revenue grew by 15% to $5.1M, whereas operating expenses increased by 4%."
    )
    report = evaluator.evaluate(case, multi_sentence)
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_directional) == 0


def test_modality_opposite_in_prior_sentence_passes(cases, evaluator):
    """An obligation modal ('must') in a preceding sentence must NOT pollute 'may approve'."""
    case = cases["policy_02_approval_and_compliance_modality"]
    multi_sentence = (
        "All employees must observe code of conduct rules. The review committee "
        "may approve the extension request, but all contractors must complete security training by Friday."
    )
    report = evaluator.evaluate(case, multi_sentence)
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_modality) == 0


# ===========================================================================
# Targeted Adversarial Test Gate: Categories 1, 2, 3
# ===========================================================================

# --- Category 1: Direction and Negation ---

def test_directional_expected_increase_grew_passes(cases, evaluator):
    """1a. Expected increase: 'Revenue grew by 15%' -> PASS."""
    case = cases["fin_02_directional_revenue_growth"]
    text = "In Q3 2025, CloudOps revenue grew by 15% to $5.1M, whereas operating expenses increased by 4%."
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_directional) == 0


def test_directional_expected_increase_dropped_fails(cases, evaluator):
    """1b. Expected increase: 'Revenue dropped by 15%' -> hard FAIL."""
    case = cases["fin_02_directional_revenue_growth"]
    text = "In Q3 2025, CloudOps revenue dropped by 15% to $5.1M, whereas operating expenses increased by 4%."
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert any(fd["issue"] == "reversed_direction" for fd in report.failed_directional)


def test_directional_expected_increase_did_not_grow_fails(cases, evaluator):
    """1c. Expected increase: 'Revenue did not grow by 15%' -> must NOT pass (hard FAIL)."""
    case = cases["fin_02_directional_revenue_growth"]
    text = "In Q3 2025, CloudOps revenue did not grow by 15% to $5.1M, whereas operating expenses increased by 4%."
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert report.critical_failure_count >= 1
    assert any(fd["issue"] == "negated_direction" for fd in report.failed_directional)


def test_directional_expected_increase_did_not_decline_returns_uncertain(cases, evaluator):
    """1d. Expected increase: 'Revenue did not decline by 15%' -> UNCERTAIN (cannot safely establish increase)."""
    case = cases["fin_02_directional_revenue_growth"]
    text = "In Q3 2025, CloudOps revenue did not decline by 15% to $5.1M, whereas operating expenses increased by 4%."
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.UNCERTAIN
    assert report.passed is False
    assert len(report.uncertain_directional) >= 1


def test_directional_negation_separated_by_intervening_words_fails(cases, evaluator):
    """1e. Negation separated from directional verb by intervening adverbs must NOT pass (hard FAIL)."""
    case = cases["fin_02_directional_revenue_growth"]
    
    # Intervening adverb: 'did not in fact grow'
    text1 = "In Q3 2025, CloudOps revenue did not in fact grow by 15% to $5.1M, whereas operating expenses increased by 4%."
    report1 = evaluator.evaluate(case, text1)
    assert report1.overall_status == EvaluationStatus.FAIL
    assert report1.passed is False

    # Intervening adverb: 'certainly did not grow'
    text2 = "In Q3 2025, CloudOps revenue certainly did not grow by 15% to $5.1M, whereas operating expenses increased by 4%."
    report2 = evaluator.evaluate(case, text2)
    assert report2.overall_status == EvaluationStatus.FAIL
    assert report2.passed is False

    # Intervening words: 'did not at all increase'
    text3 = "In Q3 2025, CloudOps revenue did not at all increase by 15% to $5.1M, whereas operating expenses increased by 4%."
    report3 = evaluator.evaluate(case, text3)
    assert report3.overall_status == EvaluationStatus.FAIL
    assert report3.passed is False


# --- Category 2: Modality Attachment ---

def test_modality_committee_may_approve_passes(cases, evaluator):
    """2a. 'The committee may approve the request' -> PASS for required possibility."""
    case = cases["policy_02_approval_and_compliance_modality"]
    text = "The review committee may approve the extension request, but all contractors must complete security training by Friday."
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_modality) == 0


def test_modality_committee_must_approve_fails(cases, evaluator):
    """2b. 'The committee must approve the request' -> hard FAIL for required possibility."""
    case = cases["policy_02_approval_and_compliance_modality"]
    text = "The review committee must approve the extension request, but all contractors must complete security training by Friday."
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert any(fm["issue"] == "modality_shift" for fm in report.failed_modality)


def test_modality_modal_in_adjacent_clause_governing_different_action_passes(cases, evaluator):
    """2c. 'must' occurs in adjacent clause governing another action; target 'may approve' must still PASS."""
    case = cases["policy_02_approval_and_compliance_modality"]
    # 'must' governs 'review logs', while 'may' governs 'approve'
    text = "Although the executive board must review all logs, the review committee may approve the extension request by Friday, but contractors must complete training."
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_modality) == 0


def test_modality_modal_near_target_verb_governing_different_action_detects_shift_fails(cases, evaluator):
    """2d. 'may' occurs near target verb but governs different action while 'must' governs target verb -> hard FAIL."""
    case = cases["policy_02_approval_and_compliance_modality"]
    # 'may' governs 'review notes', but 'must' governs 'approve'
    text = "Although the review committee may review preliminary notes, they must approve the extension request by Friday, while contractors must complete training."
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert any(fm["issue"] == "modality_shift" for fm in report.failed_modality)


def test_modality_short_inverted_question_fails_on_obligation(cases, evaluator):
    """2e. Short inverted question with obligation modal 'Must the committee approve' -> hard FAIL."""
    case = cases["policy_02_approval_and_compliance_modality"]
    text = "Must the review committee approve the extension request? Contractors must complete security training by Friday."
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert any(fm["issue"] == "modality_shift" for fm in report.failed_modality)


def test_modality_long_intervening_clause_returns_uncertain(cases, evaluator):
    """2f. Indicative past tense with long intervening parenthetical clause -> UNCERTAIN (refuses false pass)."""
    case = cases["policy_02_approval_and_compliance_modality"]
    text = (
        "The review committee, having reviewed the statutory documentation over several days "
        "and consulting with external advisors, approved the extension request by Friday. "
        "Contractors must complete security training by Friday."
    )
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.UNCERTAIN
    assert report.passed is False
    assert len(report.uncertain_modality) >= 1


def test_modality_distant_inverted_question_returns_uncertain(cases, evaluator):
    """2g. Inverted modal separated by >70 chars of complex NP cannot be safely bound -> UNCERTAIN."""
    case = cases["policy_02_approval_and_compliance_modality"]
    text = (
        "May all senior members of the newly appointed special investigative review committee "
        "formally deliberate and approve the extension request by Friday? "
        "Contractors must complete security training by Friday."
    )
    report = evaluator.evaluate(case, text)
    # The modal 'May' is separated from 'approve' by long intervening clauses (>70 chars),
    # so deterministic local window cannot prove binding -> UNCERTAIN rather than unsupported PASS.
    assert report.overall_status == EvaluationStatus.UNCERTAIN
    assert report.passed is False


# --- Category 3: Repeated Subjects and Metrics ---

def test_directional_conflicting_clauses_cannot_be_hidden_by_first_clause_fails(cases, evaluator):
    """3a. Contradictory claim ('dropped by 15%') in later clause cannot be hidden by earlier 'grew by 15%' clause -> hard FAIL."""
    case = cases["fin_02_directional_revenue_growth"]
    text = (
        "In Q3 2025, CloudOps revenue grew by 15% to $5.1M, whereas operating expenses increased by 4%, "
        "but revised audit statements confirmed CloudOps revenue dropped by 15%."
    )
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert any(fd["issue"] == "reversed_direction" for fd in report.failed_directional)
    assert report.critical_failure_count >= 1


def test_directional_conflicting_clauses_reverse_order_fails(cases, evaluator):
    """3b. First clause says 'dropped by 15%', second says 'grew by 15%' -> hard FAIL."""
    case = cases["fin_02_directional_revenue_growth"]
    text = (
        "In Q3 2025, CloudOps revenue dropped by 15% to $5.1M, whereas operating expenses increased by 4%, "
        "although initial unverified drafts claimed CloudOps revenue grew by 15%."
    )
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert any(fd["issue"] == "reversed_direction" for fd in report.failed_directional)
    assert report.critical_failure_count >= 1


def test_directional_unrelated_opposite_claim_does_not_cause_false_failure(cases, evaluator):
    """3c. Opposite direction word in unrelated metric clause must NOT cause false failure on revenue."""
    case = cases["fin_02_directional_revenue_growth"]
    text = (
        "In Q3 2025, CloudOps revenue grew by 15% to $5.1M, whereas operating expenses increased by 4%, "
        "although international marketing spend dropped by 5%."
    )
    report = evaluator.evaluate(case, text)
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.failed_directional) == 0


# =============================================================================
# Expanded 50-Case Benchmark Suite Verification
# =============================================================================

def test_50_cases_coverage_and_distribution(cases):
    """Verifies that exactly 50 cases exist across the 6 specified categories."""
    assert len(cases) == 50, f"Expected 50 cases, found {len(cases)}"
    
    cat_counts = {}
    for c in cases.values():
        cat = c.get("category")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    expected_counts = {
        "numerical_financial": 10,
        "dates_timelines": 8,
        "negation_modality": 8,
        "names_technical_terms": 7,
        "relational_directional": 7,
        "document_structure_intent": 10,
    }
    assert cat_counts == expected_counts, f"Category distribution mismatch: {cat_counts}"

    # Verify every case has required fields and unique purpose
    for cid, case in cases.items():
        assert "source_text" in case
        assert "fixtures" in case
        assert "invariant_description" in case
        assert case["id"] == cid
        assert "unchanged" in case["fixtures"]


def test_all_unchanged_fixtures_pass_or_uncertain(cases, evaluator):
    """Verifies that unchanged source text passes for all 50 cases (or UNCERTAIN if unverifiable)."""
    for cid, case in cases.items():
        unchanged = case["fixtures"]["unchanged"]
        report = evaluator.evaluate(case, unchanged)
        has_unverifiable = any(not r.get("verifiable_offline", True) for r in case.get("required_relations", []))
        expected_status = EvaluationStatus.UNCERTAIN if has_unverifiable else EvaluationStatus.PASS
        assert report.overall_status == expected_status, f"Case {cid} unchanged fixture failed: got {report.overall_status}, expected {expected_status}"


def test_all_valid_paraphrases_pass(cases, evaluator):
    """Verifies that all valid paraphrases pass across all cases that define one (no false rejections)."""
    for cid, case in cases.items():
        para = case["fixtures"].get("valid_paraphrase")
        if para:
            report = evaluator.evaluate(case, para)
            assert report.passed is True, f"Valid paraphrase incorrectly rejected for {cid}: score {report.score}%, status {report.overall_status}"


def test_all_mutations_caught_across_50_cases(cases, evaluator):
    """Verifies that every intentionally corrupted mutation is caught (fails or uncertain)."""
    missed = []
    for cid, case in cases.items():
        mutations = case["fixtures"].get("mutations", {})
        for mname, mtext in mutations.items():
            report = evaluator.evaluate(case, mtext)
            if report.passed:
                missed.append((cid, mname, report.score))
    assert len(missed) == 0, f"Missed mutations (false passes): {missed}"


def test_category_1_numerical_and_currency_corruptions(cases, evaluator):
    """Category 1: tests scale shift, basis point shift, unit corruptions, and balance sheet swaps."""
    # Scale shift: $2.4B -> $2.4M
    case_scale = cases["fin_03_currency_scale_shift"]
    rep_scale = evaluator.evaluate(case_scale, case_scale["fixtures"]["mutations"]["scale_reduced_billion_to_million"])
    assert rep_scale.passed is False
    assert rep_scale.overall_status == EvaluationStatus.FAIL

    # Basis points: 5.25% -> 5.75%
    case_rate = cases["fin_04_interest_rate_percentage_shift"]
    rep_rate = evaluator.evaluate(case_rate, case_rate["fixtures"]["mutations"]["rate_shifted_by_fifty_bps"])
    assert rep_rate.passed is False

    # Unit corruption: 750kg -> 750g
    case_unit = cases["fin_05_unit_conversion_corruption"]
    rep_unit = evaluator.evaluate(case_unit, case_unit["fixtures"]["mutations"]["unit_corrupted_kg_to_g"])
    assert rep_unit.passed is False

    # Swapped figures: $84.2M assets vs $51.6M liabilities
    case_bal = cases["fin_07_swapped_balance_sheet_figures"]
    rep_bal = evaluator.evaluate(case_bal, case_bal["fixtures"]["mutations"]["swapped_assets_and_liabilities"])
    assert rep_bal.passed is False
    assert any(fr["issue"] == "swapped_attribution" for fr in rep_bal.failed_relations)


def test_category_2_timeline_order_and_deadline_shifts(cases, evaluator):
    """Category 2: tests deadline shifts, open-ended range distortions, and sequence order inversion."""
    # Deadline shift
    case_dl = cases["timeline_02_deadline_day_shift"]
    rep_dl = evaluator.evaluate(case_dl, case_dl["fixtures"]["mutations"]["deadline_delayed_by_one_week"])
    assert rep_dl.passed is False

    # Open-ended distortion
    case_open = cases["timeline_04_open_ended_distortion"]
    rep_open = evaluator.evaluate(case_open, case_open["fixtures"]["mutations"]["end_date_omitted_open_ended"])
    assert rep_open.passed is False

    # Inverted sequence: Phase 1/Phase 2
    case_seq = cases["timeline_07_sequence_order_inversion"]
    rep_seq = evaluator.evaluate(case_seq, case_seq["fixtures"]["mutations"]["inverted_chronological_phases"])
    assert rep_seq.passed is False
    assert any(fr["issue"] == "swapped_attribution" for fr in rep_seq.failed_relations)


def test_category_3_negation_and_modality_shifts(cases, evaluator):
    """Category 3: tests removed liability negation and obligation-to-possibility downgrades."""
    # Removed negation
    case_neg = cases["neg_01_removed_negation_liability"]
    rep_neg = evaluator.evaluate(case_neg, case_neg["fixtures"]["mutations"]["removed_negation_assuming_liability"])
    assert rep_neg.passed is False
    assert any(fn == "liability" for fn in rep_neg.failed_negations)

    # Modality downgrade: must encrypt -> may encrypt
    case_mod = cases["mod_01_obligation_to_possibility_downgrade"]
    rep_mod = evaluator.evaluate(case_mod, case_mod["fixtures"]["mutations"]["obligation_downgraded_to_may"])
    assert rep_mod.passed is False

    # Prohibition to permission flip
    case_prohib = cases["mod_02_prohibition_to_permission_flip"]
    rep_prohib = evaluator.evaluate(case_prohib, case_prohib["fixtures"]["mutations"]["prohibition_flipped_to_permitted"])
    assert rep_prohib.passed is False


def test_category_4_names_and_technical_terms(cases, evaluator):
    """Category 4: tests entity substitutions, acronym corruptions, and cloud service swaps."""
    # Drug substitution: Ibuprofen -> Acetaminophen
    case_pharma = cases["term_01_entity_substitution_pharma"]
    rep_pharma = evaluator.evaluate(case_pharma, case_pharma["fixtures"]["mutations"]["drug_substituted_acetaminophen"])
    assert rep_pharma.passed is False

    # Algorithm corruption: ECDSA -> RSA
    case_algo = cases["term_02_technical_acronym_corruption"]
    rep_algo = evaluator.evaluate(case_algo, case_algo["fixtures"]["mutations"]["algorithm_corrupted_to_rsa"])
    assert rep_algo.passed is False

    # Cloud service swap: DynamoDB -> Bigtable
    case_cloud = cases["term_05_cloud_service_name_swap"]
    rep_cloud = evaluator.evaluate(case_cloud, case_cloud["fixtures"]["mutations"]["service_swapped_to_bigtable"])
    assert rep_cloud.passed is False


def test_category_5_relational_and_directional_claims(cases, evaluator):
    """Category 5: tests cause/effect reversals and contradictory clauses."""
    # Causal role assignment swap
    case_cause = cases["rel_01_cause_and_effect_reversal"]
    rep_cause = evaluator.evaluate(case_cause, case_cause["fixtures"]["mutations"]["inverted_causal_direction"])
    assert rep_cause.passed is False

    # Contradictory clauses
    case_contra = cases["rel_03_conflicting_clauses_repeated_subject"]
    rep_contra = evaluator.evaluate(case_contra, case_contra["fixtures"]["mutations"]["conflicting_contradictory_clause"])
    assert rep_contra.passed is False


def test_category_6_document_structure_and_intent(cases, evaluator):
    """Category 6: tests markdown bullet collapse, heading omission, and intent shift."""
    # Bullet list collapse
    case_bullets = cases["struct_01_collapsed_markdown_bullets"]
    rep_bullets = evaluator.evaluate(case_bullets, case_bullets["fixtures"]["mutations"]["collapsed_bullets_into_prose"])
    assert rep_bullets.passed is False
    assert "collapsed_bullets" in rep_bullets.formatting_issues

    # Heading omission
    case_head = cases["struct_02_missing_section_heading"]
    rep_head = evaluator.evaluate(case_head, case_head["fixtures"]["mutations"]["heading_stripped_entirely"])
    assert rep_head.passed is False
    assert "missing_heading" in rep_head.formatting_issues

    # Request vs demand intent
    case_req = cases["struct_03_request_vs_assertion_intent"]
    rep_req = evaluator.evaluate(case_req, case_req["fixtures"]["mutations"]["request_coerced_into_demand"])
    assert rep_req.passed is False


# ---------------------------------------------------------------------------
# Task 2: Required-Heading Identity Adversarial Tests
# ---------------------------------------------------------------------------

def test_required_heading_identity_exact_preserved(cases, evaluator):
    """Case requiring '# Incident Root Cause Analysis' passes when exact heading is preserved."""
    case = cases["struct_02_missing_section_heading"]
    candidate = "# Incident Root Cause Analysis\n\nThe primary database failed due to disk exhaustion on volume /var/data at 04:15 UTC."
    
    report = evaluator.evaluate(case, candidate)
    
    assert report.overall_status == EvaluationStatus.PASS
    assert report.passed is True
    assert len(report.formatting_issues) == 0
    assert report.critical_failure_count == 0


def test_required_heading_identity_removed_fails(cases, evaluator):
    """Case requiring '# Incident Root Cause Analysis' fails when heading is removed entirely."""
    case = cases["struct_02_missing_section_heading"]
    candidate = "The primary database failed due to disk exhaustion on volume /var/data at 04:15 UTC."
    
    report = evaluator.evaluate(case, candidate)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert "incorrect_heading_identity" in report.formatting_issues
    assert "missing_heading" in report.formatting_issues
    assert report.critical_failure_count >= 1


def test_required_heading_identity_replaced_with_unrelated_heading_fails(cases, evaluator):
    """Case requiring '# Incident Root Cause Analysis' fails when replaced with '# Status'."""
    case = cases["struct_02_missing_section_heading"]
    candidate = "# Status\n\nThe primary database failed due to disk exhaustion on volume /var/data at 04:15 UTC."
    
    report = evaluator.evaluate(case, candidate)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert "incorrect_heading_identity" in report.formatting_issues
    # Note: A heading was present, but identity was wrong -> identity mismatch
    assert report.critical_failure_count >= 1


def test_required_heading_identity_unrelated_heading_elsewhere_fails(cases, evaluator):
    """Case requiring '# Incident Root Cause Analysis' fails when unrelated heading appears elsewhere."""
    case = cases["struct_02_missing_section_heading"]
    candidate = (
        "The primary database failed due to disk exhaustion on volume /var/data at 04:15 UTC.\n\n"
        "# Status\nAll operations suspended."
    )
    
    report = evaluator.evaluate(case, candidate)
    
    assert report.overall_status == EvaluationStatus.FAIL
    assert report.passed is False
    assert "incorrect_heading_identity" in report.formatting_issues
    assert report.critical_failure_count >= 1


def test_generic_heading_preservation_for_unspecified_heading(cases, evaluator):
    """Generic heading check remains functional for cases requiring only a heading of any kind."""
    case = cases["struct_07_executive_memo_formatting"]
    
    # 1. Memo prefix format passes
    memo_cand = (
        "MEMORANDUM:\n\n"
        "TO: Executive Committee\n"
        "FROM: Chief Risk Officer\n"
        "SUBJECT: Cyber Insurance Renewal\n\n"
        "Premiums increased by 14% across tier-1 carriers."
    )
    rep_memo = evaluator.evaluate(case, memo_cand)
    assert rep_memo.overall_status == EvaluationStatus.PASS
    assert rep_memo.passed is True
    heading_chk = next(c for c in rep_memo.checks if c.name == "Format: Document Heading")
    assert heading_chk.status == EvaluationStatus.PASS

    # 2. Markdown heading format passes
    md_cand = (
        "# Executive Memorandum\n\n"
        "TO: Executive Committee\n"
        "FROM: Chief Risk Officer\n"
        "SUBJECT: Cyber Insurance Renewal\n\n"
        "Premiums increased by 14% across tier-1 carriers."
    )
    rep_md = evaluator.evaluate(case, md_cand)
    assert rep_md.overall_status == EvaluationStatus.PASS
    assert rep_md.passed is True
    heading_chk = next(c for c in rep_md.checks if c.name == "Format: Document Heading")
    assert heading_chk.status == EvaluationStatus.PASS

    # 3. Heading omitted fails
    no_head = case["fixtures"]["mutations"]["memo_heading_omitted"]
    rep_no = evaluator.evaluate(case, no_head)
    assert rep_no.overall_status == EvaluationStatus.FAIL
    assert "missing_heading" in rep_no.formatting_issues


# ---------------------------------------------------------------------------
# Task 1 & 3: Reconciled Mutation Accounting & Benchmark Integrity
# ---------------------------------------------------------------------------

def test_reconciled_mutation_accounting_exact_counts(cases, evaluator):
    """Task 1: Verify separate counts for mutations returning FAIL, UNCERTAIN, and PASS."""
    mutations_failed = 0
    mutations_uncertain = 0
    mutations_passed = 0
    total_mutations = 0

    for cid, case in cases.items():
        mutations = case.get("fixtures", {}).get("mutations", {})
        for mname, mtext in mutations.items():
            total_mutations += 1
            rep = evaluator.evaluate(case, mtext)
            if rep.overall_status == EvaluationStatus.FAIL:
                mutations_failed += 1
            elif rep.overall_status == EvaluationStatus.UNCERTAIN:
                mutations_uncertain += 1
            elif rep.overall_status == EvaluationStatus.PASS:
                mutations_passed += 1

    assert total_mutations == 55, f"Expected 55 mutations, found {total_mutations}"
    assert mutations_failed == 55, f"Expected 55 mutations returning FAIL, found {mutations_failed}"
    assert mutations_uncertain == 0, f"Expected 0 mutations returning UNCERTAIN, found {mutations_uncertain}"
    assert mutations_passed == 0, f"Expected 0 false passes, found {mutations_passed}"


def test_all_159_fixtures_explicit_and_accounted(cases, evaluator):
    """Task 3: Confirm all 159 fixtures across all 50 cases are accounted for without omission."""
    fixture_counts = {
        "unchanged": 0,
        "valid_paraphrase": 0,
        "mutations": 0,
        "adversarial_passes": 0,
        "unverifiable_syntax": 0,
    }

    for cid, case in cases.items():
        fixtures = case.get("fixtures", {})
        for ftype, data in fixtures.items():
            if ftype == "mutations":
                fixture_counts["mutations"] += len(data)
            elif ftype == "adversarial_passes":
                fixture_counts["adversarial_passes"] += len(data)
            elif ftype in fixture_counts:
                fixture_counts[ftype] += 1

    assert fixture_counts["unchanged"] == 50
    assert fixture_counts["valid_paraphrase"] == 48
    assert fixture_counts["mutations"] == 55
    assert fixture_counts["adversarial_passes"] == 2
    assert fixture_counts["unverifiable_syntax"] == 4
    total_fixtures = sum(fixture_counts.values())
    assert total_fixtures == 159, f"Expected 159 fixtures, found {total_fixtures}"




