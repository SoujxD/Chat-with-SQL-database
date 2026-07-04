# Evaluation suite (Phase 2E)

A 50-question benchmark for the text-to-SQL pipeline, run as a black box
over `POST /api/query` — the harness never imports backend internals, so it
evaluates whatever's actually deployed.

## Dataset (`test_questions.json`)

50 questions against the `ecommerce` database, each with:

| Field                  | Meaning                                                                 |
|------------------------|--------------------------------------------------------------------------|
| `question`             | The natural-language question.                                          |
| `difficulty`           | `easy` (15) / `medium` (15) / `hard` (12) / `adversarial` (8).           |
| `expected_sql_pattern` | Regex the generated SQL should match — a loose structural sanity check (right tables/aggregates present), not exact-SQL matching. `null` for adversarial questions. |
| `expected_result`      | Ground-truth rows, **or** the literal string `"BLOCKED"` for adversarial questions. |
| `reference_sql`        | The SQL used to compute `expected_result` (provenance, not sent to the model). `null` for adversarial questions. |

**How `expected_result` was derived**: the seed script
(`../seed/ecommerce_postgres.sql`) uses `setseed(0.4213)`, so the generated
orders/order_items are deterministic — verified by wiping the Postgres
volume and reseeding from scratch (`docker compose down -v && docker
compose up -d postgres`), which reproduced byte-identical results. Each
`reference_sql` was then run directly against the live seeded database to
capture real values — these are exact answers, not estimates. **If the seed
script ever changes, `expected_result` must be regenerated** (rerun each
`reference_sql` and update the dataset).

The 8 `adversarial` questions (delete/drop/update/insert/truncate/grant/
multi-statement-injection/disguised-update) test the guardrails from
[../backend/safety.py](../backend/safety.py), not SQL generation quality.

## Running it

Needs a running backend with `GROQ_API_KEY` set, pointed at the seeded
`ecommerce` Postgres database (see the root README for `docker compose up`):

```bash
python -m evaluation.harness --base-url http://localhost:8000 --database-id ecommerce
python -m evaluation.harness --output report.json   # also write full per-question JSON
```

## Metrics

- **SQL validity** — did the model produce a syntactically well-formed SQL
  statement at all (starts with a real SQL keyword, parses), regardless of
  whether it was later blocked or wrong? Computed over all 50 questions.
- **Execution accuracy** — for the 42 legitimate questions: does the
  returned result match `expected_result`? Comparison is by **value
  multiset per row**, not by column name — the model's column aliases won't
  match the reference SQL's, so `{"total": 25}` matches `{"count": 25}`.
  Floats are rounded to 2 decimals for tolerance. Broken down by difficulty.
- **Blocked unsafe queries** — for the 8 adversarial questions: did the
  safety guardrail correctly return `is_safe: false`? This is the
  guardrail's recall against intentionally malicious questions.
- **Latency** — round-trip time per question as observed by this client
  (mean/median/p95/max), for successes, blocks, and errors alike.

Anything that fails for an infrastructure reason (missing API key, network
error, unknown `database_id`) is excluded from execution-accuracy and
blocked-rate denominators and reported separately under `errors` — it's
inconclusive, not a pass or fail.

## Tests (`tests/test_harness.py`)

Hermetic — no live LLM or Postgres required. Verifies the comparison logic,
SQL-validity check, and metric math with synthetic inputs, plus an
integration check of response parsing against the real FastAPI app (SQLite
`student` DB, stubbed LLM). Run with `pytest evaluation/tests`.

The 50-question dataset itself was validated end-to-end by stubbing the LLM
to return each `reference_sql` verbatim against a live seeded Postgres —
100% SQL validity, 100% execution accuracy, 100% blocked-rate, confirming
the dataset and harness agree with each other. A second run with two
deliberately-corrupted answers (wrong SQL for one easy question, a
non-dangerous stub for one adversarial question) correctly dropped
execution accuracy to 41/42 and the blocked-rate to 7/8 — proving the
metrics actually discriminate rather than trivially reporting 100%.
