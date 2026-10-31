# app/services/admin_service.py
from app.services.http_client import get, post
import logging

logger = logging.getLogger(__name__)


async def fetch_members(token: str):
    return await get("/admin/users", headers={"Authorization": f"Bearer {token}"})


async def reset_access(token: str, user_id: int):
    return await post(f"/admin/users/{user_id}/reset-access",
                      headers={"Authorization": f"Bearer {token}"})
