import { useState } from "react";
import { Sparkles, Send } from "lucide-react";

const EXAMPLES = [
  "Research the current open-source agent frameworks and recommend one for a small engineering team.",
  "Compare three cloud platforms for deploying an AI SaaS application.",
  "Compare three AI coding assistants for a software development team and recommend the best option.",
  "Analyze whether a startup should build its own AI model or use commercial APIs.",
];

export default function RequestForm({ onSubmit, submitting }) {
  const [value, setValue] = useState("");
  const [maxRevisions, setMaxRevisions] = useState(2);

  return (
    <div className="hero-form">
      <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--accent)", fontSize: 12.5, fontWeight: 600 }}>
        <Sparkles size={15} />
        Describe your research or decision request
      </div>
      <textarea
        className="text-input"
        placeholder="e.g. Compare three cloud platforms for deploying an AI SaaS application."
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <div>
        <div style={{ fontSize: 11, color: "var(--text-faint)", marginBottom: 8, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>
          Try an example
        </div>
        <div className="chip-row">
          {EXAMPLES.map((ex) => (
            <button key={ex} className="chip" onClick={() => setValue(ex)}>
              {ex.length > 46 ? ex.slice(0, 46) + "…" : ex}
            </button>
          ))}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <label style={{ fontSize: 12, color: "var(--text-dim)", display: "flex", alignItems: "center", gap: 6 }}>
          Max revisions
          <select
            className="select-input"
            value={maxRevisions}
            onChange={(e) => setMaxRevisions(Number(e.target.value))}
          >
            {[0, 1, 2, 3].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
        <button
          className="btn btn-primary"
          disabled={!value.trim() || submitting}
          onClick={() => onSubmit(value.trim(), maxRevisions)}
        >
          <Send size={14} />
          {submitting ? "Starting…" : "Run Workflow"}
        </button>
      </div>
    </div>
  );
}
