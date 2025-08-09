# routers/categories.py

from typing import Any
from fastapi import APIRouter, HTTPException, status, Response
from schema.category import CategoryBase, CategoryOut, CategoryCreate
from datetime import datetime

router = APIRouter(prefix="/api/categories")

categories_mock_data: list[CategoryOut] = [
    {
        "id": 1,
        "name": "Rent",
        "limit_amount": 15400,
        "user_id": 1,
        "created_at": "2025-07-31T21:14:03.581Z"
    },
    {
        "id": 2,
        "name": "DSTV",
        "limit_amount": 11000,
        "user_id": 1,
        "created_at": "2025-07-31T21:14:03.581Z"
    }
]


@router.get("/")
async def get_all_categories() -> list[CategoryOut]:
    """Return mock categories data"""
    return categories_mock_data


@router.get("/{category_id}")
async def get_category_by_id(category_id: int) -> CategoryOut:
    """Return a single category"""
    for category in categories_mock_data:
        if category["id"] == category_id:
            return category
    raise HTTPException(status_code=404, detail="Cateogry not found")


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(category: CategoryCreate) -> CategoryOut:
    """Create category and add it to mock data"""
    new_id = max([c["id"] for c in categories_mock_data], default=0) + 1
    new_category = CategoryOut(
        id=new_id,
        name=category.name,
        limit_amount=category.limit_amount,
        user_id=category.user_id,
        created_at=datetime.utcnow()
    )
    categories_mock_data.append(new_category.model_dump())
    return new_category


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(category_id: int, category: CategoryCreate) -> CategoryOut:
    """Edits category and returns it"""
    for index, existing_category in enumerate(categories_mock_data):
        if existing_category["id"] == category_id:
            updated_category = CategoryOut(
                id=category_id,
                name=category.name,
                limit_amount=category.limit_amount,
                user_id=category.user_id,
                created_at=datetime.utcnow()
            )
            categories_mock_data[index] = updated_category.model_dump()
            return updated_category
    raise HTTPException(status_code=404, detail="Category not found")


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_category(category_id: int):
    """Delete acategory by id"""
    for index, category in enumerate(categories_mock_data):
        if category["id"] == category_id:
            categories_mock_data.pop(index)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    raise HTTPException(status_code=404, detail="Category not found")
