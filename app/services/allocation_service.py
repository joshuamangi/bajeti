from app.services.http_client import delete, get, post, put


async def fetch_budget_overview(token: str, budget_id: int):
    resp = await get(path=f"/budgets/{budget_id}/allocations/overview", headers={
        "Authorization": f"Bearer {token}"
    })
    return resp


async def create_allocation(token: str,
                            budget_id: int,
                            category_id: int,
                            allocated_amount: float):
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


async def update_allocation(token: str,
                            budget_id: int,
                            category_id: int,
                            allocated_amount: float):
    resp = await put(
        f"/budgets/{budget_id}/allocations/",
        json={
            "category_id": category_id,
            "allocated_amount": allocated_amount
        },
        headers={
            "Authorization": f"Bearer {token}",
        })
    return resp


async def remove_allocation(token: str,
                            budget_id: int,
                            allocation_id: int):
    resp = await delete(
        path=f"/budgets/{budget_id}/allocations/{allocation_id}",
        headers={"Authorization": f"Bearer {token}"})

    return resp
