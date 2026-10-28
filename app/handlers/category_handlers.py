# app/handlers/category_handlers.py
import logging
from fastapi import Depends, Request, Form, status

from app.utils.tokens import get_current_user
from app.services.category_service import create_category, update_category, delete_category as delete_category_service
from app.utils.redirects import redirect_with_toast

logger = logging.getLogger(__name__)


async def add_category(request: Request,
                       name: str = Form(...),
                       category_type: str = Form(...),
                       budget_id: int = Form(...),
                       allocated_amount: float = Form(...),
                       token: str = Depends(get_current_user)):  # note: Depends not allowed at top-level; we'll use get_current_user inside
    token = get_current_user(request)
    resp = await create_category(token=token, name=name,
                                 category_type=category_type, budget_id=budget_id,
                                 allocated_amount=allocated_amount)

    if resp.status_code == status.HTTP_201_CREATED:
        return redirect_with_toast("/dashboard", f"{name} created successfully!", "success")
    if resp.status_code == status.HTTP_409_CONFLICT:
        return redirect_with_toast("/dashboard", f"{name} already exists!", "error")

    return redirect_with_toast("/dashboard", "Category creation failed", "error")


async def edit_category(request: Request,
                        category_id: int,
                        name: str = Form(...)):
    token = get_current_user(request)
    resp = await update_category(token, category_id, name)
    if resp.status_code == status.HTTP_200_OK:
        return redirect_with_toast("/dashboard", f"{name} updated successfully!", "info")

    return redirect_with_toast("/dashboard", "Category update failed", "error")


async def delete_category(request: Request,
                          category_id: int):
    token = get_current_user(request)
    resp = await delete_category_service(token, category_id)
    if resp.status_code == status.HTTP_204_NO_CONTENT:
        return redirect_with_toast("/dashboard", "Category Deleted successfully!", "warning")

    return redirect_with_toast("/dashboard", "Category deletion failed", "error")
