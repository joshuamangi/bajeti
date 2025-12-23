from app.services.http_client import get, post, put


async def get_budget(token: str):
    budget_id: int = 1
    resp = await get(path=f"/budgets/{budget_id}", headers={"Authorization": f"Bearer {token}"})
    return resp


async def edit_budget(token: str,
                      budget_id: int,
                      amount: float):
    resp = await put(path=f"/budgets/{budget_id}", json={
        "name": "Monthly",
        "amount": amount,
    }, headers={"Authorization": f"Bearer {token}"})
    return resp
