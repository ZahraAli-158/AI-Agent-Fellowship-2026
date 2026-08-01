import { useState } from "react";
import React from "react";
import { ChevronRight, ChevronDown, ListTree } from "lucide-react";
import StatusBadge from "./StatusBadge";
import EmptyState from "./EmptyState";

const PRIORITY_COLOR = { High: "var(--danger)", Medium: "var(--warning)", Low: "var(--text-faint)" };

export default function TaskPlanTable({ tasks }) {
  const [expanded, setExpanded] = useState(null);

  if (!tasks || tasks.length === 0) {
    return <EmptyState icon={ListTree} title="No task plan yet" body="The Supervisor generates this dynamically once a run starts." />;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Task</th>
          <th>Description</th>
          <th>Agent</th>
          <th>Dependencies</th>
          <th>Priority</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((t) => (
          <React.Fragment key={t.id}>
            <tr style={{ cursor: "pointer" }} onClick={() => setExpanded(expanded === t.id ? null : t.id)}>
              <td className="mono" style={{ color: "var(--accent)", fontWeight: 700 }}>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                  {expanded === t.id ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  {t.id}
                </span>
              </td>
              <td>{t.description}</td>
              <td>{t.assigned_agent}</td>
              <td className="mono" style={{ color: "var(--text-faint)" }}>{t.dependencies.join(", ") || "—"}</td>
              <td>
                <span style={{ color: PRIORITY_COLOR[t.priority] || "var(--text-dim)", fontWeight: 600, fontSize: 12 }}>
                  {t.priority}
                </span>
              </td>
              <td><StatusBadge status={t.live_status} /></td>
            </tr>
            {expanded === t.id && (
              <tr>
                <td colSpan={6} style={{ background: "var(--surface-2)", fontSize: 12, color: "var(--text-dim)" }}>
                  Completed at: {t.completed_at || "—"}
                  {t.parameters?.target && <> · Target: <b>{t.parameters.target}</b></>}
                </td>
              </tr>
            )}
          </React.Fragment>
        ))}
      </tbody>
    </table>
  );
}
