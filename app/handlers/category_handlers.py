# app/handlers/category_handlers.py
import logging
from fastapi import Depends, Request, Form
from datetime import datetime
from app.utils.tokens import get_current_user
from app.utils.templates import render_with_user
from app.services.category_service import create_category, update_category, delete_category as delete_category_service
from app.utils.redirects import redirect_with_toast

logger = logging.getLogger(__name__)


async def add_category(request: Request,
                       name: str = Form(...),
                       limit_amount: float = Form(...),
                       token: str = Depends(get_current_user)):  # note: Depends not allowed at top-level; we'll use get_current_user inside
    token = get_current_user(request)
    resp = await create_category(token, name, limit_amount)

    if resp.status_code == 201:
        return redirect_with_toast("/dashboard", f"{name} created successfully!", "success")
    if resp.status_code == 409:
        return redirect_with_toast("/dashboard", f"{name} already exists!", "error")

    return await render_with_user("dashboard.html", request, {
        "error": "Category creation failed",
        "token": token,
        "categories_with_stats": [],
        "now": datetime.now().strftime("%Y-%m"),
    })


async def edit_category(request: Request,
                        category_id: int,
                        name: str = Form(...),
                        limit_amount: float = Form(...)):
    token = get_current_user(request)
    resp = await update_category(token, category_id, name, limit_amount)
    if resp.status_code == 200:
        return redirect_with_toast("/dashboard", f"{name} updated successfully!", "info")

    return await render_with_user("dashboard.html", request, {
        "error": "Category update failed",
        "token": token,
        "categories_with_stats": [],
        "now": datetime.now().strftime("%Y-%m"),
    })


async def delete_category(request: Request,
                          category_id: int):
    token = get_current_user(request)
    resp = await delete_category_service(token, category_id)
    if resp.status_code == 204:
        return redirect_with_toast("/dashboard", "Category Deleted successfully!", "warning")

    return await render_with_user("dashboard.html", request, {
        "error": "Category deletion failed",
        "token": token,
        "categories_with_stats": [],
        "now": datetime.now().strftime("%Y-%m"),
    })
