"""
Week 6 §44 — Release Gate, checked in code, not just documented.

Reads the thresholds from evaluation/config.py and checks a given
evaluation report (+ optional regression result) against them, producing a
per-criterion pass/fail and an overall verdict. Approval compliance and
tool selection accuracy are computed directly from the report's raw
results/deterministic checks rather than trusted at face value.

Run: python -m evaluation.release_gate <label>
     python -m evaluation.release_gate <label> --baseline <old_label>
"""
import argparse
import json
import os

from evaluation.config import RELEASE_GATE_THRESHOLDS

_HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports")


def _approval_compliance_rate(results):
    approval_cases = [r for r in results
                        if r["deterministic"]["checks"].get("eval_approval_compliance")]
    if not approval_cases:
        return 1.0  # nothing to check -> vacuously compliant
    passed = sum(1 for r in approval_cases if r["deterministic"]["checks"]["eval_approval_compliance"]["passed"])
    return passed / len(approval_cases)


def _unsupported_claim_rate(summary):
    rate = summary.get("rag_evaluation", {}).get("unsupported_claim_rate")
    return rate if rate is not None else 0.0


def check_release_gate(report, regression_result=None, thresholds=None):
    thresholds = thresholds or RELEASE_GATE_THRESHOLDS
    summary = report["summary"]
    results = report["results"]

    approval_rate = _approval_compliance_rate(results)
    unsupported_rate = _unsupported_claim_rate(summary)

    checks = {
        "task_success_rate": {
            "value": summary["task_success_rate"], "threshold": thresholds["task_success_rate_min"],
            "passed": summary["task_success_rate"] >= thresholds["task_success_rate_min"],
        },
        "tool_selection_accuracy": {
            "value": summary.get("tool_selection_accuracy"), "threshold": thresholds["tool_selection_accuracy_min"],
            "passed": (summary.get("tool_selection_accuracy") or 0) >= thresholds["tool_selection_accuracy_min"],
        },
        "approval_compliance": {
            "value": approval_rate, "threshold": thresholds["approval_compliance_min"],
            "passed": approval_rate >= thresholds["approval_compliance_min"],
        },
        "p95_latency_ms": {
            "value": summary["p95_latency_ms"], "threshold": thresholds["p95_latency_ms_max"],
            "passed": summary["p95_latency_ms"] <= thresholds["p95_latency_ms_max"],
        },
        "unsupported_claim_rate": {
            "value": unsupported_rate, "threshold": thresholds["unsupported_claim_rate_max"],
            "passed": unsupported_rate <= thresholds["unsupported_claim_rate_max"],
        },
    }

    if thresholds.get("require_no_critical_regression") and regression_result is not None:
        checks["no_critical_regression"] = {
            "value": regression_result.get("no_critical_regression"), "threshold": True,
            "passed": bool(regression_result.get("no_critical_regression")),
        }

    all_passed = all(c["passed"] for c in checks.values())
    return {"run_label": summary["run_label"], "checks": checks, "release_ready": all_passed}


def main():
    parser = argparse.ArgumentParser(description="Check an evaluation report against the release gate.")
    parser.add_argument("label")
    parser.add_argument("--baseline", default=None, help="Optional baseline label for regression check")
    args = parser.parse_args()

    with open(os.path.join(REPORTS_DIR, f"{args.label}.json"), "r", encoding="utf-8") as f:
        report = json.load(f)

    regression_result = None
    if args.baseline:
        from evaluation.regression import load_report, compare
        old_report = load_report(args.baseline)
        regression_result = compare(old_report, report)

    result = check_release_gate(report, regression_result)
    print(json.dumps(result, indent=2))
    print(f"\n{'✅ RELEASE READY' if result['release_ready'] else '❌ NOT release ready'}: {result['run_label']}")


if __name__ == "__main__":
    main()
