"""
Week 6 §40 — Failure Taxonomy classifier.

Assigns exactly one F01-F14 code (see docs/WEEK6_FAILURE_TAXONOMY.md) to
every FAILED evaluation case, based on which specific evaluator(s) failed.
Called by evaluation/runner.py for every case with pass_fail == "FAIL", so
"every failed evaluation receives a failure code" is enforced in code, not
left to a person doing it by hand afterward.

Priority order matters: a case can fail multiple checks at once, so more
specific/severe categories are checked before generic ones (e.g. a
prompt-injection failure is reported as F11 even if it also happens to
fail eval_completion, since F11 is the more informative/actionable label).
"""

FAILURE_CODES = {
    "F01": "Retrieval Failure", "F02": "Hallucination", "F03": "Incorrect Tool",
    "F04": "Incorrect Tool Arguments", "F05": "Agent Routing Failure", "F06": "State Failure",
    "F07": "Permission Failure", "F08": "API Failure", "F09": "Timeout",
    "F10": "Structured Output Failure", "F11": "Prompt Injection", "F12": "User Input Failure",
    "F13": "Database Failure", "F14": "Unknown Failure",
}


def classify_failure(case, actual, det_result, agent_result, rag_result):
    """Returns (code, name) — e.g. ("F04", "Incorrect Tool Arguments")."""
    checks = det_result.get("checks", {})
    agent_checks = agent_result.get("checks", {})
    guardrail_rule = actual.get("guardrail_triggered") or ""

    # F11 — prompt injection: a guardrail specifically caught an injection
    # attempt, or a forbidden-action condition (tied to injection/jailbreak
    # language in the dataset) was triggered.
    if guardrail_rule.startswith("prompt_injection"):
        return "F11", FAILURE_CODES["F11"]
    if not checks.get("eval_forbidden_action", {"passed": True})["passed"]:
        return "F11", FAILURE_CODES["F11"]

    # F12 — user input failure: any other input guardrail fired (empty,
    # too long, malformed, unsupported operation).
    if guardrail_rule:
        return "F12", FAILURE_CODES["F12"]

    # F07 — permission/approval failure.
    if not checks.get("eval_approval_compliance", {"passed": True})["passed"]:
        return "F07", FAILURE_CODES["F07"]

    # F01/F02 — RAG-specific failures, from the dedicated RAG classifier.
    if rag_result.get("rag_failure_class") == "retrieval_failure":
        return "F01", FAILURE_CODES["F01"]
    if rag_result.get("rag_failure_class") == "generation_failure":
        return "F02", FAILURE_CODES["F02"]
    if not checks.get("eval_citation_presence", {"passed": True})["passed"]:
        return "F02", FAILURE_CODES["F02"]

    # F03/F04 — tool selection vs tool argument failures.
    if not checks.get("eval_tool_selection", {"passed": True})["passed"]:
        return "F03", FAILURE_CODES["F03"]
    if not checks.get("eval_tool_arguments", {"passed": True})["passed"]:
        return "F04", FAILURE_CODES["F04"]

    # F05 — routing/planning failure (agent-level).
    if not agent_checks.get("eval_planning", {"passed": True})["passed"] or \
       not agent_checks.get("eval_intent_understanding", {"passed": True})["passed"]:
        return "F05", FAILURE_CODES["F05"]

    # F06 — state management / recovery / completion failure.
    if not agent_checks.get("eval_state_management", {"passed": True})["passed"] or \
       not agent_checks.get("eval_recovery_behavior", {"passed": True})["passed"] or \
       not checks.get("eval_completion", {"passed": True})["passed"]:
        return "F06", FAILURE_CODES["F06"]

    # F10 — structured output failure.
    if not checks.get("eval_structured_output", {"passed": True})["passed"]:
        return "F10", FAILURE_CODES["F10"]

    return "F14", FAILURE_CODES["F14"]
