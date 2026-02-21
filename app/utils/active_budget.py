from fastapi import Request, Response
from typing import Optional


def resolve_active_budget_id(
    request: Request,
    budget_id: Optional[int]
) -> Optional[int]:
    """
    Resolves active budget ID using:
    1. Explicit query param
    2. Cookie fallback
    """

    # Explicit query param wins
    if budget_id:
        return budget_id

    # Fallback to cookie
    cookie_budget = request.cookies.get("active_budget_id")
    if cookie_budget:
        try:
            return int(cookie_budget)
        except ValueError:
            return None

    return None
