from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_chat_empty_question(client):
    res = client.post("/chat", json={"message": "  "})
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == "Please provide a question."
    assert body["sql"] == ""
    assert body["data"] == []
    assert body["chart_suggested"] is False


def test_chat_happy_path(client):
    # Patch out all async dependencies called from the route
    with patch("backend.routes.chat.create_connection") as create_conn:
        create_conn.return_value = AsyncMock()

        fake_conn = AsyncMock()
        # schema_cache.get returns schema_context-like dict
        with patch("backend.routes.chat._cache.get", new=AsyncMock(return_value={"schema_prompt": "TABLES"})):
            with patch("backend.routes.chat.generate_sql", new=AsyncMock(return_value="SELECT * FROM customers")):
                with patch("backend.routes.chat.execute_readonly_select", new=AsyncMock(return_value=[{"a": 1, "b": 2}])):
                    with patch("backend.routes.chat.summarize_results", new=AsyncMock(return_value="answer ok")):
                        # also ensure conn.close is awaited
                        fake_conn.close = AsyncMock()
                        create_conn.return_value = fake_conn

                        res = client.post("/chat", json={"message": "hi"})
                        assert res.status_code == 200
                        body = res.json()
                        assert body["answer"] == "answer ok"
                        assert body["sql"] == "SELECT * FROM customers"
                        assert body["data"] == [{"a": 1, "b": 2}]
                        assert body["chart_suggested"] is True
                        assert body["chart_type"] == "bar"


def test_chat_error_path_returns_failure_message(client):
    with patch("backend.routes.chat.create_connection") as create_conn:
        fake_conn = AsyncMock()
        fake_conn.close = AsyncMock()
        create_conn.return_value = fake_conn

        with patch("backend.routes.chat._cache.get", new=AsyncMock(return_value={"schema_prompt": "TABLES"})):
            with patch("backend.routes.chat.generate_sql", new=AsyncMock(side_effect=RuntimeError("LLM down"))):
                res = client.post("/chat", json={"message": "hi"})
                assert res.status_code == 200
                body = res.json()
                assert "Failed to answer the question" in body["answer"]
                assert body["sql"] == ""
                assert body["data"] == []

