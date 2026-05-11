import pytest

from backend.db.query_executor import execute_readonly_select


class FakeTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConn:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.executed_statements = []

    def transaction(self, *, readonly: bool):
        assert readonly is True
        return FakeTx()

    async def execute(self, sql: str):
        self.executed_statements.append(sql)

    async def fetch(self, sql: str):
        # asyncpg records are dict-like; in our executor we convert via dict(r)
        # We'll return plain dicts, which still work with dict(r).
        return self._rows

    async def close(self):
        return None


@pytest.mark.parametrize(
    "bad_sql",
    [
        "UPDATE t SET a=1",
        "delete from t",
        "  insert into t(a) values (1)",
        "create table x(id int)",
        "alter table t add column y int",
        "drop table t",
        "select * from t; delete from t2",  # contains forbidden keyword even if starts with SELECT
        "select * from t where name like '%update%';",
    ],
)
async def test_execute_readonly_select_rejects_forbidden_keywords(bad_sql):
    conn = FakeConn()
    with pytest.raises(ValueError):
        await execute_readonly_select(conn, bad_sql)


@pytest.mark.parametrize(
    "good_sql",
    [
        "SELECT 1",
        " select * from t ",
        "SELECT\n* FROM t LIMIT 5",
    ],
)
async def test_execute_readonly_select_allows_select_and_sets_statement_timeout(good_sql):
    conn = FakeConn(rows=[{"col": 1}, {"col": 2}])
    rows = await execute_readonly_select(conn, good_sql, statement_timeout_ms=1234)

    # statement_timeout should be set
    assert any("SET statement_timeout" in s for s in conn.executed_statements)
    assert rows == [{"col": 1}, {"col": 2}]


async def test_execute_readonly_select_rejects_non_select():
    conn = FakeConn()
    with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
        await execute_readonly_select(conn, "WITH x AS (SELECT 1) SELECT * FROM x")

