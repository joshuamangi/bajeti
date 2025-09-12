from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import datetime
from data.db.db import get_db
from data.db.models.models import Category
from schema.category import CategoryOut, CategoryCreate
from routers.auth import get_current_user
from schema.user import UserOut

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryOut])
async def get_all_categories(
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Return all categories belonging to the current user."""
    return db.query(Category).filter(Category.user_id == current_user.id).all()


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category_by_id(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Return a single category by its ID."""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Create a new category for the current user."""
    new_category = Category(
        name=category.name,
        limit_amount=category.limit_amount,
        user_id=current_user.id
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Update an existing category by ID."""
    existing_category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")

    existing_category.name = category.name
    existing_category.limit_amount = category.limit_amount
    existing_category.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(existing_category)
    return existing_category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Delete a category by ID."""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
