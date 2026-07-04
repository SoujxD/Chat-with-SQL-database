import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { QueryHistoryItem } from "../api/types";
import { HistoryTable } from "../components/HistoryTable";

export function HistoryPage() {
  const [items, setItems] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .queryHistory()
      .then((res) => setItems(res.items))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div className="page">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Query history</h1>
        <button className="btn btn-secondary" onClick={load} type="button">
          Refresh
        </button>
      </div>
      {loading && <p className="muted">Loading…</p>}
      {error && <div className="error-banner">{error}</div>}
      {!loading && !error && (
        <div className="card">
          <HistoryTable items={items} />
        </div>
      )}
    </div>
  );
}
