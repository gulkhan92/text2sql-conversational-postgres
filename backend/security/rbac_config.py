from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Set


@dataclass(frozen=True)
class RoleAccess:
    # Base tables allowed in SQL (base tables only; no joins to disallowed tables)
    tables: Set[str]
    # Allowed columns per base table
    columns: Dict[str, Set[str]]


# Seed DB schema (public schema) used for RBAC allowlisting.
# This is intentionally conservative: if something isn't listed, it's considered disallowed.
ROLE_ACCESS: Dict[str, RoleAccess] = {
    # Admin sees everything
    "admin": RoleAccess(
        tables={"locations", "customers", "transactions"},
        columns={
            "locations": {"id", "state_names"},
            "customers": {
                "id",
                "gender",
                "age",
                "marital_status",
                "segment",
                "employees_status",
                "payment_method",
                "referral",
            },
            "transactions": {"id", "transaction_id", "transaction_date", "customer_id", "location_id", "amount_spent"},
        },
    ),
    # Staff: least privilege; allow aggregated spending analytics but restrict PII-like columns
    # (conservative heuristic: only allow non-sensitive customer attributes; deny referral/payment_method)
    "staff": RoleAccess(
        tables={"locations", "customers", "transactions"},
        columns={
            "locations": {"id", "state_names"},
            "customers": {"id", "gender", "age", "marital_status", "segment", "employees_status"},
            "transactions": {"id", "transaction_id", "transaction_date", "location_id", "amount_spent"},
        },
    ),
    # Customer: only their own transactions + limited profile fields
    # Note: Enforcement below is still SQL allowlisting; row-level ownership requires adding
    # DB-side RLS/GRANT + user identity mapping (defense-in-depth plan in RBAC.md).
    "customer": RoleAccess(
        tables={"transactions", "customers"},
        columns={
            "transactions": {"id", "transaction_id", "transaction_date", "customer_id", "amount_spent"},
            "customers": {"id", "gender", "age", "marital_status", "segment", "employees_status"},
        },
    ),
}


def allowed_tables_for_role(role: str) -> Set[str]:
    return ROLE_ACCESS[role].tables


def allowed_columns_for_role(role: str, table: str) -> Set[str]:
    return ROLE_ACCESS[role].columns.get(table, set())


def allowed_columns_for_role_as_iterable(role: str) -> Iterable[tuple[str, str]]:
    for t, cols in ROLE_ACCESS[role].columns.items():
        for c in cols:
            yield t, c
