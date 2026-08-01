import { useState } from "react";
import { ChevronRight, ChevronDown } from "lucide-react";

function typeOf(value) {
  if (value === null || value === undefined) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

function TreeNode({ nodeKey, value, depth, defaultOpen }) {
  const type = typeOf(value);
  const isExpandable = type === "object" || type === "array";
  const [open, setOpen] = useState(defaultOpen ?? depth < 1);

  if (!isExpandable) {
    const display =
      type === "string" ? `"${value}"` : type === "null" ? "null" : String(value);
    return (
      <div className="json-row" style={{ cursor: "default" }}>
        <span className="json-toggle" />
        {nodeKey !== undefined && <span className="json-key">{nodeKey}:</span>}
        <span className="json-leaf-value">{display}</span>
        <span className="json-type">{type}</span>
      </div>
    );
  }

  const entries = type === "array" ? value.map((v, i) => [i, v]) : Object.entries(value);
  const isEmpty = entries.length === 0;

  return (
    <div>
      <div className="json-row" onClick={() => !isEmpty && setOpen(!open)}>
        <span className="json-toggle">
          {!isEmpty && (open ? <ChevronDown size={13} /> : <ChevronRight size={13} />)}
        </span>
        {nodeKey !== undefined && <span className="json-key">{nodeKey}:</span>}
        <span className="json-type">
          {type === "array" ? `Array(${entries.length})` : `Object(${entries.length} keys)`}
        </span>
      </div>
      {open && !isEmpty && (
        <div className="json-node">
          {entries.map(([k, v]) => (
            <TreeNode key={k} nodeKey={k} value={v} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function JsonTreeViewer({ data }) {
  return (
    <div className="json-tree">
      <TreeNode value={data} depth={0} defaultOpen={true} />
    </div>
  );
}
