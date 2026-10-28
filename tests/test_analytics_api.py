from decimal import Decimal

from data.db.models.models import AllocationSnapshot
from services.analytics_service import shift_month
from services.snapshot_service import SnapshotService
from tests.conftest import TestingSessionLocal
from tests.helpers import make_allocation, make_user

NOW = SnapshotService.current_month()
LAST = shift_month(NOW, -1)


def spend(client, headers, category_id, amount, month=NOW, kind="spend"):
    r = client.post("/api/expenses/", json={"category_id": category_id, "amount": amount,
                                            "description": "test", "month": month, "type": kind}, headers=headers)
    assert r.status_code == 201, r.text


def snapshot(budget_id, category_id, month, amount):
    db = TestingSessionLocal()
    db.add(AllocationSnapshot(budget_id=budget_id, category_id=category_id, month=month, amount=Decimal(amount)))
    db.commit()
    db.close()


def setup(client):
    headers, _ = make_user(client)
    budget_id, groceries, _ = make_allocation(client, headers, amount=1000.0)
    _, rent, _ = make_allocation(client, headers, amount=500.0)
    spend(client, headers, groceries, 700)
    spend(client, headers, rent, 500)
    spend(client, headers, groceries, 1200, month=LAST)
    snapshot(budget_id, groceries, LAST, "1000")
    return headers, budget_id, groceries, rent


def test_month_totals_and_breakdown(client):
    headers, budget_id, groceries, rent = setup(client)
    r = client.get(f"/api/analytics/month?budget_id={budget_id}", headers=headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["month"] == NOW
    assert (d["spent"], d["budgeted"]) == ("1200.00", "1500.00")
    assert d["used_percent"] == 80.0
    assert d["previous"] == {"month": LAST, "spent": "1200.00"}
    assert d["has_previous"] is True
    assert [c["id"] for c in d["categories"]] == [groceries, rent]
    assert d["categories"][0]["share_percent"] == 58.3
    assert d["last6"][-2] == {"month": LAST, "spent": "1200.00", "budgeted": "1000.00"}
    assert d["last6"][0]["budgeted"] is None  # before the snapshots: no data


def test_this_month_is_recorded_as_a_snapshot(client):
    headers, budget_id, groceries, _ = setup(client)
    client.get(f"/api/analytics/month?budget_id={budget_id}", headers=headers)
    db = TestingSessionLocal()
    rows = db.query(AllocationSnapshot).filter(AllocationSnapshot.budget_id == budget_id,
                                               AllocationSnapshot.month == NOW).all()
    db.close()
    assert sorted(Decimal(str(r.amount)) for r in rows) == [Decimal("500"), Decimal("1000")]


def test_trends_counts_months_over_only_where_a_snapshot_exists(client):
    headers, budget_id, groceries, _ = setup(client)
    d = client.get(f"/api/analytics/trends?budget_id={budget_id}", headers=headers).json()
    assert d["months"][-1] == NOW and len(d["months"]) == 6
    g = next(c for c in d["categories"] if c["id"] == groceries)
    assert (g["months"], g["over"]) == (2, 1)
    assert d["squeezed"] == []


def test_year(client):
    headers, budget_id, groceries, rent = setup(client)
    d = client.get(f"/api/analytics/year?budget_id={budget_id}", headers=headers).json()
    assert d["year"] == int(NOW[:4])
    if LAST[:4] == NOW[:4]:
        assert d["total"] == "2400.00"
        assert d["categories"][0]["id"] == groceries


def test_category_detail(client):
    headers, budget_id, groceries, _ = setup(client)
    d = client.get(f"/api/analytics/category/{groceries}", headers=headers).json()
    assert (d["spent"], d["previous_spent"]) == ("700.00", "1200.00")
    assert d["last6"]["over"] == 1
    assert len(d["expenses"]) == 1


def test_bad_month_is_rejected(client):
    headers, budget_id, _, _ = setup(client)
    assert client.get(f"/api/analytics/month?budget_id={budget_id}&month=2026-13", headers=headers).status_code == 422


def test_other_user_gets_404_on_every_endpoint(client):
    headers, budget_id, groceries, _ = setup(client)
    other, _ = make_user(client)
    for url in (f"/api/analytics/month?budget_id={budget_id}",
                f"/api/analytics/trends?budget_id={budget_id}",
                f"/api/analytics/year?budget_id={budget_id}",
                f"/api/analytics/category/{groceries}"):
        assert client.get(url, headers=other).status_code == 404, url
    # The owner's data is unchanged.
    d = client.get(f"/api/analytics/month?budget_id={budget_id}", headers=headers).json()
    assert d["spent"] == "1200.00"


def test_requires_login(client):
    assert client.get("/api/analytics/month?budget_id=1").status_code == 401
