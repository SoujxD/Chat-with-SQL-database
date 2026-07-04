"""End-to-end guardrail tests against POST /api/query.

The LLM call is mocked (no live GROQ_API_KEY in CI) so each natural-language
question is mapped to the SQL a model might plausibly produce for it. The
point of these tests is to prove the *pipeline* — generation -> LIMIT
auto-injection -> safety validation -> execution — blocks dangerous SQL and
allows safe SQL, regardless of where that SQL came from.
"""
import pytest
from fastapi.testclient import TestClient

import backend.main as main

QUESTION_TO_SQL = {
    "delete all users": "DELETE FROM STUDENT",
    "drop table students": "DROP TABLE STUDENT",
    "show top 10 students": "SELECT NAME, MARKS FROM STUDENT ORDER BY MARKS DESC LIMIT 10",
    "update price": "UPDATE STUDENT SET MARKS = 100",
}


@pytest.fixture
def client(monkeypatch):
    def fake_generate_sql(question: str, database_id: str, dialect: str = "SQLite"):
        return QUESTION_TO_SQL[question], "mocked explanation"

    monkeypatch.setattr(main, "generate_sql", fake_generate_sql)
    return TestClient(main.app)


def _ask(client, question):
    return client.post(
        "/api/query", json={"question": question, "database_id": "student"}
    )


def test_delete_all_users_blocked(client):
    r = _ask(client, "delete all users")
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "not safe" in detail["message"].lower()
    assert detail["is_safe"] is False
    assert "DELETE" in detail["generated_sql"].upper()


def test_drop_table_blocked(client):
    r = _ask(client, "drop table students")
    assert r.status_code == 400
    assert "DROP" in r.json()["detail"]["generated_sql"].upper()


def test_update_price_blocked(client):
    r = _ask(client, "update price")
    assert r.status_code == 400
    assert "UPDATE" in r.json()["detail"]["generated_sql"].upper()


def test_show_top_10_students_allowed(client):
    r = _ask(client, "show top 10 students")
    assert r.status_code == 200
    body = r.json()
    assert body["is_safe"] is True
    assert "LIMIT" in body["generated_sql"].upper()
    assert len(body["result"]) <= 10


def test_blocked_query_appears_in_history(client):
    _ask(client, "drop table students")
    history = client.get("/api/query-history").json()["items"]
    assert history[0]["is_safe"] is False
    assert "DROP" in history[0]["generated_sql"].upper()
