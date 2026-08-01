const MESSAGES = {
  pending: ["Starting up…", "Getting things ready"],
  analyzing_request: ["Analyzing your request…", "Extracting objective and criteria"],
  awaiting_clarification: ["Waiting on clarification…", "A quick question before we begin"],
  awaiting_plan_approval: ["Waiting on plan approval…", "Review the research plan"],
  researching: ["Researching…", "Gathering evidence in parallel"],
  analyzing: ["Comparing results…", "Building the comparison framework"],
  revising: ["Refining the analysis…", "Addressing reviewer feedback"],
  reviewing: ["Reviewing findings…", "The Critic is checking the work"],
  writing_report: ["Writing report…", "Drafting the final deliverable"],
  awaiting_final_approval: ["Waiting on final review…", "Ready for your approval"],
  completed: ["Done!", "Workflow completed"],
  failed: ["Something went wrong", "Check the error details below"],
};

export default function LoadingIndicator({ status }) {
  const [message, submessage] = MESSAGES[status] || ["Working…", "Processing your request"];
  return (
    <div className="loading-block fade-in">
      <div className="loading-spinner" />
      <div style={{ textAlign: "center" }}>
        <div className="loading-message">{message}</div>
        <div className="loading-submessage">{submessage}</div>
      </div>
    </div>
  );
}
