import { useEffect, useState } from "react";
import { HelpCircle, ClipboardCheck, FileCheck2, ListTree, Target, Layers, Check, X, Pencil, ArrowLeft } from "lucide-react";

export default function CheckpointModal({ pending, onResolve, resolving }) {
  const [answers, setAnswers] = useState({});
  const [editing, setEditing] = useState(false);
  const [editObjective, setEditObjective] = useState("");
  const [editTasks, setEditTasks] = useState([]); // [{ id, description }]
  const [editInstructions, setEditInstructions] = useState("");

  // Reset the edit form whenever a new checkpoint comes in (or the
  // previous one is resolved and pending goes back to null), so stale
  // edits from a prior checkpoint never leak into a new one.
  //
  // IMPORTANT: this must NOT depend on `pending.payload` by object
  // reference. Every background status poll (every ~1s) hands the
  // component a brand-new object parsed fresh from the API response, even
  // when the checkpoint itself is unchanged and still waiting on the
  // user — so a reference-based dependency re-fired this effect on every
  // poll tick and reset `editing` back to false a few seconds after the
  // user opened the panel, closing it out from under them. Keying off a
  // content-based string instead means the effect only re-runs when the
  // checkpoint's actual name/payload changes, not merely its identity.
  const pendingKey = pending ? `${pending.name}:${JSON.stringify(pending.payload)}` : null;
  useEffect(() => {
    setEditing(false);
    setEditInstructions("");
    if (pending?.name === "checkpoint_1_plan_approval") {
      setEditObjective(pending.payload.objective || "");
      setEditTasks(
        (pending.payload.planned_tasks || []).map((t) => {
          const idx = t.indexOf(":");
          return idx === -1
            ? { id: t, description: "" }
            : { id: t.slice(0, idx), description: t.slice(idx + 1).trim() };
        })
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingKey]);

  if (!pending) return null;

  const { name, payload } = pending;

  if (name === "clarification") {
    const questions = payload.questions || [];
    const submit = () => onResolve({ answers: questions.map((q, i) => answers[i] || "") });
    return (
      <div className="modal-backdrop">
        <div className="modal">
          <div className="modal-header">
            <div className="modal-icon" style={{ background: "var(--grad-amber)" }}><HelpCircle size={20} /></div>
            <h3 style={{ margin: "0 0 6px" }}>Clarification Needed</h3>
            <p style={{ color: "var(--text-faint)", fontSize: 12.5, margin: 0 }}>
              The request was ambiguous — the Supervisor is asking before starting research (Requirement 2).
            </p>
          </div>
          <div className="modal-body">
            {questions.map((q, i) => (
              <div key={i} style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12.5, color: "var(--text-dim)", fontWeight: 600 }}>{q}</label>
                <input
                  className="text-input"
                  style={{ width: "100%", marginTop: 5 }}
                  value={answers[i] || ""}
                  onChange={(e) => setAnswers({ ...answers, [i]: e.target.value })}
                />
              </div>
            ))}
            <button className="btn btn-primary" disabled={resolving} onClick={submit} style={{ width: "100%", justifyContent: "center", marginTop: 6 }}>
              {resolving ? "Submitting…" : "Submit Answers"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (name === "checkpoint_1_plan_approval") {
    const taskCount = (payload.planned_tasks || []).length;

    if (editing) {
      const updateTaskDescription = (id, description) =>
        setEditTasks((prev) => prev.map((t) => (t.id === id ? { ...t, description } : t)));

      const submitEdit = () =>
        onResolve({
          decision: "edit",
          research_objective: editObjective.trim() || undefined,
          task_edits: editTasks
            .map((t) => ({ id: t.id, description: t.description.trim() }))
            .filter((t) => t.description),
          additional_instructions: editInstructions.trim() || undefined,
        });

      return (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-header">
              <div className="modal-icon" style={{ background: "var(--grad-indigo)" }}><Pencil size={20} /></div>
              <h3 style={{ margin: "0 0 4px" }}>Edit Research Plan</h3>
              <p style={{ color: "var(--text-faint)", fontSize: 12.5, margin: "0 0 14px" }}>
                Adjust the objective, task descriptions, or add instructions — the workflow will continue with your edits, not restart.
              </p>
            </div>
            <div className="modal-body">
              <div className="section-heading"><Target size={12} /> Objective</div>
              <textarea
                className="text-input"
                style={{ width: "100%", marginTop: 5, marginBottom: 14, minHeight: 60, resize: "vertical" }}
                value={editObjective}
                onChange={(e) => setEditObjective(e.target.value)}
              />

              <div className="section-heading"><ListTree size={12} /> Task Plan</div>
              <div style={{ marginTop: 6, marginBottom: 14 }}>
                {editTasks.map((t) => (
                  <div key={t.id} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: 11.5, color: "var(--text-faint)", width: 28, flexShrink: 0 }}>{t.id}</span>
                    <input
                      className="text-input"
                      style={{ width: "100%" }}
                      value={t.description}
                      onChange={(e) => updateTaskDescription(t.id, e.target.value)}
                    />
                  </div>
                ))}
              </div>

              <div className="section-heading"><FileCheck2 size={12} /> Additional Instructions</div>
              <textarea
                className="text-input"
                style={{ width: "100%", marginTop: 5, marginBottom: 18, minHeight: 50, resize: "vertical" }}
                placeholder="Optional — anything the Analyst/Writer should keep in mind (e.g. prioritize compliance over cost)"
                value={editInstructions}
                onChange={(e) => setEditInstructions(e.target.value)}
              />

              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn" disabled={resolving} onClick={() => setEditing(false)}>
                  <ArrowLeft size={14} /> Back
                </button>
                <button
                  className="btn btn-primary"
                  disabled={resolving}
                  onClick={submitEdit}
                  style={{ flex: 1, justifyContent: "center" }}
                >
                  {resolving ? "Saving…" : "Save & Continue"}
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="modal-backdrop">
        <div className="modal">
          <div className="modal-header">
            <div className="modal-icon" style={{ background: "var(--grad-indigo)" }}><ClipboardCheck size={20} /></div>
            <h3 style={{ margin: "0 0 4px" }}>Checkpoint 1 — Research Plan Approval</h3>
            <p style={{ color: "var(--text-faint)", fontSize: 12.5, margin: "0 0 14px" }}>Review before any research begins.</p>
          </div>
          <div className="modal-body">
            <div className="stat-grid" style={{ marginBottom: 16 }}>
              <div className="stat-card" style={{ padding: "12px 14px" }}>
                <div className="stat-icon" style={{ background: "var(--grad-teal)", width: 28, height: 28 }}><Layers size={14} /></div>
                <div><div className="stat-value" style={{ fontSize: 16 }}>{taskCount}</div><div className="stat-label">Planned Tasks</div></div>
              </div>
              <div className="stat-card" style={{ padding: "12px 14px" }}>
                <div className="stat-icon" style={{ background: "var(--grad-amber)", width: 28, height: 28 }}><Target size={14} /></div>
                <div><div className="stat-value" style={{ fontSize: 13 }}>Comparison</div><div className="stat-label">Expected Output</div></div>
              </div>
            </div>

            <div className="section-heading"><Target size={12} /> Objective</div>
            <p style={{ fontSize: 13, color: "var(--text-dim)", marginTop: 0, marginBottom: 14 }}>{payload.objective}</p>

            <div className="section-heading"><ListTree size={12} /> Planned Tasks</div>
            <ul style={{ fontSize: 12.5, color: "var(--text-dim)", paddingLeft: 18, marginTop: 6, marginBottom: 14 }}>
              {(payload.planned_tasks || []).map((t) => <li key={t} style={{ marginBottom: 3 }}>{t}</li>)}
            </ul>

            <div className="section-heading"><FileCheck2 size={12} /> Expected Output</div>
            <p style={{ fontSize: 13, color: "var(--text-dim)", marginTop: 0, marginBottom: 18 }}>{payload.expected_output}</p>

            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-danger" disabled={resolving} onClick={() => onResolve({ decision: "reject" })}>
                <X size={14} /> Reject
              </button>
              <button className="btn" disabled={resolving} onClick={() => setEditing(true)}>
                <Pencil size={14} /> Edit &amp; Continue
              </button>
              <button className="btn btn-primary" disabled={resolving} onClick={() => onResolve({ decision: "approve" })} style={{ flex: 1, justifyContent: "center" }}>
                <Check size={14} /> Approve
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (name === "checkpoint_2_final_review") {
    return (
      <div className="modal-backdrop">
        <div className="modal">
          <div className="modal-header">
            <div className="modal-icon" style={{ background: "var(--grad-teal)" }}><FileCheck2 size={20} /></div>
            <h3 style={{ margin: "0 0 4px" }}>Checkpoint 2 — Final Recommendation Review</h3>
            <p style={{ color: "var(--text-faint)", fontSize: 12.5, margin: "0 0 14px" }}>Last human check before the report is finalized.</p>
          </div>
          <div className="modal-body">
            <div className="section-heading">Report Title</div>
            <p style={{ fontSize: 13.5, fontWeight: 600, marginTop: 0, marginBottom: 14 }}>{payload.title}</p>
            <div className="section-heading">Recommendation Preview</div>
            <div className="recommendation-box" style={{ marginBottom: 18 }}>
              <p style={{ fontSize: 13 }}>{payload.recommendation}</p>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn" disabled={resolving} onClick={() => onResolve({ decision: "request_changes" })}>
                <Pencil size={14} /> Request Changes
              </button>
              <button className="btn btn-primary" disabled={resolving} onClick={() => onResolve({ decision: "approve" })} style={{ flex: 1, justifyContent: "center" }}>
                <Check size={14} /> Approve
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
