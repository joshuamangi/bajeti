from app.services.http_client import delete, get, post, put


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def fetch_recurring(token: str, budget_id: int):
    return await get(path=f"/recurring/?budget_id={budget_id}", headers=_auth(token))


async def fetch_due(token: str, budget_id: int):
    return await get(path=f"/recurring/due?budget_id={budget_id}", headers=_auth(token))


async def create_recurring(token: str, payload: dict):
    return await post(path="/recurring/", json=payload, headers=_auth(token))


async def update_recurring(token: str, recurring_id: int, payload: dict):
    return await put(path=f"/recurring/{recurring_id}", json=payload, headers=_auth(token))


async def delete_recurring(token: str, recurring_id: int):
    return await delete(path=f"/recurring/{recurring_id}", headers=_auth(token))


async def action(token: str, recurring_id: int, name: str, due_date: str = None):
    """pause, resume, approve, skip or approve-all."""
    body = {"due_date": due_date} if due_date else None
    return await post(path=f"/recurring/{recurring_id}/{name}", json=body, headers=_auth(token))


async def undo_run(token: str, recurring_id: int, due_date: str):
    return await delete(path=f"/recurring/{recurring_id}/runs/{due_date}", headers=_auth(token))
