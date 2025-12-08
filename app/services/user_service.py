# app/services/user_service.py
from app.services.http_client import post, put
from fastapi import status
import logging

logger = logging.getLogger(__name__)


async def reset_password(email: str, security_answer: str, new_password: str):
    resp = await post("/users/password/reset", json={
        "email": email,
        "security_answer": security_answer,
        "new_password": new_password
    })
    return resp


async def update_profile(token: str, payload: dict):
    resp = await put("/users/me", json=payload, headers={"Authorization": f"Bearer {token}"})
    return resp
