import { useCallback, useEffect, useState } from "react";
import { Menu } from "lucide-react";
import {
  LayoutDashboard, ListTree, FileSearch, ShieldCheck, History as HistoryIcon,
  Braces, FileText, BarChart3, Play,
} from "lucide-react";
import { api } from "./api/client";
import { usePolling } from "./hooks/usePolling";

import Sidebar from "./components/Sidebar";
import RequestForm from "./components/RequestForm";
import Panel from "./components/Panel";
import StatCard from "./components/StatCard";
import StatusBadge from "./components/StatusBadge";
import AgentPipeline from "./components/AgentPipeline";
import ProgressTimeline from "./components/ProgressTimeline";
import TaskPlanTable from "./components/TaskPlanTable";
import EvidencePanel from "./components/EvidencePanel";
import AnalysisReview from "./components/AnalysisReview";
import ExecutionLog from "./components/ExecutionLog";
import StateInspector from "./components/StateInspector";
import ReportView from "./components/ReportView";
import ChartsPanel from "./components/ChartsPanel";
import CheckpointModal from "./components/CheckpointModal";
import LoadingIndicator from "./components/LoadingIndicator";
import SettingsPanel from "./components/SettingsPanel";
import ReportsView from "./components/ReportsView";

const TABS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "tasks", label: "Task Plan", icon: ListTree },
  { id: "evidence", label: "Evidence", icon: FileSearch },
  { id: "analysis", label: "Analysis & Critic", icon: ShieldCheck },
  { id: "trace", label: "Execution Log", icon: HistoryIcon },
  { id: "state", label: "State Inspector", icon: Braces },
  { id: "report", label: "Final Report", icon: FileText },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
];

