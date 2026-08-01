import { useMemo, useState } from "react";
import { Search, FileSearch } from "lucide-react";
import StatCard from "./StatCard";
import EmptyState from "./EmptyState";

export default function EvidencePanel({ evidence, summary }) {
  const [confFilter, setConfFilter] = useState("All");
  const [researcherFilter, setResearcherFilter] = useState("All");
  const [query, setQuery] = useState("");
  const [openId, setOpenId] = useState(null);

  const researchers = useMemo(
    () => ["All", ...Array.from(new Set((evidence || []).map((e) => e.agent_id)))],
    [evidence]
  );

  if (!evidence || evidence.length === 0) {
    return <EmptyState icon={FileSearch} title="No evidence collected yet" body="Evidence will appear here once Researcher agents complete." />;
  }

  const filtered = evidence.filter((e) => {
    if (confFilter !== "All" && e.confidence !== confFilter) return false;
    if (researcherFilter !== "All" && e.agent_id !== researcherFilter) return false;
    if (query && !`${e.claim} ${e.source_title}`.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="stat-grid">
        <StatCard label="Total Evidence" value={evidence.length} icon={FileSearch} gradient="var(--grad-indigo)" />
        <StatCard label="High Confidence" value={summary?.by_confidence?.High || 0} gradient="var(--grad-teal)" icon={FileSearch} />
        <StatCard label="Medium Confidence" value={summary?.by_confidence?.Medium || 0} gradient="var(--grad-amber)" icon={FileSearch} />
        <StatCard label="Low Confidence" value={summary?.by_confidence?.Low || 0} gradient="var(--grad-rose)" icon={FileSearch} />
      </div>

      <div>
        <div className="section-heading">Evidence by Research Question</div>
        <div className="chip-row">
          {Object.entries(summary?.by_research_question || {}).map(([rq, count]) => (
            <span key={rq} className="mono chip" style={{ cursor: "default" }}>{rq}: {count}</span>
          ))}
        </div>
      </div>

      <div className="filter-bar">
        <div className="search-input-wrap">
          <Search size={14} />
          <input
            className="text-input"
            placeholder="Search claims or sources…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <select className="select-input" value={confFilter} onChange={(e) => setConfFilter(e.target.value)}>
          {["All", "High", "Medium", "Low"].map((c) => <option key={c}>{c}</option>)}
        </select>
        <select className="select-input" value={researcherFilter} onChange={(e) => setResearcherFilter(e.target.value)}>
          {researchers.map((r) => <option key={r}>{r}</option>)}
        </select>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {filtered.length === 0 && (
          <p style={{ fontSize: 12.5, color: "var(--text-faint)" }}>No evidence matches the current filters.</p>
        )}
        {filtered.map((e) => (
          <div key={e.id} className="evidence-card fade-in">
            <div className="evidence-card-header" onClick={() => setOpenId(openId === e.id ? null : e.id)}>
              <div style={{ display: "flex", gap: 10, minWidth: 0, alignItems: "center" }}>
                <span className="mono" style={{ color: "var(--accent)", fontWeight: 700, flexShrink: 0 }}>{e.id}</span>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 13 }}>{e.claim}</span>
              </div>
              <span className={`confidence-badge ${e.confidence}`}>{e.confidence}</span>
            </div>
            {openId === e.id && (
              <div className="evidence-card-body">
                <p style={{ marginBottom: 10 }}>{e.supporting_text}</p>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                  <div><span style={{ color: "var(--text-faint)" }}>Source:</span> {e.source_title}</div>
                  <div><span style={{ color: "var(--text-faint)" }}>Research Q:</span> <span className="mono">{e.research_question}</span></div>
                  <div><span style={{ color: "var(--text-faint)" }}>Researcher:</span> {e.agent_id}</div>
                  <div><span style={{ color: "var(--text-faint)" }}>Retrieved:</span> {e.retrieval_date}</div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
