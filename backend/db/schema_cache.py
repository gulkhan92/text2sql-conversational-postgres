import time
from typing import Any, Dict, Optional

import asyncpg

from backend.db.introspection import introspect_schema


class SchemaCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._last_loaded: float = 0.0
        self._data: Optional[Dict[str, Any]] = None

    def is_fresh(self) -> bool:
        if self._data is None:
            return False
        return (time.time() - self._last_loaded) < self.ttl_seconds

    async def get(self, conn: asyncpg.Connection) -> Dict[str, Any]:
        if self.is_fresh():
            return self._data or {"tables": []}
        self._data = await introspect_schema(conn)
        self._last_loaded = time.time()
        return self._data
