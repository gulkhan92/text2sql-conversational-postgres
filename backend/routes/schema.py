from fastapi import APIRouter

from backend.db.connection import create_connection
from backend.db.schema_cache import SchemaCache

router = APIRouter()

_cache = SchemaCache(ttl_seconds=300)


@router.get("/schema")
async def schema():
    conn = await create_connection()
    try:
        return await _cache.get(conn)
    finally:
        await conn.close()
