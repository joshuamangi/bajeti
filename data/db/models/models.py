from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from data.db.db import Base


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
    security_answer = Column(String(255), nullable=True)  # bcrypt hash, never plain text

    # Raised to invalidate every token issued earlier (password reset, log out everywhere).
    token_version = Column(Integer, nullable=False, default=0, server_default="0")

    @property
    def has_security_answer(self) -> bool:
        return bool(self.security_answer)

    categories = relationship("Category", back_populates="owner")
    expenses = relationship("Expense", back_populates="owner")
    transfers = relationship("Transfer", back_populates="owner")
    budgets = relationship("Budget", back_populates="owner")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)

    type = Column(String(20), nullable=False,
                  default="expense", server_default="expense")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="budgets")
    allocations = relationship("Allocation", back_populates="budget",
                               cascade="all, delete-orphan")
    targets = relationship("Target", back_populates="budget",
                           cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_budget_name"),
        CheckConstraint("type IN ('expense', 'savings')",
                        name="ck_budgets_type")
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String(20), nullable=False,
                  default="expense", server_default="expense")
    limit_amount = Column(Numeric, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="categories")
    expenses = relationship("Expense", back_populates="category")

    outgoing_transfers = relationship("Transfer", foreign_keys="Transfer.from_category_id",
                                      back_populates="from_category")
    incoming_transfers = relationship("Transfer", foreign_keys="Transfer.to_category_id",
                                      back_populates="to_category")
    allocations = relationship(
        "Allocation", back_populates="category", cascade="all, delete-orphan")

    targets = relationship(
        "Target", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "name", "type",
                         name="uq_user_category_name"),
        CheckConstraint("type IN ('expense','savings')",
                        name="ck_categories_type"),
    )


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Numeric, nullable=False)
    description = Column(String, nullable=True)
    type = Column(String(20), nullable=False,
                  default="spend", server_default="spend")
    month = Column(String, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")
    __table_args__ = (
        CheckConstraint("type IN ('spend','withdrawal')",
                        name="ck_expenses_type"),
        # Analytics groups spending by user, month and category.
        Index("ix_expenses_user_month_category", "user_id", "month", "category_id"),
    )


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

    __table_args__ = (
        Index("ix_transfers_user_month", "user_id", "month"),
    )


class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(Integer, primary_key=True)

    budget_id = Column(Integer, ForeignKey(
        "budgets.id", ondelete="CASCADE"), nullable=False)

    category_id = Column(Integer, ForeignKey(
        "categories.id", ondelete="CASCADE"), nullable=False)

    allocated_amount = Column(Numeric, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    budget = relationship("Budget", back_populates="allocations")
    category = relationship("Category", back_populates="allocations")

    __table_args__ = (
        UniqueConstraint("budget_id", "category_id",
                         name="uq_budget_category_allocation"),
    )


class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True)

    budget_id = Column(Integer, ForeignKey(
        "budgets.id", ondelete="CASCADE"), nullable=False)

    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"),
                         nullable=False)

    short_term_amount = Column(Numeric, nullable=True)
    mid_term_amount = Column(Numeric, nullable=True)
    long_term_amount = Column(Numeric, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    budget = relationship("Budget", back_populates="targets")
    category = relationship("Category", back_populates="targets")

    __table_args__ = (
        UniqueConstraint("budget_id", "category_id",
                         name="uq_budget_category_target"),
    )


class AllocationSnapshot(Base):
    """A category's allocation in one month, so analytics compares each month with what was
    allocated then. Recorded from the live allocations while the month is current."""
    __tablename__ = "allocation_snapshots"

    id = Column(Integer, primary_key=True)
    budget_id = Column(Integer, ForeignKey(
        "budgets.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey(
        "categories.id", ondelete="CASCADE"), nullable=False)
    month = Column(String(7), nullable=False)
    amount = Column(Numeric, nullable=False)

    __table_args__ = (
        UniqueConstraint("budget_id", "category_id", "month",
                         name="uq_allocation_snapshot_month"),
    )


class RecurringExpense(Base):
    """A bill that repeats monthly. Due items are worked out when a page loads."""
    __tablename__ = "recurring_expenses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # No cascade: deleting a category that still has recurring items is refused.
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String(60), nullable=False)
    amount = Column(Numeric, nullable=False)
    anchor_day = Column(Integer, nullable=False)
    next_due = Column(Date, nullable=False)
    mode = Column(String(10), nullable=False, default="ask_first", server_default="ask_first")
    paused = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("mode IN ('ask_first', 'auto')", name="ck_recurring_mode"),
        CheckConstraint("anchor_day BETWEEN 1 AND 31", name="ck_recurring_anchor_day"),
    )


class RecurringRun(Base):
    """One due date of a recurring item that was approved, skipped or added automatically."""
    __tablename__ = "recurring_runs"

    id = Column(Integer, primary_key=True)
    recurring_id = Column(Integer, ForeignKey("recurring_expenses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    due_date = Column(Date, nullable=False)
    action = Column(String(10), nullable=False)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # One run per due date: approving twice (or from two tabs) cannot record two expenses.
        UniqueConstraint("recurring_id", "due_date", name="uq_recurring_run_due_date"),
        CheckConstraint("action IN ('approved', 'skipped', 'auto')", name="ck_recurring_run_action"),
    )


class PendingPayment(Base):
    """A captured M-Pesa SMS or payment email waiting for a category (docs/design/payments.md)."""
    __tablename__ = "pending_payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source = Column(String(10), nullable=False, default="paste")
    kind = Column(String(10), nullable=False)
    # Sensitive: cleared on approve or dismiss unless KEEP_RAW_MESSAGES; never logged.
    raw_text = Column(Text, nullable=True)
    amount = Column(Numeric, nullable=True)
    fee = Column(Numeric, nullable=True)
    payee = Column(String(80), nullable=True)
    reference = Column(String(20), nullable=True)
    paid_on = Column(Date, nullable=True)
    status = Column(String(10), nullable=False, default="pending")
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Dedupe: the same transaction code cannot be captured twice by one user.
        UniqueConstraint("user_id", "reference", name="uq_pending_payment_reference"),
        CheckConstraint("status IN ('pending', 'approved', 'dismissed')", name="ck_pending_payment_status"),
        CheckConstraint("source IN ('paste', 'sms', 'email')", name="ck_pending_payment_source"),
    )


class PayeeRule(Base):
    """'Remember Demo Grocer for next time': a payee's usual category."""
    __tablename__ = "payee_rules"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payee = Column(String(80), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "payee", name="uq_payee_rule"),
    )
