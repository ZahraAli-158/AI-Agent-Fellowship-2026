"""Week 6 §44 — release gate is checked programmatically, not just
documented as prose thresholds."""
from evaluation.release_gate import check_release_gate
from evaluation.config import RELEASE_GATE_THRESHOLDS


def _fake_report(task_success=0.95, tool_accuracy=0.98, p95=1000, unsupported=0.0, approval_passed=True):
    results = [{
        "test_id": "D09", "category": "D_tool_use",
        "deterministic": {"checks": {"eval_approval_compliance": {"passed": approval_passed}}},
    }]
    return {
        "summary": {
            "run_label": "fake_run", "task_success_rate": task_success,
            "tool_selection_accuracy": tool_accuracy, "p95_latency_ms": p95,
            "rag_evaluation": {"unsupported_claim_rate": unsupported},
        },
        "results": results,
    }


def test_release_gate_passes_when_all_thresholds_met():
    report = _fake_report()
    result = check_release_gate(report)
    assert result["release_ready"]


def test_release_gate_fails_on_low_task_success():
    report = _fake_report(task_success=0.5)
    result = check_release_gate(report)
    assert not result["release_ready"]
    assert not result["checks"]["task_success_rate"]["passed"]


def test_release_gate_fails_on_high_p95_latency():
    report = _fake_report(p95=15000)
    result = check_release_gate(report)
    assert not result["checks"]["p95_latency_ms"]["passed"]


def test_release_gate_fails_on_approval_noncompliance():
    report = _fake_report(approval_passed=False)
    result = check_release_gate(report)
    assert not result["checks"]["approval_compliance"]["passed"]


def test_release_gate_fails_on_high_unsupported_claim_rate():
    report = _fake_report(unsupported=0.5)
    result = check_release_gate(report)
    assert not result["checks"]["unsupported_claim_rate"]["passed"]


def test_release_gate_incorporates_regression_result():
    report = _fake_report()
    regression_result = {"no_critical_regression": False}
    result = check_release_gate(report, regression_result=regression_result)
    assert not result["release_ready"]
    assert not result["checks"]["no_critical_regression"]["passed"]


def test_release_gate_thresholds_are_env_configurable(monkeypatch):
    monkeypatch.setenv("RELEASE_GATE_TASK_SUCCESS_MIN", "0.5")
    import importlib
    import evaluation.config as config_module
    importlib.reload(config_module)
    assert config_module.RELEASE_GATE_THRESHOLDS["task_success_rate_min"] == 0.5
    importlib.reload(config_module)  # restore defaults for other tests


def test_real_agent_system_v3_report_passes_release_gate():
    import json
    import os
    from evaluation.runner import REPORTS_DIR
    with open(os.path.join(REPORTS_DIR, "agent-system-v3.json"), "r", encoding="utf-8") as f:
        report = json.load(f)
    result = check_release_gate(report)
    assert result["release_ready"]