export default function App() {
  const [activeRunId, setActiveRunId] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [sidebarView, setSidebarView] = useState(null); // null | "history" | "reports" | "settings"
  const [starting, setStarting] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const runIsLive = (status) => status && !["finished", "error"].includes(status);
  // A run is only really "done" once its session has stopped AND the
  // workflow itself reached a terminal status — a session can finish its
  // background thread while workflow_status is still e.g. "researching" if
  // something went wrong, so both are checked before polling backs off.
  const workflowIsTerminal = (workflowStatus) => ["completed", "failed"].includes(workflowStatus);

  const { data: runs } = usePolling(() => api.listRuns(), [], { intervalMs: 2500 });

  const [lastKnownStatus, setLastKnownStatus] = useState(null);
  const statusIsLive =
    lastKnownStatus == null ||
    (runIsLive(lastKnownStatus.session_status) && !workflowIsTerminal(lastKnownStatus.workflow_status));

  const { data: status } = usePolling(
    () => api.getStatus(activeRunId),
    [activeRunId],
    { enabled: !!activeRunId, intervalMs: statusIsLive ? 1000 : 10000 }
  );

  useEffect(() => {
    if (status) setLastKnownStatus(status);
  }, [status]);

  // Reset to fast polling whenever the user switches to a different run,
  // instead of inheriting the previous run's (possibly terminal) status.
  useEffect(() => {
    setLastKnownStatus(null);
  }, [activeRunId]);

  const isLive = runIsLive(status?.session_status) && !workflowIsTerminal(status?.workflow_status);

  const { data: tasksData } = usePolling(
    () => api.getTasks(activeRunId),
    [activeRunId, status?.workflow_status],
    { enabled: !!activeRunId, intervalMs: isLive ? 1200 : 30000 }
  );
  const { data: evidenceData } = usePolling(
    () => api.getEvidence(activeRunId),
    [activeRunId, status?.evidence_count],
    { enabled: !!activeRunId, intervalMs: isLive ? 1500 : 30000 }
  );
  const { data: traceData } = usePolling(
    () => api.getTrace(activeRunId),
    [activeRunId, status?.workflow_status],
    { enabled: !!activeRunId, intervalMs: isLive ? 1200 : 30000 }
  );
  const { data: reportData } = usePolling(
    () => api.getReport(activeRunId),
    [activeRunId, status?.workflow_status],
    { enabled: !!activeRunId, intervalMs: isLive ? 2000 : 30000 }
  );
  const { data: stateData } = usePolling(
    () => api.getState(activeRunId),
    [activeRunId, status?.workflow_status],
    { enabled: !!activeRunId && (activeTab === "state" || activeTab === "analysis"), intervalMs: 2000 }
  );

  const handleStartRun = useCallback(async (userRequest, maxRevisions) => {
    setStarting(true);
    try {
      const { run_id } = await api.startRun(userRequest, maxRevisions);
      setActiveRunId(run_id);
      setSidebarView(null);
      setActiveTab("overview");
      setMobileOpen(false);
    } catch (err) {
      alert(`Failed to start run: ${err.message}`);
    } finally {
      setStarting(false);
    }
  }, []);

  const handleResolveCheckpoint = useCallback(
    async (body) => {
      setResolving(true);
      try {
        await api.resolveCheckpoint(activeRunId, body);
      } catch (err) {
        alert(`Failed to submit checkpoint decision: ${err.message}`);
      } finally {
        setResolving(false);
      }
    },
    [activeRunId]
  );

  const selectRun = (id) => {
    setActiveRunId(id);
    setSidebarView(null);
    setActiveTab("overview");
    setMobileOpen(false);
  };

  const tasks = tasksData?.tasks || [];
  const evidence = evidenceData?.evidence || [];
  const showLoadingOverlay = activeRunId && !status;

  return (
    <div className="app-shell">
      <Sidebar
        runs={runs || []}
        activeRunId={activeRunId}
        onSelectRun={selectRun}
        onNewRun={() => { setActiveRunId(null); setSidebarView(null); setMobileOpen(false); }}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        view={sidebarView}
        onChangeView={(v) => { setSidebarView(v); setMobileOpen(false); }}
      />

      <div className="main">
        <div className="topbar">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button className="btn btn-icon mobile-menu-btn" onClick={() => setMobileOpen(true)}>
              <Menu size={16} />
            </button>
            <div>
              <h1>Multi-Agent Research &amp; Decision Intelligence Platform</h1>
              <div className="subtitle">
                {activeRunId ? `${activeRunId} · ${status?.user_request || "…"}` : "No active run"}
              </div>
            </div>
          </div>
          {status && <StatusBadge status={status.workflow_status} />}
        </div>

        {sidebarView === "settings" ? (
          <div className="content"><SettingsPanel /></div>
        ) : sidebarView === "reports" ? (
          <div className="content"><ReportsView runs={runs || []} onSelectRun={(id) => { selectRun(id); setActiveTab("report"); }} /></div>
        ) : sidebarView === "history" ? (
          <div className="content">
            <ReportsView runs={runs || []} onSelectRun={selectRun} />
          </div>
        ) : !activeRunId ? (
          <div className="content">
            <Panel title="Start a New Research Request" icon={Play}>
              <RequestForm onSubmit={handleStartRun} submitting={starting} />
            </Panel>
          </div>
        ) : showLoadingOverlay ? (
          <div className="content"><LoadingIndicator status="pending" /></div>
        ) : (
          <>
            <div className="tabs">
              {TABS.map((t) => {
                const Icon = t.icon;
                return (
                  <button
                    key={t.id}
                    className={`tab ${activeTab === t.id ? "active" : ""}`}
                    onClick={() => setActiveTab(t.id)}
                  >
                    <Icon size={14} />
                    {t.label}
                  </button>
                );
              })}
            </div>

            <div className="content">
              {activeTab === "overview" && (
                <>
                  <div className="stat-grid">
                    <StatCard label="Workflow Status" value={status?.workflow_status || "…"} icon={LayoutDashboard} gradient="var(--grad-indigo)" />
                    <StatCard label="Tasks Done" value={`${tasksData?.completed_count ?? 0} / ${tasksData?.total_count ?? 0}`} icon={ListTree} gradient="var(--grad-teal)" />
                    <StatCard label="Evidence" value={status?.evidence_count ?? 0} icon={FileSearch} gradient="var(--grad-amber)" />
                    <StatCard label="Revisions" value={`${status?.revision_count ?? 0} / ${status?.max_revisions ?? 2}`} icon={ShieldCheck} gradient="var(--grad-rose)" />
                    <StatCard label="Errors" value={status?.error_count ?? 0} icon={HistoryIcon} gradient="var(--grad-slate)" />
                    <StatCard label="Elapsed" value={`${status?.elapsed_s ?? 0}s`} icon={HistoryIcon} gradient="var(--grad-indigo)" />
                  </div>

                  <Panel title="Workflow Progress" icon={BarChart3}>
                    <ProgressTimeline workflowStatus={status?.workflow_status} lastActiveStatus={status?.last_active_status} />
                  </Panel>

                  <Panel title="Agent Pipeline" icon={LayoutDashboard} subtitle="Supervisor → Researchers (parallel) → Analyst → Critic → Writer">
                    <AgentPipeline tasks={tasks} />
                  </Panel>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                    <Panel title="Checkpoint 1 — Research Plan Approval">
                      <StatusBadge status={status?.checkpoint_1_status} />
                    </Panel>
                    <Panel title="Checkpoint 2 — Final Recommendation Review">
                      <StatusBadge status={status?.checkpoint_2_status} />
                    </Panel>
                  </div>

                  {status?.research_objective?.objective && (
                    <Panel title="Research Objective">
                      <p style={{ margin: 0, fontSize: 13 }}>{status.research_objective.objective}</p>
                    </Panel>
                  )}
                  {status?.error && (
                    <Panel title="Run Error">
                      <pre style={{ fontSize: 11, color: "var(--danger)", whiteSpace: "pre-wrap" }}>{status.error}</pre>
                    </Panel>
                  )}
                </>
              )}

              {activeTab === "tasks" && (
                <Panel title="Task Plan" icon={ListTree} subtitle="Dynamically generated by the Supervisor">
                  <TaskPlanTable tasks={tasks} />
                </Panel>
              )}

              {activeTab === "evidence" && (
                <Panel title="Evidence Store" icon={FileSearch}>
                  <EvidencePanel evidence={evidence} summary={evidenceData?.summary} />
                </Panel>
              )}

              {activeTab === "analysis" && (
                <Panel title="Analysis & Critic Review" icon={ShieldCheck}>
                  <AnalysisReview state={stateData} />
                </Panel>
              )}

              {activeTab === "trace" && (
                <Panel title="Execution Trace" icon={HistoryIcon} subtitle="Operational events only — no chain-of-thought is stored">
                  <ExecutionLog trace={traceData?.trace} summary={traceData?.summary} runId={activeRunId} />
                </Panel>
              )}

              {activeTab === "state" && (
                <Panel title="Workflow State Inspector" icon={Braces} subtitle="Read-only view of the shared LangGraph state">
                  <StateInspector state={stateData} />
                </Panel>
              )}

              {activeTab === "report" && (
                <Panel icon={FileText}>
                  <ReportView reportData={reportData} />
                </Panel>
              )}

              {activeTab === "analytics" && (
                <Panel title="Analytics" icon={BarChart3} subtitle="Live visual breakdown of this run's evidence and task data">
                  <ChartsPanel evidenceSummary={evidenceData?.summary} tasks={tasks} workflowStatus={status?.workflow_status} />
                </Panel>
              )}
            </div>
          </>
        )}
      </div>

      <CheckpointModal
        pending={status?.pending_checkpoint}
        onResolve={handleResolveCheckpoint}
        resolving={resolving}
      />
    </div>
  );
}
