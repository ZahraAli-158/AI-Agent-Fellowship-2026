"""
Regression testing (Week 6, Requirement 43) + prompt/model comparison
(Requirements 22/23).

Compares two evaluation/reports/<label>.json reports and classifies every
test case as newly passing, newly failing, or unchanged, plus flags
quality/latency/cost regressions at the summary level.
"""
import argparse
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports")


def load_report(label_or_path):
    path = label_or_path if label_or_path.endswith(".json") else os.path.join(REPORTS_DIR, f"{label_or_path}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare(old_report, new_report):
    old_by_id = {r["test_id"]: r for r in old_report["results"]}
    new_by_id = {r["test_id"]: r for r in new_report["results"]}

    newly_passing, newly_failing, unchanged = [], [], []
    for tid, new_r in new_by_id.items():
        old_r = old_by_id.get(tid)
        if old_r is None:
            continue
        if old_r["pass_fail"] == "FAIL" and new_r["pass_fail"] == "PASS":
            newly_passing.append(tid)
        elif old_r["pass_fail"] == "PASS" and new_r["pass_fail"] == "FAIL":
            newly_failing.append(tid)
        else:
            unchanged.append(tid)

    old_s, new_s = old_report["summary"], new_report["summary"]
    quality_delta = round((new_s["task_success_rate"] - old_s["task_success_rate"]) * 100, 2)
    latency_delta = round(new_s["p95_latency_ms"] - old_s["p95_latency_ms"], 1)
    cost_delta = round(new_s["total_cost"] - old_s["total_cost"], 6)

    return {
        "old_run": old_s["run_label"], "new_run": new_s["run_label"],
        "newly_passing": newly_passing, "newly_failing": newly_failing, "unchanged_count": len(unchanged),
        "task_success_rate_delta_pct": quality_delta,
        "p95_latency_delta_ms": latency_delta,
        "cost_delta": cost_delta,
        "quality_regression": quality_delta < 0,
        "latency_regression": latency_delta > 0,
        "cost_regression": cost_delta > 0,
        "no_critical_regression": len(newly_failing) == 0,
        "verdict": "IMPROVEMENT" if quality_delta > 0 and not newly_failing else
                    ("REGRESSION" if quality_delta < 0 or newly_failing else "NO CHANGE"),
    }


def main():
    parser = argparse.ArgumentParser(description="Compare two evaluation runs.")
    parser.add_argument("old_label")
    parser.add_argument("new_label")
    args = parser.parse_args()
    old_report = load_report(args.old_label)
    new_report = load_report(args.new_label)
    result = compare(old_report, new_report)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
