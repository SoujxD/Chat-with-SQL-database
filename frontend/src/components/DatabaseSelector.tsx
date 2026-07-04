import { useDatabase } from "../context/DatabaseContext";

export function DatabaseSelector() {
  const { databases, selectedId, setSelectedId, loading } = useDatabase();

  if (loading) return <span className="muted">Loading databases…</span>;
  if (databases.length === 0) return <span className="muted">No databases registered.</span>;

  return (
    <select
      className="select"
      value={selectedId}
      onChange={(e) => setSelectedId(e.target.value)}
      aria-label="Select database"
    >
      {databases.map((db) => (
        <option key={db.id} value={db.id}>
          {db.name} ({db.kind})
        </option>
      ))}
    </select>
  );
}
