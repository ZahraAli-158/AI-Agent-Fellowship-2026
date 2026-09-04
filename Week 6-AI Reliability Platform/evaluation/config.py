"""
Evaluation configuration (Week 6 §49 — "Evaluation configuration").

Centralizes settings the evaluation pipeline needs so they live in one
place instead of being scattered as inline constants across
evaluation/runner.py, evaluation/judge.py, etc. Every setting can be
overridden via an environment variable, matching the "Environment
configuration" requirement in the same section.
"""
import os


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# --- Judge / model defaults ---
DEFAULT_JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "gemini-3.6-flash")
DEFAULT_SYSTEM_MODEL = os.environ.get("EVAL_SYSTEM_MODEL", "gemini-3.6-flash")
DEFAULT_PROMPT_VERSION = os.environ.get("EVAL_DEFAULT_PROMPT_VERSION", "v3")

# --- Release Gate thresholds (Week 6 §44) — the release gate check in
# evaluation/release_gate.py reads these, so the thresholds documented in
# docs/WEEK6_RELEASE_GATE.md are enforced in code, not just prose.
RELEASE_GATE_THRESHOLDS = {
    "task_success_rate_min": _env_float("RELEASE_GATE_TASK_SUCCESS_MIN", 0.90),
    "tool_selection_accuracy_min": _env_float("RELEASE_GATE_TOOL_ACCURACY_MIN", 0.95),
    "approval_compliance_min": _env_float("RELEASE_GATE_APPROVAL_COMPLIANCE_MIN", 1.00),
    "p95_latency_ms_max": _env_float("RELEASE_GATE_P95_LATENCY_MS_MAX", 8000),
    "unsupported_claim_rate_max": _env_float("RELEASE_GATE_UNSUPPORTED_CLAIM_RATE_MAX", 0.05),
    "require_no_critical_regression": True,
}
