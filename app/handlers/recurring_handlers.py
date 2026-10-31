# app/handlers/recurring_handlers.py
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import Depends, Form, Request, status
from fastapi.responses import HTMLResponse

from app.handlers.dashboard_handlers import render_app_page
from app.services import recurring_service
from app.utils.redirects import redirect_with_toast
from app.utils.tokens import get_current_user

HTMLResponse = HTMLResponse  # expose to router
PAGE = "/recurring"


def _detail(resp, fallback: str) -> str:
    try:
        return str(resp.json().get("detail", fallback))
    except ValueError:
        return fallback


def _amount(value: str) -> Optional[str]:
    try:
        amount = Decimal(value.replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return None
    return format(amount.quantize(Decimal("0.01")), "f") if amount > 0 else None


async def recurring_page(request: Request, token: str = Depends(get_current_user), budget_id: Optional[int] = None):
    async def extra(context, active_id):
        if not active_id:
            return {"recurring": None}
        response = await recurring_service.fetch_recurring(token, active_id)
        return {"recurring": response.json() if response.status_code == status.HTTP_200_OK else None}
    return await render_app_page("recurring.html", "more", request, token, budget_id, extra_async=extra)


async def _save(request: Request, recurring_id: Optional[int], name: str, amount: str, category_id: int,
                next_due: str, mode: str, usual_fee: str = ""):
    token = get_current_user(request)
    value = _amount(amount)
    if not value:
        return redirect_with_toast(PAGE, "Enter an amount greater than 0.", "error")
    payload = {"name": name, "amount": value, "category_id": category_id, "next_due": next_due, "mode": mode,
               "usual_fee": None}
    if usual_fee.strip():
        try:
            fee = Decimal(usual_fee.replace(",", "").strip())
        except InvalidOperation:
            return redirect_with_toast(PAGE, "Enter the usual fee as a number, or leave it blank.", "error")
        # 0 means no usual fee.
        payload["usual_fee"] = format(fee.quantize(Decimal("0.01")), "f") if fee > 0 else None
    if recurring_id:
        resp = await recurring_service.update_recurring(token, recurring_id, payload)
        ok = resp.status_code == status.HTTP_200_OK
    else:
        resp = await recurring_service.create_recurring(token, payload)
        ok = resp.status_code == status.HTTP_201_CREATED
    if ok:
        return redirect_with_toast(PAGE, f"Saved {name}", "success")
    return redirect_with_toast(PAGE, _detail(resp, "Could not save the recurring expense."), "error")


async def add_recurring(request: Request, name: str = Form(...), amount: str = Form(...),
                        category_id: int = Form(...), next_due: str = Form(...), mode: str = Form("ask_first"),
                        usual_fee: str = Form("")):
    return await _save(request, None, name, amount, category_id, next_due, mode, usual_fee)


async def edit_recurring(request: Request, recurring_id: int, name: str = Form(...), amount: str = Form(...),
                         category_id: int = Form(...), next_due: str = Form(...), mode: str = Form("ask_first"),
                         usual_fee: str = Form("")):
    return await _save(request, recurring_id, name, amount, category_id, next_due, mode, usual_fee)


async def delete_recurring(request: Request, recurring_id: int):
    token = get_current_user(request)
    resp = await recurring_service.delete_recurring(token, recurring_id)
    if resp.status_code == status.HTTP_204_NO_CONTENT:
        return redirect_with_toast(PAGE, "Recurring expense deleted", "warning")
    return redirect_with_toast(PAGE, _detail(resp, "Could not delete it."), "error")


MESSAGES = {"pause": "Paused", "resume": "Resumed", "approve": "Recorded", "skip": "Skipped this time",
            "approve-all": "Recorded all overdue payments"}


async def recurring_action(request: Request, recurring_id: int, name: str, due_date: str = Form("")):
    token = get_current_user(request)
    if name not in MESSAGES:
        return redirect_with_toast(PAGE, "Unknown action.", "error")
    resp = await recurring_service.action(token, recurring_id, name, due_date or None)
    if resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED):
        return redirect_with_toast(PAGE, MESSAGES[name], "success")
    return redirect_with_toast(PAGE, _detail(resp, "Something went wrong. Nothing was saved."), "error")


async def undo_recurring_run(request: Request, recurring_id: int, due_date: str):
    token = get_current_user(request)
    resp = await recurring_service.undo_run(token, recurring_id, due_date)
    if resp.status_code == status.HTTP_204_NO_CONTENT:
        return redirect_with_toast(PAGE, "Undone", "info")
    return redirect_with_toast(PAGE, _detail(resp, "Could not undo it."), "error")
