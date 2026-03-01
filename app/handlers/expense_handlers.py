# app/handlers/expense_handlers.py
import logging
from fastapi import Request, Form
from typing import Optional
from app.utils.tokens import get_current_user
from app.utils.templates import render_with_user
from app.services.expense_service import create_expense, create_withdrawal, delete_withdrawal, update_expense, delete_expense as delete_expense_service, update_withdrawal
from app.utils.redirects import redirect_with_toast
from datetime import datetime

logger = logging.getLogger(__name__)


async def add_expense(request: Request,
                      category_id: int = Form(...),
                      amount: float = Form(...),
                      description: str = Form(""),
                      expense_type: str = Form(...),
                      month: Optional[str] = Form(None)):
    token = get_current_user(request)
    payload = {"category_id": category_id,
               "amount": amount, "description": description, "type": expense_type}
    if month:
        payload["month"] = month

    if expense_type == "spend":
        resp = await create_expense(token, payload)
    else:
        resp = await create_withdrawal(token=token, payload=payload)

    if resp.status_code == 201:
        return redirect_with_toast("/dashboard", "Expense created successfully!", "success")

    return await render_with_user("dashboard.html", request, {
        "error": "Expense creation failed",
        "token": token,
        "categories_with_stats": [],
        "now": datetime.now().strftime("%Y-%m"),
    })


async def edit_expense(request: Request,
                       expense_id: int,
                       category_id: int = Form(...),
                       amount: float = Form(...),
                       description: str = Form(""),
                       expense_type: str = Form(...),
                       month: Optional[str] = Form(None)):
    token = get_current_user(request)
    payload = {"category_id": category_id,
               "amount": amount, "description": description}
    if month:
        payload["month"] = month

    if expense_type == "spend":
        resp = await update_expense(token, expense_id, payload)
    else:
        resp = await update_withdrawal(token=token, expense_id=expense_id, payload=payload)

    if resp.status_code == 200:
        return redirect_with_toast("/dashboard", "Expense updated successfully!", "info")

    return await render_with_user("dashboard.html", request, {
        "error": "Expense update failed",
        "token": token,
        "categories_with_stats": [],
        "now": datetime.now().strftime("%Y-%m"),
    })


async def delete_expense(request: Request,
                         expense_id: int,
                         expense_type: str = Form(...),):
    token = get_current_user(request)

    if expense_type == "spend":
        resp = await delete_expense_service(token, expense_id)
    else:
        resp = await delete_withdrawal(token=token, expense_id=expense_id)
    if resp.status_code == 204:
        return redirect_with_toast("/dashboard", "Expense deleted successfully!", "warning")

    return await render_with_user("dashboard.html", request, {
        "error": "Expense deletion failed",
        "token": token,
        "categories_with_stats": [],
        "now": datetime.now().strftime("%Y-%m"),
    })
