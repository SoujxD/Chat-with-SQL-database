"""In-memory query history (most recent first)."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

from .config import HISTORY_MAX_ITEMS

_history: deque[dict] = deque(maxlen=HISTORY_MAX_ITEMS)


def record(
    *,
    question: str,
    database_id: str,
    generated_sql: str,
    is_safe: bool,
    latency_ms: int,
    row_count: int,
    error: str | None = None,
) -> None:
    _history.appendleft(
        {
            "question": question,
            "database_id": database_id,
            "generated_sql": generated_sql,
            "is_safe": is_safe,
            "latency_ms": latency_ms,
            "row_count": row_count,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def list_history() -> list[dict]:
    return list(_history)
