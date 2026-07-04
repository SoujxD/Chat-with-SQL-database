"""Natural-language -> SQL generation using Groq (via langchain-groq)."""
from __future__ import annotations

import json
import re

from langchain_groq import ChatGroq

from .config import GROQ_API_KEY, GROQ_MODEL, MAX_RESULT_ROWS
from .database import schema_as_text

_SYSTEM_PROMPT = """You are an expert data analyst that translates questions into \
SQL for a {dialect} database.

Rules:
- Generate exactly ONE read-only SELECT statement. Never write INSERT, UPDATE, \
DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, or any statement that \
changes data, schema, or permissions.
- If the question asks you to modify, delete, or create data or schema, refuse: \
set "sql" to an empty string and use "explanation" to say only read queries \
are supported.
- Always include a top-level LIMIT clause. Default to LIMIT {max_rows} unless \
the question implies a smaller number (e.g. "top 10").
- Use only the tables and columns from the schema below. Do not invent names.
- Do not wrap the SQL in markdown fences.

Schema:
{schema}

Respond with a strict JSON object and nothing else, of the form:
{{"sql": "<the SELECT query>", "explanation": "<one or two sentences explaining \
what the query does in plain English>"}}"""


class LLMNotConfigured(RuntimeError):
    """Raised when GROQ_API_KEY is missing."""


def is_configured() -> bool:
    return bool(GROQ_API_KEY)


def generate_sql(question: str, database_id: str, dialect: str = "SQLite") -> tuple[str, str]:
    """Return (sql, explanation) for the question. Raises LLMNotConfigured if no key."""
    if not is_configured():
        raise LLMNotConfigured(
            "GROQ_API_KEY is not set. Set it in the environment or a .env file."
        )

    llm = ChatGroq(groq_api_key=GROQ_API_KEY, model_name=GROQ_MODEL, temperature=0)
    system = _SYSTEM_PROMPT.format(
        dialect=dialect, schema=schema_as_text(database_id), max_rows=MAX_RESULT_ROWS
    )
    response = llm.invoke([("system", system), ("human", question)])
    content = response.content if isinstance(response.content, str) else str(response.content)

    sql, explanation = _parse_response(content)
    return sql, explanation


def _parse_response(content: str) -> tuple[str, str]:
    """Extract sql/explanation from the model output, tolerating stray fences."""
    text = content.strip()
    # Strip ```json ... ``` fences if the model added them anyway.
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()

    try:
        data = json.loads(text)
        sql = str(data.get("sql", "")).strip()
        explanation = str(data.get("explanation", "")).strip()
        if sql:
            return sql, explanation or "No explanation provided."
    except json.JSONDecodeError:
        pass

    # Fallback: try to find a JSON object anywhere in the text.
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            sql = str(data.get("sql", "")).strip()
            explanation = str(data.get("explanation", "")).strip()
            if sql:
                return sql, explanation or "No explanation provided."
        except json.JSONDecodeError:
            pass

    # Last resort: treat the whole response as SQL.
    return text, "Model did not return structured output; using raw response as SQL."
