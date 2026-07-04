"""Database engine management, schema introspection, and read-only execution.

Guardrails enforced here (in addition to the SQL-text checks in safety.py):
  - Connections are opened read-only (SQLite `mode=ro`; MySQL/Postgres
    sessions set to read-only right after connecting) so a statement that
    slipped past the validator still can't mutate anything.
  - Every query gets a hard wall-clock timeout, enforced by the database
    engine itself (SQLite progress handler / MySQL `MAX_EXECUTION_TIME` /
    Postgres `statement_timeout`) so a runaway query is actually cancelled,
    not just abandoned by the caller.
  - Result rows are capped at MAX_RESULT_ROWS regardless of the query's own
    LIMIT.
"""
from __future__ import annotations

import sqlite3
import time

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from . import config
from .config import DIALECT_NAMES, DatabaseConfig, get_database


class QueryTimeoutError(RuntimeError):
    """Raised when a query exceeds the configured timeout."""


# Cache one engine per database_id.
_engines: dict[str, Engine] = {}


def _build_engine(cfg: DatabaseConfig) -> Engine:
    if cfg.kind == "sqlite":
        path = cfg.params["path"]
        # Open the file read-only so nothing can mutate it, even by mistake.
        # check_same_thread=False: SQLAlchemy's pool may check the connection
        # out from a different thread than created it; we never share a
        # connection across concurrent queries, so this is safe here.
        creator = lambda: sqlite3.connect(
            f"file:{path}?mode=ro", uri=True, check_same_thread=False
        )
        return create_engine("sqlite:///", creator=creator)

    if cfg.kind == "mysql":
        p = cfg.params
        url = (
            f"mysql+mysqlconnector://{p['user']}:{p['password']}"
            f"@{p['host']}/{p['database']}"
        )
        engine = create_engine(url)

        @event.listens_for(engine, "connect")
        def _enforce_read_only(dbapi_conn, _record) -> None:
            # Defense in depth: even if the configured DB user isn't
            # provisioned as read-only, the session itself refuses writes.
            cursor = dbapi_conn.cursor()
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.close()

        return engine

    if cfg.kind == "postgres":
        p = cfg.params
        url = (
            f"postgresql+psycopg2://{p['user']}:{p['password']}"
            f"@{p['host']}:{p['port']}/{p['database']}"
        )
        # AUTOCOMMIT: we only ever run reads, so there's no transaction to
        # commit — this also avoids leaving idle-in-transaction connections
        # in the pool that would otherwise hold the READ ONLY session open.
        engine = create_engine(url, isolation_level="AUTOCOMMIT")

        @event.listens_for(engine, "connect")
        def _enforce_read_only(dbapi_conn, _record) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
            cursor.close()

        return engine

    raise ValueError(f"Unsupported database kind: {cfg.kind}")


def get_engine(database_id: str) -> Engine:
    """Return a cached engine for the given database id (raises KeyError if unknown)."""
    if database_id not in _engines:
        _engines[database_id] = _build_engine(get_database(database_id))
    return _engines[database_id]


def get_schema(database_id: str) -> list[dict]:
    """Return [{name, columns: [{name, type}]}] for every table."""
    engine = get_engine(database_id)
    inspector = inspect(engine)
    tables = []
    for table_name in inspector.get_table_names():
        columns = [
            {"name": col["name"], "type": str(col["type"])}
            for col in inspector.get_columns(table_name)
        ]
        tables.append({"name": table_name, "columns": columns})
    return tables


def dialect_name(database_id: str) -> str:
    """Human-readable SQL dialect name for the LLM prompt (e.g. 'PostgreSQL')."""
    return DIALECT_NAMES[get_database(database_id).kind]


def schema_as_text(database_id: str) -> str:
    """Compact schema description used to prompt the LLM."""
    lines = []
    for table in get_schema(database_id):
        cols = ", ".join(f"{c['name']} {c['type']}" for c in table["columns"])
        lines.append(f"TABLE {table['name']}({cols})")
    return "\n".join(lines)


def _apply_sqlite_timeout(conn, timeout_seconds: float) -> None:
    raw = conn.connection.dbapi_connection
    deadline = time.monotonic() + timeout_seconds

    def _progress() -> int:
        # Non-zero return aborts the currently running SQLite statement.
        return 1 if time.monotonic() > deadline else 0

    raw.set_progress_handler(_progress, 1000)


def _clear_sqlite_timeout(conn) -> None:
    conn.connection.dbapi_connection.set_progress_handler(None, 0)


def run_query(database_id: str, sql: str) -> list[dict]:
    """Execute an already-validated read-only query and return rows as dicts."""
    cfg = get_database(database_id)
    engine = get_engine(database_id)
    timeout = config.QUERY_TIMEOUT_SECONDS

    with engine.connect() as conn:
        if cfg.kind == "sqlite":
            _apply_sqlite_timeout(conn, timeout)
        elif cfg.kind == "mysql":
            conn.execute(text(f"SET SESSION MAX_EXECUTION_TIME={int(timeout * 1000)}"))
        elif cfg.kind == "postgres":
            conn.execute(text(f"SET statement_timeout = {int(timeout * 1000)}"))

        try:
            cursor = conn.execute(text(sql))
            rows = cursor.mappings().fetchmany(config.MAX_RESULT_ROWS)
            return [dict(row) for row in rows]
        except OperationalError as exc:
            if _is_timeout_error(exc):
                raise QueryTimeoutError(
                    f"Query exceeded the {timeout}s timeout."
                ) from exc
            raise
        finally:
            if cfg.kind == "sqlite":
                _clear_sqlite_timeout(conn)


def _is_timeout_error(exc: OperationalError) -> bool:
    # SQLite: "interrupted" (raised by our own progress handler).
    # MySQL: "...interrupted, max_statement_time exceeded" (MAX_EXECUTION_TIME).
    # Postgres: "canceling statement due to statement timeout".
    msg = str(exc).lower()
    return "interrupted" in msg or "timeout" in msg or "canceling statement" in msg
