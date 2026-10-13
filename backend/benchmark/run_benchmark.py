"""Offline Benchmark Harness for HumanizeAI-FactGuard.

Runs factual integrity evaluation on offline benchmark cases and pre-recorded rewrites
without network access, GPU usage, or provider API calls.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

try:
    from benchmark.evaluator import EvaluationReport, EvaluationStatus, FactualBenchmarkEvaluator
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from benchmark.evaluator import EvaluationReport, EvaluationStatus, FactualBenchmarkEvaluator


def load_cases(cases_path: Path) -> List[Dict[str, Any]]:
    with open(cases_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_offline_harness(cases_path: Path) -> int:
    cases = load_cases(cases_path)
    evaluator = FactualBenchmarkEvaluator()

    total_runs = 0
    passed_runs = 0
    failed_runs = 0
    uncertain_runs = 0

    mutations_total = 0
    mutations_failed = 0
    mutations_uncertain = 0
    mutations_passed = 0
    passed_paraphrases = 0
    rejected_paraphrases = 0
    passed_unchanged = 0
    failed_unchanged = 0

    category_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
        "cases": 0,
        "mutations_total": 0,
        "mutations_failed": 0,
        "mutations_uncertain": 0,
        "mutations_passed": 0,
        "paraphrases_total": 0,
        "paraphrases_passed": 0,
        "uncertain": 0,
    })

    print("=" * 88)
    print("HUMANIZEAI-FACTGUARD OFFLINE BENCHMARK HARNESS (ZERO PROVIDER CALLS)")
    print("=" * 88)

    for case in cases:
        cid = case["id"]
        cat = case.get("category", "unspecified")
        category_stats[cat]["cases"] += 1
        fixtures = case.get("fixtures", {})
        
        # 1. Test unchanged source text
        unchanged = fixtures.get("unchanged")
        if unchanged:
            total_runs += 1
            report: EvaluationReport = evaluator.evaluate(case, unchanged)
            has_unverifiable = any(not r.get("verifiable_offline", True) for r in case.get("required_relations", []))
            expected_status = EvaluationStatus.UNCERTAIN if has_unverifiable else EvaluationStatus.PASS
            is_correct = (report.overall_status == expected_status)
            status_symbol = report.overall_status.value
            print(f"[{status_symbol:<11}] {cid:<35} [fixture: unchanged] -> Score: {report.score}% (Expected: {expected_status.value})")
            if is_correct:
                if report.overall_status == EvaluationStatus.UNCERTAIN:
                    uncertain_runs += 1
                    category_stats[cat]["uncertain"] += 1
                else:
                    passed_runs += 1
                    passed_unchanged += 1
            else:
                failed_runs += 1
                failed_unchanged += 1

        # 2. Test valid paraphrase (if present)
        paraphrase = fixtures.get("valid_paraphrase")
        if paraphrase:
            total_runs += 1
            category_stats[cat]["paraphrases_total"] += 1
            report = evaluator.evaluate(case, paraphrase)
            status_symbol = "PASS" if report.passed else "FAIL"
            print(f"[{status_symbol:<11}] {cid:<35} [fixture: paraphrase] -> Score: {report.score}%")
            if report.passed:
                passed_runs += 1
                passed_paraphrases += 1
                category_stats[cat]["paraphrases_passed"] += 1
            else:
                failed_runs += 1
                rejected_paraphrases += 1

        # 3. Test mutations (must return FAIL to count as detected failure; UNCERTAIN safely blocked)
        mutations = fixtures.get("mutations", {})
        for mut_name, mut_text in mutations.items():
            total_runs += 1
            mutations_total += 1
            category_stats[cat]["mutations_total"] += 1
            report = evaluator.evaluate(case, mut_text)
            
            if report.overall_status == EvaluationStatus.FAIL:
                status_symbol = "CAUGHT_FAIL"
                mutations_failed += 1
                category_stats[cat]["mutations_failed"] += 1
                passed_runs += 1  # detected corruption
            elif report.overall_status == EvaluationStatus.UNCERTAIN:
                status_symbol = "BLOCKED_UNC"
                mutations_uncertain += 1
                category_stats[cat]["mutations_uncertain"] += 1
                uncertain_runs += 1
                category_stats[cat]["uncertain"] += 1
            else:  # PASS
                status_symbol = "MISSED_PASS"
                mutations_passed += 1
                category_stats[cat]["mutations_passed"] += 1
                failed_runs += 1  # false pass (safety violation)

            print(
                f"[{status_symbol:<11}] {cid:<35} [mutation: {mut_name}] -> "
                f"Status: {report.overall_status.value} (Score: {report.score}%)"
            )

        # 4. Test adversarial pass fixtures (opposite term in unrelated clause must still PASS)
        adv_passes = fixtures.get("adversarial_passes", {})
        for adv_name, adv_text in adv_passes.items():
            total_runs += 1
            report = evaluator.evaluate(case, adv_text)
            status_symbol = "PASS" if report.passed else "FAIL"
            print(f"[{status_symbol:<11}] {cid:<35} [adversarial: {adv_name}] -> Score: {report.score}%")
            if report.passed:
                passed_runs += 1
            else:
                failed_runs += 1

        # 5. Test unverifiable syntax fixture
        unverifiable = fixtures.get("unverifiable_syntax")
        if unverifiable:
            total_runs += 1
            report = evaluator.evaluate(case, unverifiable)
            status_symbol = "UNCERTAIN" if report.overall_status == EvaluationStatus.UNCERTAIN else "FAILED"
            print(f"[{status_symbol:<11}] {cid:<35} [fixture: unverifiable] -> Status: {report.overall_status.value}")
            if report.overall_status == EvaluationStatus.UNCERTAIN:
                uncertain_runs += 1
                category_stats[cat]["uncertain"] += 1
            else:
                failed_runs += 1

    print("=" * 88)
    print("CATEGORY BREAKDOWN")
    print("=" * 88)
    print(f"{'Category':<28} | {'Cases':<5} | {'Mut FAIL':<8} | {'Mut UNC':<7} | {'Mut PASS':<8} | {'Para PASS':<9} | {'Uncertain'}")
    print("-" * 88)
    for cat_name, stats in sorted(category_stats.items()):
        mf_str = f"{stats['mutations_failed']}/{stats['mutations_total']}"
        mu_str = f"{stats['mutations_uncertain']}"
        mp_str = f"{stats['mutations_passed']}"
        para_str = f"{stats['paraphrases_passed']}/{stats['paraphrases_total']}"
        print(f"{cat_name:<28} | {stats['cases']:<5} | {mf_str:<8} | {mu_str:<7} | {mp_str:<8} | {para_str:<9} | {stats['uncertain']}")

    print("=" * 88)
    print("SUMMARY AUDIT TOTALS")
    print("=" * 88)
    print(f"Total benchmark cases:               {len(cases)}")
    print(f"Total test fixtures evaluated:       {total_runs}")
    print(f"Mutations evaluated:                 {mutations_total}")
    print(f"  - Mutations returning FAIL:        {mutations_failed}/{mutations_total} (detected failures)")
    print(f"  - Mutations returning UNCERTAIN:   {mutations_uncertain}/{mutations_total} (safely blocked, not detected FAIL)")
    print(f"  - Mutations returning PASS:        {mutations_passed}/{mutations_total} (false passes / missed)")
    print(f"Valid paraphrases verified:          {passed_paraphrases}/{passed_paraphrases + rejected_paraphrases}")
    print(f"Valid paraphrases rejected:          {rejected_paraphrases}")
    print(f"Unchanged sources verified:          {passed_unchanged}/{passed_unchanged + failed_unchanged}")
    print(f"Total uncertain outcomes:            {uncertain_runs}")
    print(f"Unexpected results / Failures:       {failed_runs}")
    print(f"Overall test fixture pass rate:      {(passed_runs + uncertain_runs)/total_runs * 100:.1f}%")
    print("=" * 88)

    return 0 if failed_runs == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Run HumanizeAI-FactGuard offline benchmark evaluator.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).parent / "cases.json",
        help="Path to cases.json benchmark file"
    )
    args = parser.parse_args()

    sys.exit(run_offline_harness(args.cases))


if __name__ == "__main__":
    main()
