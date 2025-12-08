# app/services/auth_service.py
from app.services.http_client import post, get
from typing import Optional
from fastapi import status
import logging

logger = logging.getLogger(__name__)


async def login(username: str, password: str):
    # posts to /auth/token as original
    resp = await post("/auth/token", data={"username": username, "password": password})
    return resp


async def register(first_name: str, last_name: str, email: str, password: str, security_answer: str):
    resp = await post("/auth/", json={
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password,
        "security_answer": security_answer
    })
    return resp


async def get_current_user(token: str):
    resp = await get("/auth/users/me", headers={"Authorization": f"Bearer {token}"})
    return resp
