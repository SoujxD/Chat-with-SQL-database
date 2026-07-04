import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api/client";
import type { DatabaseInfo } from "../api/types";

const STORAGE_KEY = "chatsql.selectedDatabaseId";

interface DatabaseContextValue {
  databases: DatabaseInfo[];
  selectedId: string;
  setSelectedId: (id: string) => void;
  loading: boolean;
  error: string | null;
}

const DatabaseContext = createContext<DatabaseContextValue | null>(null);

export function DatabaseProvider({ children }: { children: ReactNode }) {
  const [databases, setDatabases] = useState<DatabaseInfo[]>([]);
  const [selectedId, setSelectedIdState] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) ?? ""
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .databases()
      .then((res) => {
        if (cancelled) return;
        setDatabases(res.databases);
        setSelectedIdState((current) => {
          if (current && res.databases.some((d) => d.id === current)) {
            return current;
          }
          return res.databases[0]?.id ?? "";
        });
      })
      .catch((err) => !cancelled && setError(String(err)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const setSelectedId = (id: string) => {
    setSelectedIdState(id);
    localStorage.setItem(STORAGE_KEY, id);
  };

  return (
    <DatabaseContext.Provider value={{ databases, selectedId, setSelectedId, loading, error }}>
      {children}
    </DatabaseContext.Provider>
  );
}

export function useDatabase(): DatabaseContextValue {
  const ctx = useContext(DatabaseContext);
  if (!ctx) throw new Error("useDatabase must be used within a DatabaseProvider");
  return ctx;
}
