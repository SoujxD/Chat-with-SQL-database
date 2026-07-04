import type {
  DatabasesResponse,
  HealthResponse,
  QueryErrorDetail,
  QueryHistoryResponse,
  QueryResponse,
  SchemaResponse,
  ValidateSQLResponse,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Thrown for non-2xx responses. `detail` is the raw FastAPI `detail` field —
// either a plain string or a QueryErrorDetail object (see backend/main.py).
export class ApiError extends Error {
  status: number;
  detail: string | QueryErrorDetail;

  constructor(status: number, detail: string | QueryErrorDetail) {
    super(typeof detail === "string" ? detail : detail.message);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(0, `Could not reach the backend at ${BASE_URL}. Is it running?`);
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  databases: () => request<DatabasesResponse>("/api/databases"),

  schema: (databaseId: string) =>
    request<SchemaResponse>(`/api/schema?database_id=${encodeURIComponent(databaseId)}`),

  validateSql: (sql: string) =>
    request<ValidateSQLResponse>("/api/validate-sql", {
      method: "POST",
      body: JSON.stringify({ sql }),
    }),

  query: (question: string, databaseId: string) =>
    request<QueryResponse>("/api/query", {
      method: "POST",
      body: JSON.stringify({ question, database_id: databaseId }),
    }),

  queryHistory: () => request<QueryHistoryResponse>("/api/query-history"),
};
