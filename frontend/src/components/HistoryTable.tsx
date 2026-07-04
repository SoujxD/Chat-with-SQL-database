import type { QueryHistoryItem } from "../api/types";
import { SafetyBadge } from "./SafetyBadge";

interface HistoryTableProps {
  items: QueryHistoryItem[];
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function HistoryTable({ items }: HistoryTableProps) {
  if (items.length === 0) {
    return <p className="empty-state">No queries have been run yet.</p>;
  }

  return (
    <div className="scroll-x">
      <table>
        <thead>
          <tr>
            <th>When</th>
            <th>Database</th>
            <th>Question</th>
            <th>Generated SQL</th>
            <th>Safety</th>
            <th>Rows</th>
            <th>Latency</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i}>
              <td className="muted">{formatTimestamp(item.timestamp)}</td>
              <td>{item.database_id}</td>
              <td style={{ whiteSpace: "normal", minWidth: 200 }}>{item.question}</td>
              <td>
                <code title={item.generated_sql || item.error || undefined}>
                  {item.generated_sql
                    ? item.generated_sql.length > 60
                      ? `${item.generated_sql.slice(0, 60)}…`
                      : item.generated_sql
                    : "—"}
                </code>
              </td>
              <td>
                <SafetyBadge isSafe={item.is_safe} />
              </td>
              <td>{item.row_count}</td>
              <td className="muted">{item.latency_ms} ms</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
