import { FileBarChart2, Download } from "lucide-react";
import StatusBadge from "./StatusBadge";
import EmptyState from "./EmptyState";

export default function ReportsView({ runs, onSelectRun }) {
  const withReports = runs.filter((r) => r.has_report);

  if (withReports.length === 0) {
    return <EmptyState icon={FileBarChart2} title="No completed reports yet" body="Reports appear here once a run finishes with an approved final report." />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {withReports.map((r) => (
        <div key={r.run_id} className="panel fade-in" style={{ cursor: "pointer" }} onClick={() => onSelectRun(r.run_id)}>
          <div className="panel-body" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {r.user_request}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 4, fontFamily: "var(--font-mono)" }}>
                {r.run_id} · {r.evidence_count} evidence items
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
              <StatusBadge status={r.workflow_status} />
              <Download size={15} style={{ color: "var(--text-faint)" }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
