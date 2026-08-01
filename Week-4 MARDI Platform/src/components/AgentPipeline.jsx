import { ChevronRight, Crown, Search, BarChart3, ShieldCheck, FileText } from "lucide-react";
import StatusBadge from "./StatusBadge";

const AGENT_ICON = {
  Supervisor: { icon: Crown, gradient: "var(--grad-indigo)" },
  Researcher: { icon: Search, gradient: "var(--grad-teal)" },
  Analyst: { icon: BarChart3, gradient: "var(--grad-amber)" },
  Critic: { icon: ShieldCheck, gradient: "var(--grad-rose)" },
  Writer: { icon: FileText, gradient: "var(--grad-slate)" },
};

/**
 * Requirement 16: "a simple visualization such as: Supervisor ✓, Researcher A ✓,
 * Researcher B Running, ... is sufficient. The goal is observability, not animation."
 * This derives that exact view from real task + status API data — no mock states —
 * while adding tasteful (not distracting) motion for the "running" state.
 */
export default function AgentPipeline({ tasks }) {
  if (!tasks || tasks.length === 0) {
    return <p style={{ color: "var(--text-faint)", fontSize: 13 }}>No task plan yet — start a run to see the pipeline.</p>;
  }

  const nodes = tasks.map((t) => ({
    id: t.id,
    role: t.assigned_agent,
    sub: t.assigned_agent === "Researcher" && t.parameters?.target ? t.parameters.target : null,
    status: t.live_status,
  }));

  return (
    <div className="pipeline">
      {nodes.map((n, i) => {
        const meta = AGENT_ICON[n.role] || AGENT_ICON.Supervisor;
        const Icon = meta.icon;
        return (
          <div key={n.id} style={{ display: "flex", alignItems: "stretch" }}>
            <div className={`pipeline-node ${n.status}`}>
              <div className="pipeline-node-icon" style={{ background: meta.gradient }}>
                <Icon size={15} />
              </div>
              <div className="pipeline-node-name">{n.role}</div>
              {n.sub && <div className="pipeline-node-sub">{n.sub}</div>}
              <StatusBadge status={n.status} />
            </div>
            {i < nodes.length - 1 && (
              <div className={`pipeline-connector ${n.status === "completed" ? "active" : ""}`}>
                <ChevronRight size={16} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
