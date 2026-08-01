import { Plus, History, FileBarChart2, Settings, Sparkles, X } from "lucide-react";
import StatusBadge from "./StatusBadge";
import ThemeToggle from "./ThemeToggle";

export default function Sidebar({ runs, activeRunId, onSelectRun, onNewRun, mobileOpen, onCloseMobile, view, onChangeView }) {
  return (
    <>
      {mobileOpen && <div className="sidebar-backdrop" onClick={onCloseMobile} />}
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo"><Sparkles size={16} /></div>
          <div style={{ flex: 1 }}>
            <div className="sidebar-title">MARDI Platform</div>
            <div className="sidebar-subtitle">Multi-Agent Research &amp; Decision Intelligence</div>
          </div>
          <button className="btn btn-icon" style={{ display: mobileOpen ? "inline-flex" : "none" }} onClick={onCloseMobile}>
            <X size={14} />
          </button>
        </div>

        <nav className="sidebar-nav">
          <button className="sidebar-nav-item active" onClick={onNewRun}>
            <Plus size={15} /> New Run
          </button>
          <button className={`sidebar-nav-item ${view === "history" ? "active" : ""}`} onClick={() => onChangeView("history")}>
            <History size={15} /> Run History
          </button>
          <button className={`sidebar-nav-item ${view === "reports" ? "active" : ""}`} onClick={() => onChangeView("reports")}>
            <FileBarChart2 size={15} /> Reports
          </button>
          <button className={`sidebar-nav-item ${view === "settings" ? "active" : ""}`} onClick={() => onChangeView("settings")}>
            <Settings size={15} /> Settings
          </button>
        </nav>

        <div className="sidebar-section" style={{ paddingBottom: 0 }}>
          <div className="sidebar-section-label">Recent Runs</div>
        </div>
        <div className="sidebar-runs">
          {runs.length === 0 && <p style={{ fontSize: 12, color: "var(--text-faint)", padding: "0 4px" }}>No runs yet.</p>}
          {runs.map((r) => (
            <div
              key={r.run_id}
              className={`run-item ${r.run_id === activeRunId ? "active" : ""}`}
              onClick={() => onSelectRun(r.run_id)}
            >
              <div className="run-item-title">
                {r.user_request.length > 42 ? r.user_request.slice(0, 42) + "…" : r.user_request}
              </div>
              <div className="run-item-meta">
                <StatusBadge status={r.workflow_status || r.status} />
                <span className="mono">{r.elapsed_s}s</span>
              </div>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <ThemeToggle />
        </div>
      </aside>
    </>
  );
}
