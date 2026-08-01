import { Inbox } from "lucide-react";

export default function EmptyState({ icon: Icon = Inbox, title, body }) {
  return (
    <div className="empty-state">
      <Icon size={28} strokeWidth={1.5} />
      <div className="empty-state-title">{title}</div>
      {body && <div>{body}</div>}
    </div>
  );
}
