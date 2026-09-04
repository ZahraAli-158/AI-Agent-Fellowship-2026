"""
Evaluation pipeline (Week 6, Requirement 42).

    Load Dataset -> Execute Cases -> Collect Traces -> Deterministic Evals
    -> LLM Judge -> Calculate Metrics -> Compare With Baseline -> Report

Run it:
    python -m evaluation.runner --label baseline_v1 --prompt-version v1 --mode offline
    python -m evaluation.runner --label agent-system-v3 --prompt-version v3 --mode offline

The evaluator never needs to manually copy/paste the 62 prompts — this file
is the single command that runs the whole suite end to end.
"""
import argparse
import csv
import json
import os
import statistics
import time

from evaluation.system_under_test import run_system
from evaluation.evaluators.deterministic import run_deterministic_evaluators
from evaluation.evaluators.rag_eval import evaluate_rag_case, aggregate_rag_metrics
from evaluation.evaluators.agent_eval import run_agent_evaluators, aggregate_agent_metrics
from evaluation.evaluators.failure_taxonomy import classify_failure
from evaluation.judge import judge_response, average_score, JUDGE_LIMITATIONS
from app.observability.cost import estimate_cost, cost_per_successful_task
from app.observability.metrics import percentile
from app.observability.logging import log_structured

_HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(_HERE, "dataset.jsonl")
REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports")


def load_dataset(path=DATASET_PATH):
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    # Validate against the Pydantic schema (Week 6 §49) so a malformed
    # dataset fails loudly here, not with a confusing downstream KeyError
    # deep inside an evaluator.
    from evaluation.schema import validate_dataset
    validate_dataset(cases)
    return cases


def run_case(case, mode="offline", model="gemini-3.6-flash", prompt_version="v3", run_judge=True):
    start = time.time()
    actual = run_system(case, mode=mode, model=model, prompt_version=prompt_version)
    latency_ms = actual.get("latency_ms") or int((time.time() - start) * 1000)

    det = run_deterministic_evaluators(case, actual)
    judge_result = judge_response(case, actual.get("response_text", "")) if run_judge else None
    rag_metrics = evaluate_rag_case(case, actual, judge_result)
    agent_eval = run_agent_evaluators(case, actual)

    input_tokens = actual.get("input_tokens", 0) or len((case.get("user_input") or "")) // 4
    output_tokens = actual.get("output_tokens", 0) or len((actual.get("response_text") or "")) // 4
    cost = estimate_cost(input_tokens, output_tokens)

    # Overall pass/fail = deterministic checks AND agent-specific checks
    # both hold. RAG metrics are reported (§14) but the RAG failure
    # classification (§15) is diagnostic, not an independent pass/fail gate
    # on top of the deterministic citation-presence check.
    overall_pass = det["passed"] and agent_eval["passed"]
    failure_code, failure_name = (None, None) if overall_pass else classify_failure(
        case, actual, det, agent_eval, rag_metrics)
    log_structured("evaluation_completed", test_id=case["test_id"], category=case["category"],
                    pass_fail="PASS" if overall_pass else "FAIL",
                    judge_avg_score=average_score(judge_result) if judge_result else None)
    return {
        "test_id": case["test_id"], "category": case["category"], "pass_fail": "PASS" if overall_pass else "FAIL",
        "failure_code": failure_code, "failure_name": failure_name,
        "deterministic": det, "agent_eval": agent_eval, "rag_metrics": rag_metrics, "judge": judge_result,
        "judge_avg_score": average_score(judge_result) if judge_result else None,
        "latency_ms": latency_ms, "input_tokens": input_tokens, "output_tokens": output_tokens,
        "cost": cost, "actual_response": actual.get("response_text", "")[:500],
        "tool_called": actual.get("tool_called"), "final_state": actual.get("final_state"),
    }


