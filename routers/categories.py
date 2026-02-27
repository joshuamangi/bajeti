from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from core.security import get_current_user
from data.db.db import get_db
from schema.category import CategoryAllocationCreate, CategoryBase, CategoryOut, CategoryStats
from schema.user import UserOut

from services.category_service import CategoryService

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryOut])
async def get_all_categories(
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    return CategoryService.get_all_categories(db, current_user.id)


@router.get("/with-stats/{budget_id}", response_model=list[CategoryStats], status_code=status.HTTP_200_OK)
async def get_categories_with_stats(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    return CategoryService.get_categories_with_stats(db=db, user_id=current_user.id, budget_id=budget_id)


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category_by_id(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    category = CategoryService.get_category_by_id(
        db, current_user.id, category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    return category


@router.get("/category_type/{category_type}", response_model=list[CategoryOut], status_code=status.HTTP_200_OK)
async def fetch_categories_by_type(
    category_type: str,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    budget_categories = CategoryService.get_categories_by_type(
        db=db, user_id=current_user.id, category_type=category_type)
    if not budget_categories:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categories not found")
    return budget_categories


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryBase,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    existing = CategoryService.get_existing_category(
        db, current_user.id, category)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists"
        )

    new_category = CategoryService.save_new_category(
        db, current_user.id, category)

    return new_category


@router.post("/category_allocation", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category_and_allocation(
    category: CategoryAllocationCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    existing = CategoryService.get_existing_category(
        db, current_user.id, category)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists"
        )

    new_category = CategoryService.save_new_category_with_allocation(
        db, current_user.id, category)

    return new_category


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    category: CategoryBase,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    existing_category = CategoryService.get_category_by_id(
        db, current_user.id, category_id)

    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    updated = CategoryService.update_category(db, existing_category, category)
    return updated


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    category = CategoryService.get_category_by_id(
        db, current_user.id, category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    CategoryService.delete_category(db, category)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
