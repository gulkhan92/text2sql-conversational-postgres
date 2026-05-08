from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from backend.db.connection import create_connection
from backend.db.query_executor import execute_readonly_select
from backend.db.schema_cache import SchemaCache
from backend.llm.gemini_client import generate_sql, get_client, summarize_results

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
async def chat(req: ChatRequest):
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

        client = get_client()
        sql = await generate_sql(
            client,
            schema_context={"schema_prompt": str(schema_context)},
            question=question,
        )

        # Execute SQL (read-only + statement_timeout)
        data = await execute_readonly_select(conn, sql, statement_timeout_ms=30_000)

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
