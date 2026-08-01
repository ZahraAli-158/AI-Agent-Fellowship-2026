import EmptyState from "./EmptyState";
import JsonTreeViewer from "./JsonTreeViewer";
import { Database } from "lucide-react";

const RELEVANT_FIELDS = [
  "user_request", "clarifications", "research_objective", "task_plan",
  "completed_tasks", "evidence", "analysis", "critic_feedback",
  "revision_count", "max_revisions", "checkpoint_1_status", "checkpoint_2_status",
  "final_report", "errors", "workflow_status",
];

export default function StateInspector({ state }) {
  if (!state || Object.keys(state).length === 0) {
    return <EmptyState icon={Database} title="No workflow state yet" body="Start a run to inspect the shared LangGraph state object." />;
  }

  const filtered = {};
  for (const key of RELEVANT_FIELDS) {
    if (key in state) filtered[key] = state[key];
  }

  return (
    <div>
      <p style={{ fontSize: 12, color: "var(--text-faint)", marginBottom: 12 }}>
        Read-only, collapsible view of the shared <span className="mono">WorkflowState</span> object — click any row to expand.
      </p>
      <div style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "12px 14px" }}>
        <JsonTreeViewer data={filtered} />
      </div>
    </div>
  );
}
