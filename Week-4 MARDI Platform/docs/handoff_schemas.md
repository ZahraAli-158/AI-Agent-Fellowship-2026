# Agent Handoff Schemas

Per Requirement 9 (Section 17). Every handoff between agents is a typed
Pydantic object, not free text.

## Researcher -> Analyst

Carried implicitly through `state.evidence` (merged via reducer from all
parallel Researcher branches). Each `Evidence` item provides:

| Field | Description |
|---|---|
| `research_question` | Which task (e.g. `R2`) this answers — lets the Analyst group by comparison target |
| `claim` | The specific finding |
| `confidence` | High / Medium / Low |
| `evidence_type` | fact / claim / assumption / missing_information |
| `agent_id` | Which Researcher instance produced it |

Known gaps (a Researcher couldn't find anything for a task) surface as a
structured `errors` entry with `type: empty_research_results`, which the
Analyst can see via `state.errors` and factor into `known_gaps`.

## Analyst -> Critic

`AnalysisOutput`:
```
comparison_framework: str        # how the alternatives were compared
conclusions: List[str]
evidence_refs: List[str]         # evidence IDs actually cited
assumptions: List[str]           # explicitly labeled, never silent
known_gaps: List[str]            # what evidence was missing/weak
```

## Critic -> Supervisor

`CriticFeedback`:
```
decision: "approved" | "revision_requested"
problems_found: List[str]
missing_evidence: List[str]
required_revisions: Optional[str]
criteria_scores: dict            # pass/fail per the 6 review criteria
```

The Supervisor's `decide_after_critic` node is the only place that acts on
this — it increments `revision_count` (capped at `max_revisions`) and
routes back to the Analyst, or forwards to the Writer.

## Writer -> Human (Checkpoint 2)

`FinalReport`:
```
title, executive_summary, research_objective, methodology
findings: List[{tag: evidence|analysis|recommendation, text: str}]
risks_and_limitations: str
recommendation: str
evidence_references: List[str]
```

## Human checkpoints (both directions)

`human_review_callback(checkpoint_name: str, payload: dict) -> dict`

| Checkpoint | Payload shown to human | Expected response |
|---|---|---|
| `clarification` | `{questions: [...]}` | `{answers: [...]}` |
| `checkpoint_1_plan_approval` | `{objective, planned_tasks, expected_output}` | `{decision: approve\|edit\|reject}` |
| `checkpoint_2_final_review` | `{title, recommendation}` | `{decision: approve\|request_changes}` |
