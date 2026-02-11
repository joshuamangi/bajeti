from app.services.http_client import delete, get, post, put


async def add_budget(token: str,
                     amount: float,
                     budget_name: str,
                     budget_type: str):
    resp = await post(path=f"budgets/",
                      json={
                          "name": budget_name,
                          "amount": amount,
                          "type": budget_type
                      },
                      headers={"Authorization": f"Bearer {token}"})
    return resp


async def get_budget(token: str):
    resp = await get(path=f"/budgets/current", headers={"Authorization": f"Bearer {token}"})
    return resp


async def get_all_budgets(token: str):
    resp = await get(path=f"/budgets/", headers={"Authorization": f"Bearer {token}"})
    return resp


async def edit_budget(token: str,
                      budget_id: int,
                      amount: float,
                      budget_name: str,
                      budget_type: str):
    resp = await put(path=f"/budgets/{budget_id}", json={
        "name": budget_name,
        "amount": amount,
        "type": budget_type
    }, headers={"Authorization": f"Bearer {token}"})
    return resp


async def delete_budget(token: str,
                        budget_id: int):
    # call delete api endpoint
    resp = await delete(path=f"/budgets/{budget_id}",
                        headers={"Authorization": f"Bearer {token}"})
    return resp
