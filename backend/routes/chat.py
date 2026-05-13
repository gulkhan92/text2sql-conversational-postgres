from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from backend.db.connection import create_connection
from backend.db.query_executor import execute_readonly_select
from backend.db.schema_cache import SchemaCache
from backend.llm.gemini_client import generate_sql, get_client, summarize_results
from backend.security.auth import get_current_role
from backend.security.rbac_config import ROLE_ACCESS

router = APIRouter()

_cache = SchemaCache(ttl_seconds=300)


class ChatRequest(BaseModel):
    message: str


def _maybe_chart_suggestion(rows: list[Dict[str, Any]]) -> tuple[bool, str]:
    # lightweight heuristic: if first row has at least 2 fields, suggest bar
    if not rows:
        return False, "bar"
    if len(rows[0].keys()) >= 2:
        return True, "bar"
    return False, "table"


@router.post("/chat")
async def chat(req: ChatRequest, role: str = get_current_role()):
    question = (req.message or "").strip()
    if not question:
        return {
            "answer": "Please provide a question.",
            "sql": "",
            "data": [],
            "chart_suggested": False,
            "chart_type": "table",
        }

    conn = await create_connection()
    try:
        schema_context = await _cache.get(conn)
        # Role-aware schema shaping: prevent Gemini from seeing disallowed columns/tables.
        role_access = ROLE_ACCESS.get(role)
        if role_access:
            allowed_cols = role_access.columns
            allowed_tables = role_access.tables
            schema_context = {
                "tables": [
                    {
                        "name": t["name"],
                        "columns": [
                            c
                            for c in t["columns"]
                            if t["name"] in allowed_tables
                            and c["name"] in allowed_cols.get(t["name"], set())
                        ],
                    }
                    for t in schema_context.get("tables", [])
                    if t.get("name") in allowed_tables
                ]
            }

        client = get_client()
        sql = await generate_sql(
            client,
            schema_context={"schema_prompt": str(schema_context)},
            question=question,
        )

        # Execute SQL (read-only + statement_timeout)
        data = await execute_readonly_select(conn, sql, role=role, statement_timeout_ms=30_000)

        # Summarize
        answer = await summarize_results(
            client,
            question=question,
            sql=sql,
            results=data,
        )

        chart_suggested, chart_type = _maybe_chart_suggestion(data)

        return {
            "answer": answer,
            "sql": sql,
            "data": data,
            "chart_suggested": chart_suggested,
            "chart_type": chart_type,
        }
    except Exception as e:
        return {
            "answer": f"Failed to answer the question: {e}",
            "sql": "",
            "data": [],
            "chart_suggested": False,
            "chart_type": "table",
        }
    finally:
        await conn.close()
