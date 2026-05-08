import json
from typing import Any, Dict, List, Optional, Sequence

import asyncpg


async def execute_readonly_select(
    conn: asyncpg.Connection,
    sql: str,
    *,
    statement_timeout_ms: int = 30_000,
) -> List[Dict[str, Any]]:
    """
    Executes a SQL string as read-only and SELECT-only.
    Returns list of rows as dicts.

    Guardrails:
    - Reject non-SELECT queries (basic).
    - Uses READ ONLY transaction + statement_timeout.
    """
    normalized = (sql or "").strip().lower()
    if not normalized.startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")

    # Basic disallow keywords that often indicate write operations
    forbidden = [" insert ", " update ", " delete ", " create ", " drop ", " alter ", " truncate "]
    padded = f" {normalized} "
    if any(k in padded for k in forbidden):
        raise ValueError("Query appears to contain forbidden keywords.")

    async with conn.transaction(readonly=True):
        await conn.execute(f"SET statement_timeout = {int(statement_timeout_ms)};")

        rows = await conn.fetch(sql)
        # asyncpg Record -> dict
        return [dict(r) for r in rows]
