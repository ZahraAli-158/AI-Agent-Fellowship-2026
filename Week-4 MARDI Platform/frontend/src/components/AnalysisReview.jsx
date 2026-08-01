import EmptyState from "./EmptyState";
import StatusBadge from "./StatusBadge";
import { BarChart3, ShieldCheck, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function AnalysisReview({ state }) {
  const analysis = state?.analysis;
  const feedback = state?.critic_feedback;
  const revisionCount = state?.revision_count ?? 0;
  const maxRevisions = state?.max_revisions ?? 2;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span className="mono" style={{ fontSize: 12, color: "var(--text-dim)", fontWeight: 600 }}>
          Revision {revisionCount} of {maxRevisions}
        </span>
        {feedback && <StatusBadge status={feedback.decision} />}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div className="panel" style={{ borderColor: "var(--accent-border)" }}>
          <div className="panel-header">
            <h3 className="panel-title"><BarChart3 size={15} style={{ color: "var(--accent)" }} /> Analyst Output</h3>
          </div>
          <div className="panel-body">
            {analysis ? (
              <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 10 }}>
                <p style={{ margin: 0 }}><b>Framework:</b> {analysis.comparison_framework}</p>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {analysis.conclusions.map((c, i) => <li key={i} style={{ marginBottom: 4 }}>{c}</li>)}
                </ul>
                {analysis.known_gaps?.length > 0 && (
                  <div style={{ display: "flex", gap: 8, alignItems: "flex-start", background: "var(--warning-dim)", border: "1px solid var(--warning-border)", borderRadius: "var(--radius-sm)", padding: "8px 10px" }}>
                    <AlertTriangle size={14} style={{ color: "var(--warning)", flexShrink: 0, marginTop: 2 }} />
                    <span style={{ color: "var(--text)", fontSize: 12.5 }}>{analysis.known_gaps.join("; ")}</span>
                  </div>
                )}
              </div>
            ) : (
              <EmptyState icon={BarChart3} title="Analysis not yet generated" body="Waiting for all research tasks to complete." />
            )}
          </div>
        </div>

        <div className="panel" style={{ borderColor: feedback?.decision === "revision_requested" ? "var(--warning-border)" : "var(--success-border)" }}>
          <div className="panel-header">
            <h3 className="panel-title"><ShieldCheck size={15} style={{ color: "var(--danger)" }} /> Critic Feedback</h3>
          </div>
          <div className="panel-body">
            {feedback ? (
              <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 10 }}>
                {feedback.problems_found?.length > 0 && (
                  <div>
                    <b>Problems found:</b>
                    <ul style={{ margin: "4px 0 0", paddingLeft: 18, color: "var(--warning)" }}>
                      {feedback.problems_found.map((p, i) => <li key={i}>{p}</li>)}
                    </ul>
                  </div>
                )}
                {feedback.missing_evidence?.length > 0 && (
                  <div>
                    <b>Missing evidence:</b>
                    <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                      {feedback.missing_evidence.map((p, i) => <li key={i}>{p}</li>)}
                    </ul>
                  </div>
                )}
                {feedback.required_revisions && (
                  <p style={{ margin: 0 }}><b>Required revisions:</b> {feedback.required_revisions}</p>
                )}
                {feedback.decision === "approved" && (
                  <div style={{ display: "flex", gap: 8, alignItems: "center", background: "var(--success-dim)", border: "1px solid var(--success-border)", borderRadius: "var(--radius-sm)", padding: "8px 10px" }}>
                    <CheckCircle2 size={14} style={{ color: "var(--success)" }} />
                    <span style={{ fontSize: 12.5 }}>Approved — no revisions requested.</span>
                  </div>
                )}
              </div>
            ) : (
              <EmptyState icon={ShieldCheck} title="No critic review yet" body="Runs after the Analyst produces output." />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
