import { Check, X } from "lucide-react";

const STAGES = [
  { key: "analysis", label: "Request Analysis", statuses: ["pending", "analyzing_request", "awaiting_clarification"] },
  { key: "planning", label: "Task Planning", statuses: ["awaiting_plan_approval"] },
  { key: "research", label: "Research", statuses: ["researching"] },
  { key: "analyze", label: "Analysis", statuses: ["analyzing", "revising"] },
  { key: "critic", label: "Critic Review", statuses: ["reviewing"] },
  { key: "report", label: "Report Generation", statuses: ["writing_report", "awaiting_final_approval"] },
  { key: "done", label: "Completed", statuses: ["completed"] },
];

export default function ProgressTimeline({ workflowStatus, lastActiveStatus }) {
  const isFailed = workflowStatus === "failed";
  // On failure, `workflowStatus` is just "failed" — it doesn't say which
  // stage the run actually reached before failing, since workflow_status
  // only ever holds the current value, not history. `lastActiveStatus` is
  // the last non-terminal status the backend recorded, so we use that to
  // find the failure point instead of the terminal "failed" status itself
  // (which doesn't match any stage and previously caused every stage to
  // be misread as completed).
  const referenceStatus = isFailed ? lastActiveStatus : workflowStatus;
  const currentIndex = STAGES.findIndex((s) => s.statuses.includes(referenceStatus));
  // If the run failed before any status_change was ever recorded (e.g. an
  // empty request), there's no reference stage at all — treat that as
  // having failed at the very first stage rather than defaulting to "all
  // stages complete".
  const effectiveIndex = currentIndex === -1 ? (isFailed ? 0 : -1) : currentIndex;

  return (
    <div className="progress-timeline">
      {STAGES.map((stage, i) => {
        let state = "pending";
        if (isFailed && i === effectiveIndex) state = "failed";
        else if (i < effectiveIndex) state = "completed";
        else if (!isFailed && i === effectiveIndex) state = "active";

        return (
          <div key={stage.key} className={`timeline-stage ${state}`}>
            <div className="timeline-dot">
              {i < STAGES.length - 1 && <div className="timeline-line" />}
              {state === "completed" ? <Check size={15} /> : state === "failed" ? <X size={15} /> : i + 1}
            </div>
            <div className="timeline-label">{stage.label}</div>
          </div>
        );
      })}
    </div>
  );
}
