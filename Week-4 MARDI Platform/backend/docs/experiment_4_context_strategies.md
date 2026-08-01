# Experiment 4 — Shared Full Context vs Role-Specific Context

Request: "Compare three cloud platforms for deploying an AI SaaS application." — measuring what the Analyst's ACTUAL prompt payload (role-specific: filtered evidence + criteria) costs versus the alternative (shared full context: the entire WorkflowState, including full trace history).

| Metric | Role-Specific Context (actual) | Shared Full Context (hypothetical) |
|---|---|---|
| Payload size (chars) | 3471 | 10698 |
| Approx. tokens (~4 chars/token) | 867 | 2674 |
| Estimated input-token cost (USD, illustrative rate) | $0.00035 | $0.00107 |
| **Token reduction from role-specific context** | — | **67.6%** |

## Output relevance — measured honestly, not fabricated

This experiment does **not** report a measured 'output relevance' score for the shared-full-context condition, because mock mode's LLM responses are deterministic functions of a few specific input fields — feeding it a larger, noisier payload would not actually change its output the way a real model's output degrades with excess/irrelevant context (a well-documented behavior sometimes called context dilution or the 'lost in the middle' effect). Claiming a measured relevance drop here would be fabricating a number mock mode cannot honestly produce. The token-count difference above is real and directly measured; the relevance/quality argument for role-specific context rests on that documented LLM behavior plus the practical points in `docs/context_management.md` (agents cite evidence IDs instead of re-reading full text, aggregate summaries instead of full evidence dumps, etc.), not on a number this script invents.

## Interpretation

For this run, role-specific context uses **67.6% fewer tokens** than shared full context would, primarily because the full-context version carries the entire execution trace (every tool call, agent start/end, and handoff event) and task plan into every single agent call, none of which the Analyst actually needs to do its job. At scale (longer runs, more revision cycles, larger evidence stores), this gap grows roughly linearly with trace length, since role-specific context stays flat (bounded by evidence + criteria) while shared full context grows with every additional logged event.