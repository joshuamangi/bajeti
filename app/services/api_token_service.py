from app.services.http_client import delete, get, post


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def fetch_tokens(token: str):
    return await get(path="/tokens/", headers=_auth(token))


async def create_token(token: str, name: str):
    return await post(path="/tokens/", json={"name": name}, headers=_auth(token))


async def revoke_token(token: str, token_id: int):
    return await delete(path=f"/tokens/{token_id}", headers=_auth(token))
