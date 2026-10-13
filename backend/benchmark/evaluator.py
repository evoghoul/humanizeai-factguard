"""Benchmark evaluator for factual integrity in HumanizeAI-FactGuard.

DESIGN PRINCIPLES & LIMITATIONS:
1. Normalization Rules:
   - Currency: Accepts standard representations ($4.2M, $4.2 million, USD 4.2M) but
     strictly rejects scale shifts ($4.2B, $4.2K), value shifts ($4.5M), or unit changes.
   - Percentages: Normalizes '15%' and '15 percent'; strictly rejects other numerical rates.
   - Dates & Periods: Normalizes 'Q2 2025' and 'second quarter of 2025'.
   - Date Ranges: Strictly enforces closed boundaries (e.g., 'August 1 to September 30').
     Detects open-ended distortions (e.g., 'since August 1') and missing boundaries.
2. Relational Verification Beyond Co-occurrence:
   - Simple string proximity or sentence co-occurrence is INSUFFICIENT to prove attribution.
     When multiple metrics and targets exist (e.g., $4.2M for Q2 and $5.1M for Q3),
     clause-level parsing detects cross-attribution swaps.
   - Ambiguous or syntactically distant relations that cannot be verified deterministically
     are classified as UNCERTAIN / NOT_CHECKED, never falsely reported as PASS.
3. Scoring & Hard Failure Gate:
   - Retention percentages (e.g., 90%) must NEVER mask a critical factual error.
   - Any single critical failure (swapped relation, dropped negation, corrupted dosage/currency)
     immediately forces overall_status = FAIL and passed = False.
4. Comprehensive Safety Caveat:
   - Passing a finite benchmark or mutation suite demonstrates coverage against known
     failure modes, but does NOT prove zero risk of factual drift across unconstrained text.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set, Tuple


class EvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"
    NOT_CHECKED = "NOT_CHECKED"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"


@dataclass
class CheckResult:
    name: str
    category: str  # "values", "relations", "negations", "unexpected_values", "formatting"
    status: EvaluationStatus
    severity: Severity
    expected: Any
    found: Any
    details: str


@dataclass
class EvaluationReport:
    case_id: str
    overall_status: EvaluationStatus  # PASS, FAIL, or UNCERTAIN
    passed: bool
    score: float  # 0.0 - 100.0 based on passed checks / total checks
    critical_failure_count: int
    warning_count: int
    checks: List[CheckResult] = field(default_factory=list)
    missing_values: List[str] = field(default_factory=list)
    altered_values: List[str] = field(default_factory=list)
    unexpected_values: List[str] = field(default_factory=list)
    failed_relations: List[Dict[str, Any]] = field(default_factory=list)
    uncertain_relations: List[Dict[str, Any]] = field(default_factory=list)
    failed_negations: List[str] = field(default_factory=list)
    formatting_issues: List[str] = field(default_factory=list)
    failed_directional: List[Dict[str, Any]] = field(default_factory=list)
    uncertain_directional: List[Dict[str, Any]] = field(default_factory=list)
    failed_modality: List[Dict[str, Any]] = field(default_factory=list)
    uncertain_modality: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Normalization & Pattern Helpers
# ---------------------------------------------------------------------------

def _split_clauses(text: str) -> List[str]:
    """Split text into sentences and sub-clauses for fine-grained binding checks."""
    delimiters = r'(?:\. |\n+|; |:\s+|(?:,\s*)?(?:while|whereas|although|though)\s+|,\s*(?:but|and\s+then|yet|however)\s+)'
    clauses = re.split(delimiters, text, flags=re.IGNORECASE)
    return [c.strip() for c in clauses if c.strip()]


def _build_scope_pattern(term: str) -> re.Pattern:
    """Build an inflection-aware regex pattern for scope terms."""
    cleaned = term.strip().lower()
    if " " in cleaned:
        words = cleaned.split()
        last_word = words[-1]
        last_stem = last_word[:-1] if last_word.endswith("e") else (last_word[:-1] if last_word.endswith("s") else last_word)
        pat_str = r'\s+'.join(re.escape(w) for w in words[:-1]) + rf'\s+{re.escape(last_stem)}(?:e|ed|ing|es|s)?'
        return re.compile(rf'(?<!\w){pat_str}(?!\w)', re.IGNORECASE)

    # Single word: e.g. "authorize" -> stem "authoriz" -> authorize, authorized, authorizing, authorizes
    # "exceed" -> stem "exceed" -> exceed, exceeded, exceeding, exceeds
    stem = cleaned[:-1] if cleaned.endswith("e") else cleaned
    return re.compile(rf'(?<!\w){re.escape(stem)}(?:e|ed|ing|es|s)?(?!\w)', re.IGNORECASE)


def _build_value_patterns(value: str, val_type: str) -> List[re.Pattern]:
    """Generate acceptable regex patterns for a given value based on its type."""
    patterns: List[re.Pattern] = []
    
    if val_type == "currency":
        m = re.match(r'^([\$€£])([0-9,]+(?:\.[0-9]+)?)([kKmMbBtT]?)$', value)
        if m:
            sym, raw_num, scale = m.group(1), m.group(2).replace(",", ""), m.group(3).upper()
            curr_names = {"$": ["dollars", "usd"], "€": ["euros", "eur"], "£": ["pounds", "gbp"]}
            sym_names = curr_names.get(sym, ["dollars", "usd"])
            escaped_num = re.escape(raw_num)
            num_with_commas = re.escape(f"{int(float(raw_num)):,}") if "." not in raw_num and raw_num.isdigit() else escaped_num
            num_pat = rf'(?:{escaped_num}|{num_with_commas})'
            scale_name = {"K": "thousand", "M": "million", "B": "billion", "T": "trillion"}.get(scale, "")
            
            # Format 1: $4.2M, €50M, £18M
            if scale:
                patterns.append(re.compile(rf'\{sym}\s*{num_pat}\s*{scale}\b', re.IGNORECASE))
                # Format 2: $4.2 million, €50 million
                if scale_name:
                    patterns.append(re.compile(rf'\{sym}\s*{num_pat}[-\s]+{scale_name}\b', re.IGNORECASE))
                    patterns.append(re.compile(rf'\b{num_pat}[-\s]+{scale_name}\s*(?:{"|".join(sym_names)})\b', re.IGNORECASE))
                    for sn in sym_names:
                        patterns.append(re.compile(rf'\b{sn}\s*{num_pat}\s*(?:{scale}|{scale_name})\b', re.IGNORECASE))
            else:
                patterns.append(re.compile(rf'\{sym}\s*{num_pat}\b', re.IGNORECASE))
                patterns.append(re.compile(rf'\b{num_pat}\s*(?:{"|".join(sym_names)})\b', re.IGNORECASE))

    elif val_type == "percentage":
        m = re.match(r'^([0-9]+(?:\.[0-9]+)?)%$', value)
        if m:
            num = re.escape(m.group(1))
            patterns.append(re.compile(rf'\b{num}\s*%', re.IGNORECASE))
            patterns.append(re.compile(rf'\b{num}\s*percent\b', re.IGNORECASE))

    elif val_type == "date_period":
        m = re.match(r'^Q([1-4])\s+(\d{4})$', value, re.IGNORECASE)
        if m:
            quarter, year = m.group(1), m.group(2)
            q_words = {"1": "first", "2": "second", "3": "third", "4": "fourth"}
            q_word = q_words.get(quarter, quarter)
            patterns.append(re.compile(rf'\bq{quarter}\s*(?:of\s+)?{year}\b', re.IGNORECASE))
            patterns.append(re.compile(rf'\b{year}\s*q{quarter}\b', re.IGNORECASE))
            patterns.append(re.compile(rf'\b{q_word}\s+quarter\s+(?:of\s+)?{year}\b', re.IGNORECASE))
        else:
            escaped = re.escape(value)
            patterns.append(re.compile(rf'\b{escaped}(?:th|st|nd|rd)?\b', re.IGNORECASE))

    elif val_type == "time":
        m = re.match(r'^(\d{1,2}:\d{2})\s*(UTC|GMT|PST|EST)?$', value, re.IGNORECASE)
        if m:
            time_str = re.escape(m.group(1))
            zone = re.escape(m.group(2)) if m.group(2) else ""
            if zone:
                patterns.append(re.compile(rf'\b{time_str}\s*{zone}\b', re.IGNORECASE))
            else:
                patterns.append(re.compile(rf'\b{time_str}\b', re.IGNORECASE))

    elif val_type == "quantity":
        if value.endswith("mg"):
            num = re.escape(value[:-2].strip())
            patterns.append(re.compile(rf'\b{num}\s*mg\b', re.IGNORECASE))
        elif "-minute" in value or " minute" in value:
            num = re.escape(re.match(r'^\d+', value).group(0))
            patterns.append(re.compile(rf'\b{num}[-\s]+minute(?:\s+window)?\b', re.IGNORECASE))
        elif value.isdigit():
            num = re.escape(value)
            digit_words = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five"}
            w = digit_words.get(value, "")
            patterns.append(re.compile(rf'\b{num}\b'))
            if w:
                patterns.append(re.compile(rf'\b{w}\b', re.IGNORECASE))
        else:
            escaped = re.escape(value)
            patterns.append(re.compile(rf'(?<!\w){escaped}(?!\w)', re.IGNORECASE))

    elif val_type == "date_range":
        m = re.match(r'^([A-Z][a-z]+\s+\d{1,2}(?:,\s*\d{4})?)\s+to\s+([A-Z][a-z]+\s+\d{1,2}(?:,\s*\d{4})?)$', value, re.IGNORECASE)
        if m:
            start_p = re.escape(m.group(1))
            end_p = re.escape(m.group(2))
            patterns.append(re.compile(
                rf'\b(?:from|between\s+)?{start_p}(?:st|nd|rd|th)?\s+(?:to|through|and|-|until)\s+{end_p}(?:st|nd|rd|th)?\b',
                re.IGNORECASE
            ))

    elif val_type == "entity":
        escaped = re.escape(value)
        patterns.append(re.compile(rf'(?<!\w){escaped}(?!\w)', re.IGNORECASE))

    # Fallback pattern without assuming word characters at boundaries
    if not patterns:
        patterns.append(re.compile(rf'(?<!\w){re.escape(value)}(?!\w)', re.IGNORECASE))
        
    return patterns


def _matches_value(value: str, val_type: str, text: str) -> bool:
    patterns = _build_value_patterns(value, val_type)
    return any(p.search(text) is not None for p in patterns)


def _resolve_type(val: str, type_map: Dict[str, str]) -> str:
    """Resolve type for a value from explicit map or inference."""
    if val in type_map:
        return type_map[val]
    if val.startswith(("$", "€", "£")):
        return "currency"
    if val.endswith("%"):
        return "percentage"
    if re.match(r'^Q[1-4]\s+\d{4}$', val, re.IGNORECASE):
        return "date_period"
    if val.endswith("mg"):
        return "quantity"
    return "entity"


INCREASE_TERMS = {
    "grew", "grow", "grown", "growing",
    "increased", "increase", "increases", "increasing",
    "rose", "rise", "rises", "rising",
    "expanded", "expand", "expands", "expanding",
    "climbed", "climb", "climbs", "climbing",
    "gained", "gain", "gains", "gaining",
    "surged", "surge", "surges", "surging",
}

DECREASE_TERMS = {
    "dropped", "drop", "drops", "dropping",
    "decreased", "decrease", "decreases", "decreasing",
    "fell", "fall", "falls", "falling",
    "contracted", "contract", "contracts", "contracting",
    "declined", "decline", "declines", "declining",
    "diminished", "diminish", "diminishes", "diminishing",
    "slumped", "slump", "slumps", "slumping",
}

POSSIBILITY_MARKERS = {
    "may", "might", "could", "can", "possibly", "optional", "permitted to", "allowed to"
}

OBLIGATION_MARKERS = {
    "must", "shall", "required", "mandatory", "obligated", "has to", "have to", "needs to", "is required to"
}


def _evaluate_directional_claims(
    case: Dict[str, Any],
    candidate_text: str,
    clauses: List[str],
    checks: List[CheckResult],
    failed_directional: List[Dict[str, Any]],
    uncertain_directional: List[Dict[str, Any]],
) -> None:
    claims = case.get("directional_claims", [])
    if not claims:
        return

    for claim in claims:
        subject = claim.get("subject", "").strip()
        metric = claim.get("target_metric", "").strip()
        expected_dir = claim.get("direction", "increase").lower()
        sev = Severity(claim.get("severity", "critical"))

        if expected_dir == "increase":
            accepted_terms = set(claim.get("accepted_terms", [])) or INCREASE_TERMS
            reversed_terms = set(claim.get("reversed_terms", [])) or DECREASE_TERMS
        else:
            accepted_terms = set(claim.get("accepted_terms", [])) or DECREASE_TERMS
            reversed_terms = set(claim.get("reversed_terms", [])) or INCREASE_TERMS

        target_clauses: List[str] = []
        if subject and metric:
            target_clauses = [
                c for c in clauses
                if re.search(rf'\b{re.escape(subject)}\b', c, re.IGNORECASE)
                and re.search(rf'(?<!\w){re.escape(metric)}(?!\w)', c, re.IGNORECASE)
            ]
        if not target_clauses and subject:
            target_clauses = [c for c in clauses if re.search(rf'\b{re.escape(subject)}\b', c, re.IGNORECASE)]
        if not target_clauses and metric:
            target_clauses = [c for c in clauses if re.search(rf'(?<!\w){re.escape(metric)}(?!\w)', c, re.IGNORECASE)]

        if not target_clauses:
            checks.append(CheckResult(
                name=f"Directional Claim: {subject or metric} ({expected_dir})",
                category="directional",
                status=EvaluationStatus.FAIL,
                severity=sev,
                expected=f"{expected_dir} for {subject or metric}",
                found="Constituents missing",
                details=f"Directional claim failed: Neither subject '{subject}' nor metric '{metric}' found in text."
            ))
            failed_directional.append({"claim": claim, "issue": "missing_constituents"})
            continue

        found_reversed = None
        reversed_details = ""
        found_accepted = None
        has_negated_accepted = False

        negation_pattern = re.compile(
            r'\b(?:not|did\s+not|didn\'t|no|never|without|failed\s+to|had\s+not|has\s+not|have\s+not)\b',
            re.IGNORECASE
        )

        for scoped_clause in target_clauses:
            for r_term in reversed_terms:
                m = re.search(rf'\b{re.escape(r_term)}\b', scoped_clause, re.IGNORECASE)
                if m:
                    preceding = scoped_clause[max(0, m.start() - 45):m.start()]
                    if not negation_pattern.search(preceding):
                        found_reversed = r_term
                        reversed_details = f"Clause '{scoped_clause.strip()}' described reversed direction '{r_term}'."
                        break
            if found_reversed:
                break

            for a_term in accepted_terms:
                m = re.search(rf'\b{re.escape(a_term)}\b', scoped_clause, re.IGNORECASE)
                if m:
                    preceding = scoped_clause[max(0, m.start() - 45):m.start()]
                    if negation_pattern.search(preceding):
                        has_negated_accepted = True
                    else:
                        found_accepted = a_term

        if found_reversed:
            checks.append(CheckResult(
                name=f"Directional Claim: {subject or metric} ({expected_dir})",
                category="directional",
                status=EvaluationStatus.FAIL,
                severity=sev,
                expected=f"{expected_dir} direction for '{subject or metric}'",
                found=f"Reversed term '{found_reversed}'",
                details=f"Directional reversal: '{subject or metric}' was described with reversed direction '{found_reversed}' (expected {expected_dir}). {reversed_details}"
            ))
            failed_directional.append({"claim": claim, "issue": "reversed_direction", "found": found_reversed})
            continue

        if has_negated_accepted and not found_accepted:
            checks.append(CheckResult(
                name=f"Directional Claim: {subject or metric} ({expected_dir})",
                category="directional",
                status=EvaluationStatus.FAIL,
                severity=sev,
                expected=f"{expected_dir} direction for '{subject or metric}'",
                found="Explicitly negated direction",
                details=f"Directional claim negated: Expected {expected_dir} for '{subject or metric}' was explicitly negated in text."
            ))
            failed_directional.append({"claim": claim, "issue": "negated_direction"})
            continue

        if found_accepted:
            checks.append(CheckResult(
                name=f"Directional Claim: {subject or metric} ({expected_dir})",
                category="directional",
                status=EvaluationStatus.PASS,
                severity=sev,
                expected=f"{expected_dir} direction for '{subject or metric}'",
                found=f"Preserved via '{found_accepted}'",
                details=f"Directional claim verified: '{subject or metric}' preserved {expected_dir} via '{found_accepted}'."
            ))
        else:
            checks.append(CheckResult(
                name=f"Directional Claim: {subject or metric} ({expected_dir})",
                category="directional",
                status=EvaluationStatus.UNCERTAIN,
                severity=sev,
                expected=f"{expected_dir} direction for '{subject or metric}'",
                found="Directional predicate omitted or unverified",
                details=f"Directional claim '{subject or metric} -> {expected_dir}' cannot be deterministically verified offline."
            ))
            uncertain_directional.append({"claim": claim, "issue": "unverified_predicate"})


def _evaluate_modality_claims(
    case: Dict[str, Any],
    candidate_text: str,
    clauses: List[str],
    checks: List[CheckResult],
    failed_modality: List[Dict[str, Any]],
    uncertain_modality: List[Dict[str, Any]],
) -> None:
    claims = case.get("modality", [])
    if not claims:
        return

    for claim in claims:
        scope_term = claim.get("scope_term", "").strip()
        entity = claim.get("target_entity", "").strip()
        required_modality = claim.get("required_modality", "possibility").lower()
        sev = Severity(claim.get("severity", "critical"))

        if required_modality == "possibility":
            accepted_markers = set(claim.get("accepted_markers", [])) or POSSIBILITY_MARKERS
            reversed_markers = set(claim.get("reversed_markers", [])) or OBLIGATION_MARKERS
        else:
            accepted_markers = set(claim.get("accepted_markers", [])) or OBLIGATION_MARKERS
            reversed_markers = set(claim.get("reversed_markers", [])) or POSSIBILITY_MARKERS

        scope_pat = _build_scope_pattern(scope_term)

        # Clause scoping: prioritize clause containing both scope_term and target_entity
        target_clauses = []
        if entity:
            target_clauses = [
                c for c in clauses
                if scope_pat.search(c) and re.search(rf'\b{re.escape(entity)}\b', c, re.IGNORECASE)
            ]
        if not target_clauses:
            target_clauses = [c for c in clauses if scope_pat.search(c)]

        if not target_clauses:
            checks.append(CheckResult(
                name=f"Modality Claim: {scope_term} ({required_modality})",
                category="modality",
                status=EvaluationStatus.FAIL,
                severity=sev,
                expected=f"Modal condition on '{scope_term}' ({required_modality})",
                found="Scope term missing",
                details=f"Modality claim failed: Scope term '{scope_term}' missing from text."
            ))
            failed_modality.append({"claim": claim, "issue": "missing_scope_term"})
            continue

        found_reversed = None
        found_accepted = None

        # In natural language, modal auxiliaries govern the verb phrase directly.
        # Inspect the immediate preceding window (and following window if copular predicate)
        # bounded by sub-clause delimiters across all matching clauses.
        for scoped_clause in target_clauses:
            scope_matches = list(scope_pat.finditer(scoped_clause))
            for match in scope_matches:
                verb_start = match.start()
                raw_prec = scoped_clause[max(0, verb_start - 50):verb_start]
                prec = re.split(r'[\.;,]', raw_prec)[-1]
                raw_foll = scoped_clause[match.end():min(len(scoped_clause), match.end() + 40)]
                foll = re.split(r'[\.;,]', raw_foll)[0]

                for r_marker in reversed_markers:
                    r_pat = rf'\b{re.escape(r_marker)}\b'
                    if re.search(r_pat, prec, re.IGNORECASE) or re.search(r_pat, foll, re.IGNORECASE):
                        found_reversed = r_marker
                        break
                if found_reversed:
                    break

                for a_marker in accepted_markers:
                    a_pat = rf'\b{re.escape(a_marker)}\b'
                    if re.search(a_pat, prec, re.IGNORECASE) or re.search(a_pat, foll, re.IGNORECASE):
                        found_accepted = a_marker
                        break
            if found_reversed:
                break

        if found_reversed:
            checks.append(CheckResult(
                name=f"Modality Claim: {scope_term} ({required_modality})",
                category="modality",
                status=EvaluationStatus.FAIL,
                severity=sev,
                expected=f"{required_modality} modal governing '{scope_term}'",
                found=f"Reversed modal '{found_reversed}'",
                details=f"Modality shift: '{scope_term}' governed by conflicting modal '{found_reversed}' (expected {required_modality})."
            ))
            failed_modality.append({"claim": claim, "issue": "modality_shift", "found": found_reversed})
            continue

        if found_accepted:
            checks.append(CheckResult(
                name=f"Modality Claim: {scope_term} ({required_modality})",
                category="modality",
                status=EvaluationStatus.PASS,
                severity=sev,
                expected=f"{required_modality} modal governing '{scope_term}'",
                found=f"Preserved via '{found_accepted}'",
                details=f"Modality verified: '{scope_term}' governed by accepted modal '{found_accepted}' ({required_modality})."
            ))
        else:
            checks.append(CheckResult(
                name=f"Modality Claim: {scope_term} ({required_modality})",
                category="modality",
                status=EvaluationStatus.UNCERTAIN,
                severity=sev,
                expected=f"{required_modality} modal governing '{scope_term}'",
                found="Modal auxiliary omitted or unmodalized",
                details=f"Modality for '{scope_term}' cannot be verified deterministically; modal auxiliary omitted or unmodalized."
            ))
            uncertain_modality.append({"claim": claim, "issue": "unmodalized_or_omitted"})


# ---------------------------------------------------------------------------
# Core Evaluator Implementation
# ---------------------------------------------------------------------------

class FactualBenchmarkEvaluator:
    """Offline benchmark evaluator enforcing hard factual integrity rules."""

    def evaluate(self, case: Dict[str, Any], candidate_text: str) -> EvaluationReport:
        case_id = case.get("id", "unknown_case")
        checks: List[CheckResult] = []
        
        missing_values: List[str] = []
        altered_values: List[str] = []
        unexpected_values: List[str] = []
        failed_relations: List[Dict[str, Any]] = []
        uncertain_relations: List[Dict[str, Any]] = []
        failed_negations: List[str] = []
        formatting_issues: List[str] = []
        failed_directional: List[Dict[str, Any]] = []
        uncertain_directional: List[Dict[str, Any]] = []
        failed_modality: List[Dict[str, Any]] = []
        uncertain_modality: List[Dict[str, Any]] = []

        required_values = case.get("required_values", [])
        type_map = {v["value"]: v.get("type", "entity") for v in required_values}

        # 1. Required Values Preservation
        for val_spec in required_values:
            val = val_spec["value"]
            val_type = val_spec.get("type", "entity")
            sev = Severity(val_spec.get("severity", "critical"))
            
            matched = _matches_value(val, val_type, candidate_text)
            
            # Specific check for date range distortion (closed range turned to "since <date>")
            if val_type == "date_range" and not matched:
                start_date = val_spec.get("start_date")
                if start_date and re.search(rf'\bsince\s+{re.escape(start_date)}\b', candidate_text, re.IGNORECASE):
                    checks.append(CheckResult(
                        name=f"Value Preservation: {val}",
                        category="values",
                        status=EvaluationStatus.FAIL,
                        severity=sev,
                        expected=val,
                        found="open-ended 'since' clause",
                        details=f"Timeline distortion: Closed range '{val}' altered to open-ended 'since {start_date}'."
                    ))
                    altered_values.append(val)
                    continue

            if matched:
                checks.append(CheckResult(
                    name=f"Value Preservation: {val}",
                    category="values",
                    status=EvaluationStatus.PASS,
                    severity=sev,
                    expected=val,
                    found=val,
                    details=f"Preserved under {val_type} normalization rules."
                ))
            else:
                checks.append(CheckResult(
                    name=f"Value Preservation: {val}",
                    category="values",
                    status=EvaluationStatus.FAIL,
                    severity=sev,
                    expected=val,
                    found=None,
                    details=f"Missing or corrupted {val_type} value '{val}'."
                ))
                missing_values.append(val)

        # 2. Unexpected Protected Values (Hallucinations)
        source_text = case.get("source_text", "")
        currency_token_pattern = re.compile(
            r'[\$€£][0-9,]+(?:\.[0-9]+)?(?:\s*(?:[kKmMbBtT]|thousand|million|billion|trillion))?\b',
            re.IGNORECASE
        )
        found_currency_tokens = set(currency_token_pattern.findall(candidate_text))
        
        for fc in found_currency_tokens:
            fc_clean = fc.strip()
            if fc_clean.lower() in source_text.lower():
                continue
            matches_known = False
            for req in required_values:
                if req.get("type") == "currency":
                    if _matches_value(req["value"], "currency", fc_clean):
                        matches_known = True
                        break
            if not matches_known:
                unexpected_values.append(fc_clean)
                checks.append(CheckResult(
                    name=f"Ungrounded Value: {fc_clean}",
                    category="unexpected_values",
                    status=EvaluationStatus.FAIL,
                    severity=Severity.CRITICAL,
                    expected="No ungrounded financial metrics",
                    found=fc_clean,
                    details=f"Unexpected protected value '{fc_clean}' introduced without grounding in source text."
                ))

        # 3. Explicit Relational Verification (Beyond Co-occurrence)
        required_relations = case.get("required_relations", [])
        clauses = _split_clauses(candidate_text)
        
        for rel in required_relations:
            subj = rel["subject"]
            target = rel["target"]
            pred = rel.get("predicate", "related_to")
            sev = Severity(rel.get("severity", "critical"))
            verifiable_offline = rel.get("verifiable_offline", True)

            if not verifiable_offline:
                checks.append(CheckResult(
                    name=f"Relation: {subj} -> {target}",
                    category="relations",
                    status=EvaluationStatus.UNCERTAIN,
                    severity=sev,
                    expected=f"{subj} {pred} {target}",
                    found="Unverifiable via deterministic offline syntax",
                    details=f"Relation '{subj} -> {target}' cannot be deterministically verified offline; marked UNCERTAIN."
                ))
                uncertain_relations.append(rel)
                continue

            subj_type = _resolve_type(subj, type_map)
            target_type = _resolve_type(target, type_map)

            # Find which clauses contain subject and target
            subj_clauses = [i for i, c in enumerate(clauses) if _matches_value(subj, subj_type, c)]
            target_clauses = [i for i, c in enumerate(clauses) if _matches_value(target, target_type, c)]

            # Check for direct clause co-binding
            common_clauses = set(subj_clauses).intersection(set(target_clauses))

            # Check for cross-attribution swap
            is_swapped = False
            swapped_details = ""
            for other_rel in required_relations:
                if other_rel["target"] != target and other_rel.get("verifiable_offline", True):
                    other_subj = other_rel["subject"]
                    other_subj_type = _resolve_type(other_subj, type_map)
                    
                    for t_idx in target_clauses:
                        clause_txt = clauses[t_idx]
                        if _matches_value(other_subj, other_subj_type, clause_txt) and not _matches_value(subj, subj_type, clause_txt):
                            is_swapped = True
                            swapped_details = (
                                f"Swapped attribution: '{target}' was syntactically bound to conflicting value "
                                f"'{other_subj}' rather than expected '{subj}'."
                            )
                            break
                if is_swapped:
                    break

            if is_swapped:
                checks.append(CheckResult(
                    name=f"Relation Attribution: {subj} -> {target}",
                    category="relations",
                    status=EvaluationStatus.FAIL,
                    severity=sev,
                    expected=f"{subj} bound to {target}",
                    found=swapped_details,
                    details=swapped_details
                ))
                failed_relations.append({"relation": rel, "issue": "swapped_attribution", "details": swapped_details})
            elif common_clauses:
                checks.append(CheckResult(
                    name=f"Relation Attribution: {subj} -> {target}",
                    category="relations",
                    status=EvaluationStatus.PASS,
                    severity=sev,
                    expected=f"{subj} bound to {target}",
                    found=f"Co-bound in clause {list(common_clauses)[0]}",
                    details=f"Syntactic clause binding verified between '{subj}' and '{target}'."
                ))
            else:
                subj_exists = _matches_value(subj, subj_type, candidate_text)
                target_exists = _matches_value(target, target_type, candidate_text)
                
                if not subj_exists or not target_exists:
                    checks.append(CheckResult(
                        name=f"Relation Attribution: {subj} -> {target}",
                        category="relations",
                        status=EvaluationStatus.FAIL,
                        severity=sev,
                        expected=f"{subj} bound to {target}",
                        found="Missing constituents",
                        details=f"Cannot verify relation: constituents missing from text."
                    ))
                    failed_relations.append({"relation": rel, "issue": "missing_constituents"})
                else:
                    checks.append(CheckResult(
                        name=f"Relation Attribution: {subj} -> {target}",
                        category="relations",
                        status=EvaluationStatus.UNCERTAIN,
                        severity=sev,
                        expected=f"{subj} bound to {target}",
                        found="Disparate clauses without clear syntactic binding",
                        details=f"Constituents present but lack deterministic clause binding; marked UNCERTAIN."
                    ))
                    uncertain_relations.append(rel)

        # 4. Negation & Polarity Verification
        negations = case.get("negations", [])
        for neg in negations:
            scope_term = neg["scope_term"]
            orig_polarity = neg.get("original_polarity", "negative")
            sev = Severity(neg.get("severity", "critical"))

            scope_pat = _build_scope_pattern(scope_term)
            has_scope = scope_pat.search(candidate_text) is not None
            
            # Negation markers: not, did not, didn't, no, never, without, failed to, neither, nor
            # Look for negation marker within reasonable distance before the scope term
            has_negation_marker = False
            for match in scope_pat.finditer(candidate_text):
                start_pos = max(0, match.start() - 50)
                preceding_snippet = candidate_text[start_pos:match.start()]
                if re.search(r'\b(?:not|did\s+not|didn\'t|no|never|without|failed\s+to|neither|nor)\b', preceding_snippet, re.IGNORECASE):
                    has_negation_marker = True
                    break

            if orig_polarity == "negative":
                if has_scope and not has_negation_marker:
                    checks.append(CheckResult(
                        name=f"Negation Preservation: {scope_term}",
                        category="negations",
                        status=EvaluationStatus.FAIL,
                        severity=sev,
                        expected=f"Negated '{scope_term}'",
                        found=f"Affirmative '{scope_term}'",
                        details=f"Missing negation: Scope term '{scope_term}' used affirmatively, reversing source fact."
                    ))
                    failed_negations.append(scope_term)
                elif has_negation_marker:
                    checks.append(CheckResult(
                        name=f"Negation Preservation: {scope_term}",
                        category="negations",
                        status=EvaluationStatus.PASS,
                        severity=sev,
                        expected=f"Negated '{scope_term}'",
                        found=f"Negation active on '{scope_term}'",
                        details=f"Negative polarity preserved for '{scope_term}'."
                    ))
                else:
                    checks.append(CheckResult(
                        name=f"Negation Preservation: {scope_term}",
                        category="negations",
                        status=EvaluationStatus.UNCERTAIN,
                        severity=sev,
                        expected=f"Negated '{scope_term}'",
                        found="Term omitted",
                        details=f"Scope term '{scope_term}' omitted in rewrite; cannot verify polarity deterministically."
                    ))

        # 5. Structure & Layout Verification (e.g., Email Format)
        expected_struct = case.get("expected_structure", {})
        if case.get("format_type") == "email" or expected_struct:
            if expected_struct.get("requires_greeting"):
                has_greeting = bool(re.search(r'^(?:dear|hi|hello|to)\b', candidate_text.strip(), re.IGNORECASE))
                if not has_greeting:
                    checks.append(CheckResult(
                        name="Format: Salutation / Greeting",
                        category="formatting",
                        status=EvaluationStatus.FAIL,
                        severity=Severity.WARNING,
                        expected="Salutation at start of email",
                        found="Missing greeting",
                        details="Email format collapsed: missing standard salutation (e.g., 'Dear Team,')."
                    ))
                    formatting_issues.append("missing_greeting")
                else:
                    checks.append(CheckResult(
                        name="Format: Salutation / Greeting",
                        category="formatting",
                        status=EvaluationStatus.PASS,
                        severity=Severity.WARNING,
                        expected="Salutation at start of email",
                        found="Present",
                        details="Salutation verified."
                    ))

            if expected_struct.get("requires_signoff"):
                has_signoff = bool(re.search(r'(?:best regards|regards|sincerely|thanks|cheers|best)[,\s]+[a-zA-Z\s]+$', candidate_text.strip(), re.IGNORECASE))
                if not has_signoff:
                    checks.append(CheckResult(
                        name="Format: Sign-off",
                        category="formatting",
                        status=EvaluationStatus.FAIL,
                        severity=Severity.WARNING,
                        expected="Sign-off at end of email",
                        found="Missing sign-off",
                        details="Email format collapsed: missing closing sign-off (e.g., 'Best regards, Operations Lead')."
                    ))
                    formatting_issues.append("missing_signoff")
                else:
                    checks.append(CheckResult(
                        name="Format: Sign-off",
                        category="formatting",
                        status=EvaluationStatus.PASS,
                        severity=Severity.WARNING,
                        expected="Sign-off at end of email",
                        found="Present",
                        details="Sign-off verified."
                    ))

            min_paragraphs = expected_struct.get("min_paragraphs", 1)
            paragraphs = [p for p in re.split(r'\n\s*\n', candidate_text.strip()) if p.strip()]
            if len(paragraphs) < min_paragraphs:
                checks.append(CheckResult(
                    name="Format: Paragraph Separation",
                    category="formatting",
                    status=EvaluationStatus.FAIL,
                    severity=Severity.WARNING,
                    expected=f"At least {min_paragraphs} paragraphs",
                    found=f"{len(paragraphs)} paragraph(s)",
                    details="Email format collapse: line breaks and paragraphs collapsed into single continuous block."
                ))
                formatting_issues.append("collapsed_paragraphs")
            else:
                checks.append(CheckResult(
                    name="Format: Paragraph Separation",
                    category="formatting",
                    status=EvaluationStatus.PASS,
                    severity=Severity.WARNING,
                    expected=f"At least {min_paragraphs} paragraphs",
                    found=f"{len(paragraphs)} paragraph(s)",
                    details="Paragraph layout preserved."
                ))

            min_bullets = expected_struct.get("min_bullets", 0)
            if min_bullets > 0:
                bullets = [line for line in candidate_text.splitlines() if re.match(r'^\s*(?:[-*•]|\d+\.)\s+.+$', line)]
                sev = Severity(expected_struct.get("bullets_severity", "critical"))
                if len(bullets) < min_bullets:
                    checks.append(CheckResult(
                        name="Format: Bullet List Structure",
                        category="formatting",
                        status=EvaluationStatus.FAIL,
                        severity=sev,
                        expected=f"At least {min_bullets} list item(s)",
                        found=f"{len(bullets)} item(s)",
                        details=f"Document structure collapsed: list items collapsed into continuous text (expected >= {min_bullets})."
                    ))
                    formatting_issues.append("collapsed_bullets")
                else:
                    checks.append(CheckResult(
                        name="Format: Bullet List Structure",
                        category="formatting",
                        status=EvaluationStatus.PASS,
                        severity=sev,
                        expected=f"At least {min_bullets} list item(s)",
                        found=f"{len(bullets)} item(s)",
                        details="List structure preserved."
                    ))

            if expected_struct.get("requires_heading"):
                required_heading_text = expected_struct.get("required_heading_text")
                acceptable_headings = expected_struct.get("acceptable_headings", [])
                if required_heading_text and not acceptable_headings:
                    acceptable_headings = [required_heading_text]

                sev = Severity(expected_struct.get("heading_severity", "critical"))

                if acceptable_headings:
                    # Specific heading identity verification
                    found_heading = None
                    for h in acceptable_headings:
                        escaped_h = re.escape(h)
                        if re.search(rf'^(?:#+\s+{escaped_h}\b|{escaped_h}:?\s*$)', candidate_text.strip(), re.MULTILINE | re.IGNORECASE):
                            found_heading = h
                            break

                    if not found_heading:
                        has_any_heading = bool(re.search(r'^(?:#+\s+[^\n]+|[A-Z][A-Za-z0-9\s_-]{2,50}:)', candidate_text.strip(), re.MULTILINE))
                        if not has_any_heading:
                            formatting_issues.append("missing_heading")
                        formatting_issues.append("incorrect_heading_identity")
                        checks.append(CheckResult(
                            name="Format: Document Heading Identity",
                            category="formatting",
                            status=EvaluationStatus.FAIL,
                            severity=sev,
                            expected=f"Heading matching '{acceptable_headings[0]}'",
                            found="Missing heading" if not has_any_heading else "Incorrect heading",
                            details=f"Document heading identity mismatch: expected heading matching '{acceptable_headings[0]}', but heading was {'missing entirely' if not has_any_heading else 'replaced with unrelated heading'}."
                        ))
                    else:
                        checks.append(CheckResult(
                            name="Format: Document Heading Identity",
                            category="formatting",
                            status=EvaluationStatus.PASS,
                            severity=sev,
                            expected=f"Heading matching '{acceptable_headings[0]}'",
                            found=found_heading,
                            details=f"Specified document heading '{found_heading}' verified."
                        ))
                else:
                    # Generic heading presence verification (for cases requiring any heading)
                    has_heading = bool(re.search(r'^(?:#+\s+[^\n]+|[A-Z][A-Za-z0-9\s_-]{2,50}:)', candidate_text.strip(), re.MULTILINE))
                    if not has_heading:
                        checks.append(CheckResult(
                            name="Format: Document Heading",
                            category="formatting",
                            status=EvaluationStatus.FAIL,
                            severity=sev,
                            expected="Document heading or section title",
                            found="Missing heading",
                            details="Document structure collapsed: missing required section heading or title."
                        ))
                        formatting_issues.append("missing_heading")
                    else:
                        checks.append(CheckResult(
                            name="Format: Document Heading",
                            category="formatting",
                            status=EvaluationStatus.PASS,
                            severity=sev,
                            expected="Document heading or section title",
                            found="Present",
                            details="Document heading verified."
                        ))

        # 6. Directional Claims Verification
        _evaluate_directional_claims(
            case, candidate_text, clauses, checks, failed_directional, uncertain_directional
        )

        # 7. Modality Claims Verification
        _evaluate_modality_claims(
            case, candidate_text, clauses, checks, failed_modality, uncertain_modality
        )

        # -------------------------------------------------------------------
        # Scoring & Hard Failure Gate
        # -------------------------------------------------------------------
        total_checks = len(checks)
        passed_checks = sum(1 for c in checks if c.status == EvaluationStatus.PASS)
        critical_failures = [c for c in checks if c.status == EvaluationStatus.FAIL and c.severity == Severity.CRITICAL]
        warnings = [c for c in checks if c.status == EvaluationStatus.FAIL and c.severity == Severity.WARNING]
        uncertain_checks = [c for c in checks if c.status == EvaluationStatus.UNCERTAIN]

        score = (passed_checks / total_checks * 100.0) if total_checks > 0 else 0.0

        if critical_failures:
            overall_status = EvaluationStatus.FAIL
            passed = False
            summary = f"HARD FAILURE: {len(critical_failures)} critical check(s) failed ({critical_failures[0].details}). Score {score:.1f}% overridden."
        elif warnings:
            overall_status = EvaluationStatus.FAIL
            passed = False
            summary = f"FAILURE: {len(warnings)} warning check(s) failed ({warnings[0].details})."
        elif uncertain_checks:
            overall_status = EvaluationStatus.UNCERTAIN
            passed = False
            summary = f"UNCERTAIN: {len(uncertain_checks)} relation(s)/condition(s) cannot be verified deterministically offline."
        else:
            overall_status = EvaluationStatus.PASS
            passed = True
            summary = f"PASSED: All {total_checks} deterministic factual and structural checks passed (Score {score:.1f}%)."

        return EvaluationReport(
            case_id=case_id,
            overall_status=overall_status,
            passed=passed,
            score=round(score, 1),
            critical_failure_count=len(critical_failures),
            warning_count=len(warnings),
            checks=checks,
            missing_values=missing_values,
            altered_values=altered_values,
            unexpected_values=unexpected_values,
            failed_relations=failed_relations,
            uncertain_relations=uncertain_relations,
            failed_negations=failed_negations,
            formatting_issues=formatting_issues,
            failed_directional=failed_directional,
            uncertain_directional=uncertain_directional,
            failed_modality=failed_modality,
            uncertain_modality=uncertain_modality,
            summary=summary
        )
