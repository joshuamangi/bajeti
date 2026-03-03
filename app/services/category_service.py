# app/services/category_service.py
from app.services.http_client import post, put, delete, get
import logging

logger = logging.getLogger(__name__)


async def create_category(token: str, name: str, category_type: str,
                          budget_id: int, allocated_amount: float):
    resp = await post("/categories/category_allocation", json={
        "name": name,
        "type": category_type,
        "budget_id": budget_id,
        "amount": allocated_amount
    }, headers={"Authorization": f"Bearer {token}"})
    return resp


async def update_category(token: str, category_id: int, name: str):
    resp = await put(f"/categories/{category_id}", json={
        "name": name
    }, headers={"Authorization": f"Bearer {token}"})
    return resp


async def delete_category(token: str, category_id: int):
    resp = await delete(f"/categories/{category_id}", headers={"Authorization": f"Bearer {token}"})
    return resp


async def get_categories_with_stats(token: str, budget_id: int):
    resp = await get(f"/categories/with-stats/{budget_id}",
                     headers={"Authorization": f"Bearer {token}"})
    return resp


async def get_categories_by_type(token: str, category_type: str):
    resp = await get(f"/categories/category_type/{category_type}",
                     headers={"Authorization": f"Bearer {token}"})
    return resp
