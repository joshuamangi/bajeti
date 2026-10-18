from app.services.http_client import delete, get, post, put


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def fetch_targets(token: str, budget_id: int):
    return await get(path=f"/budgets/{budget_id}/targets/", headers=_auth(token))


async def save_target(token: str, budget_id: int, category_id: int, amounts: dict):
    """Create the target for a category, or update the existing one (API returns 201 or 200)."""
    return await post(
        path=f"/budgets/{budget_id}/targets/",
        json={"category_id": category_id, **amounts},
        headers=_auth(token))


async def update_target(token: str, budget_id: int, target_id: int, amounts: dict):
    return await put(
        f"/budgets/{budget_id}/targets/{target_id}",
        json=amounts,
        headers=_auth(token))


async def remove_target(token: str, budget_id: int, target_id: int):
    return await delete(
        path=f"/budgets/{budget_id}/targets/{target_id}",
        headers=_auth(token))
