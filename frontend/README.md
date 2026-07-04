# Chat with SQL — Frontend (Phase 2D)

React + TypeScript + Vite UI for the FastAPI backend in [`../backend`](../backend).

## Setup

```bash
npm install
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000
npm run dev
```

`VITE_API_BASE_URL` is inlined into the JS bundle at build time — it's the
URL the *browser* uses to reach the backend, so it must be reachable from
wherever the page is opened (not a Docker-internal hostname).

## Pages

| Route         | Purpose                                                                 |
|---------------|--------------------------------------------------------------------------|
| `/query`      | Ask a natural-language question; see generated SQL, safety status, explanation, and results. |
| `/schema`     | Browse tables and columns for the selected database.                     |
| `/history`    | Full query history (safe and blocked attempts) from the backend.         |
| `/evaluation` | Runs a fixed set of guardrail test questions live against the backend and reports pass/fail. |

The database selector in the top nav is shared across all pages (persisted
to `localStorage`).

## Components (`src/components/`)

`QuestionBox`, `SqlPanel`, `SafetyBadge`, `ResultTable`, `SchemaExplorer`,
`ExplanationPanel`, `HistoryTable`, `DatabaseSelector`.

## Error handling

When `/api/query` blocks or fails, the backend returns a structured
`detail` object (`{ message, generated_sql, explanation, is_safe, reason? }`)
instead of a plain string — see `ApiError` in `src/api/client.ts`. This lets
`/query` still show the SQL and safety status for a *blocked* query, not just
a generic error message.

## Build

```bash
npm run build    # tsc -b && vite build, output in dist/
npm run preview  # serve the production build locally
```
