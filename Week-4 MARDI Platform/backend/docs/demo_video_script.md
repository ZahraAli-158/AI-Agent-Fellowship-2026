# Demo Video — Recording Script

A ready-to-follow script for a ~5 minute screen recording. Use
Windows Game Bar (Win+Alt+R) or OBS Studio (free) to record your screen.
Read the narration lines aloud as you perform each action.

## Setup before recording

1. Both servers running (`uvicorn` on :8000, `npm run dev` on :5173)
2. Browser at http://localhost:5173, zoomed to a comfortable size
3. Have this script open on a second screen/phone to read from

## Shot list (with narration)

**0:00 – 0:30 — Introduction**
> "This is MARDI — a Multi-Agent Research and Decision Intelligence
> Platform. It's a FastAPI backend running a LangGraph multi-agent
> workflow with five specialized agents, and a React dashboard that
> shows the whole thing live. Let me walk through a real run."

**0:30 – 1:00 — Starting a request**
- Click an example chip (e.g. "Research the current open-source agent
  frameworks...")
- Click "Run Workflow"
> "I'll use one of the example requests. The Supervisor agent analyzes
> this first — extracting the objective, sub-questions, and evaluation
> criteria — before any research happens."

**1:00 – 1:30 — Checkpoint 1**
- Show the modal that appears
> "Before any research runs, the system pauses for human approval — this
> is Requirement 12's first checkpoint. It shows the exact plan: which
> tasks, which agent, and what's expected. I'll approve it."
- Click Approve

**1:30 – 2:15 — Live pipeline**
- Switch to Overview tab, point at the Agent Pipeline and Progress Timeline
> "Now three Researcher agents run in parallel — one per candidate
> framework — which is Requirement 11's parallel execution. You can see
> the pipeline and the 7-stage progress timeline update live."

**2:15 – 2:45 — Evidence tab**
- Click Evidence tab, demonstrate search + confidence filter
> "Every piece of evidence has a structured ID, confidence level, source,
> and the specific research question it answers. I can search and filter
> by confidence or by which researcher found it."

**2:45 – 3:15 — Analysis & Critic**
- Click Analysis & Critic tab
> "The Analyst compares the evidence against the criteria, and the Critic
> reviews that work — here you can see it flagged a low-confidence gap
> and requested one revision cycle, which is the quality-control loop from
> Requirement 10."

**3:15 – 3:35 — Checkpoint 2**
- Approve the final review modal
> "Before the report is finalized, there's a second human checkpoint —
> reviewing the actual recommendation."

**3:35 – 4:15 — Final Report + export**
- Click Final Report tab, scroll through sections, click Export → show dropdown
> "The final report clearly separates evidence, analysis, and
> recommendation with color-coded tags, and exports as Markdown, PDF, or
> Word."

**4:15 – 4:45 — Execution Log + State Inspector**
- Click Execution Log, then State Inspector
> "For observability, there's a full execution trace — every agent start,
> tool call, and handoff, with no chain-of-thought stored — and a
> collapsible view of the complete shared workflow state."

**4:45 – 5:00 — Closing**
- Show Sidebar → Run History
> "And every run is saved in history for later review. That's the full
> workflow, end to end."

## After recording

1. Trim dead air at the start/end
2. Export as MP4
3. Upload to YouTube (unlisted) or GitHub's video upload in a release/issue
4. Add the link to the main `README.md`'s "Demo Video" section
