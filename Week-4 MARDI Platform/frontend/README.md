# MARDI Frontend

React + Vite dashboard for the Multi-Agent Research and Decision
Intelligence Platform. Consumes the FastAPI backend in `../backend` —
every panel here reads live data; there is no mock/hardcoded data anywhere
in this app.

## Run

```bash
npm install
npm run dev
```

Open http://localhost:5173. Requires the backend running on port 8000
(see `../backend/README.md`) — `vite.config.js` proxies `/api/*` requests
to `http://127.0.0.1:8000` so no CORS configuration is needed in dev.

## Structure

```
src/
├── main.jsx              # entry point
├── App.jsx                # top-level layout, tabs, polling orchestration
├── api/client.js           # fetch wrapper for every backend endpoint
├── hooks/usePolling.js      # generic interval-polling hook
├── components/
│   ├── Sidebar.jsx           # run history + new-run button
│   ├── RequestForm.jsx        # initial request input + example chips
│   ├── AgentPipeline.jsx       # Requirement 16's "Supervisor ✓ / Researcher B Running" view
│   ├── TaskPlanTable.jsx        # dynamic task plan with live status
│   ├── EvidencePanel.jsx         # evidence store, filters, aggregates
│   ├── AnalysisReview.jsx         # Analyst output vs Critic feedback, revision cycle
│   ├── ExecutionLog.jsx            # structured trace (no chain-of-thought)
│   ├── StateInspector.jsx           # read-only shared-state field viewer
│   ├── ReportView.jsx                # final report, evidence/analysis/recommendation tags
│   ├── CheckpointModal.jsx            # blocks on pending human checkpoints
│   ├── StatusBadge.jsx, Panel.jsx, Stat.jsx, EmptyState.jsx   # small shared UI atoms
└── styles/App.css            # dark enterprise theme (CSS variables, no framework)
```

## How live data flows

1. `POST /api/runs` starts a run; the returned `run_id` becomes the active run.
2. `usePolling` hooks in `App.jsx` hit `/status`, `/tasks`, `/evidence`,
   `/trace`, `/report`, `/state` on an interval (faster while the run is
   live, slower once finished) and pass the results down as props.
3. When the backend reports a `pending_checkpoint` in `/status`,
   `CheckpointModal` renders over everything else. Submitting a decision
   calls `POST /api/runs/{id}/checkpoint`, which unblocks the backend's
   waiting thread — the next poll picks up the workflow's progress.

No component fetches on its own; `App.jsx` owns all network calls and
passes plain data down, keeping every panel a simple, testable, presentational
component.
