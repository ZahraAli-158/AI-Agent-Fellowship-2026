export default function StatCard({ label, value, icon: Icon, gradient = "var(--grad-indigo)" }) {
  return (
    <div className="stat-card fade-in">
      <div className="stat-icon" style={{ background: gradient }}>
        <Icon size={17} />
      </div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}
