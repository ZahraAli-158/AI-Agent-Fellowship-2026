# Evaluation Metrics — Section 29

Computed from the same 25 real runs used in `docs/evaluation_dataset.md` (`LLM_MODE=mock`, deterministic and reproducible — run `python -m evaluation.evaluation_metrics` to regenerate).

| Metric | Measured Value | Target | Status |
|---|---|---|---|
| Task Planning Accuracy | 100.0% | — | — |
| Agent Routing Accuracy | 100.0% | ≥ 90% | ✅ MET |
| Workflow Completion Rate | 100.0% | ≥ 80% | ✅ MET |
| Evidence Coverage (avg items/run) | 3.27 | — | — |
| Evidence Coverage (runs w/ any evidence) | 59.1% | — | — |
| Critic Detection Rate | 92.3% | — | — |
| Handoff Success Rate | 100.0% | ≥ 90% | ✅ MET |
| Human Approval Compliance | 100.0% | ≥ 100% | ✅ MET |
| Average Workflow Time (s, mock mode) | 0.025s | — | — |
| Average Agent Calls per Run | 7.00 | — | — |
| Approximate Cost Per Run (USD, estimated live-mode) | $0.0140 | — | — |

## Notes on methodology

- All metrics except cost are **measured directly** from real workflow executions in mock LLM mode — mock mode exercises the exact same graph, routing, and agent logic as live mode, only the LLM text generation itself is swapped for a deterministic function, so orchestration-level metrics (routing, handoffs, completion, human approval) are representative of live-mode behavior too.
- **Approximate Cost Per Run** is the only estimated (not measured) figure, since mock mode makes zero network calls and therefore costs $0 — the estimate uses a conservative small-model per-call price ($0.002/call) multiplied by the average number of LLM calls a run makes.
- **Evidence Coverage** is reported two ways: average item count (useful for judging report richness) and fraction of runs with any evidence at all (useful for judging how often the local corpus's limited topic coverage causes a legitimate missing-evidence failure — see docs/evaluation_dataset.md for detail).
- **Human Approval Compliance** measures whether checkpoints were properly surfaced and resolved (never silently bypassed) across every non-ambiguous, non-empty-request run — it does not by itself measure whether the *content* shown at each checkpoint was accurate (that's covered by the evaluation dataset's per-scenario checks).