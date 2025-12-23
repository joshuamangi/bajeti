from app.services.http_client import get, post


async def fetch_budget_overview(token: str, budget_id: int):
    resp = await get(path=f"/budgets/{budget_id}/allocations/overview", headers={
        "Authorization": f"Bearer {token}"
    })
    return resp


async def create_allocation(token: str,
                            budget_id: int,
                            category_id: int,
                            allocated_amount: float):
    print(
        f"BudgetId: {budget_id}, Category_Id {category_id}, Allocated {allocated_amount}")
    resp = await post(
        path=f"/budgets/{budget_id}/allocations/",
        json={
            "category_id": category_id,
            "allocated_amount": allocated_amount
        },
        headers={
            "Authorization": f"Bearer {token}"
        })
    return resp
