import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from data.db.db import get_db
from data.db.models.models import Category
from routers.auth import get_current_user
from schema.category import CategoryBase, CategoryOut
from schema.user import UserOut

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryOut])
async def get_all_categories(
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Return all categories belonging to the current user."""
    categories = db.query(Category).filter(
        Category.user_id == current_user.id).all()
    logger.info(
        "Fetched %d categories for user %d", len(categories), current_user.id)
    return categories


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
        logger.warning(
            "Category %d not found for user %d", category_id, current_user.id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryBase,
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
    logger.info(
        "Created category '%s' for user %d", new_category.name, current_user.id)
    return new_category


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    category: CategoryBase,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Update an existing category by ID."""
    existing_category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not existing_category:
        logger.warning(
            "Update failed - category %d not found for user %d", category_id, current_user.id)
        raise HTTPException(status_code=404, detail="Category not found")

    existing_category.name = category.name
    existing_category.limit_amount = category.limit_amount
    existing_category.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(existing_category)
    logger.info("Updated category %d for user %d",
                category_id, current_user.id)
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
        logger.warning(
            "Delete failed - category %d not found for user %d", category_id, current_user.id)
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()
    logger.info("Deleted category %d for user %d",
                category_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
