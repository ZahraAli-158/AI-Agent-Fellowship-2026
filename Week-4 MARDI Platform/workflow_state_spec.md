# Workflow State Specification

Full field-by-field spec of `app/graph/state.py::WorkflowState`, per
Requirement 8 (Section 16) and Section 27's required format.

| Field | Type | Purpose | Read by | Write by |
|---|---|---|---|---|
| `run_id` | str | Unique run identifier for tracing/history | All | Supervisor (set once at start) |
| `user_request` | str | Original, unmodified user request | All | Supervisor (set once at start) |
| `clarifications` | List[str] | User's answers to clarification questions | Supervisor | Human checkpoint (`clarify` node) |
| `needs_clarification` | bool | Whether the request was ambiguous | Supervisor, routing | Supervisor (`analyze_request`) |
| `clarification_questions` | List[str] | Questions to ask the user | Human checkpoint | Supervisor (`analyze_request`) |
| `research_objective` | dict | Objective, sub-questions, criteria, constraints, missing info | All | Supervisor (`analyze_request`) |
| `task_plan` | List[Task] | The dynamically generated plan | All | Supervisor (`create_plan`) |
| `current_tasks` | List[str] (reducer: add) | Task IDs currently in flight | Dashboard/observability | Researcher nodes |
| `completed_tasks` | List[str] (reducer: add) | Task IDs finished | Supervisor, routing | Supervisor, Researcher |
| `evidence` | List[Evidence] (reducer: add) | The evidence store | Analyst, Critic, Writer | Researcher (parallel-safe via reducer) |
| `analysis` | Optional[AnalysisOutput] | Analyst's comparison output | Critic, Writer | Analyst |
| `critic_feedback` | Optional[CriticFeedback] | Critic's review result | Supervisor, Analyst | Critic |
| `revision_count` | int | How many revision cycles have run | Supervisor, routing | Supervisor (`decide_after_critic`) |
| `max_revisions` | int | Hard cap on revision cycles | Supervisor, routing | set once at start |
| `checkpoint_1_status` | str | waiting / approved / edited / rejected | All | Human checkpoint 1 |
| `checkpoint_2_status` | str | waiting / approved / request_changes | All | Human checkpoint 2 |
| `final_report` | Optional[FinalReport] | The finished deliverable | All | Writer |
| `errors` | List[dict] (reducer: add) | Structured failure log | Dashboard/observability | Any agent |
| `trace` | List[dict] (reducer: add) | Structured execution events (no chain-of-thought) | Dashboard/observability | Every node |
| `workflow_status` | str | Current overall status (see `WorkflowStatus` enum) | All | Every node |

## Why reducers matter here

`evidence`, `completed_tasks`, `errors`, and `trace` are the fields written
by **parallel** branches (the fan-out over research tasks). Each is declared
as `Annotated[List[X], operator.add]` so that when three `researcher` node
invocations each return, e.g., `{"evidence": [...]}` in the same LangGraph
"superstep", their lists are concatenated instead of one overwriting
another. Every other field is written by exactly one node at a time, so a
plain (non-reducer) field is safe.

## Agents do not exchange raw chat history

No agent ever receives the full `trace` or another agent's raw prompt/
response text. Each agent's LLM call payload is built from a narrow,
purpose-built subset of state (see `docs/context_management.md`), which is
what Requirement 13 (Context Management) and the "agents should not rely
only on passing long chat histories to each other" instruction in
Requirement 8 both require.
