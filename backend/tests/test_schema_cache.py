import time
from unittest.mock import AsyncMock, patch

import pytest

from backend.db.schema_cache import SchemaCache


class FakeConn:
    async def close(self):
        return None


@pytest.mark.asyncio
async def test_schema_cache_returns_cached_data_when_fresh():
    cache = SchemaCache(ttl_seconds=300)
    conn = FakeConn()

    with patch("backend.db.schema_cache.time.time", side_effect=[1000.0, 1000.0]):
        # first call loads
        with patch("backend.db.schema_cache.introspect_schema", new=AsyncMock(return_value={"tables": []})) as introspect:
            data1 = await cache.get(conn)
            assert data1 == {"tables": []}
            introspect.assert_awaited_once()

    # second call should be fresh (same patched time)
    with patch("backend.db.schema_cache.time.time", side_effect=[1001.0]):
        with patch("backend.db.schema_cache.introspect_schema", new=AsyncMock(return_value={"tables": [{"name": "x"}]})) as introspect2:
            data2 = await cache.get(conn)
            assert data2 == {"tables": []}
            introspect2.assert_not_awaited()


@pytest.mark.asyncio
async def test_schema_cache_refreshes_data_when_stale():
    cache = SchemaCache(ttl_seconds=10)
    conn = FakeConn()

    with patch("backend.db.schema_cache.time.time", side_effect=[1000.0]):
        with patch("backend.db.schema_cache.introspect_schema", new=AsyncMock(return_value={"tables": [{"name": "a"}]})) as introspect:
            data1 = await cache.get(conn)
            assert data1 == {"tables": [{"name": "a"}]}
            introspect.assert_awaited_once()

    # stale: last_loaded=1000.0, now=1011.0
    with patch("backend.db.schema_cache.time.time", side_effect=[1011.0]):
        with patch("backend.db.schema_cache.introspect_schema", new=AsyncMock(return_value={"tables": [{"name": "b"}]})) as introspect2:
            data2 = await cache.get(conn)
            assert data2 == {"tables": [{"name": "b"}]}
            introspect2.assert_awaited_once()

