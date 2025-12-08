# app/services/expense_service.py
from app.services.http_client import post, put, delete, get
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def create_expense(token: str, payload: dict):
    resp = await post("/expenses/", json=payload, headers={"Authorization": f"Bearer {token}"})
    return resp


async def update_expense(token: str, expense_id: int, payload: dict):
    resp = await put(f"/expenses/{expense_id}", json=payload, headers={"Authorization": f"Bearer {token}"})
    return resp


async def delete_expense(token: str, expense_id: int):
    resp = await delete(f"/expenses/{expense_id}", headers={"Authorization": f"Bearer {token}"})
    return resp
