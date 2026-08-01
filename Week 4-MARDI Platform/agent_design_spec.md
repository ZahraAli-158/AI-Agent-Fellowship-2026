# Agent Design Specification

Per Requirement 4 (Section 12) and Section 26. Format: Agent Name, Purpose,
Responsibilities, Inputs, Outputs, Tools, Allowed Actions, Prohibited
Actions, Handoff Conditions, Failure Conditions, Prompt Strategy.

---

## 1. Supervisor / Orchestrator Agent

- **Purpose**: Understand the user's objective and drive the workflow without doing research itself.
- **Responsibilities**: Request analysis, clarification detection, dynamic task planning, tracking task completion, deciding when the workflow is done or must terminate.
- **Inputs**: `user_request`, `clarifications`, `critic_feedback`, `task_plan` status.
- **Outputs**: `research_objective`, `task_plan`, `workflow_status`, `revision_count` updates.
- **Tools**: none (database/state read-write only — see permission matrix below).
- **Allowed Actions**: parse request, generate task plan, increment `revision_count`, mark workflow complete/failed.
- **Prohibited Actions**: calling the search tool; writing Evidence; rewriting Analyst/Critic output.
- **Handoff Conditions**: hands the approved plan to Researcher agents (via `checkpoint_1`); hands final termination decisions after Critic review.
- **Failure Conditions**: invalid/unparsable LLM JSON output -> `invalid_structured_output` error, workflow marked `failed`; underlying model API failure -> `model_api_failure` error after one retry.
- **Prompt Strategy**: single structured-JSON-only system prompt; the topic/candidate detection (Section "Dynamic Planning") is done with a lightweight deterministic keyword step around the LLM call so planning depends on the request even in mock mode.

## 2. Research Agent

- **Purpose**: Gather structured, sourced evidence for one specific research task.
- **Responsibilities**: Query the approved local corpus, extract relevant excerpts, tag each item's confidence and evidence type (fact/claim/assumption/missing information), store it.
- **Inputs**: a single `Task` (via `Send`), containing `target` and `topic` parameters.
- **Outputs**: `List[Evidence]`, `completed_tasks` update.
- **Tools**: Search Tool, Content Extraction Tool, Evidence Storage Tool.
- **Allowed Actions**: search the local corpus (optionally filtered by framework/topic), extract excerpts, construct and store Evidence objects.
- **Prohibited Actions**: comparing across options (that's the Analyst's job); writing to `analysis`, `critic_feedback`, or `final_report`.
- **Handoff Conditions**: hands evidence to the Analyst once dispatched via the parallel fan-in edge `researcher -> analyst`.
- **Failure Conditions**: empty corpus hits -> retries once with a broadened query -> if still empty, logs `empty_research_results` to `state.errors` and marks its task complete without evidence (does not crash the graph).
- **Prompt Strategy**: N/A for the corpus search itself (deterministic tool call); an LLM call would only be used in a live-web variant to summarize retrieved pages.

## 3. Analyst Agent

- **Purpose**: Compare alternatives strictly from retrieved evidence.
- **Responsibilities**: Build a comparison framework against the stated evaluation criteria, produce trade-off conclusions, label assumptions explicitly, flag known evidence gaps.
- **Inputs**: filtered `Evidence` (via Evidence Retrieval Tool), `evaluation_criteria`, prior `critic_feedback` (if this is a revision pass).
- **Outputs**: `AnalysisOutput` (comparison_framework, conclusions, evidence_refs, assumptions, known_gaps).
- **Tools**: Evidence Retrieval Tool, Calculator (for weighted scoring).
- **Allowed Actions**: read evidence, compute weighted scores, cite evidence IDs, state assumptions.
- **Prohibited Actions**: calling the search tool directly (must work from what Researchers already retrieved); inventing facts with no evidence backing.
- **Handoff Conditions**: hands `AnalysisOutput` to the Critic.
- **Failure Conditions**: no evidence available at all -> `missing_evidence` error, workflow routed to `END` rather than crashing on a `None` analysis.
- **Prompt Strategy**: system prompt explicitly forbids inventing unsupported facts; user payload is the evidence list + criteria as JSON, not the full workflow history.

## 4. Critic / Reviewer Agent

- **Purpose**: Evaluate — not rewrite — the Analyst's output.
- **Responsibilities**: Score against six criteria (evidence coverage, logical consistency, completeness, unsupported claims, contradictions, relevance); decide approve vs revision-requested; state exactly what's missing.
- **Inputs**: `AnalysisOutput`.
- **Outputs**: `CriticFeedback` (decision, problems_found, missing_evidence, required_revisions, criteria_scores).
- **Tools**: none (pure evaluation over the analysis object already in state).
- **Allowed Actions**: approve, request revision with specific required changes.
- **Prohibited Actions**: editing analysis text directly; calling research/search tools.
- **Handoff Conditions**: hands `CriticFeedback` to the Supervisor's `decide_after_critic` node, which enforces the revision cap.
- **Failure Conditions**: model API failure after one retry -> logged, workflow halted rather than looping indefinitely.
- **Prompt Strategy**: system prompt lists the six review criteria explicitly and forbids rewriting; response is structured JSON only.

## 5. Report Writer Agent

- **Purpose**: Produce the final, professional deliverable from validated state only.
- **Responsibilities**: Organize findings, clearly tag Evidence vs Analysis vs Recommendation, preserve source references, write the executive summary/methodology/risks sections.
- **Inputs**: `research_objective`, approved `AnalysisOutput`, `Evidence` store.
- **Outputs**: `FinalReport` (markdown-exportable).
- **Tools**: Report Export (markdown formatter) only.
- **Allowed Actions**: synthesize and format validated content.
- **Prohibited Actions**: calling the search tool; introducing new claims not present in evidence/analysis (no "unrestricted web search access", per Requirement 4's explicit example).
- **Handoff Conditions**: hands the draft report to the human `checkpoint_2` (Final Recommendation Review).
- **Failure Conditions**: model API failure -> logged, routed to `END` rather than emitting a partially-built report.
- **Prompt Strategy**: system prompt explicitly says "do NOT invent new research"; user payload is the objective + analysis object, not raw evidence text dumps (context management, see docs/context_management.md).
