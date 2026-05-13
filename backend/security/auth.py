import os
from typing import Literal, Optional

from fastapi import Header, HTTPException, status

Role = Literal["admin", "staff", "customer"]


def _getenv(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def get_role_from_token(token: str) -> Role:
    """
    Token->role mapping via environment variables.

    Expected env vars:
      - ADMIN_TOKEN
      - STAFF_TOKEN
      - CUSTOMER_TOKEN

    If a token doesn't match any role, raise 401.
    """
    admin_token = _getenv("ADMIN_TOKEN")
    staff_token = _getenv("STAFF_TOKEN")
    customer_token = _getenv("CUSTOMER_TOKEN")

    if token and admin_token and token == admin_token:
        return "admin"
    if token and staff_token and token == staff_token:
        return "staff"
    if token and customer_token and token == customer_token:
        return "customer"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing token.",
    )


def parse_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer <token>.",
        )

    return parts[1]


def get_current_role(
    *,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Role:
    token = parse_bearer_token(authorization)
    return get_role_from_token(token)
