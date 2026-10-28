from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from data.db.models.models import Allocation, AllocationSnapshot


class SnapshotService:

    @staticmethod
    def current_month() -> str:
        return datetime.utcnow().strftime("%Y-%m")

    @staticmethod
    def record_current_month(db: Session, budget_id: int):
        """Make this month's snapshot of the budget match its live allocations.

        Called whenever a budget's month is read (Home stats, Analytics). Past months are
        never changed, so each keeps the allocations last seen while it was current.
        Writes only when something changed. The caller has checked the budget's owner."""
        month = SnapshotService.current_month()
        live = {a.category_id: Decimal(str(a.allocated_amount))
                for a in db.query(Allocation).filter(Allocation.budget_id == budget_id).all()}
        saved = {s.category_id: s for s in db.query(AllocationSnapshot).filter(
            AllocationSnapshot.budget_id == budget_id,
            AllocationSnapshot.month == month).all()}
        changed = False
        for category_id, amount in live.items():
            row = saved.get(category_id)
            if row is None:
                db.add(AllocationSnapshot(budget_id=budget_id, category_id=category_id,
                                          month=month, amount=amount))
                changed = True
            elif Decimal(str(row.amount)) != amount:
                row.amount = amount
                changed = True
        for category_id, row in saved.items():
            if category_id not in live:
                db.delete(row)
                changed = True
        if changed:
            db.commit()
