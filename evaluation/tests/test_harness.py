"""Unit tests for evaluation/harness.py's own logic (no live LLM/DB needed).

These don't run the real 50-question suite (that requires GROQ_API_KEY and
the seeded Postgres database) — they verify the harness's comparison logic,
SQL-validity check, and metric math are correct using synthetic inputs, plus
an integration check of run_case's HTTP-response parsing against the
"student" SQLite DB with a stubbed LLM.
"""
import pytest
from fastapi.testclient import TestClient

from evaluation.harness import (
    CaseResult,
    compute_metrics,
    load_dataset,
    looks_like_sql,
    results_match,
    run_case,
)


def test_dataset_loads_and_has_50_questions():
    dataset = load_dataset()
    assert len(dataset) == 50
    by_difficulty = {}
    for q in dataset:
        by_difficulty[q["difficulty"]] = by_difficulty.get(q["difficulty"], 0) + 1
        assert {"id", "question", "difficulty", "expected_sql_pattern", "expected_result"} <= q.keys()
    assert by_difficulty == {"easy": 15, "medium": 15, "hard": 12, "adversarial": 8}


class TestLooksLikeSql:
    def test_valid_select(self):
        assert looks_like_sql("SELECT * FROM products LIMIT 5") is True

    def test_valid_with_cte(self):
        assert looks_like_sql("WITH t AS (SELECT 1) SELECT * FROM t") is True

    def test_empty_is_invalid(self):
        assert looks_like_sql("") is False
        assert looks_like_sql("   ") is False

    def test_garbage_is_invalid(self):
        assert looks_like_sql("not really sql at all") is False

    def test_dangerous_sql_is_still_structurally_valid(self):
        # Validity != safety: a DROP is syntactically valid SQL.
        assert looks_like_sql("DROP TABLE products") is True


class TestResultsMatch:
    def test_identical_rows_match(self):
        assert results_match([{"count": 25}], [{"count": 25}])

    def test_different_column_names_still_match(self):
        # LLM might alias the column differently than the reference SQL.
        assert results_match([{"total_products": 25}], [{"count": 25}])

    def test_float_rounding_tolerance(self):
        assert results_match([{"revenue": 40850.899999}], [{"revenue": 40850.9}])

    def test_row_order_independent(self):
        actual = [{"name": "B", "n": 2}, {"name": "A", "n": 1}]
        expected = [{"name": "A", "n": 1}, {"name": "B", "n": 2}]
        assert results_match(actual, expected)

    def test_different_row_count_fails(self):
        assert not results_match([{"count": 25}], [{"count": 25}, {"count": 26}])

    def test_different_values_fail(self):
        assert not results_match([{"count": 24}], [{"count": 25}])

    def test_empty_results_match(self):
        assert results_match([], [])

    def test_heterogeneous_row_types_dont_crash_sort(self):
        # Regression: sorting raw (float, str) signature tuples across rows
        # of different shapes raises "'<' not supported between float and str".
        actual = [{"revenue": 100.5}, {"name": "Books", "count": 3}]
        expected = [{"name": "Books", "count": 3}, {"revenue": 100.5}]
        assert results_match(actual, expected)


