import {
  ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  Tooltip, Legend, CartesianGrid,
} from "recharts";
import EmptyState from "./EmptyState";
import { PieChart as PieIcon } from "lucide-react";

const CONFIDENCE_COLORS = { High: "#2dd4bf", Medium: "#fbbf24", Low: "#fb7185" };
const TASK_COLORS = { completed: "#2dd4bf", running: "#a855f7", pending: "#6f6688" };

function ChartCard({ title, children }) {
  return (
    <div className="chart-card">
      <div className="section-heading">{title}</div>
      <div style={{ width: "100%", height: 220 }}>{children}</div>
    </div>
  );
}

export default function ChartsPanel({ evidenceSummary, tasks, workflowStatus }) {
  const hasData = evidenceSummary && Object.keys(evidenceSummary.by_confidence || {}).length > 0;

  if (!hasData) {
    return <EmptyState icon={PieIcon} title="No analytics yet" body="Charts populate once evidence and task data are available." />;
  }

  const confidenceData = Object.entries(evidenceSummary.by_confidence || {}).map(([name, value]) => ({ name, value }));
  const rqData = Object.entries(evidenceSummary.by_research_question || {}).map(([name, value]) => ({ name, value }));
  const agentData = Object.entries(evidenceSummary.by_agent || {}).map(([name, value]) => ({
    name: name.length > 16 ? name.slice(0, 16) + "…" : name, value,
  }));

  const statusCounts = { completed: 0, running: 0, pending: 0 };
  (tasks || []).forEach((t) => { statusCounts[t.live_status] = (statusCounts[t.live_status] || 0) + 1; });
  const taskData = Object.entries(statusCounts).map(([name, value]) => ({ name, value }));

  return (
    <div className="chart-grid">
      <ChartCard title="Confidence Distribution">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={confidenceData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={78} paddingAngle={3}>
              {confidenceData.map((d) => <Cell key={d.name} fill={CONFIDENCE_COLORS[d.name] || "#818cf8"} />)}
            </Pie>
            <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Task Completion">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={taskData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={78} paddingAngle={3}>
              {taskData.map((d) => <Cell key={d.name} fill={TASK_COLORS[d.name] || "#818cf8"} />)}
            </Pie>
            <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Evidence by Research Question">
        <ResponsiveContainer>
          <BarChart data={rqData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--text-faint)" }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "var(--text-faint)" }} />
            <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
            <Bar dataKey="value" fill="#a855f7" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Evidence by Researcher">
        <ResponsiveContainer>
          <BarChart data={agentData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: "var(--text-faint)" }} />
            <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 10.5, fill: "var(--text-faint)" }} />
            <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
            <Bar dataKey="value" fill="#2dd4bf" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
