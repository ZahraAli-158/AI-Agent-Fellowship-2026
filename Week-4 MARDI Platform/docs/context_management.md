# Context Management Strategy

Per Requirement 13 (Section 21). "Do not send the complete workflow history
to every agent" — here is what each agent actually receives.

| Agent | Receives | Does NOT receive |
|---|---|---|
| Supervisor | `user_request`, `clarifications`, `critic_feedback` (summary only) | Full evidence text, raw researcher tool-call logs |
| Researcher | One `Task` (its own `target`/`topic` parameters) | Other researchers' tasks, evidence, or analysis |
| Analyst | `evidence` filtered via the Evidence Retrieval Tool (by research question / confidence), `evaluation_criteria` | Raw search-tool logs, other agents' prompts/responses, the full `trace` |
| Critic | `AnalysisOutput` only | The underlying raw evidence text (it reviews reasoning quality/structure, not re-verifies each source itself in this design) |
| Writer | `research_objective`, the approved `AnalysisOutput`, evidence store (for reference IDs only) | Critic's rejected drafts from earlier revision cycles, raw trace/log data |

## How large evidence collections are summarized

`app/tools/evidence.py::summarize_evidence_counts` produces aggregate
counts (by research question, by agent, by confidence) for
dashboard/report use, so the Writer's report and the dashboard's Evidence
Panel don't need to re-render every evidence item's full text to convey
"how much was found."

`Evidence.to_summary_line()` gives a one-line compact form
(`[EV-003|High] claim text (source: title)`) — this is what a context
budget-constrained agent would receive instead of the full
`supporting_text` field, if the evidence store grew large.

## How previous results are referenced

Agents reference prior work by ID, not by re-reading it:
- Analyst cites `evidence_refs: List[str]` (evidence IDs), not evidence text, in its handoff.
- Writer's `evidence_references` in the final report are also IDs, resolved against the evidence store only at render time.
- The Critic's `required_revisions` is a short instruction string, not a diff of the full analysis text.

## Token usage tracking (bonus)

`LLMResult` in `app/services/llm_client.py` is the natural extension point:
in live mode, `response.usage.input_tokens` / `output_tokens` from the
Anthropic API response would be captured there and appended to
`state.errors`-style structured trace events (e.g. `{"type": "token_usage",
"agent": ..., "input_tokens": ..., "output_tokens": ...}`) rather than
tracked separately, keeping a single source of observability truth. This is
not currently wired up to avoid making network calls a hard requirement
for running the test suite.
