from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship
from data.db.db import Base


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="budgets")
    allocations = relationship(
        "Allocation",
        back_populates="budget",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_budget_name"),
    )


class User(Base):
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
    transfers = relationship("Transfer", back_populates="owner")
    budgets = relationship("Budget", back_populates="owner")


class Category(Base):
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

    outgoing_transfers = relationship(
        "Transfer",
        foreign_keys="Transfer.from_category_id",
        back_populates="from_category"
    )
    incoming_transfers = relationship(
        "Transfer",
        foreign_keys="Transfer.to_category_id",
        back_populates="to_category"
    )
    allocations = relationship("Allocation", back_populates="category")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_category_name"),
    )


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Numeric, nullable=False)
    description = Column(String, nullable=True)
    month = Column(String, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)

    from_category_id = Column(
        Integer, ForeignKey("categories.id"), nullable=True)
    to_category_id = Column(Integer, ForeignKey(
        "categories.id"), nullable=True)

    amount = Column(Numeric, nullable=False)
    description = Column(String, nullable=True)
    month = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="transfers")

    from_category = relationship("Category", foreign_keys=[
                                 from_category_id], back_populates="outgoing_transfers")
    to_category = relationship("Category", foreign_keys=[
                               to_category_id], back_populates="incoming_transfers")


class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(Integer, primary_key=True)

    budget_id = Column(Integer, ForeignKey(
        "budgets.id", ondelete="CASCADE"), nullable=False)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    allocated_amount = Column(Numeric, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    budget = relationship("Budget", back_populates="allocations")
    category = relationship("Category", back_populates="allocations")
