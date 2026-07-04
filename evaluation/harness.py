"""Evaluation harness for the text-to-SQL pipeline (Phase 2E).

Treats the backend as a black box over HTTP (`POST /api/query`), so it
evaluates whatever is actually deployed rather than reaching into backend
internals. Loads `evaluation/test_questions.json` and reports four metrics:

- **SQL validity**: did the model produce a syntactically well-formed SQL
  statement at all (regardless of whether it was later blocked or wrong)?
- **Execution accuracy**: for legitimate questions, does the returned result
  match `expected_result` (value-based comparison, tolerant to column
  naming/order differences and float rounding)?
- **Blocked unsafe queries**: for adversarial questions, did the safety
  guardrail correctly block them?
- **Latency**: round-trip time per question, as observed by this client.

Run directly: `python -m evaluation.harness --database-id ecommerce`
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import sqlparse
from sqlparse import tokens as T

DATASET_PATH = Path(__file__).parent / "test_questions.json"


def load_dataset(path: Path = DATASET_PATH) -> list[dict]:
    with open(path) as f:
        return json.load(f)


_SQL_START_KEYWORDS = {
    "SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
    "ALTER", "TRUNCATE", "GRANT", "REVOKE", "EXPLAIN", "PRAGMA", "MERGE",
    "REPLACE", "CALL", "EXEC", "EXECUTE",
}


def looks_like_sql(sql: str) -> bool:
    """Cheap structural check: non-empty, parseable, starts with a real SQL
    statement keyword (not just any reserved word — e.g. "not" is a SQL
    keyword too, but "not really sql" isn't a statement)."""
    if not sql or not sql.strip():
        return False
    statements = [s for s in sqlparse.parse(sql) if str(s).strip()]
    if not statements:
        return False
    for token in statements[0].flatten():
        if token.is_whitespace or token.ttype in T.Comment:
            continue
        return token.value.upper() in _SQL_START_KEYWORDS
    return False


def _normalize_value(v: Any) -> Any:
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    if isinstance(v, str):
        try:
            return round(float(v), 2)
        except ValueError:
            return v.strip().lower()
    return v


def _row_signature(row: dict) -> tuple:
    # Compare by value multiset, not by column name/order — the model's
    # column aliases rarely match the reference SQL's exactly.
    return tuple(sorted((_normalize_value(v) for v in row.values()), key=str))


def results_match(actual: list[dict], expected: list[dict]) -> bool:
    if len(actual) != len(expected):
        return False
    # key=str: row signatures can mix types across rows (one row all-numeric,
    # another with a string column), which breaks tuple `<` comparison.
    return sorted((_row_signature(r) for r in actual), key=str) == sorted(
        (_row_signature(r) for r in expected), key=str
    )


@dataclass
class CaseResult:
    id: str
    question: str
    difficulty: str
    latency_ms: float
    generated_sql: str
    sql_valid: bool
    is_safe: bool | None
    http_status: int
    blocked_correct: bool | None = None  # adversarial only
    execution_correct: bool | None = None  # non-adversarial only
    error: str | None = None


def run_case(client: httpx.Client, base_url: str, database_id: str, case: dict) -> CaseResult:
    is_adversarial = case["difficulty"] == "adversarial"
    started = time.perf_counter()
    try:
        resp = client.post(
            f"{base_url}/api/query",
            json={"question": case["question"], "database_id": database_id},
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return CaseResult(
            id=case["id"], question=case["question"], difficulty=case["difficulty"],
            latency_ms=latency_ms, generated_sql="", sql_valid=False, is_safe=None,
            http_status=0, error=f"Request failed: {exc}",
        )
    latency_ms = (time.perf_counter() - started) * 1000

    if resp.status_code == 200:
        body = resp.json()
        generated_sql = body["generated_sql"]
        sql_valid = looks_like_sql(generated_sql)
        result = CaseResult(
            id=case["id"], question=case["question"], difficulty=case["difficulty"],
            latency_ms=latency_ms, generated_sql=generated_sql, sql_valid=sql_valid,
            is_safe=True, http_status=200,
        )
        if is_adversarial:
            # A 200 means the guardrail failed to block a dangerous question.
            result.blocked_correct = False
        else:
            result.execution_correct = results_match(body["result"], case["expected_result"])
        return result

    # Non-2xx: detail is either a structured dict (safety block / execution
    # failure after SQL was generated) or a plain string (infra error, e.g.
    # missing GROQ_API_KEY, unknown database_id).
    try:
        detail = resp.json().get("detail")
    except ValueError:
        detail = None

    if isinstance(detail, dict):
        generated_sql = detail.get("generated_sql", "") or ""
        is_safe = detail.get("is_safe")
        sql_valid = looks_like_sql(generated_sql)
        result = CaseResult(
            id=case["id"], question=case["question"], difficulty=case["difficulty"],
            latency_ms=latency_ms, generated_sql=generated_sql, sql_valid=sql_valid,
            is_safe=is_safe, http_status=resp.status_code, error=detail.get("message"),
        )
        if is_adversarial:
            result.blocked_correct = is_safe is False
        else:
            result.execution_correct = False
        return result

    # Plain-string detail: infra error, inconclusive for both metrics.
    return CaseResult(
        id=case["id"], question=case["question"], difficulty=case["difficulty"],
        latency_ms=latency_ms, generated_sql="", sql_valid=False, is_safe=None,
        http_status=resp.status_code, error=str(detail),
    )


def run_suite(base_url: str, database_id: str, dataset: list[dict]) -> list[CaseResult]:
    with httpx.Client() as client:
        return [run_case(client, base_url, database_id, case) for case in dataset]


def compute_metrics(results: list[CaseResult]) -> dict:
    legit = [r for r in results if r.execution_correct is not None]
    adversarial = [r for r in results if r.blocked_correct is not None]
    latencies = [r.latency_ms for r in results]

    def pct(numerator: int, denominator: int) -> float | None:
        return round(100.0 * numerator / denominator, 2) if denominator else None

    def by_difficulty(pred) -> dict:
        out = {}
        for d in ("easy", "medium", "hard"):
            subset = [r for r in legit if r.difficulty == d]
            out[d] = {"passed": sum(1 for r in subset if pred(r)), "total": len(subset)}
        return out

    return {
        "total_questions": len(results),
        "sql_validity": {
            "passed": sum(1 for r in results if r.sql_valid),
            "total": len(results),
            "pct": pct(sum(1 for r in results if r.sql_valid), len(results)),
        },
        "execution_accuracy": {
            "passed": sum(1 for r in legit if r.execution_correct),
            "total": len(legit),
            "pct": pct(sum(1 for r in legit if r.execution_correct), len(legit)),
            "by_difficulty": by_difficulty(lambda r: r.execution_correct),
        },
        "blocked_unsafe_queries": {
            "passed": sum(1 for r in adversarial if r.blocked_correct),
            "total": len(adversarial),
            "pct": pct(sum(1 for r in adversarial if r.blocked_correct), len(adversarial)),
        },
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 1) if latencies else None,
            "median": round(statistics.median(latencies), 1) if latencies else None,
            "p95": round(sorted(latencies)[int(len(latencies) * 0.95) - 1], 1) if latencies else None,
            "max": round(max(latencies), 1) if latencies else None,
        },
        "errors": [
            {"id": r.id, "question": r.question, "error": r.error}
            for r in results if r.error and r.blocked_correct is None and r.execution_correct is None
        ],
    }


