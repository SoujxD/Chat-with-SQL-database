"""Backend configuration: database registry and LLM settings."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root = parent of the backend/ package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---- LLM ----
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "Llama3-8b-8192")

# ---- Query history ----
HISTORY_MAX_ITEMS = int(os.getenv("HISTORY_MAX_ITEMS", "100"))

# Max rows returned to the client from any query.
MAX_RESULT_ROWS = int(os.getenv("MAX_RESULT_ROWS", "200"))

# Hard wall-clock limit (seconds) for executing a single query.
QUERY_TIMEOUT_SECONDS = float(os.getenv("QUERY_TIMEOUT_SECONDS", "5"))


class DatabaseConfig:
    """A registered database the API can query."""

    def __init__(self, database_id: str, name: str, kind: str, **params: str) -> None:
        self.database_id = database_id
        self.name = name
        self.kind = kind  # "sqlite" | "mysql" | "postgres"
        self.params = params


# Human-readable SQL dialect name per kind, used to prompt the LLM correctly.
DIALECT_NAMES = {
    "sqlite": "SQLite",
    "mysql": "MySQL",
    "postgres": "PostgreSQL",
}

# Registry of databases addressable by `database_id`.
# Extend this to add MySQL, more SQLite files, or more Postgres databases.
DATABASES: dict[str, DatabaseConfig] = {
    "student": DatabaseConfig(
        database_id="student",
        name="Student SQLite DB",
        kind="sqlite",
        path=str(PROJECT_ROOT / "student.db"),
    ),
    "ecommerce": DatabaseConfig(
        database_id="ecommerce",
        name="Ecommerce Analytics (Postgres)",
        kind="postgres",
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "chatsql"),
        password=os.getenv("POSTGRES_PASSWORD", "chatsql"),
        database=os.getenv("POSTGRES_DB", "ecommerce"),
    ),
}


def get_database(database_id: str) -> DatabaseConfig:
    if database_id not in DATABASES:
        raise KeyError(database_id)
    return DATABASES[database_id]
