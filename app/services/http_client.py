# app/services/http_client.py
import httpx
from typing import Optional
from fastapi import status
from app.config import settings
import logging

logger = logging.getLogger(__name__)
API_BASE_URL = settings.API_BASE_URL


async def post(path: str, json=None, data=None, headers: Optional[dict] = None, timeout: float = 10.0):
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=json, data=data, headers=headers)
            return resp
        except httpx.RequestError as e:
            logger.error("HTTP POST request failed: %s %s", url, str(e))
            raise


async def get(path: str, headers: Optional[dict] = None, timeout: float = 10.0):
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(url, headers=headers)
            return resp
        except httpx.RequestError as e:
            logger.error("HTTP GET request failed: %s %s", url, str(e))
            raise


async def put(path: str, json=None, headers: Optional[dict] = None, timeout: float = 10.0):
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.put(url, json=json, headers=headers)
            return resp
        except httpx.RequestError as e:
            logger.error("HTTP PUT request failed: %s %s", url, str(e))
            raise


async def delete(path: str, headers: Optional[dict] = None, timeout: float = 10.0):
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.delete(url, headers=headers)
            return resp
        except httpx.RequestError as e:
            logger.error("HTTP DELETE request failed: %s %s", url, str(e))
            raise
