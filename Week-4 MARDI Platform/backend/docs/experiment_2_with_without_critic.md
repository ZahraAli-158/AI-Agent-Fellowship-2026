# Experiment 2 — With vs Without Critic

Request: "Research the current open-source agent frameworks and recommend one for a small engineering team." (chosen because its first research task always surfaces a low-confidence 'reliability' evidence item, giving the Critic something real to catch).

| Signal | With Critic (max_revisions=2) | Without Critic (max_revisions=0) |
|---|---|---|
| Revision cycles used | 1 | 0 |
| Analyst independently detects the low-confidence gap | True | True |
| Critic explicitly names a problem in its feedback | False | True |
| **Conclusions show a critic-driven revision actually happened** | **True** | **False** |
| Final report's Risks section surfaces the gap | True | True |
| Final workflow status | completed | completed |

## Interpretation

The Analyst independently flags the low-confidence evidence gap in both conditions (it computes `known_gaps` directly from the evidence confidence distribution, with no dependency on the Critic) — so a naive 'does the gap get flagged at all' signal doesn't isolate the Critic's contribution. The row that does isolate it is whether the conclusions show a **critic-driven revision actually happened**: with the Critic able to act (`max_revisions=2`), it reviews the Analyst's first pass, flags the gap as an *unsupported-claims* problem, and forces one revision cycle whose output explicitly notes what was addressed. With `max_revisions=0`, the Critic node still runs and still produces the same `revision_requested` decision internally, but the routing logic (`decide_after_critic`) is forced to treat the cap as already reached, so the Analyst's un-revised first draft goes straight to the Writer with no record of a critic-driven correction. This is the concrete, measurable value one revision cycle buys.

*(Note: `critic_explicitly_flagged_a_problem` looks reversed at first glance because it reflects the LAST recorded critic_feedback in each run — in the with-critic case, that's the critic's SECOND look, after the revision, where it now approves; in the without-critic case, it's the critic's only (rejected) look, whose rejection was simply never acted on.)*