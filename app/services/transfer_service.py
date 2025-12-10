# app/services/expense_service.py
from app.services.http_client import post, put, delete, get
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def create_transfer(token: str, payload: dict):
    resp = await post("/transfers/", json=payload, headers={"Authorization": f"Bearer {token}"})
    return resp


async def delete_transfer(token: str, transfer_id: int):
    resp = await delete(f"/transfers/{transfer_id}", headers={"Authorization": f"Bearer {token}"})
    return resp
