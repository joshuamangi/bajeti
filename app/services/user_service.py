# app/services/user_service.py
from typing import Optional

from app.services.http_client import forward_client_ip, post, put
from fastapi import status
import logging

logger = logging.getLogger(__name__)


async def reset_password(email: str, security_answer: str, new_password: str,
                         client_ip: Optional[str] = None):
    resp = await post("/users/password/reset", json={
        "email": email,
        "security_answer": security_answer,
        "new_password": new_password
    }, headers=forward_client_ip(client_ip))
    return resp


async def update_profile(token: str, payload: dict):
    resp = await put("/users/me", json=payload, headers={"Authorization": f"Bearer {token}"})
    return resp


async def change_password(token: str, current_password: str, new_password: str,
                          client_ip: Optional[str] = None):
    headers = {"Authorization": f"Bearer {token}", **(forward_client_ip(client_ip) or {})}
    return await post("/users/me/password", json={
        "current_password": current_password,
        "new_password": new_password
    }, headers=headers)


async def use_reset_link(link_token: str, new_password: str, client_ip: Optional[str] = None):
    return await post("/auth/reset-link", json={"token": link_token, "new_password": new_password},
                      headers=forward_client_ip(client_ip))
