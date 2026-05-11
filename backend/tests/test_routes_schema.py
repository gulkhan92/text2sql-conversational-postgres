from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.main import app


def test_schema_route_uses_cache_and_closes_conn():
    client = TestClient(app)

    with patch("backend.routes.schema.create_connection") as create_conn:
        fake_conn = AsyncMock()
        fake_conn.close = AsyncMock()
        create_conn.return_value = fake_conn

        with patch("backend.routes.schema._cache.get", new=AsyncMock(return_value={"tables": []})) as cache_get:
            res = client.get("/schema")
            assert res.status_code == 200
            assert res.json() == {"tables": []}
            cache_get.assert_awaited_once()
            fake_conn.close.assert_awaited_once()

