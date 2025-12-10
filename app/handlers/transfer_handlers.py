# app/requests_transfers.py (or append to your requests handlers group)
from datetime import datetime
import logging
from fastapi import APIRouter, Request, Form, Depends, status
import httpx
from urllib.parse import urlencode
from app.config import settings
from app.utils.redirects import redirect_with_toast
from app.utils.templates import render_with_user
from app.utils.tokens import get_current_user
from app.services.transfer_service import create_transfer, delete_transfer

API_BASE_URL = settings.API_BASE_URL
logger = logging.getLogger("app.requests.transfers")
router = APIRouter()


@router.post("/dashboard/transfers")
async def add_transfer(request: Request,
                       from_category_id: int = Form(...),
                       to_category_id: int = Form(...),
                       amount: float = Form(...),
                       description: str = Form(""),
                       month: str = Form(...),
                       token: str = Depends(get_current_user)):
    token = get_current_user(request)
    payload = {
        "from_category_id": from_category_id,
        "to_category_id": to_category_id,
        "amount": amount,
        "description": description,
        "month": month
    }
    response = await create_transfer(token, payload=payload)

    if response.status_code == status.HTTP_201_CREATED:
        return redirect_with_toast("/dashboard", "Transfer completed successfully!", "success")

    # fallback: render dashboard with error
    try:
        err = response.json().get("detail", "Transfer failed")
    except Exception:
        err = "Transfer failed"
    return await render_with_user("dashboard.html", request, {
        "error": err,
        "token": token,
        "categories_with_stats": [],
        "now": month,
    })


async def undo_transfer(request: Request,
                        transfer_id: int):
    token = get_current_user(request)
    resp = await delete_transfer(token, transfer_id)
    if resp.status_code == 204:
        return redirect_with_toast("/dashboard", "transfer deleted successfully!", "warning")

    return await render_with_user("dashboard.html", request, {
        "error": "transfer deletion failed",
        "token": token,
        "categories_with_stats": [],
        "now": datetime.now().strftime("%Y-%m"),
    })
