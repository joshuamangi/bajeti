from app.services.http_client import get, post


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def capture(token: str, raw: str):
    return await post(path="/payments/capture", json={"raw": raw, "source": "paste"}, headers=_auth(token))


async def fetch_pending(token: str, budget_id: int):
    return await get(path=f"/payments/?budget_id={budget_id}", headers=_auth(token))


async def fetch_count(token: str):
    return await get(path="/payments/count", headers=_auth(token))


async def approve(token: str, payment_id: int, payload: dict):
    return await post(path=f"/payments/{payment_id}/approve", json=payload, headers=_auth(token))


async def file_recurring(token: str, payment_id: int, payload: dict):
    return await post(path=f"/payments/{payment_id}/recurring", json=payload, headers=_auth(token))


async def dismiss(token: str, payment_id: int):
    return await post(path=f"/payments/{payment_id}/dismiss", headers=_auth(token))


async def restore(token: str, payment_id: int):
    return await post(path=f"/payments/{payment_id}/restore", headers=_auth(token))
