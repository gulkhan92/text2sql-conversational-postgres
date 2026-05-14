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

        # Generate SQL + fallback loop on execution errors.
        # If the LLM produces invalid SQL (or it's blocked by RBAC),
        # feed the error back and ask for a corrected query.
        last_err: Exception | None = None
        sql: str = ""
        data: list[Dict[str, Any]] = []

        for _ in range(3):
            sql = await generate_sql(
                client,
                schema_context={"schema_prompt": str(schema_context), "error_hint": ""},
                question=question,
            )

            try:
                data = await execute_readonly_select(
                    conn,
                    sql,
                    role=role,
                    statement_timeout_ms=30_000,
                )
                break
            except Exception as e:
                last_err = e
                # If RBAC denies the query, do not keep retrying.
                err_str = str(e).lower()
                if "not allowed" in err_str or "role '" in err_str or "forbidden" in err_str:
                    raise

                # Provide error feedback to LLM on next iteration.
                schema_context = {
                    "tables": schema_context.get("tables", []),
                    "error_hint": str(e),
                }

        else:
            # Ran out of retries
            raise last_err or RuntimeError("Failed to generate an executable SQL query.")


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
        # If the RBAC SQL allowlisting blocks the query, return a role-appropriate message.
        err = str(e)
        if "not allowed" in err or "Role '" in err or "allowed" in err:
            return {
                "answer": "You don't have access to the requested data for your role.",
                "sql": "",
                "data": [],
                "chart_suggested": False,
                "chart_type": "table",
            }

        return {
            "answer": f"Failed to answer the question: {e}",
            "sql": "",
            "data": [],
            "chart_suggested": False,
            "chart_type": "table",
        }
    finally:
        await conn.close()
