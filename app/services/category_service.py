# app/services/category_service.py
from app.services.http_client import post, put, delete, get
import logging

logger = logging.getLogger(__name__)


async def create_category(token: str, name: str, limit_amount: float):
    resp = await post("/categories/", json={
        "name": name,
        "limit_amount": limit_amount
    }, headers={"Authorization": f"Bearer {token}"})
    return resp


async def update_category(token: str, category_id: int, name: str, limit_amount: float):
    resp = await put(f"/categories/{category_id}", json={
        "name": name,
        "limit_amount": limit_amount
    }, headers={"Authorization": f"Bearer {token}"})
    return resp


async def delete_category(token: str, category_id: int):
    resp = await delete(f"/categories/{category_id}", headers={"Authorization": f"Bearer {token}"})
    return resp


async def get_categories_with_stats(token: str):
    resp = await get("/categories/with-stats", headers={"Authorization": f"Bearer {token}"})
    return resp