def print_report(metrics: dict) -> None:
    print(f"\n{'=' * 60}\nEvaluation report ({metrics['total_questions']} questions)\n{'=' * 60}")

    v = metrics["sql_validity"]
    print(f"\nSQL validity:          {v['passed']}/{v['total']} ({v['pct']}%)")

    e = metrics["execution_accuracy"]
    print(f"Execution accuracy:    {e['passed']}/{e['total']} ({e['pct']}%)")
    for d, s in e["by_difficulty"].items():
        p = round(100.0 * s["passed"] / s["total"], 1) if s["total"] else None
        print(f"  - {d:8s}: {s['passed']}/{s['total']} ({p}%)")

    b = metrics["blocked_unsafe_queries"]
    print(f"Blocked unsafe queries: {b['passed']}/{b['total']} ({b['pct']}%)")

    lat = metrics["latency_ms"]
    print(f"\nLatency (ms): mean={lat['mean']}  median={lat['median']}  p95={lat['p95']}  max={lat['max']}")

    if metrics["errors"]:
        print(f"\n{len(metrics['errors'])} inconclusive (infra error, not a validity/accuracy/safety failure):")
        for err in metrics["errors"][:10]:
            print(f"  - [{err['id']}] {err['question']!r}: {err['error']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the text-to-SQL evaluation suite.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--database-id", default="ecommerce")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--output", type=Path, help="Write full JSON report to this path.")
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    results = run_suite(args.base_url, args.database_id, dataset)
    metrics = compute_metrics(results)
    print_report(metrics)

    if args.output:
        report = {"metrics": metrics, "results": [vars(r) for r in results]}
        args.output.write_text(json.dumps(report, indent=2))
        print(f"\nFull report written to {args.output}")


if __name__ == "__main__":
    main()
