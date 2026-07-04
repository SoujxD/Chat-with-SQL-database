import { useState } from "react";

interface SqlPanelProps {
  sql: string;
}

export function SqlPanel({ sql }: SqlPanelProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (!sql) {
    return <p className="empty-state">No SQL generated yet.</p>;
  }

  return (
    <div className="stack" style={{ gap: 6 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>Generated SQL</h3>
        <button className="btn btn-secondary" onClick={handleCopy} type="button">
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="sql-panel">{sql}</pre>
    </div>
  );
}
