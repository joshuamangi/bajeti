# routers/categories.py

from typing import Any
from fastapi import APIRouter

router = APIRouter(prefix="/api/categories")

categories_mock_data: list[dict[str, Any]] = [
    {
        "id": 1,
        "amount": 15400,
        "month": "2025-02",
        "description": "Rent payment for 2025-02",
        "category_id": 1,
        "user_id": 1,
        "created_at": "2025-07-31T21:14:03.581Z"
    },
    {
        "id": 2,
        "amount": 15400,
        "month": "2025-03",
        "description": "Rent payment for 2025-03",
        "category_id": 1,
        "user_id": 1,
        "created_at": "2025-07-31T21:14:03.581Z"
    }
]


@router.get("/")
async def read_all_categories() -> list[dict[str, Any]]:
    """Return mock categories data"""
    return categories_mock_data

# @router.post("")
# async def create_categories()
