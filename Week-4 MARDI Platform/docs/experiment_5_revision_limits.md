# Experiment 5 — Different Revision Limits (0, 1, 2)

Request: "Research the current open-source agent frameworks and recommend one for a small engineering team." (same evidence-gap-triggering request used in Experiment 2, run three times with `max_revisions` set to 0, 1, and 2).

| max_revisions | Revision cycles actually used | Gap explicitly addressed | Extra LLM calls vs. 0 | Est. extra cost (USD) | Final status |
|---|---|---|---|---|---|
| 0 | 0 | False | +0 | $0.0000 | completed |
| 1 | 1 | True | +2 | $0.0040 | completed |
| 2 | 1 | True | +2 | $0.0040 | completed |

## Interpretation

With `max_revisions=0`, the Critic's rejection is never actionable — the workflow completes on the Analyst's first pass regardless of what the Critic finds, at the lowest cost. With `max_revisions=1` or higher, the single evidence gap this request always surfaces gets caught and explicitly addressed in exactly one revision cycle — going from 1 to 2 does not buy anything further for THIS request, because the mock Critic only ever asks for one concrete fix before approving (a deliberate design choice so the quality-control loop is demonstrably bounded, per Requirement 10). In a live-LLM deployment where the Critic might reasonably ask for more than one round of changes on harder requests, the marginal cost of raising the cap from 1 to 2 is exactly one more Analyst+Critic call pair (~2 calls), spent only if actually needed — the cap is a ceiling, not a fixed cost.