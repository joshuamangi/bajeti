# routers/categories.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from schema.category import CategoryOut, CategoryCreate
from routers.auth import get_current_user
from schema.user import UserOut

router = APIRouter(prefix="/api/categories", tags=["categories"])

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


@router.get("/", response_model=list[CategoryOut])
async def get_all_categories(current_user: UserOut = Depends(get_current_user)):
    """Return mock categories data"""
    return [c for c in categories_mock_data if c["user_id"] == current_user.id]


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category_by_id(
        category_id: int,
        current_user: UserOut = Depends(get_current_user)):
    """Return a single category"""
    for category in categories_mock_data:
        if category["id"] == category_id and category["user_id"] == current_user.id:
            return category
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail="Cateogry not found")


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    current_user: UserOut = Depends(get_current_user)
):
    """Create category and add it to mock data"""
    new_id = max([c["id"] for c in categories_mock_data], default=0) + 1
    new_category = CategoryOut(
        id=new_id,
        name=category.name,
        limit_amount=category.limit_amount,
        user_id=current_user.id,
        created_at=datetime.utcnow()
    )
    categories_mock_data.append(new_category.model_dump())
    return new_category


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    category: CategoryCreate,
    current_user: UserOut = Depends(get_current_user)
):
    """Edits category and returns it"""
    for index, existing_category in enumerate(categories_mock_data):
        if existing_category["id"] == category_id and existing_category["user_id"] == current_user.id:
            updated_category = CategoryOut(
                id=category_id,
                name=category.name,
                limit_amount=category.limit_amount,
                user_id=current_user.id,
                created_at=datetime.utcnow()
            )
            categories_mock_data[index] = updated_category.model_dump()
            return updated_category
    raise HTTPException(status_code=404, detail="Category not found")


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_category(
        category_id: int,
        current_user: UserOut = Depends(get_current_user)):
    """Delete acategory by id"""
    for index, category in enumerate(categories_mock_data):
        if category["id"] == category_id and category["user_id"] == current_user.id:
            categories_mock_data.pop(index)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    raise HTTPException(status_code=204, detail="No COntent")
