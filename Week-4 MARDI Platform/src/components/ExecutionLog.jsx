import StatCard from "./StatCard";
import EmptyState from "./EmptyState";
import { Play, Square, Wrench, ArrowRightLeft, RotateCcw, XCircle, UserCheck, Info, History, GitBranch, AlertOctagon } from "lucide-react";

const EVENT_META = {
  agent_start: { icon: Play, color: "var(--accent)" },
  agent_end: { icon: Square, color: "var(--text-faint)" },
  tool_call: { icon: Wrench, color: "var(--purple)" },
  handoff: { icon: ArrowRightLeft, color: "var(--accent)" },
  revision: { icon: RotateCcw, color: "var(--warning)" },
  error: { icon: XCircle, color: "var(--danger)" },
  human_approval: { icon: UserCheck, color: "var(--success)" },
  status_change: { icon: Info, color: "var(--text-faint)" },
};

function describeEvent(e) {
  switch (e.type) {
    case "agent_start": return `${e.agent} started`;
    case "agent_end": return `${e.agent} finished`;
    case "tool_call": return `${e.agent} called ${e.tool}${e.success ? "" : " (failed)"} ${e.detail || ""}`;
    case "handoff": return `${e.from_agent} → ${e.to_agent}${e.summary ? `: ${e.summary}` : ""}`;
    case "revision": return `Revision ${e.cycle}/${e.max_cycles} — ${e.reason}`;
    case "error": return `${e.agent}: ${e.error_type} — ${e.detail}`;
    case "human_approval": return `Human checkpoint "${e.checkpoint}" → ${e.decision}`;
    case "status_change": return `Workflow status → ${e.status}`;
    default: return JSON.stringify(e);
  }
}

export default function ExecutionLog({ trace, summary, runId }) {
  if (!trace || trace.length === 0) {
    return <EmptyState icon={History} title="No execution trace yet" body="Structured operational events will appear here as the workflow runs. No chain-of-thought is ever stored." />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="stat-grid">
        <StatCard label="Run ID" value={runId?.slice(-8) || "—"} icon={GitBranch} gradient="var(--grad-indigo)" />
        <StatCard label="Agent Calls" value={summary?.agents_invoked?.length ?? 0} icon={Play} gradient="var(--grad-teal)" />
        <StatCard label="Tool Calls" value={summary?.tools_called ?? 0} icon={Wrench} gradient="var(--grad-amber)" />
        <StatCard label="Handoffs" value={summary?.handoffs ?? 0} icon={ArrowRightLeft} gradient="var(--grad-indigo)" />
        <StatCard label="Revisions" value={summary?.revision_cycles ?? 0} icon={RotateCcw} gradient="var(--grad-amber)" />
        <StatCard label="Errors" value={summary?.errors ?? 0} icon={AlertOctagon} gradient="var(--grad-rose)" />
      </div>
      <div>
        {trace.map((e, i) => {
          const meta = EVENT_META[e.type] || EVENT_META.status_change;
          const Icon = meta.icon;
          return (
            <div className={`log-line type-${e.type}`} key={i}>
              <span className="log-time">{e.time}</span>
              <Icon size={13} className="log-icon" style={{ color: meta.color, marginTop: 2 }} />
              <span className="log-text" style={{ color: e.type === "error" ? "var(--danger)" : "var(--text-dim)" }}>
                {describeEvent(e)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
