from app.services.http_client import get


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def fetch_month(token: str, budget_id: int, month: str):
    return await get(path=f"/analytics/month?budget_id={budget_id}&month={month}", headers=_auth(token))


async def fetch_trends(token: str, budget_id: int, end: str):
    return await get(path=f"/analytics/trends?budget_id={budget_id}&end={end}&months=6", headers=_auth(token))


async def fetch_year(token: str, budget_id: int, year: int):
    return await get(path=f"/analytics/year?budget_id={budget_id}&year={year}", headers=_auth(token))


async def fetch_category(token: str, category_id: int, month: str):
    return await get(path=f"/analytics/category/{category_id}?month={month}", headers=_auth(token))
