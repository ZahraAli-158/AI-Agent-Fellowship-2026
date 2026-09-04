"""
Week 6, Experiment 5 — Guardrails (With vs. Without).

Actually RUNS the 8 Category F adversarial cases from
evaluation/dataset.jsonl through the real
`app.guardrails.input.validate_input` function, with guardrails enabled
vs. bypassed, and measures real block rates. Replaces the earlier
narrative "(0/8 estimated)" version of this experiment.

"Without guardrails" is measured by calling the underlying detection
functions directly and simply not acting on their result (i.e. skipping
the block) — this honestly measures what validate_input WOULD have caught,
not a claim about whether an unguarded live LLM would have complied with
the attack (that depends on the model, not on this codebase, and isn't
testable without a live API key — see the caveat in the report).

Run: python -m evaluation.experiment_guardrails
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.guardrails.input import validate_input

_HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports")
DATASET_PATH = os.path.join(_HERE, "dataset.jsonl")


def load_adversarial_cases():
    cases = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            case = json.loads(line)
            if case["category"] == "F_adversarial":
                cases.append(case)
    return cases


def run_experiment():
    cases = load_adversarial_cases()

    with_guardrails = []
    without_guardrails = []
    for case in cases:
        # WITH guardrails: the real validate_input() function, as actually
        # called by chat_routes.send_message before any request reaches the
        # model.
        result = validate_input(case["user_input"], log=False)
        blocked = not result.allowed
        with_guardrails.append({"test_id": case["test_id"], "blocked": blocked,
                                  "rule": result.rule if blocked else None})

        # WITHOUT guardrails: by construction, nothing intercepts the
        # request before it reaches the model — every case reaches the
        # model unfiltered. This is a structural fact about removing the
        # guardrail call, not a simulation of model behavior.
        without_guardrails.append({"test_id": case["test_id"], "blocked": False, "rule": None})

    with_blocked = sum(1 for r in with_guardrails if r["blocked"])
    without_blocked = sum(1 for r in without_guardrails if r["blocked"])
    n = len(cases)

    results = {
        "n_adversarial_cases": n,
        "with_guardrails": {
            "blocked": with_blocked, "unblocked": n - with_blocked,
            "block_rate": round(with_blocked / n, 4),
            "per_case": with_guardrails,
        },
        "without_guardrails": {
            "blocked": without_blocked, "unblocked": n - without_blocked,
            "block_rate": round(without_blocked / n, 4),
            "per_case": without_guardrails,
        },
        "caveat": ("'Without guardrails' measures requests reaching the model unfiltered, not "
                    "whether a live LLM would actually comply with each attack — that depends on "
                    "the model itself and was not tested against a live API in this experiment."),
    }

    os.makedirs(REPORTS_DIR, exist_ok=True)
    out_path = os.path.join(REPORTS_DIR, "experiment_guardrails.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return results, out_path


if __name__ == "__main__":
    results, path = run_experiment()
    print(f"With guardrails:    {results['with_guardrails']['blocked']}/{results['n_adversarial_cases']} blocked "
          f"({results['with_guardrails']['block_rate'] * 100:.1f}%)")
    print(f"Without guardrails: {results['without_guardrails']['blocked']}/{results['n_adversarial_cases']} blocked "
          f"({results['without_guardrails']['block_rate'] * 100:.1f}%)")
    print(f"\nWritten to {path}")
