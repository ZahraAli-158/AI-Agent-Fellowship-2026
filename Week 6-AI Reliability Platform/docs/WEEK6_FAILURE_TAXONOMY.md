# Week 6 — Failure Taxonomy

Per §40. Every failed evaluation case (deterministic evaluator failure,
guardrail trigger, or judge-flagged issue) is assigned one of the following
codes. Used by `evaluation/runner.py` results and `docs/WEEK6_ROOT_CAUSE_ANALYSIS.md`.

| Code | Name | Description | Detected by |
|---|---|---|---|
| F01 | Retrieval Failure | Correct information existed in the knowledge base but was not retrieved (or the wrong chunks were retrieved) | `eval_citation_presence`, RAG failure classification (§15) |
| F02 | Hallucination | Answer contains claims not supported by retrieved context or verifiable knowledge | LLM judge `groundedness` score, `eval_citation_presence` |
| F03 | Incorrect Tool | Wrong tool selected for the request | `eval_tool_selection` |
| F04 | Incorrect Tool Arguments | Correct tool, wrong/missing/malformed arguments | `eval_tool_arguments` |
| F05 | Agent Routing Failure | Multi-agent/multi-step request routed to the wrong step or skipped a required step | Manual review of `final_state` + trace steps |
| F06 | State Failure | Conversation/task state not updated or updated incorrectly | `eval_completion` |
| F07 | Permission Failure | High-risk action executed without required approval, or a low-risk action wrongly blocked | `eval_approval_compliance`, `eval_forbidden_action` |
| F08 | API Failure | Upstream model/API call failed | `app.reliability.retries` / `app.reliability.fallback` |
| F09 | Timeout | A stage exceeded its allotted time | `app.reliability.timeouts.OperationTimeout` |
| F10 | Structured Output Failure | Response did not match the required schema | `eval_structured_output` |
| F11 | Prompt Injection | Direct or indirect injection succeeded in altering behavior | `app.guardrails.input`, `eval_forbidden_action` |
| F12 | User Input Failure | Malformed, empty, or otherwise invalid input reached the model unfiltered | `app.guardrails.input.validate_input` |
| F13 | Database Failure | A DB read/write failed | Failure-injection tests (`tests/test_week6_failure_injection.py`) |
| F14 | Unknown Failure | Doesn't fit another category — requires manual triage | — |

Every row in `evaluation/reports/*.json` with `pass_fail == "FAIL"` is
expected to be tagged with one of these codes during root-cause analysis
(see `docs/WEEK6_ROOT_CAUSE_ANALYSIS.md`).
