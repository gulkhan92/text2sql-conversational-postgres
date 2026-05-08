import os
from typing import Optional

import asyncpg


def _getenv(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing env var: {name}")
    return val


async def create_connection() -> asyncpg.Connection:
    host = _getenv("POSTGRES_HOST", "db")
    port = int(_getenv("POSTGRES_PORT", "5432"))
    database = _getenv("POSTGRES_DB", "text2sql")
    user = _getenv("POSTGRES_USER", "postgres")
    password = _getenv("POSTGRES_PASSWORD", "postgres")

    return await asyncpg.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    )
