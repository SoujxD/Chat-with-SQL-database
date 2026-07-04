"""FastAPI application exposing the Chat-with-SQL backend (Phase 2A)."""
from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import history
from .config import DATABASES, MAX_RESULT_ROWS
from .database import QueryTimeoutError, dialect_name, get_schema, run_query
from .llm import LLMNotConfigured, generate_sql, is_configured
from .models import (
    DatabaseInfo,
    DatabasesResponse,
    HealthResponse,
    QueryHistoryResponse,
    QueryRequest,
    QueryResponse,
    SchemaResponse,
    ValidateSQLRequest,
    ValidateSQLResponse,
)
from .safety import ensure_limit, validate_sql

app = FastAPI(
    title="Chat with SQL Database API",
    description="Natural-language to SQL over registered databases.",
    version="2.0.0",
)

# Allow local frontends (e.g. Streamlit / a future web UI) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        llm_configured=is_configured(),
        databases=list(DATABASES.keys()),
    )


@app.get("/api/databases", response_model=DatabasesResponse)
def databases() -> DatabasesResponse:
    return DatabasesResponse(
        databases=[
            DatabaseInfo(id=cfg.database_id, name=cfg.name, kind=cfg.kind)
            for cfg in DATABASES.values()
        ]
    )


@app.get("/api/schema", response_model=SchemaResponse)
def schema(database_id: str = Query("student", description="Registered database id.")) -> SchemaResponse:
    if database_id not in DATABASES:
        raise HTTPException(status_code=404, detail=f"Unknown database_id: {database_id}")
    return SchemaResponse(database_id=database_id, tables=get_schema(database_id))


@app.post("/api/validate-sql", response_model=ValidateSQLResponse)
def validate_sql_endpoint(req: ValidateSQLRequest) -> ValidateSQLResponse:
    is_safe, reason = validate_sql(req.sql)
    return ValidateSQLResponse(is_safe=is_safe, reason=reason)


@app.get("/api/query-history", response_model=QueryHistoryResponse)
def query_history() -> QueryHistoryResponse:
    return QueryHistoryResponse(items=history.list_history())


@app.post("/api/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    if req.database_id not in DATABASES:
        raise HTTPException(status_code=404, detail=f"Unknown database_id: {req.database_id}")

    start = time.perf_counter()

    # 1. Generate SQL from the question.
    try:
        generated_sql, explanation = generate_sql(
            req.question, req.database_id, dialect=dialect_name(req.database_id)
        )
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # network/model errors
        raise HTTPException(status_code=502, detail=f"SQL generation failed: {exc}") from exc

    if not generated_sql.strip():
        latency_ms = int((time.perf_counter() - start) * 1000)
        message = explanation or "Question requires a write operation, which is not supported."
        history.record(
            question=req.question,
            database_id=req.database_id,
            generated_sql="",
            is_safe=False,
            latency_ms=latency_ms,
            row_count=0,
            error=f"Model declined to generate SQL: {explanation}",
        )
        raise HTTPException(
            status_code=400,
            detail={"message": message, "generated_sql": "", "explanation": explanation, "is_safe": False},
        )

    # Auto-add a LIMIT if the model forgot one, so benign queries aren't
    # rejected outright — the row cap in run_query enforces the ceiling
    # either way, this just keeps intent explicit in the executed SQL.
    generated_sql = ensure_limit(generated_sql, MAX_RESULT_ROWS)

    # 2. Safety-check before executing.
    is_safe, reason = validate_sql(generated_sql)
    if not is_safe:
        latency_ms = int((time.perf_counter() - start) * 1000)
        history.record(
            question=req.question,
            database_id=req.database_id,
            generated_sql=generated_sql,
            is_safe=False,
            latency_ms=latency_ms,
            row_count=0,
            error=f"Blocked unsafe SQL: {reason}",
        )
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Generated SQL is not safe: {reason}",
                "generated_sql": generated_sql,
                "explanation": explanation,
                "is_safe": False,
                "reason": reason,
            },
        )

    # 3. Execute read-only and return rows.
    try:
        result = run_query(req.database_id, generated_sql)
    except QueryTimeoutError as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        history.record(
            question=req.question,
            database_id=req.database_id,
            generated_sql=generated_sql,
            is_safe=True,
            latency_ms=latency_ms,
            row_count=0,
            error=str(exc),
        )
        raise HTTPException(
            status_code=408,
            detail={"message": str(exc), "generated_sql": generated_sql, "explanation": explanation, "is_safe": True},
        ) from exc
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        history.record(
            question=req.question,
            database_id=req.database_id,
            generated_sql=generated_sql,
            is_safe=True,
            latency_ms=latency_ms,
            row_count=0,
            error=str(exc),
        )
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Query execution failed: {exc}",
                "generated_sql": generated_sql,
                "explanation": explanation,
                "is_safe": True,
            },
        ) from exc

    latency_ms = int((time.perf_counter() - start) * 1000)
    history.record(
        question=req.question,
        database_id=req.database_id,
        generated_sql=generated_sql,
        is_safe=True,
        latency_ms=latency_ms,
        row_count=len(result),
    )

    return QueryResponse(
        generated_sql=generated_sql,
        explanation=explanation,
        result=result,
        is_safe=True,
        latency_ms=latency_ms,
    )