class TestComputeMetrics:
    def _case(self, **kwargs):
        defaults = dict(
            id="X", question="q", difficulty="easy", latency_ms=10.0,
            generated_sql="SELECT 1", sql_valid=True, is_safe=True, http_status=200,
        )
        defaults.update(kwargs)
        return CaseResult(**defaults)

    def test_all_pass(self):
        results = [
            self._case(id="E1", execution_correct=True),
            self._case(id="E2", execution_correct=True),
            self._case(id="A1", difficulty="adversarial", blocked_correct=True, execution_correct=None),
        ]
        metrics = compute_metrics(results)
        assert metrics["sql_validity"]["pct"] == 100.0
        assert metrics["execution_accuracy"] == {
            "passed": 2, "total": 2, "pct": 100.0,
            "by_difficulty": {"easy": {"passed": 2, "total": 2}, "medium": {"passed": 0, "total": 0}, "hard": {"passed": 0, "total": 0}},
        }
        assert metrics["blocked_unsafe_queries"] == {"passed": 1, "total": 1, "pct": 100.0}

    def test_mixed_results(self):
        results = [
            self._case(id="E1", difficulty="easy", execution_correct=True),
            self._case(id="M1", difficulty="medium", execution_correct=False),
            self._case(id="A1", difficulty="adversarial", blocked_correct=True, execution_correct=None),
            self._case(id="A2", difficulty="adversarial", blocked_correct=False, execution_correct=None, sql_valid=True),
        ]
        metrics = compute_metrics(results)
        assert metrics["execution_accuracy"]["passed"] == 1
        assert metrics["execution_accuracy"]["total"] == 2
        assert metrics["execution_accuracy"]["pct"] == 50.0
        assert metrics["blocked_unsafe_queries"]["passed"] == 1
        assert metrics["blocked_unsafe_queries"]["total"] == 2
        assert metrics["blocked_unsafe_queries"]["pct"] == 50.0

    def test_infra_errors_excluded_from_accuracy_but_tracked(self):
        results = [
            self._case(id="E1", execution_correct=None, sql_valid=False, is_safe=None,
                       http_status=503, error="GROQ_API_KEY is not set."),
        ]
        metrics = compute_metrics(results)
        assert metrics["execution_accuracy"]["total"] == 0
        assert metrics["blocked_unsafe_queries"]["total"] == 0
        assert len(metrics["errors"]) == 1

    def test_latency_stats(self):
        results = [self._case(id=str(i), latency_ms=float(i), execution_correct=True) for i in range(1, 21)]
        metrics = compute_metrics(results)
        assert metrics["latency_ms"]["mean"] == 10.5
        assert metrics["latency_ms"]["max"] == 20.0
        assert metrics["latency_ms"]["median"] == 10.5


class TestRunCaseAgainstRealApp:
    """Exercises run_case's HTTP-response parsing against the real FastAPI app
    (in-process via ASGI transport), stubbing only the LLM call — proves the
    harness correctly interprets all three response shapes the backend can
    return, without needing a live server or LLM key."""

    @pytest.fixture
    def client(self, monkeypatch):
        import backend.main as main

        def fake_generate_sql(question, database_id, dialect="SQLite"):
            if question == "list students":
                return "SELECT NAME, MARKS FROM STUDENT LIMIT 5", "stub"
            if question == "delete everyone":
                return "DELETE FROM STUDENT", "stub"
            raise AssertionError(f"unexpected question: {question}")

        monkeypatch.setattr(main, "generate_sql", fake_generate_sql)
        return TestClient(main.app)

    def test_successful_legit_case(self, client):
        case = {
            "id": "T1", "question": "list students", "difficulty": "easy",
            "expected_sql_pattern": r"STUDENT", "expected_result": [],
        }
        result = run_case(client, "http://testserver", "student", case)
        assert result.http_status == 200
        assert result.sql_valid is True
        assert result.is_safe is True
        assert result.execution_correct is not None  # graded against (wrong) expected_result=[]

    def test_blocked_adversarial_case(self, client):
        case = {"id": "A1", "question": "delete everyone", "difficulty": "adversarial",
                "expected_sql_pattern": None, "expected_result": "BLOCKED"}
        result = run_case(client, "http://testserver", "student", case)
        assert result.http_status == 400
        assert result.blocked_correct is True
        assert "DELETE" in result.generated_sql.upper()

    def test_infra_error_case(self, client, monkeypatch):
        import backend.main as main
        from backend.llm import LLMNotConfigured

        def raise_not_configured(question, database_id, dialect="SQLite"):
            raise LLMNotConfigured("GROQ_API_KEY is not set.")

        monkeypatch.setattr(main, "generate_sql", raise_not_configured)
        case = {"id": "E1", "question": "anything", "difficulty": "easy",
                "expected_sql_pattern": None, "expected_result": []}
        result = run_case(client, "http://testserver", "student", case)
        assert result.http_status == 503
        assert result.execution_correct is None
        assert result.blocked_correct is None
        assert "GROQ_API_KEY" in result.error
