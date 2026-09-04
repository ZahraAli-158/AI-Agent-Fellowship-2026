"""Week 6 §40 — every failed evaluation case receives an automated F01-F14
failure code (not just a documented taxonomy)."""
from evaluation.evaluators.failure_taxonomy import classify_failure, FAILURE_CODES
from evaluation.runner import run_suite


def test_all_14_codes_are_defined():
    assert set(FAILURE_CODES.keys()) == {f"F{i:02d}" for i in range(1, 15)}


def test_classify_failure_prompt_injection():
    case = {"category": "F_adversarial"}
    actual = {"guardrail_triggered": "prompt_injection:override_instructions"}
    code, name = classify_failure(case, actual, {"checks": {}}, {"checks": {}}, {"rag_failure_class": "not_applicable"})
    assert code == "F11"


def test_classify_failure_user_input_failure():
    case = {"category": "F_adversarial"}
    actual = {"guardrail_triggered": "unsupported_operation:web_browsing"}
    code, name = classify_failure(case, actual, {"checks": {}}, {"checks": {}}, {"rag_failure_class": "not_applicable"})
    assert code == "F12"


def test_classify_failure_incorrect_tool():
    case = {"category": "D_tool_use"}
    actual = {}
    det = {"checks": {"eval_tool_selection": {"passed": False}}}
    code, name = classify_failure(case, actual, det, {"checks": {}}, {"rag_failure_class": "not_applicable"})
    assert code == "F03"


def test_classify_failure_incorrect_tool_arguments():
    case = {"category": "D_tool_use"}
    actual = {}
    det = {"checks": {"eval_tool_selection": {"passed": True}, "eval_tool_arguments": {"passed": False}}}
    code, name = classify_failure(case, actual, det, {"checks": {}}, {"rag_failure_class": "not_applicable"})
    assert code == "F04"


def test_classify_failure_retrieval_failure():
    case = {"category": "E_knowledge_rag"}
    code, name = classify_failure(case, {}, {"checks": {}}, {"checks": {}},
                                    {"rag_failure_class": "retrieval_failure"})
    assert code == "F01"


def test_classify_failure_generation_failure():
    case = {"category": "E_knowledge_rag"}
    code, name = classify_failure(case, {}, {"checks": {}}, {"checks": {}},
                                    {"rag_failure_class": "generation_failure"})
    assert code == "F02"


def test_classify_failure_permission_failure():
    case = {"category": "D_tool_use"}
    det = {"checks": {"eval_approval_compliance": {"passed": False}}}
    code, name = classify_failure(case, {}, det, {"checks": {}}, {"rag_failure_class": "not_applicable"})
    assert code == "F07"


def test_classify_failure_state_failure_from_recovery():
    case = {"category": "D_tool_use"}
    det = {"checks": {}}
    agent = {"checks": {"eval_recovery_behavior": {"passed": False}}}
    code, name = classify_failure(case, {}, det, agent, {"rag_failure_class": "not_applicable"})
    assert code == "F06"


def test_classify_failure_falls_back_to_unknown():
    code, name = classify_failure({"category": "A_normal"}, {}, {"checks": {}}, {"checks": {}},
                                    {"rag_failure_class": "not_applicable"})
    assert code == "F14"


def test_baseline_v1_every_fail_has_a_failure_code():
    import os
    from evaluation.runner import REPORTS_DIR
    label = "test_failure_codes_v1"
    try:
        report, _ = run_suite(label, mode="offline", prompt_version="v1", run_judge=False)
        for r in report["results"]:
            if r["pass_fail"] == "FAIL":
                assert r["failure_code"] is not None
                assert r["failure_code"] in FAILURE_CODES
            else:
                assert r["failure_code"] is None
    finally:
        for suffix in (".json", "_filled_dataset.jsonl", "_filled_dataset.csv"):
            path = os.path.join(REPORTS_DIR, f"{label}{suffix}")
            if os.path.exists(path):
                os.remove(path)
        _restore_v1_score()


def test_summary_includes_failure_code_breakdown():
    import os
    from evaluation.runner import REPORTS_DIR
    label = "test_failure_breakdown_v1"
    try:
        report, _ = run_suite(label, mode="offline", prompt_version="v1", run_judge=False)
        assert "failure_code_breakdown" in report["summary"]
    finally:
        for suffix in (".json", "_filled_dataset.jsonl", "_filled_dataset.csv"):
            path = os.path.join(REPORTS_DIR, f"{label}{suffix}")
            if os.path.exists(path):
                os.remove(path)
        _restore_v1_score()


def _restore_v1_score():
    """Undo update_evaluation_score("v1", ...) side effects from a
    throwaway run so prompts/metadata.json keeps reflecting the real
    canonical baseline_v1.json report."""
    import os
    import json
    from evaluation.runner import REPORTS_DIR
    from prompts.registry import update_evaluation_score
    baseline_path = os.path.join(REPORTS_DIR, "baseline_v1.json")
    if os.path.exists(baseline_path):
        with open(baseline_path, "r", encoding="utf-8") as f:
            real_score = json.load(f)["summary"]["task_success_rate"]
        update_evaluation_score("v1", real_score)
