from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import asyncpg


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    sample_values: List[Any]


@dataclass
class TableInfo:
    name: str
    columns: List[ColumnInfo]


async def introspect_schema(conn: asyncpg.Connection, sample_distinct_per_column: int = 5) -> Dict[str, Any]:
    """
    Returns a cache-friendly schema context:
    {
      "tables": [
        {"name": ..., "columns":[{"name":..., "data_type":..., "sample_values":[...]}]}
      ]
    }
    """
    # Get table names
    rows = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
    )
    table_names = [r["table_name"] for r in rows]

    tables: List[TableInfo] = []

    for table_name in table_names:
        col_rows = await conn.fetch(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=$1
            ORDER BY ordinal_position;
            """,
            table_name,
        )

        columns: List[ColumnInfo] = []
        for c in col_rows:
            col_name = c["column_name"]
            data_type = c["data_type"]

            # sample distinct values
            sample_values: List[Any] = []
            try:
                sv = await conn.fetch(
                    f"""
                    SELECT DISTINCT {asyncpg.identify(col_name)} AS v
                    FROM {asyncpg.identify(table_name)}
                    WHERE {asyncpg.identify(col_name)} IS NOT NULL
                    LIMIT {int(sample_distinct_per_column)};
                    """,
                )
                sample_values = [x["v"] for x in sv]
            except Exception:
                sample_values = []

            columns.append(
                ColumnInfo(
                    name=col_name,
                    data_type=data_type,
                    sample_values=sample_values,
                )
            )

        tables.append(TableInfo(name=table_name, columns=columns))

    # Convert to JSON-able dict
    return {
        "tables": [
            {
                "name": t.name,
                "columns": [
                    {"name": col.name, "data_type": col.data_type, "sample_values": col.sample_values}
                    for col in t.columns
                ],
            }
            for t in tables
        ]
    }


def schema_to_prompt(schema_context: Dict[str, Any]) -> str:
    parts: List[str] = []
    for t in schema_context.get("tables", []):
        parts.append(f"Table: {t['name']}")
        for c in t.get("columns", []):
            sv = c.get("sample_values") or []
            sv_str = ", ".join([str(x) for x in sv[:5]]) if sv else "[]"
            parts.append(f"- {c['name']} ({c['data_type']}) sample: {sv_str}")
    return "\n".join(parts)
