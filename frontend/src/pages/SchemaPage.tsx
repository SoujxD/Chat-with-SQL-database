import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { TableSchema } from "../api/types";
import { useDatabase } from "../context/DatabaseContext";
import { SchemaExplorer } from "../components/SchemaExplorer";

export function SchemaPage() {
  const { selectedId } = useDatabase();
  const [tables, setTables] = useState<TableSchema[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .schema(selectedId)
      .then((res) => !cancelled && setTables(res.tables))
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? String(err.message) : String(err));
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  return (
    <div className="page">
      <h1>Schema explorer</h1>
      {loading && <p className="muted">Loading schema…</p>}
      {error && <div className="error-banner">{error}</div>}
      {!loading && !error && <SchemaExplorer tables={tables} />}
    </div>
  );
}
