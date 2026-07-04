"""Pydantic request/response schemas for the API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural-language question.")
    database_id: str = Field(..., min_length=1, description="Registered database id.")


class QueryResponse(BaseModel):
    generated_sql: str
    explanation: str
    result: list[dict]
    is_safe: bool
    latency_ms: int


class ValidateSQLRequest(BaseModel):
    sql: str = Field(..., min_length=1)


class ValidateSQLResponse(BaseModel):
    is_safe: bool
    reason: str


class ColumnInfo(BaseModel):
    name: str
    type: str


class TableSchema(BaseModel):
    name: str
    columns: list[ColumnInfo]


class SchemaResponse(BaseModel):
    database_id: str
    tables: list[TableSchema]


class QueryHistoryItem(BaseModel):
    question: str
    database_id: str
    generated_sql: str
    is_safe: bool
    latency_ms: int
    row_count: int
    error: str | None = None
    timestamp: str


class QueryHistoryResponse(BaseModel):
    items: list[QueryHistoryItem]


class HealthResponse(BaseModel):
    status: str
    llm_configured: bool
    databases: list[str]


class DatabaseInfo(BaseModel):
    id: str
    name: str
    kind: str


class DatabasesResponse(BaseModel):
    databases: list[DatabaseInfo]
