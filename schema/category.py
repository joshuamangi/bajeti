# Schema for representing Category

from datetime import datetime

from pydantic import BaseModel


class CategoryBase(BaseModel):
    """defines the structure of Category Base"""
    name: str
    limit_amount: float


class CategoryCreate(CategoryBase):
    """defines the structure of the creation of a catrgory"""
    user_id: int


class CategoryOut(CategoryBase):
    """defines the structure for return a category"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """defines a class that allows creation of SQL Alchemy objects"""
        orm_mode = True
