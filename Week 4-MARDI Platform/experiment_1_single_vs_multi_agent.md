# Experiment 1 — Single Agent vs Multi-Agent

Request: "Compare three cloud platforms for deploying an AI SaaS application."

| Metric | Single Agent | Multi-Agent |
|---|---|---|
| Completeness score (0-5 checks) | 2/5 | 5/5 |
| Evidence items cited | 0 (no evidence store) | 4 |
| LLM calls | 1 | ~9 |
| Estimated cost (USD, live-mode rate) | $0.0020 | $0.0180 |
| Latency (mock mode, s) | 0.0 | 0.027 |
| Critic-reviewed | No | Yes (1 revision cycle(s)) |
| Human checkpoints | 0 | 2 |

## Interpretation

The single-agent baseline is cheaper and faster per run (1 vs ~9 LLM calls), but scored 2/5 vs 5/5 on the completeness checks — specifically, it never cites a traceable source, never explicitly separates evidence from opinion, and gives no structured risk/limitation section, because there is no Evidence store, no Critic, and no Report Writer enforcing those sections. This is the concrete cost/quality trade-off Part 1's requirement ("must not immediately send the entire request to one LLM") is designed around: multi-agent costs roughly proportionally more calls, in exchange for traceable, reviewed, structured output.