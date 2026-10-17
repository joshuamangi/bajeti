import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from data.db.models.models import Category, Target
from schema.target import TargetCreate, TargetOut, TargetUpdate
from services.budget_service import BudgetService
from services.category_service import CategoryService

logger = logging.getLogger(__name__)


class TargetService:
    @staticmethod
    def _get_owned_budget(db: Session, user_id: int, budget_id: int):
        """Every operation starts here, so no target is reachable through a budget the user does not own."""
        budget = BudgetService.get_budget_by_id(
            db=db, user_id=user_id, budget_id=budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Budget not Found")
        return budget

    @staticmethod
    def _get_target(db: Session, budget_id: int, target_id: int) -> Target:
        target = db.query(Target).filter(
            Target.id == target_id,
            Target.budget_id == budget_id,
        ).first()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Target not Found")
        return target

    @staticmethod
    def to_out(target: Target) -> TargetOut:
        return TargetOut(
            id=target.id,
            budget_id=target.budget_id,
            category_id=target.category_id,
            category_name=target.category.name,
            short_term_amount=target.short_term_amount,
            mid_term_amount=target.mid_term_amount,
            long_term_amount=target.long_term_amount,
            created_at=target.created_at,
            updated_at=target.updated_at,
        )

    @staticmethod
    def get_targets_by_budget(db: Session, user_id: int, budget_id: int):
        TargetService._get_owned_budget(db, user_id, budget_id)
        targets = (
            db.query(Target)
            .join(Category, Category.id == Target.category_id)
            .filter(Target.budget_id == budget_id, Category.user_id == user_id)
            .order_by(Category.name)
            .all()
        )
        return [TargetService.to_out(t) for t in targets]

    @staticmethod
    def create_target(db: Session, user_id: int, budget_id: int, data: TargetCreate):
        """Create the target for a category, or update it when one already exists
        (the backfill migration creates empty rows for existing categories).
        Returns (target, created)."""
        budget = TargetService._get_owned_budget(db, user_id, budget_id)

        category = CategoryService.get_category_by_id(
            db=db, user_id=user_id, category_id=data.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not Found")
        if category.type != budget.type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category type does not match budget type")

        amounts = data.model_dump(exclude={"category_id"})
        now = datetime.utcnow()
        try:
            target = db.query(Target).filter(
                Target.budget_id == budget_id,
                Target.category_id == data.category_id,
            ).first()
            created = target is None
            if created:
                target = Target(budget_id=budget_id,
                                category_id=data.category_id,
                                created_at=now, updated_at=now, **amounts)
                db.add(target)
            else:
                for field, value in amounts.items():
                    setattr(target, field, value)
                target.updated_at = now
            db.commit()
            db.refresh(target)
        except SQLAlchemyError:
            db.rollback()
            logger.exception("create_target failed")
            raise
        return TargetService.to_out(target), created

    @staticmethod
    def update_target(db: Session, user_id: int, budget_id: int, target_id: int, data: TargetUpdate):
        TargetService._get_owned_budget(db, user_id, budget_id)
        target = TargetService._get_target(db, budget_id, target_id)
        try:
            for field, value in data.model_dump().items():
                setattr(target, field, value)
            target.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(target)
        except SQLAlchemyError:
            db.rollback()
            logger.exception("update_target failed")
            raise
        return TargetService.to_out(target)

    @staticmethod
    def delete_target(db: Session, user_id: int, budget_id: int, target_id: int):
        TargetService._get_owned_budget(db, user_id, budget_id)
        target = TargetService._get_target(db, budget_id, target_id)
        try:
            db.delete(target)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception("delete_target failed")
            raise
