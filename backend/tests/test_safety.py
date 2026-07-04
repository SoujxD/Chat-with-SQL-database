"""Unit tests for the SQL guardrail layer (backend/safety.py)."""
import pytest

from backend.safety import ensure_limit, validate_sql

DANGEROUS_QUERIES = {
    "drop": "DROP TABLE STUDENT",
    "delete": "DELETE FROM STUDENT WHERE NAME = 'John'",
    "update": "UPDATE STUDENT SET MARKS = 100",
    "insert": "INSERT INTO STUDENT VALUES ('X', 'Y', 'Z', 1)",
    "alter": "ALTER TABLE STUDENT ADD COLUMN AGE INT",
    "truncate": "TRUNCATE TABLE STUDENT",
    "create": "CREATE TABLE EVIL (id INT)",
    "grant": "GRANT ALL ON STUDENT TO 'x'@'%'",
    "revoke": "REVOKE ALL ON STUDENT FROM 'x'@'%'",
}


@pytest.mark.parametrize("name,sql", DANGEROUS_QUERIES.items(), ids=DANGEROUS_QUERIES.keys())
def test_dangerous_sql_is_blocked(name, sql):
    is_safe, reason = validate_sql(sql)
    assert is_safe is False, f"{name} should be blocked: {sql}"


def test_multi_statement_blocked():
    is_safe, _ = validate_sql("SELECT * FROM STUDENT LIMIT 10; DROP TABLE STUDENT")
    assert is_safe is False


def test_non_select_start_blocked():
    is_safe, reason = validate_sql("PRAGMA table_info(STUDENT)")
    assert is_safe is False


def test_select_without_limit_blocked():
    is_safe, reason = validate_sql("SELECT * FROM STUDENT")
    assert is_safe is False
    assert "LIMIT" in reason


def test_select_with_limit_allowed():
    is_safe, reason = validate_sql("SELECT * FROM STUDENT LIMIT 10")
    assert is_safe is True, reason


def test_cte_with_limit_allowed():
    is_safe, reason = validate_sql(
        "WITH t AS (SELECT * FROM STUDENT) SELECT NAME FROM t LIMIT 5"
    )
    assert is_safe is True, reason


def test_limit_inside_subquery_does_not_satisfy_top_level_requirement():
    # A LIMIT nested inside a subquery isn't a top-level cap on the outer result.
    is_safe, reason = validate_sql(
        "SELECT * FROM (SELECT * FROM STUDENT LIMIT 5) AS sub"
    )
    assert is_safe is False
    assert "LIMIT" in reason


def test_empty_sql_blocked():
    is_safe, _ = validate_sql("")
    assert is_safe is False


def test_ensure_limit_appends_when_missing():
    sql = ensure_limit("SELECT * FROM STUDENT", 50)
    assert sql == "SELECT * FROM STUDENT LIMIT 50"


def test_ensure_limit_leaves_existing_limit_untouched():
    sql = ensure_limit("SELECT * FROM STUDENT LIMIT 5", 50)
    assert sql == "SELECT * FROM STUDENT LIMIT 5"
