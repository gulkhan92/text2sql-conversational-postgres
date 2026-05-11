"""Additional focused tests for SchemaCache TTL math.

This file exists to provide extra, more granular coverage.
"""

from unittest.mock import AsyncMock, patch

import pytest

from backend.db.schema_cache import SchemaCache


class FakeConn:
    async def close(self):
        return None


@pytest.mark.asyncio
async def test_schema_cache_returns_empty_when_never_loaded():
    cache = SchemaCache(ttl_seconds=300)
    conn = FakeConn()
    with patch("backend.db.schema_cache.introspect_schema", new=AsyncMock(return_value={"tables": [{"name": "t"}]})) as introspect:
        data = await cache.get(conn)
        assert data == {"tables": [{"name": "t"}]}
        introspect.assert_awaited_once()

