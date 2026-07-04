// Mirrors backend/models.py. Keep in sync with the FastAPI response models.

export interface QueryRequest {
  question: string;
  database_id: string;
}

export interface QueryResponse {
  generated_sql: string;
  explanation: string;
  result: Record<string, unknown>[];
  is_safe: boolean;
  latency_ms: number;
}

// Shape of HTTPException.detail for POST /api/query error responses
// (see backend/main.py) — present whenever the backend managed to generate
// SQL before failing, so the UI can still show what was attempted.
export interface QueryErrorDetail {
  message: string;
  generated_sql: string;
  explanation: string;
  is_safe: boolean;
  reason?: string;
}

export interface ValidateSQLRequest {
  sql: string;
}

export interface ValidateSQLResponse {
  is_safe: boolean;
  reason: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
}

export interface TableSchema {
  name: string;
  columns: ColumnInfo[];
}

export interface SchemaResponse {
  database_id: string;
  tables: TableSchema[];
}

export interface QueryHistoryItem {
  question: string;
  database_id: string;
  generated_sql: string;
  is_safe: boolean;
  latency_ms: number;
  row_count: number;
  error: string | null;
  timestamp: string;
}

export interface QueryHistoryResponse {
  items: QueryHistoryItem[];
}

export interface HealthResponse {
  status: string;
  llm_configured: boolean;
  databases: string[];
}

export interface DatabaseInfo {
  id: string;
  name: string;
  kind: string;
}

export interface DatabasesResponse {
  databases: DatabaseInfo[];
}
