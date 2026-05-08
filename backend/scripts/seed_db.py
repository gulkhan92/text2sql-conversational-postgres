import csv
import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Tuple

import asyncpg
from dotenv import load_dotenv

load_dotenv()


CSV_PATH = os.getenv("CSV_PATH", "customer_spending_1M_2018_2025.csv")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS locations (
  id BIGSERIAL PRIMARY KEY,
  state_names TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS customers (
  id BIGSERIAL PRIMARY KEY,

  gender TEXT,
  age INTEGER,
  marital_status TEXT,
  segment TEXT,
  employees_status TEXT,
  payment_method TEXT,
  referral TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
  id BIGSERIAL PRIMARY KEY,

  transaction_id TEXT UNIQUE,
  transaction_date TIMESTAMPTZ,

  customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
  location_id BIGINT NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,

  amount_spent NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_transactions_customer_id ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_location_id ON transactions(location_id);
CREATE INDEX IF NOT EXISTS idx_transactions_transaction_date ON transactions(transaction_date);
"""


def parse_int(x):
    if x is None:
        return None
    x = str(x).strip()
    if not x or x.lower() in {"nan", "none"}:
        return None
    try:
        return int(float(x))
    except Exception:
        return None


def parse_amount(x):
    if x is None:
        return None
    x = str(x).strip()
    if not x or x.lower() in {"nan", "none"}:
        return None
    try:
        return float(x)
    except Exception:
        return None


def parse_datetime(x):
    if x is None:
        return None
    x = str(x).strip()
    if not x or x.lower() in {"nan", "none"}:
        return None

    # Try common formats; fall back to NULL.
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(x, fmt)
            return dt.isoformat()
        except Exception:
            pass
    try:
        # Let Postgres parse if possible
        return x
    except Exception:
        return None


async def seed():
    host = os.getenv("POSTGRES_HOST", "db")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    db = os.getenv("POSTGRES_DB", "text2sql")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found at: {CSV_PATH}")

    conn = await asyncpg.connect(
        host=host, port=port, database=db, user=user, password=password
    )

    try:
        await conn.execute(SCHEMA_SQL)

        # Speed: disable auto-commit; use COPY where possible for large inserts.
        # We'll do batched INSERT for simplicity and reliability in this scaffold.
        # (This can be upgraded to COPY later.)
        await conn.execute("TRUNCATE TABLE transactions RESTART IDENTITY CASCADE;")
        await conn.execute("TRUNCATE TABLE customers RESTART IDENTITY CASCADE;")
        await conn.execute("TRUNCATE TABLE locations RESTART IDENTITY CASCADE;")

        location_cache: Dict[str, int] = {}
        customer_cache: Dict[
            Tuple[str, int, str, str, str, str, str], int
        ] = {}

        async def get_location_id(state_names: str) -> int:
            if state_names in location_cache:
                return location_cache[state_names]

            row = await conn.fetchrow(
                "INSERT INTO locations (state_names) VALUES ($1) "
                "ON CONFLICT (state_names) DO UPDATE SET state_names = EXCLUDED.state_names "
                "RETURNING id;",
                state_names,
            )
            location_cache[state_names] = row["id"]
            return row["id"]

        async def get_customer_id(
            gender, age, marital_status, segment, employees_status, payment_method, referral
        ) -> int:
            key = (gender, age, marital_status, segment, employees_status, payment_method, referral)
            if key in customer_cache:
                return customer_cache[key]

            row = await conn.fetchrow(
                """
                INSERT INTO customers (gender, age, marital_status, segment, employees_status, payment_method, referral)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                RETURNING id;
                """,
                gender,
                age,
                marital_status,
                segment,
                employees_status,
                payment_method,
                referral,
            )
            customer_cache[key] = row["id"]
            return row["id"]

        # Insert in batches
        batch_transactions = []
        batch_size = 5000

        with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, r in enumerate(reader, start=1):
                transaction_id = (r.get("Transaction_ID") or "").strip()
                transaction_date = parse_datetime(r.get("Transaction_date"))
                gender = (r.get("Gender") or "").strip() or None
                age = parse_int(r.get("Age"))
                marital_status = (r.get("Marital_status") or "").strip() or None
                state_names = (r.get("State_names") or "").strip() or "Unknown"
                segment = (r.get("Segment") or "").strip() or None
                employees_status = (r.get("Employees_status") or "").strip() or None
                payment_method = (r.get("Payment_method") or "").strip() or None
                referral = (r.get("Referral") or "").strip() or None
                amount_spent = parse_amount(r.get("Amount_spent"))

                location_id = await get_location_id(state_names)
                customer_id = await get_customer_id(
                    gender, age, marital_status, segment, employees_status, payment_method, referral
                )

                batch_transactions.append(
                    (transaction_id, transaction_date, customer_id, location_id, amount_spent)
                )

                if len(batch_transactions) >= batch_size:
                    await conn.executemany(
                        """
                        INSERT INTO transactions (transaction_id, transaction_date, customer_id, location_id, amount_spent)
                        VALUES ($1,$2,$3,$4,$5)
                        ON CONFLICT (transaction_id) DO NOTHING;
                        """,
                        batch_transactions,
                    )
                    batch_transactions.clear()
                    if i % 50000 == 0:
                        print(f"Seeded ~{i} rows...")

        if batch_transactions:
            await conn.executemany(
                """
                INSERT INTO transactions (transaction_id, transaction_date, customer_id, location_id, amount_spent)
                VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT (transaction_id) DO NOTHING;
                """,
                batch_transactions,
            )

        await conn.execute("ANALYZE;")
        print("Seeding complete.")

    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except KeyboardInterrupt:
        sys.exit(130)
