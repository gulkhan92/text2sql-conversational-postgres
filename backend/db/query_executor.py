import json
from typing import Any, Dict, List, Optional, Sequence

import re

import asyncpg

from backend.security.rbac_config import allowed_columns_for_role, allowed_tables_for_role


def _validate_sql_allowlisting(*, sql: str, role: str) -> None:
    """Conservative SQL allowlisting.

    This is intentionally best-effort and blocks anything it can't confidently
    understand.
    """
    s = (sql or "").strip()
    if not s:
        raise ValueError("Empty SQL.")

    tables_allowed = allowed_tables_for_role(role)

    # Find base tables referenced in FROM/JOIN.
    # Supports: FROM public.t / FROM t / JOIN public.t / JOIN t
    table_tokens = []
    for m in re.finditer(r"\b(?:from|join)\s+(?:public\.)?(?P<table>[a-zA-Z_][a-zA-Z0-9_]*)\b", s, flags=re.IGNORECASE):
        table_tokens.append(m.group("table"))

    for t in table_tokens:
        if t not in tables_allowed:
            raise ValueError(f"Role '{role}' is not allowed to query table '{t}'.")

    # Extract SELECT clause up to first FROM.
    m_sel = re.search(r"\bselect\b(?P<select_body>[\s\S]*?)\bfrom\b", s, flags=re.IGNORECASE)
    if not m_sel:
        # If we can't parse, do not allow.
        raise ValueError("Unable to parse SELECT clause for allowlisting.")
    select_body = m_sel.group("select_body")

    # If '*' selected, only allow for admin.
    if "*" in select_body:
        if role != "admin":
            raise ValueError(f"Role '{role}' is not allowed to use SELECT *.")

    # Split by commas at top-level (best-effort: no nested functions parsing).
    items = [it.strip() for it in select_body.split(",") if it.strip()]

    # Build a set of referenced base tables (from FROM/JOIN) for column resolution.
    referenced_tables = set(table_tokens)

    for item in items:
        # Remove aliases: expr AS alias  OR expr alias
        item_no_alias = re.split(r"\s+as\s+", item, flags=re.IGNORECASE)[0]
        item_no_alias = re.split(r"\s{1,}" , item_no_alias)[0] if " " in item_no_alias else item_no_alias
        item_no_alias = item_no_alias.strip()

        # Qualified column: t.col
        m_col = re.match(r"^(?P<table>[a-zA-Z_][a-zA-Z0-9_]*)\.(?P<col>[a-zA-Z_][a-zA-Z0-9_]*)$", item_no_alias)
        if m_col:
            t = m_col.group("table")
            col = m_col.group("col")
            # If alias used for table, we may not map it. Deny unless admin.
            if role != "admin":
                if t not in referenced_tables:
                    raise ValueError(f"Role '{role}' is not allowed to reference column '{item}'.")
                allowed_cols = allowed_columns_for_role(role, t)
                if col not in allowed_cols:
                    raise ValueError(f"Role '{role}' is not allowed to select column '{t}.{col}'.")
            continue

        # Unqualified column: col or aggregate(col)
        m_unqual = re.match(r"^(?P<col>[a-zA-Z_][a-zA-Z0-9_]*)$", item_no_alias)
        if m_unqual:
            col = m_unqual.group("col")
            # For non-admin, require column exists in exactly one allowed table among referenced tables.
            if role != "admin":
                candidates = [t for t in referenced_tables if col in allowed_columns_for_role(role, t)]
                if len(candidates) != 1:
                    raise ValueError(f"Role '{role}' is not allowed to select ambiguous column '{col}'.")
            continue

        # Any complex expression we can't validate -> deny for non-admin.
        if role != "admin":
            raise ValueError(f"Role '{role}' is not allowed to use complex select expression '{item}'.")


async def execute_readonly_select(
    conn: asyncpg.Connection,
    sql: str,
    *,
    role: str = "admin",
    statement_timeout_ms: int = 30_000,
) -> List[Dict[str, Any]]:
    """
    Executes a SQL string as read-only and SELECT-only.
    Returns list of rows as dicts.

    Guardrails:
    - Reject non-SELECT queries (basic).
    - Blocks write-like keywords.
    - Enforces RBAC allowlisting for base tables + selected columns using
      `backend.security.rbac_config`.
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

    # Role-aware allowlisting (best-effort SQL parsing; conservative by design)
    _validate_sql_allowlisting(sql=sql, role=role)

    async with conn.transaction(readonly=True):
        await conn.execute(f"SET statement_timeout = {int(statement_timeout_ms)};")

        rows = await conn.fetch(sql)
        # asyncpg Record -> dict
        return [dict(r) for r in rows]
