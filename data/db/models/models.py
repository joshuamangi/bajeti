"""Model for handling data"""

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship
from data.db.db import Base


class User(Base):
    """Defines the structure for saving User data"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    security_answer = Column(String(255), nullable=True)

    categories = relationship("Category", back_populates="owner")
    expenses = relationship("Expense", back_populates="owner")


class Category(Base):
    """Defines the structure for Categories"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    limit_amount = Column(Numeric, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="categories")
    expenses = relationship("Expense", back_populates="category")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_category_name"),
    )


class Expense(Base):
    """Defines the structure of Expense"""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Numeric, nullable=False)
    description = Column(String, nullable=True)
    month = Column(String, index=True)  # "YYYY-MM"
    category_id = Column(Integer, ForeignKey("categories.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")