def run_suite(label, dataset_path=DATASET_PATH, mode="offline", model="gemini-3.6-flash",
              prompt_version="v3", run_judge=True):
    cases = load_dataset(dataset_path)
    results = [run_case(c, mode=mode, model=model, prompt_version=prompt_version, run_judge=run_judge)
                for c in cases]

    total = len(results)
    passed = sum(1 for r in results if r["pass_fail"] == "PASS")
    latencies = sorted(r["latency_ms"] for r in results)
    judge_scores = [r["judge_avg_score"] for r in results if r["judge_avg_score"] is not None]
    total_cost = round(sum(r["cost"] for r in results), 6)
    input_tokens_list = [r["input_tokens"] for r in results]
    output_tokens_list = [r["output_tokens"] for r in results]

    by_category = {}
    for r in results:
        cat = r["category"]
        bucket = by_category.setdefault(cat, {"total": 0, "passed": 0})
        bucket["total"] += 1
        bucket["passed"] += 1 if r["pass_fail"] == "PASS" else 0
    for cat, bucket in by_category.items():
        bucket["failed"] = bucket["total"] - bucket["passed"]
        bucket["success_rate"] = round(bucket["passed"] / bucket["total"], 4) if bucket["total"] else 0.0
        bucket["failure_rate"] = round(bucket["failed"] / bucket["total"], 4) if bucket["total"] else 0.0

    failed_test_ids_by_category = {}
    failure_code_breakdown = {}
    for r in results:
        if r["pass_fail"] == "FAIL":
            failed_test_ids_by_category.setdefault(r["category"], []).append(r["test_id"])
            code = r.get("failure_code") or "F14"
            failure_code_breakdown.setdefault(code, []).append(r["test_id"])

    tool_cases = [r for r in results if r["category"] == "D_tool_use"]
    tool_correct = sum(1 for r in tool_cases if r["deterministic"]["checks"]["eval_tool_selection"]["passed"])
    tool_accuracy = round(tool_correct / len(tool_cases), 4) if tool_cases else None

    rag_results = [r["rag_metrics"] for r in results if r["rag_metrics"]["rag_failure_class"] != "not_applicable"]
    rag_summary = aggregate_rag_metrics(rag_results)

    agent_results = [r["agent_eval"] for r in results]
    agent_summary = aggregate_agent_metrics(agent_results)

    summary = {
        "run_label": label, "mode": mode, "model": model, "prompt_version": prompt_version,
        "total_cases": total, "passed_cases": passed,
        "task_success_rate": round(passed / total, 4) if total else 0.0,
        "avg_judge_score": round(statistics.fmean(judge_scores), 2) if judge_scores else None,
        "tool_selection_accuracy": tool_accuracy,
        "avg_latency_ms": round(statistics.fmean(latencies), 1) if latencies else 0,
        "p95_latency_ms": round(percentile(latencies, 95), 1) if latencies else 0,
        "avg_input_tokens": round(statistics.fmean(input_tokens_list), 1) if input_tokens_list else 0,
        "avg_output_tokens": round(statistics.fmean(output_tokens_list), 1) if output_tokens_list else 0,
        "avg_total_tokens": round(statistics.fmean([i + o for i, o in
                                    zip(input_tokens_list, output_tokens_list)]), 1) if input_tokens_list else 0,
        "total_cost": total_cost,
        "cost_per_successful_task": cost_per_successful_task(total_cost, passed),
        "by_category": by_category, "failed_test_ids_by_category": failed_test_ids_by_category,
        "failure_code_breakdown": failure_code_breakdown,
        "rag_evaluation": rag_summary, "agent_evaluation": agent_summary,
        "judge_limitations": JUDGE_LIMITATIONS.strip(),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    full_report = {"summary": summary, "results": results}

    os.makedirs(REPORTS_DIR, exist_ok=True)
    out_path = os.path.join(REPORTS_DIR, f"{label}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    _write_filled_dataset(label, cases, results)

    try:
        from prompts.registry import update_evaluation_score
        update_evaluation_score(prompt_version, summary["task_success_rate"])
    except Exception:  # pragma: no cover - scoring back to metadata.json must never break a run
        pass

    return full_report, out_path


def _write_filled_dataset(label, cases, results):
    """Writes the evaluation dataset back out (JSONL + CSV) with
    Actual Result / Score / Pass-Fail / Notes populated per case, per Week 6
    §9 ('Store the dataset in JSON/JSONL/CSV... with these fields')."""
    results_by_id = {r["test_id"]: r for r in results}
    filled = []
    for c in cases:
        r = results_by_id.get(c["test_id"])
        row = dict(c)
        if r:
            row["actual_result"] = r["actual_response"]
            row["score"] = r["judge_avg_score"]
            row["pass_fail"] = r["pass_fail"]
            row["failure_code"] = r.get("failure_code")
            checks = r["deterministic"]["checks"]
            failed_checks = [name for name, v in checks.items() if not v["passed"]]
            if failed_checks:
                row["notes"] = f"[{r.get('failure_code')}] {r.get('failure_name')} — failed_checks={failed_checks}"
            else:
                row["notes"] = "all deterministic checks passed"
        filled.append(row)

    jsonl_path = os.path.join(REPORTS_DIR, f"{label}_filled_dataset.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for row in filled:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_path = os.path.join(REPORTS_DIR, f"{label}_filled_dataset.csv")
    fieldnames = ["test_id", "category", "user_input", "expected_behavior", "expected_tool",
                   "expected_source", "expected_structured_output", "approval_required",
                   "critical_failure_conditions", "actual_result", "score", "pass_fail",
                   "failure_code", "notes"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in filled:
            out_row = dict(row)
            out_row["critical_failure_conditions"] = json.dumps(out_row.get("critical_failure_conditions", []))
            out_row["expected_structured_output"] = json.dumps(out_row.get("expected_structured_output"))
            writer.writerow(out_row)


def main():
    parser = argparse.ArgumentParser(description="Run the Week 6 evaluation suite.")
    parser.add_argument("--label", default="baseline_v1")
    parser.add_argument("--dataset", default=DATASET_PATH)
    parser.add_argument("--mode", default="offline", choices=["offline", "live"])
    parser.add_argument("--model", default="gemini-3.6-flash")
    parser.add_argument("--prompt-version", default="v3")
    parser.add_argument("--no-judge", action="store_true")
    args = parser.parse_args()

    report, path = run_suite(args.label, dataset_path=args.dataset, mode=args.mode, model=args.model,
                               prompt_version=args.prompt_version, run_judge=not args.no_judge)
    s = report["summary"]
    print(f"Run '{s['run_label']}' ({s['mode']}, prompt {s['prompt_version']}): "
          f"{s['passed_cases']}/{s['total_cases']} passed "
          f"({s['task_success_rate'] * 100:.1f}%), "
          f"avg judge score={s['avg_judge_score']}, "
          f"P95 latency={s['p95_latency_ms']}ms, total cost=${s['total_cost']}")
    print(f"Report written to {path}")


if __name__ == "__main__":
    main()
