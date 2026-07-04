"""Tests for execution-layer guardrails in backend/database.py."""
import time

import pytest

import backend.database as db


def test_run_query_returns_rows():
    rows = db.run_query("student", "SELECT NAME, MARKS FROM STUDENT LIMIT 5")
    assert isinstance(rows, list)
    assert rows
    assert set(rows[0].keys()) == {"NAME", "MARKS"}


def test_run_query_caps_rows_regardless_of_limit(monkeypatch):
    monkeypatch.setattr(db.config, "MAX_RESULT_ROWS", 2)
    rows = db.run_query("student", "SELECT * FROM STUDENT LIMIT 100")
    assert len(rows) <= 2


def test_run_query_times_out_on_slow_statement(monkeypatch):
    # A tiny timeout plus a query that has to scan/sort repeatedly should trip
    # the SQLite progress-handler cancellation.
    monkeypatch.setattr(db.config, "QUERY_TIMEOUT_SECONDS", 0.0001)
    slow_sql = (
        "WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt "
        "WHERE x < 50000000) SELECT COUNT(*) FROM cnt LIMIT 1"
    )
    with pytest.raises(db.QueryTimeoutError):
        db.run_query("student", slow_sql)


def test_sqlite_connection_is_read_only():
    engine = db.get_engine("student")
    with engine.connect() as conn:
        with pytest.raises(Exception):
            conn.exec_driver_sql("INSERT INTO STUDENT VALUES ('X','Y','Z',1)")


def test_dialect_name_per_database():
    assert db.dialect_name("student") == "SQLite"
    assert db.dialect_name("ecommerce") == "PostgreSQL"


def test_ecommerce_registered_as_postgres():
    cfg = db.get_database("ecommerce")
    assert cfg.kind == "postgres"
    assert set(cfg.params) >= {"host", "port", "user", "password", "database"}


def test_postgres_engine_builds_without_connecting():
    # create_engine() is lazy — building the engine must not require a live
    # Postgres server, only actually connecting should.
    engine = db.get_engine("ecommerce")
    assert engine.url.get_backend_name() == "postgresql"
    assert engine.url.drivername == "postgresql+psycopg2"
