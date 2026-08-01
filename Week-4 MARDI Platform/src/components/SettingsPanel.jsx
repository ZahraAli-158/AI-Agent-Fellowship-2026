import { useEffect, useState } from "react";
import { Settings, Cpu, Shield, Info } from "lucide-react";
import { api } from "../api/client";
import ThemeToggle from "./ThemeToggle";

export default function SettingsPanel() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 560 }}>
      <div className="panel">
        <div className="panel-header"><h3 className="panel-title"><Cpu size={15} style={{ color: "var(--accent)" }} /> Backend Status</h3></div>
        <div className="panel-body">
          {health ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
              <div><span style={{ color: "var(--text-faint)" }}>Status:</span> {health.status}</div>
              <div><span style={{ color: "var(--text-faint)" }}>LLM Provider:</span> {health.llm_provider}</div>
              <div><span style={{ color: "var(--text-faint)" }}>LLM Mode:</span> {health.llm_mode}</div>
            </div>
          ) : (
            <p style={{ fontSize: 12.5, color: "var(--text-faint)" }}>Could not reach backend health endpoint.</p>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header"><h3 className="panel-title"><Settings size={15} style={{ color: "var(--accent)" }} /> Appearance</h3></div>
        <div className="panel-body">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 13 }}>Theme</span>
            <ThemeToggle />
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header"><h3 className="panel-title"><Shield size={15} style={{ color: "var(--accent)" }} /> Workflow Controls</h3></div>
        <div className="panel-body">
          <p style={{ fontSize: 12.5, color: "var(--text-dim)", margin: 0, display: "flex", gap: 8 }}>
            <Info size={14} style={{ flexShrink: 0, marginTop: 2, color: "var(--text-faint)" }} />
            Max revisions and human-checkpoint behavior are configured per-run when you submit a request
            (see the "Max revisions" field on the New Run screen), or via backend environment variables
            (<span className="mono">MAX_REVISIONS</span>, <span className="mono">LLM_TIMEOUT_S</span>) for
            the server defaults.
          </p>
        </div>
      </div>
    </div>
  );
}
