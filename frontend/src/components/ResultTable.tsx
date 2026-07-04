interface ResultTableProps {
  rows: Record<string, unknown>[];
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function ResultTable({ rows }: ResultTableProps) {
  if (rows.length === 0) {
    return <p className="empty-state">Query ran successfully but returned no rows.</p>;
  }

  const columns = Object.keys(rows[0]);

  return (
    <div className="stack" style={{ gap: 6 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>Results</h3>
        <span className="muted">{rows.length} row{rows.length === 1 ? "" : "s"}</span>
      </div>
      <div className="scroll-x">
        <table>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td key={col}>{formatCell(row[col])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
