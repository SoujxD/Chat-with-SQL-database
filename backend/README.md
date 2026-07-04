# Chat-with-SQL Backend (Phase 2A)

FastAPI backend that turns natural-language questions into safe, read-only SQL
over registered databases using Groq.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then set GROQ_API_KEY
```

## Run

```bash
uvicorn backend.main:app --reload
```

Interactive docs at http://127.0.0.1:8000/docs

## Endpoints

| Method | Path                 | Description                                        |
|--------|----------------------|----------------------------------------------------|
| GET    | `/health`            | Liveness + whether the LLM key is configured.      |
| GET    | `/api/databases`     | Registered databases (id, display name, kind).     |
| GET    | `/api/schema`        | Table/column schema (`?database_id=student`).      |
| POST   | `/api/query`         | NL question -> generated SQL, explanation, rows.   |
| POST   | `/api/validate-sql`  | Check whether a SQL string is a safe read query.   |
| GET    | `/api/query-history` | Recent queries (most recent first).                |

### `POST /api/query`

```json
{ "question": "Who are the top 2 students?", "database_id": "student" }
```

On success (200): `generated_sql`, `explanation`, `result`, `is_safe`, `latency_ms`.

On a blocked or failed query (4xx), `detail` is a structured object rather
than a plain string, so callers can still show what was attempted:

```json
{ "detail": {
  "message": "Generated SQL is not safe: Forbidden keyword: 'DELETE'.",
  "generated_sql": "DELETE FROM STUDENT",
  "explanation": "...",
  "is_safe": false,
  "reason": "Forbidden keyword: 'DELETE'."
} }
```

## Guardrails

Every SQL statement — whether typed into `POST /api/validate-sql` or generated
by the LLM inside `POST /api/query` — passes through `backend/safety.py`:

- **SELECT-only**: the statement must start with `SELECT` or `WITH`; exactly
  one statement is allowed (no `;`-separated smuggling).
- **Blocked keywords**: `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`,
  `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE` (plus `REPLACE`, `MERGE`, `ATTACH`,
  `PRAGMA`, `EXEC`, `INTO`, … as defense in depth) anywhere in the statement.
- **LIMIT required**: a top-level `LIMIT` clause must be present. In the
  `/api/query` pipeline, a missing `LIMIT` is auto-appended (`MAX_RESULT_ROWS`)
  rather than rejected outright, so benign questions still work.

Execution in `backend/database.py` enforces the rest even if a statement
somehow got past validation:

- **Read-only connections**: SQLite is opened `mode=ro`; MySQL and Postgres
  sessions are set read-only right after connecting (`SET SESSION TRANSACTION
  READ ONLY` / `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY`), in
  addition to provisioning the configured DB user as read-only.
- **Query timeout** (`QUERY_TIMEOUT_SECONDS`, default 5s): SQLite queries are
  cancelled via a progress handler; MySQL via `MAX_EXECUTION_TIME`; Postgres
  via `statement_timeout`. A timeout returns HTTP `408`.
- **Max rows returned** (`MAX_RESULT_ROWS`, default 200): results are always
  truncated with `fetchmany`, regardless of the query's own `LIMIT`.

Tests for all of the above live in `backend/tests/` (`pip install -r
requirements-dev.txt && pytest backend/tests`).

## Databases

Registered in `backend/config.py` under `DATABASES`:

- `student` — bundled SQLite file.
- `ecommerce` — Postgres, seeded from `seed/ecommerce_postgres.sql` (see the
  root [README](../README.md) for `docker compose` setup).

Add more by registering a new `DatabaseConfig` (SQLite path, MySQL, or
Postgres) and addressing it via `database_id`.
