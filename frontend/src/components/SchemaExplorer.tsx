import type { TableSchema } from "../api/types";

interface SchemaExplorerProps {
  tables: TableSchema[];
}

export function SchemaExplorer({ tables }: SchemaExplorerProps) {
  if (tables.length === 0) {
    return <p className="empty-state">This database has no tables.</p>;
  }

  return (
    <div className="stack" style={{ gap: 12 }}>
      {tables.map((table) => (
        <details key={table.name} className="card" open>
          <summary style={{ cursor: "pointer", fontWeight: 600, color: "var(--text-h)" }}>
            {table.name}{" "}
            <span className="muted" style={{ fontWeight: 400 }}>
              ({table.columns.length} column{table.columns.length === 1 ? "" : "s"})
            </span>
          </summary>
          <div className="scroll-x" style={{ marginTop: 10 }}>
            <table>
              <thead>
                <tr>
                  <th>Column</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {table.columns.map((col) => (
                  <tr key={col.name}>
                    <td>{col.name}</td>
                    <td className="muted">{col.type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ))}
    </div>
  );
}
