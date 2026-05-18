from fastapi import APIRouter, Depends


from backend.db.connection import create_connection
from backend.db.schema_cache import SchemaCache
from backend.security.auth import get_current_role
from backend.security.rbac_config import ROLE_ACCESS


router = APIRouter()

_cache = SchemaCache(ttl_seconds=300)


@router.get("/schema")
async def schema(role: str = Depends(get_current_role)):

    conn = await create_connection()
    try:
        schema_context = await _cache.get(conn)
        # Role-aware sanitization for least-privilege schema sharing.
        role_access = ROLE_ACCESS.get(role)
        if not role_access:
            return schema_context

        allowed_cols = role_access.columns
        allowed_tables = role_access.tables

        sanitized = {
            "tables": [
                {
                    "name": t["name"],
                    "columns": [
                        c
                        for c in t["columns"]
                        if t["name"] in allowed_tables and c["name"] in allowed_cols.get(t["name"], set())
                    ],
                }
                for t in schema_context.get("tables", [])
                if t.get("name") in allowed_tables
            ]
        }
        return sanitized
    finally:
        await conn.close()
