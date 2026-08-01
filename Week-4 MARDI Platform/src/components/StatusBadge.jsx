export default function StatusBadge({ status }) {
  const label = {
    completed: "Completed",
    running: "Running",
    pending: "Pending",
    waiting: "Waiting",
    approved: "Approved",
    edited: "Edited",
    rejected: "Rejected",
    request_changes: "Changes Requested",
    failed: "Failed",
    error: "Error",
    revision_requested: "Revision Requested",
  }[status] || status || "Unknown";

  const cls = ["approved", "completed"].includes(status)
    ? "completed"
    : status === "running"
    ? "running"
    : ["failed", "error", "rejected"].includes(status)
    ? "failed"
    : status === "revision_requested"
    ? "revision"
    : "waiting";

  return (
    <span className={`badge ${cls}`}>
      <span className="dot" />
      {label}
    </span>
  );
}
